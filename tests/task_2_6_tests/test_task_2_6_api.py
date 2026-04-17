"""
Task 2.6 API Integration Tests — Twitter/X Tweet Stream Ingestion

Design Pattern: OBSERVER (Task 2.6)
─────────────────────────────────────────────────────────────────────────────
TweetIngestClient (Subject) sends tweet ingest requests and notifies all
registered observers after every response. AssertionObserver (Concrete
Observer) records each result. New observers (Slack notifier, metric counter)
can be plugged in without touching any test logic.
─────────────────────────────────────────────────────────────────────────────

Covers the two new endpoints introduced in Task 2.6:
  GET  /api/streams/tweet/health  — reports tweet endpoint configuration.
  POST /api/streams/tweet/ingest  — validates, parses, and persists tweet payloads.

Requires the API to be running with a live PostgreSQL connection before execution.
Run with: pytest task_2_6_tests -q
"""

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
        method (str): HTTP verb (GET, POST).
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
            payload = resp.read().decode("utf-8")
            return resp.status, dict(resp.headers), payload
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        return exc.code, dict(exc.headers), payload
    except urllib.error.URLError as exc:
        raise AssertionError(
            f"API unreachable at {BASE_URL}. Start the API before running tests. ({exc})"
        ) from exc


def _parse_json(body, context):
    """
    Parses a JSON response body, raising AssertionError on failure.

    Args:
        body (str): Raw response body string.
        context (str): Label used in the error message.

    Returns:
        dict | list: Parsed JSON value.
    """
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Invalid JSON for {context}.") from exc


# ── OBSERVER ──────────────────────────────────────────────────────────────────

class IngestResultObserver:
    """
    Observer interface — subclasses implement on_result().

    The Subject (TweetIngestClient) calls on_result() after every POST.
    New side-effects (logging, metrics, alerts) are added as new subclasses —
    no existing code changes.
    """
    def on_result(self, status: int, payload: dict):
        raise NotImplementedError("on_result() must be implemented by subclass")


class AssertionObserver(IngestResultObserver):
    """
    Concrete Observer — records every ingest response.

    Tests can inspect .results or call .latest() / .accepted_count()
    for cross-test state without coupling individual test functions.
    """

    def __init__(self):
        self.results: list = []

    def on_result(self, status: int, payload: dict):
        self.results.append({"status": status, "payload": payload})

    def latest(self):
        return self.results[-1] if self.results else None

    def accepted_count(self) -> int:
        return sum(
            1 for r in self.results
            if r["payload"].get("data", {}).get("status") == "accepted"
        )


class TweetIngestClient:
    """
    Subject — sends tweet ingest POST requests and notifies all observers.

    Tests subscribe observers once at module level, then call ingest() —
    the client handles HTTP and observer notification automatically.
    """

    def __init__(self):
        self._observers: list = []

    def subscribe(self, observer: IngestResultObserver):
        """Register a new observer."""
        self._observers.append(observer)

    def unsubscribe(self, observer: IngestResultObserver):
        """Remove a previously registered observer."""
        self._observers = [o for o in self._observers if o is not observer]

    def ingest(self, tweet: dict, path_suffix: str = "", extra_headers: dict = None):
        """
        POST a tweet payload → notifies observers → returns (status, payload).
        path_suffix appends query params, e.g. '?stream_name=pytest-tweets'.
        """
        body = json.dumps(tweet).encode()
        path = f"/api/streams/tweet/ingest{path_suffix}"
        headers = {"Content-Type": "application/json", **(extra_headers or {})}
        status, _, response_body = _request("POST", path, body=body, headers=headers)
        payload = _parse_json(response_body, "tweet ingest")
        for obs in self._observers:
            obs.on_result(status, payload)
        return status, payload


# Subject + Observer wired once — shared across all tests
_observer = AssertionObserver()
_tweet_client = TweetIngestClient()
_tweet_client.subscribe(_observer)


# ── Health ────────────────────────────────────────────────────────────────────

def test_tweet_health_endpoint():
    """GET /api/streams/tweet/health returns the tweet endpoint configuration."""
    status, _, body = _request("GET", "/api/streams/tweet/health")
    assert status == 200
    payload = _parse_json(body, "tweet health")
    data = payload.get("data", {})
    assert data.get("format") == "tweet"
    assert data.get("structure_kind") == "semi_structured"
    assert isinstance(data.get("validation_chain"), list)
    assert len(data["validation_chain"]) == 3


# ── Ingest (uses Observer Subject) ────────────────────────────────────────────

def test_tweet_minimal_ingest():
    """POST with only id and text — the minimum valid tweet payload."""
    status, payload = _tweet_client.ingest(
        {"id": f"min-{RUN_ID}", "text": "BTC looking bullish today"}
    )
    assert status == 201
    assert payload["data"]["format"] == "tweet"
    assert payload["data"]["structure_kind"] == "semi_structured"
    assert payload["data"]["parser_key"] == "tweet_parser"
    assert payload["data"]["record_count"] == 1


def test_tweet_full_ingest():
    """POST with all Twitter API v2 fields including metrics and entities."""
    tweet = {
        "id": f"full-{RUN_ID}",
        "text": "Bitcoin is going to the moon! #BTC #crypto",
        "author_id": "987654321",
        "created_at": "2026-04-06T00:00:00.000Z",
        "public_metrics": {
            "retweet_count": 5,
            "like_count": 23,
            "reply_count": 2,
            "quote_count": 1,
        },
        "entities": {
            "hashtags": [{"tag": "BTC"}, {"tag": "crypto"}],
            "mentions": [],
            "urls": [],
        },
    }
    status, payload = _tweet_client.ingest(
        tweet,
        path_suffix="?stream_name=pytest-tweets",
        extra_headers={"x-source": f"pytest-{RUN_ID}"},
    )
    assert status == 201
    assert payload["data"]["source"] == f"pytest-{RUN_ID}"
    assert payload["data"]["stream_name"] == "pytest-tweets"
    assert payload["data"]["format"] == "tweet"
    assert payload["data"]["status"] == "accepted"


# ── Validation (Chain of Responsibility) ──────────────────────────────────────

def test_tweet_validation_missing_id():
    """POST without id field is rejected by TweetRequiredFieldsValidator."""
    status, payload = _tweet_client.ingest({"text": "no id here"})
    assert status == 400
    assert "id" in payload.get("error", "").lower() or "text" in payload.get("error", "").lower()


def test_tweet_validation_text_too_long():
    """POST with text > 280 chars is rejected by TweetTextLengthValidator."""
    status, payload = _tweet_client.ingest({"id": "1", "text": "x" * 281})
    assert status == 400
    assert "280" in payload.get("error", "")


# ── Events Query ──────────────────────────────────────────────────────────────

def test_tweet_events_queryable_by_format():
    """GET /api/streams/events?format=tweet returns the ingested tweet records."""
    status, _, body = _request(
        "GET",
        f"/api/streams/events?format=tweet&source=pytest-{RUN_ID}&limit=5",
    )
    assert status == 200
    payload = _parse_json(body, "tweet events query")
    assert isinstance(payload.get("data"), list)
    assert any(row["format"] == "tweet" for row in payload["data"])
