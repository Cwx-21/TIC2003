import json
import os
import time
import urllib.error
import urllib.request

import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")
TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT", "5"))


def _request(method, path, headers=None):
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
        raise AssertionError(
            f"API unreachable at {BASE_URL}. Start the API before running tests. ({exc})"
        ) from exc


def _parse_json(body, context):
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Invalid JSON for {context}.") from exc


def test_health_endpoint():
    status, _, body = _request("GET", "/")
    assert status == 200
    payload = _parse_json(body, "health")
    assert isinstance(payload, dict)
    assert payload.get("message")


def test_backtests_endpoint():
    status, _, body = _request("GET", "/api/backtests?limit=10")
    assert status == 200
    payload = _parse_json(body, "backtests")
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_sessions_endpoint():
    status, _, body = _request("GET", "/api/sessions?limit=10")
    assert status == 200
    payload = _parse_json(body, "sessions")
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_alerts_endpoint():
    status, _, body = _request("GET", "/api/alerts?limit=20")
    assert status == 200
    payload = _parse_json(body, "alerts")
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_alerts_edge_params():
    status, _, body = _request("GET", "/api/alerts?limit=0&backtest_id=abc")
    assert status == 200
    payload = _parse_json(body, "alerts edge params")
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_cors_preflight():
    status, headers, _ = _request(
        "OPTIONS",
        "/api/alerts",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert status in (200, 204)
    assert headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"


def test_rate_limit_enforced():
    if os.getenv("SKIP_RATE_LIMIT") == "1":
        pytest.skip("Rate limit test skipped by SKIP_RATE_LIMIT=1")

    seen_429 = False
    for _ in range(121):
        status, _, _ = _request("GET", "/api/alerts")
        if status == 429:
            seen_429 = True
            break
        time.sleep(0.01)

    assert seen_429, "Expected at least one 429 response after exceeding rate limit."
