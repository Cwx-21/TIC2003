import json
import os
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


def test_assets_endpoint():
    status, _, body = _request("GET", "/api/assets?limit=5")
    assert status == 200
    payload = _parse_json(body, "assets")
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_assets_filters():
    status, _, body = _request("GET", "/api/assets?type=crypto&active=true")
    assert status == 200
    payload = _parse_json(body, "assets filters")
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_sentiment_endpoint():
    status, _, body = _request("GET", "/api/sentiment/BTC?limit=10")
    assert status == 200
    payload = _parse_json(body, "sentiment")
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_prices_endpoint():
    status, _, body = _request("GET", "/api/prices/BTC?limit=10")
    assert status == 200
    payload = _parse_json(body, "prices")
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)


def test_correlation_endpoint():
    status, _, body = _request("GET", "/api/correlation/BTC?limit=10")
    assert status == 200
    payload = _parse_json(body, "correlation")
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), list)
