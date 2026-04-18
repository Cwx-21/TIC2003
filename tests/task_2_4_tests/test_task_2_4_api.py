"""
Design Pattern: FACTORY METHOD (Task 2.4)
─────────────────────────────────────────────────────────────────────────────
ApiRequestFactory.for_X() methods return _RequestSpec objects (method + path
+ headers) for each endpoint family. Test functions call the factory instead
of hardcoding HTTP verbs or paths — adding a new endpoint means adding one
factory method, not editing every test.
─────────────────────────────────────────────────────────────────────────────
"""

import json
import os
import time
import urllib.error
import urllib.request

import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")
TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT", "5"))


# ── Low-level helpers ─────────────────────────────────────────────────────────

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


# ── FACTORY METHOD ────────────────────────────────────────────────────────────

class _RequestSpec:
    """
    Value object produced by the factory.
    Holds the method, path, and headers for one API call.
    """
    def __init__(self, method: str, path: str, headers: dict = None):
        self.method  = method
        self.path    = path
        self.headers = headers or {}


class ApiRequestFactory:
    """
    FACTORY METHOD — one factory method per endpoint family.

    Tests call ApiRequestFactory.for_health() etc. instead of hardcoding
    HTTP verbs and paths. The factory is the single source of truth for
    all endpoint definitions — renaming a route only requires one change here.
    """

    @staticmethod
    def for_health() -> _RequestSpec:
        return _RequestSpec("GET", "/")

    @staticmethod
    def for_backtests(limit: int = 10) -> _RequestSpec:
        return _RequestSpec("GET", f"/api/backtests?limit={limit}")

    @staticmethod
    def for_sessions(limit: int = 10) -> _RequestSpec:
        return _RequestSpec("GET", f"/api/sessions?limit={limit}")

    @staticmethod
    def for_alerts(limit: int = 20, **extra_params) -> _RequestSpec:
        qs = f"limit={limit}" + "".join(f"&{k}={v}" for k, v in extra_params.items())
        return _RequestSpec("GET", f"/api/alerts?{qs}")

    @staticmethod
    def for_cors_preflight() -> _RequestSpec:
        return _RequestSpec(
            "OPTIONS",
            "/api/alerts",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )


# ── Tests (factory builds every request spec) ─────────────────────────────────

def test_health_endpoint():
    spec = ApiRequestFactory.for_health()
    status, _, body = _request(spec.method, spec.path, spec.headers)
    payload = _parse_json(body, "health")
    assert status == 200
    assert isinstance(payload, dict)
    assert payload.get("message")


def test_backtests_endpoint():
    spec = ApiRequestFactory.for_backtests()
    status, _, body = _request(spec.method, spec.path, spec.headers)
    payload = _parse_json(body, "backtests")
    assert status == 200
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_sessions_endpoint():
    spec = ApiRequestFactory.for_sessions()
    status, _, body = _request(spec.method, spec.path, spec.headers)
    payload = _parse_json(body, "sessions")
    assert status == 200
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_alerts_endpoint():
    spec = ApiRequestFactory.for_alerts()
    status, _, body = _request(spec.method, spec.path, spec.headers)
    payload = _parse_json(body, "alerts")
    assert status == 200
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_alerts_edge_params():
    spec = ApiRequestFactory.for_alerts(limit=0, backtest_id="abc")
    status, _, body = _request(spec.method, spec.path, spec.headers)
    payload = _parse_json(body, "alerts edge params")
    assert status == 200
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_cors_preflight():
    spec = ApiRequestFactory.for_cors_preflight()
    status, headers, _ = _request(spec.method, spec.path, spec.headers)
    assert status in (200, 204)
    assert headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"


def test_rate_limit_enforced():
    if os.getenv("SKIP_RATE_LIMIT") == "1":
        pytest.skip("Rate limit test skipped by SKIP_RATE_LIMIT=1")

    spec = ApiRequestFactory.for_alerts()
    seen_429 = False
    for _ in range(121):
        status, _, _ = _request(spec.method, spec.path, spec.headers)
        if status == 429:
            seen_429 = True
            break
        time.sleep(0.01)

    assert seen_429, "Expected at least one 429 response after exceeding rate limit."
