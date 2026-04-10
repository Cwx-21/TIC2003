"""
Task 2.6 API Integration Tests — Twitter/X Tweet Stream Ingestion

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


# ─── Health ───────────────────────────────────────────────────────────────────

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


# ─── Ingest ───────────────────────────────────────────────────────────────────

def test_tweet_minimal_ingest():
    """POST with only id and text — the minimum valid tweet payload."""
    body = json.dumps({"id": f"min-{RUN_ID}", "text": "BTC looking bullish today"}).encode()
    status, _, response_body = _request(
        "POST",
        "/api/streams/tweet/ingest",
        body=body,
        headers={"Content-Type": "application/json"},
    )
    assert status == 201
    payload = _parse_json(response_body, "minimal tweet ingest")
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
    body = json.dumps(tweet).encode()
    status, _, response_body = _request(
        "POST",
        f"/api/streams/tweet/ingest?stream_name=pytest-tweets",
        body=body,
        headers={"Content-Type": "application/json", "x-source": f"pytest-{RUN_ID}"},
    )
    assert status == 201
    payload = _parse_json(response_body, "full tweet ingest")
    assert payload["data"]["source"] == f"pytest-{RUN_ID}"
    assert payload["data"]["stream_name"] == "pytest-tweets"
    assert payload["data"]["format"] == "tweet"
    assert payload["data"]["status"] == "accepted"


# ─── Validation (Chain of Responsibility) ─────────────────────────────────────

def test_tweet_validation_missing_id():
    """POST without id field is rejected by TweetRequiredFieldsValidator."""
    body = json.dumps({"text": "no id here"}).encode()
    status, _, response_body = _request(
        "POST",
        "/api/streams/tweet/ingest",
        body=body,
        headers={"Content-Type": "application/json"},
    )
    assert status == 400
    payload = _parse_json(response_body, "missing id rejection")
    assert "id" in payload.get("error", "").lower() or "text" in payload.get("error", "").lower()


def test_tweet_validation_text_too_long():
    """POST with text > 280 chars is rejected by TweetTextLengthValidator."""
    body = json.dumps({"id": "1", "text": "x" * 281}).encode()
    status, _, response_body = _request(
        "POST",
        "/api/streams/tweet/ingest",
        body=body,
        headers={"Content-Type": "application/json"},
    )
    assert status == 400
    payload = _parse_json(response_body, "text length rejection")
    assert "280" in payload.get("error", "")


# ─── Events Query ─────────────────────────────────────────────────────────────

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
