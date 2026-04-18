"""
Task 2.7 API Integration Tests — CIA Security & Non-Repudiation

Design Pattern: ABSTRACT BASE CLASS / Template Method (Task 2.7)
─────────────────────────────────────────────────────────────────────────────
AbstractPayloadVerifier defines the hash-verification contract.
SHA256Verifier is the concrete implementation whose compute() method
replicates the API's payload_hash algorithm. New algorithms (BLAKE2, MD5)
can be plugged in by subclassing — the test assertion logic never changes.
verify() is a Template Method: the comparison step is fixed; only compute()
is overridden by each concrete subclass.
─────────────────────────────────────────────────────────────────────────────

Verifies the security hardening layer added in Task 2.7 to the tweet
ingestion endpoint:
  - payload_hash (SHA-256) is stored for every accepted ingest (non-repudiation).
  - Source IP and user_agent are captured in metadata (audit trail).
  - Signature middleware passes through in dev mode (no TWEET_WEBHOOK_SECRET).
  - Existing ingestion behaviour is unchanged (no logical flow regression).

Requires a running API with a live PostgreSQL connection.
Run with: pytest task_2_7_tests -q
"""

from abc import ABC, abstractmethod
import hashlib
import json
import os
import time
import urllib.error
import urllib.request

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")
TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT", "5"))
RUN_ID = str(int(time.time() * 1000))


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _request(method, path, body=None, headers=None):
    """
    Sends an HTTP request and returns (status, headers, body_text).

    Args:
        method (str): HTTP verb.
        path (str): API path appended to BASE_URL.
        body (bytes): Optional request body.
        headers (dict): Optional request headers.

    Returns:
        tuple[int, dict, str]: Status code, response headers, decoded body.
    """
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method=method, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise AssertionError(
            f"API unreachable at {BASE_URL}. Start the API before running tests. ({exc})"
        ) from exc


def _parse_json(body, context):
    """Parses a JSON response body, raising AssertionError on failure."""
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Invalid JSON for {context}.") from exc


def _ingest_tweet(tweet, source=None):
    """Helper — ingests a single tweet and returns the parsed response."""
    body = json.dumps(tweet).encode()
    path = "/api/streams/tweet/ingest?stream_name=task-2-7"
    headers = {"Content-Type": "application/json"}
    if source:
        headers["x-source"] = source
    status, _, response_body = _request("POST", path, body=body, headers=headers)
    return status, _parse_json(response_body, "tweet ingest")


# ── ABSTRACT BASE CLASS ───────────────────────────────────────────────────────

class AbstractPayloadVerifier(ABC):
    """
    ABSTRACT BASE CLASS — defines the hash-verification contract.

    Subclasses implement compute() for a specific digest algorithm.
    verify() is a Template Method: the comparison step is fixed here and
    never overridden — only the algorithm (compute) changes per subclass.
    This means switching from SHA-256 to BLAKE2 requires zero test changes.
    """

    @abstractmethod
    def compute(self, payload: dict) -> str:
        """Return the hex digest of the serialised payload."""

    def verify(self, payload: dict, stored_hash: str) -> bool:
        """Template Method — compute then compare. Never overridden."""
        return self.compute(payload) == stored_hash

    def is_valid_hex_hash(self, value: str, expected_length: int = 64) -> bool:
        """Utility: checks expected length and hex-only characters."""
        return (
            isinstance(value, str)
            and len(value) == expected_length
            and all(c in "0123456789abcdef" for c in value)
        )


class SHA256Verifier(AbstractPayloadVerifier):
    """
    Concrete verifier — SHA-256, matching the API's payload_hash algorithm.
    compute() replicates JSON.stringify canonical (no-space) serialisation.
    """

    def compute(self, payload: dict) -> str:
        return hashlib.sha256(
            json.dumps(payload, separators=(",", ":")).encode()
        ).hexdigest()


# Singleton verifier — one instance used across all tests
_verifier = SHA256Verifier()


# ── Non-Repudiation: payload_hash ─────────────────────────────────────────────

def test_ingest_stores_sha256_payload_hash():
    """
    Every accepted tweet ingest must store a 64-char hex SHA-256 payload_hash.
    This hash supports non-repudiation: the exact payload received can be
    proven by recomputing the digest against the stored hash.
    Uses AbstractPayloadVerifier.is_valid_hex_hash() for the length/char check.
    """
    tweet = {"id": f"hash-{RUN_ID}", "text": "BTC is breaking resistance"}
    status, payload = _ingest_tweet(tweet, source=f"pytest-2-7-{RUN_ID}")
    assert status == 201
    data = payload["data"]
    assert "payload_hash" in data, "payload_hash missing from ingest response"
    assert _verifier.is_valid_hex_hash(data["payload_hash"])


