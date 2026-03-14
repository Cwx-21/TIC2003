import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")
TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT", "5"))


def request(method, path, headers=None):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, dict(resp.headers), body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, dict(exc.headers), body
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
    # Task 2.4 checks (health, backtests, sessions, alerts, CORS)
    status, _, body = request("GET", "/")
    check(status, 200, "Health")
    parse_json(body, "Health")

    status, _, body = request("GET", "/api/backtests?limit=10")
    check(status, 200, "Backtests")
    payload = parse_json(body, "Backtests")
    if not isinstance(payload.get("data"), list):
        print("Backtests failed: data is not a list")
        sys.exit(5)

    status, _, body = request("GET", "/api/sessions?limit=10")
    check(status, 200, "Sessions")
    payload = parse_json(body, "Sessions")
    if not isinstance(payload.get("data"), list):
        print("Sessions failed: data is not a list")
        sys.exit(6)

    status, _, body = request("GET", "/api/alerts?limit=20")
    check(status, 200, "Alerts")
    payload = parse_json(body, "Alerts")
    if not isinstance(payload.get("data"), list):
        print("Alerts failed: data is not a list")
        sys.exit(7)

    status, headers, _ = request(
        "OPTIONS",
        "/api/alerts",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    if status not in (200, 204):
        print(f"CORS preflight failed: status {status}")
        sys.exit(8)

    if headers.get("Access-Control-Allow-Origin") != "http://localhost:5173":
        print("CORS preflight failed: origin not allowed")
        sys.exit(9)

    # Task 2.2 checks (assets, sentiment, prices, correlation)
    status, _, body = request("GET", "/api/assets?limit=5")
    check(status, 200, "Assets")
    payload = parse_json(body, "Assets")
    if not isinstance(payload.get("data"), list):
        print("Assets failed: data is not a list")
        sys.exit(10)

    status, _, body = request("GET", "/api/sentiment/BTC?limit=10")
    check(status, 200, "Sentiment")
    payload = parse_json(body, "Sentiment")
    if not isinstance(payload.get("data"), list):
        print("Sentiment failed: data is not a list")
        sys.exit(11)

    status, _, body = request("GET", "/api/prices/BTC?limit=10")
    check(status, 200, "Prices")
    payload = parse_json(body, "Prices")
    if not isinstance(payload.get("data"), list):
        print("Prices failed: data is not a list")
        sys.exit(12)

    status, _, body = request("GET", "/api/correlation/BTC?limit=10")
    check(status, 200, "Correlation")
    payload = parse_json(body, "Correlation")
    if not isinstance(payload.get("data"), list):
        print("Correlation failed: data is not a list")
        sys.exit(13)

    print("Task 2.2 and Task 2.4 checks passed.")


if __name__ == "__main__":
    main()
