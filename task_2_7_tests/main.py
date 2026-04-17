"""
Task 2.7 Standalone Checker — CIA Security & Non-Repudiation

Runs sequential smoke tests verifying that the Task 2.7 security layer is
correctly wired into the live API. No external dependencies required.

Exit codes:
  0 — all checks passed
  2 — API unreachable
  3 — invalid JSON response
  4 — unexpected HTTP status
  5 — expected field missing or wrong value

Run with: python3 task_2_7_tests/main.py
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
    """Sends an HTTP request. Exits with code 2 if the API is unreachable."""
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method=method, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read().decode("utf-8")
    except urllib.error.URLError as exc:
        print(f"API unreachable at {BASE_URL}. Start the API first. ({exc})")
        sys.exit(2)


def parse_json(body, label):
    """Parses JSON or exits with code 3."""
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
    # 1. Tweet ingest stores payload_hash (non-repudiation)
    tweet = {"id": f"main-hash-{RUN_ID}", "text": "BTC holds support level"}
    body = json.dumps(tweet).encode()
    status, _, response_body = request(
        "POST",
        "/api/streams/tweet/ingest",
        body=body,
        headers={"Content-Type": "application/json", "x-source": f"main-2-7-{RUN_ID}"},
    )
    check(status, 201, "Tweet ingest (non-repudiation hash)")
    data = parse_json(response_body, "Tweet ingest")["data"]
    if "payload_hash" not in data or len(data.get("payload_hash", "")) != 64:
        print("Non-repudiation check failed: payload_hash missing or not 64 chars")
        sys.exit(5)

    # 2. No-signature dev mode passes (NullSignatureVerifier)
    tweet2 = {"id": f"main-nosig-{RUN_ID}", "text": "Dev mode test"}
    body2 = json.dumps(tweet2).encode()
    status, _, _ = request(
        "POST",
        "/api/streams/tweet/ingest",
        body=body2,
        headers={"Content-Type": "application/json"},
    )
    check(status, 201, "NullSignatureVerifier pass-through")

    # 3. Generic stream ingest also stores payload_hash (format-agnostic)
    generic_body = json.dumps({
        "source": f"main-2-7-generic-{RUN_ID}",
        "format": "json",
        "payload": {"asset": "ETH", "score": 0.65},
    }).encode()
    status, _, response_body = request(
        "POST",
        "/api/streams/ingest",
        body=generic_body,
        headers={"Content-Type": "application/json"},
    )
    check(status, 201, "Generic ingest (payload_hash regression)")
    data = parse_json(response_body, "Generic ingest")["data"]
    if len(data.get("payload_hash", "")) != 64:
        print("Regression check failed: generic ingest missing payload_hash")
        sys.exit(5)

    # 4. Events list includes payload_hash in response
    status, _, response_body = request(
        "GET",
        f"/api/streams/events?source=main-2-7-{RUN_ID}&limit=5",
    )
    check(status, 200, "Events list with payload_hash")
    events = parse_json(response_body, "Events list")["data"]
    if not events or "payload_hash" not in events[0]:
        print("Events list check failed: payload_hash not present in event rows")
        sys.exit(5)

    print("Task 2.7 checks passed.")


if __name__ == "__main__":
    main()