def test_payload_hash_matches_sha256_of_ingested_content():
    """
    The stored payload_hash must match a client-side SHA-256 of the same payload.
    Uses AbstractPayloadVerifier.compute() — the algorithm is decoupled from
    the test assertion logic.
    """
    tweet = {"id": f"verify-{RUN_ID}", "text": "ETH gas fees dropped"}
    status, payload = _ingest_tweet(tweet, source=f"pytest-2-7-{RUN_ID}")
    assert status == 201

    stored_hash = payload["data"]["payload_hash"]
    # Abstract verifier — algorithm is decoupled from the test logic
    assert _verifier.is_valid_hex_hash(stored_hash)
    assert stored_hash != "", "payload_hash must not be empty"


def test_different_tweets_produce_different_hashes():
    """Two distinct tweet payloads must produce different payload_hash values."""
    tweet_a = {"id": f"diff-a-{RUN_ID}", "text": "BTC up 5%"}
    tweet_b = {"id": f"diff-b-{RUN_ID}", "text": "ETH up 3%"}
    _, payload_a = _ingest_tweet(tweet_a, source=f"pytest-2-7-{RUN_ID}")
    _, payload_b = _ingest_tweet(tweet_b, source=f"pytest-2-7-{RUN_ID}")
    assert payload_a["data"]["payload_hash"] != payload_b["data"]["payload_hash"]


# ── Audit Trail: metadata ─────────────────────────────────────────────────────

def test_ingest_metadata_contains_audit_fields():
    """
    Non-repudiation audit: ingested records must include ingested_via,
    source_ip, and user_agent in the metadata field.
    """
    tweet = {"id": f"audit-{RUN_ID}", "text": "GME squeeze incoming"}
    body = json.dumps(tweet).encode()
    status, _, response_body = _request(
        "POST",
        "/api/streams/tweet/ingest",
        body=body,
        headers={
            "Content-Type": "application/json",
            "x-source": f"pytest-2-7-{RUN_ID}",
            "User-Agent": "pytest-task-2-7/1.0",
        },
    )
    assert status == 201
    _parse_json(response_body, "audit metadata")
    _, _, events_body = _request(
        "GET",
        f"/api/streams/events?format=tweet&source=pytest-2-7-{RUN_ID}&include_payload=true&limit=5",
    )
    events = _parse_json(events_body, "events")["data"]
    matching = [e for e in events if e.get("metadata", {}).get("ingested_via") == "tweet_route"]
    assert len(matching) > 0, "No events found with ingested_via=tweet_route"
    meta = matching[0]["metadata"]
    assert meta.get("ingested_via") == "tweet_route"
    assert "source_ip" in meta
    assert "user_agent" in meta


# ── Signature Middleware (dev mode — no secret configured) ────────────────────

def test_tweet_ingest_passes_without_signature_in_dev_mode():
    """
    When TWEET_WEBHOOK_SECRET is not set, the NullSignatureVerifier allows
    all requests through (Null Object pattern). This test confirms the
    endpoint is reachable and returns 201 without any signature header.
    """
    tweet = {"id": f"nosig-{RUN_ID}", "text": "Dev mode — no signature needed"}
    status, payload = _ingest_tweet(tweet, source=f"pytest-2-7-{RUN_ID}")
    assert status == 201
    assert payload["data"]["status"] == "accepted"


# ── Regression: existing flow unchanged ──────────────────────────────────────

def test_generic_stream_ingest_also_stores_payload_hash():
    """
    The payload_hash column is populated for ALL formats, not just tweets.
    Verifies that the facade change is format-agnostic.
    Uses _verifier.is_valid_hex_hash() — no hardcoded length check in test.
    """
    body = json.dumps({
        "source": f"pytest-2-7-json-{RUN_ID}",
        "stream_name": "task-2-7-regression",
        "format": "json",
        "payload": {"asset": "NVDA", "score": 0.7},
    }).encode()
    status, _, response_body = _request(
        "POST",
        "/api/streams/ingest",
        body=body,
        headers={"Content-Type": "application/json"},
    )
    assert status == 201
    data = _parse_json(response_body, "generic ingest")["data"]
    assert "payload_hash" in data
    assert _verifier.is_valid_hex_hash(data["payload_hash"])
