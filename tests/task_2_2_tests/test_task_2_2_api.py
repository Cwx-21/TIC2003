"""
Design Pattern: FACADE (Task 2.2)
Reference: https://www.geeksforgeeks.org/facade-design-pattern-introduction/
─────────────────────────────────────────────────────────────────────────────
ApiClientFacade hides the two-step (_request + _parse_json) behind a single
get() call. Test functions are the "clients" — they call facade.get() and
receive a ready-to-assert (status, headers, payload) tuple without knowing
anything about urllib or JSON parsing internals.
─────────────────────────────────────────────────────────────────────────────
"""

import json
import os
import urllib.error
import urllib.request

import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")
TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT", "5"))


# ── Low-level helpers (used internally by the facade) ────────────────────────

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


# ── FACADE ────────────────────────────────────────────────────────────────────

class ApiClientFacade:
    """
    FACADE — single entry-point for all test HTTP calls.

    Hides urllib request construction and JSON parsing behind a clean get()
    method. Test functions never touch _request or _parse_json directly;
    the facade composes both steps internally.

    Adding a new HTTP method (e.g. post()) only requires one change here —
    not in every test function.
    """

    def __init__(self, base_url: str, timeout: float):
        self._base_url = base_url
        self._timeout  = timeout

    def get(self, path: str):
        """GET an endpoint → returns (status, headers, parsed_payload)."""
        status, headers, body = _request("GET", path)
        return status, headers, _parse_json(body, path)


# Singleton facade — one instance shared across all tests
_client = ApiClientFacade(BASE_URL, TIMEOUT_SECONDS)


# ── Tests (use facade — no raw _request / _parse_json calls) ─────────────────

def test_assets_endpoint():
    status, _, payload = _client.get("/api/assets?limit=5")
    assert status == 200
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_assets_filters():
    status, _, payload = _client.get("/api/assets?type=crypto&active=true")
    assert status == 200
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_sentiment_endpoint():
    status, _, payload = _client.get("/api/sentiment/BTC?limit=10")
    assert status == 200
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_prices_endpoint():
    status, _, payload = _client.get("/api/prices/BTC?limit=10")
    assert status == 200
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_correlation_endpoint():
    status, _, payload = _client.get("/api/correlation/BTC?limit=10")
    assert status == 200
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)
