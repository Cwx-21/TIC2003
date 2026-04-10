"""
Task 2.6 Standalone Checker — Twitter/X Tweet Stream Ingestion

Runs five sequential smoke tests against the live API without any external
test framework. Exit codes mirror the Task 2.5 convention:
  0 — all checks passed
  2 — API unreachable
  3 — invalid JSON response
  4 — unexpected HTTP status
  5 — response body missing expected field

Run with: python3 task_2_6_tests/main.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")
TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT", "5"))
RUN_ID = str(int(time.time() * 1000))


def request(method, path, body=None, headers=None):
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
            payload = resp.read().decode("utf-8")
            return resp.status, dict(resp.headers), payload
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        return exc.code, dict(exc.headers), payload
    except urllib.error.URLError as exc:
        print(f"API unreachable at {BASE_URL}. Start the API first. ({exc})")
        sys.exit(2)


def parse_json(body, label):
    """
    Parses a JSON response body, exiting on failure.

    Args:
        body (str): Raw response body string.
        label (str): Label printed in the error message.

    Returns:
        dict | list: Parsed JSON value.
    """
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        print(f"Invalid JSON for {label}.")
        sys.exit(3)


def check(status, expected, label):
    """Exits with code 4 if status does not match expected."""
    if status != expected:
        print(f"{label} failed: expected {expected}, got {status}")
        sys.exit(4)


def main():
    # 1. Tweet endpoint health
    status, _, body = request("GET", "/api/streams/tweet/health")
    check(status, 200, "Tweet health")
    payload = parse_json(body, "Tweet health")
    if payload.get("data", {}).get("format") != "tweet":
        print("Tweet health failed: format field missing or wrong")
        sys.exit(5)

    # 2. Minimal tweet ingest (id + text only)
    minimal_body = json.dumps({"id": f"main-min-{RUN_ID}", "text": "BTC looking bullish"}).encode()
    status, _, body = request(
        "POST",
        "/api/streams/tweet/ingest",
        body=minimal_body,
        headers={"Content-Type": "application/json"},
    )
    check(status, 201, "Minimal tweet ingest")
    payload = parse_json(body, "Minimal tweet ingest")
    if payload.get("data", {}).get("format") != "tweet":
        print("Minimal tweet ingest failed: wrong format in response")
        sys.exit(5)

    # 3. Full tweet ingest with metrics and entities
    full_tweet = {
        "id": f"main-full-{RUN_ID}",
        "text": "Ethereum gas fees are dropping #ETH",
        "author_id": "111222333",
        "created_at": "2026-04-06T00:00:00.000Z",
        "public_metrics": {"retweet_count": 2, "like_count": 10, "reply_count": 1, "quote_count": 0},
        "entities": {"hashtags": [{"tag": "ETH"}], "mentions": [], "urls": []},
    }
    full_body = json.dumps(full_tweet).encode()
    status, _, body = request(
        "POST",
        f"/api/streams/tweet/ingest?stream_name=main-tweets",
        body=full_body,
        headers={"Content-Type": "application/json", "x-source": f"main-{RUN_ID}"},
    )
    check(status, 201, "Full tweet ingest")

    # 4. Validation rejection — missing id field
    bad_body = json.dumps({"text": "no id here"}).encode()
    status, _, body = request(
        "POST",
        "/api/streams/tweet/ingest",
        body=bad_body,
        headers={"Content-Type": "application/json"},
    )
    check(status, 400, "Validation rejection (missing id)")

    # 5. Events query filtered by tweet format
    status, _, body = request(
        "GET",
        f"/api/streams/events?format=tweet&source=main-{RUN_ID}&limit=5",
    )
    check(status, 200, "Tweet events query")
    payload = parse_json(body, "Tweet events query")
    if not isinstance(payload.get("data"), list):
        print("Tweet events query failed: data is not a list")
        sys.exit(5)

    print("Task 2.6 checks passed.")


if __name__ == "__main__":
    main()
