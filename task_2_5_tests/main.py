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
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        print(f"Invalid JSON for {label}.")
        sys.exit(3)


def check(status, expected, label):
    if status != expected:
        print(f"{label} failed: expected {expected}, got {status}")
        sys.exit(4)


def main():
    status, _, body = request("GET", "/api/streams/health")
    check(status, 200, "Streams health")
    payload = parse_json(body, "Streams health")
    if "supported_formats" not in payload.get("data", {}):
        print("Streams health failed: supported_formats missing")
        sys.exit(5)

    json_body = json.dumps(
        {
            "source": f"main-json-{RUN_ID}",
            "stream_name": "task-2-5-main",
            "format": "json",
            "metadata": {"runner": "main.py"},
            "payload": [{"asset": "BTC", "score": 0.88}],
        }
    ).encode("utf-8")
    status, _, body = request(
        "POST",
        "/api/streams/ingest",
        body=json_body,
        headers={"Content-Type": "application/json"},
    )
    check(status, 201, "JSON ingest")
    payload = parse_json(body, "JSON ingest")
    if payload.get("data", {}).get("format") != "json":
        print("JSON ingest failed: wrong format")
        sys.exit(6)

    csv_body = "symbol,price\nBTC,65000".encode("utf-8")
    status, _, body = request(
        "POST",
        f"/api/streams/ingest?source=main-csv-{RUN_ID}&stream_name=task-2-5-main&format=csv",
        body=csv_body,
        headers={"Content-Type": "text/csv"},
    )
    check(status, 201, "CSV ingest")

    status, _, body = request("GET", f"/api/streams/events?source=main-json-{RUN_ID}&limit=5")
    check(status, 200, "Streams events")
    payload = parse_json(body, "Streams events")
    if not isinstance(payload.get("data"), list):
        print("Streams events failed: data is not a list")
        sys.exit(7)

    print("Task 2.5 checks passed.")


if __name__ == "__main__":
    main()
