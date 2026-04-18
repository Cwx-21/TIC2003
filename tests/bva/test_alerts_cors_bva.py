"""
Boundary Value Analysis (BVA) — Alerts API & CORS Middleware
=============================================================

Target scripts
──────────────
  apps/api/routes/alerts.js          — GET /api/alerts
  apps/api/middleware/cors.js         — origin allow-list
  apps/api/utils/query.js             — parseLimit / parsePositiveInt

BVA rationale: Defects cluster at boundary edges. Testing values
immediately below, exactly at, and just above each boundary catches
off-by-one errors and incorrect operator choices (> vs >=, <= vs <).

Boundaries under test
─────────────────────
1. limit parameter — parseLimit(value, default=100, max=500)
     missing / invalid  → default 100  (200 OK, array returned)
     0                  → default 100  (parsePositiveInt returns null for 0)
     1                  → 1            (minimum valid value)
     499                → 499          (one below max)
     500                → 500          (exactly at max — accepted)
     501                → 500          (one above max — clamped, not rejected)

2. backtest_id / session_id — parsePositiveInt
     "abc" (non-numeric) → ignored (no filter applied, 200 returned)
     0                   → ignored (≤ 0 → null)
     1                   → applied (positive int, 200 returned)
     -1                  → ignored (negative → null)

3. CORS origin allow-list
     http://localhost:5173      → allowed  (Access-Control-Allow-Origin set)
     http://127.0.0.1:5173      → allowed
     http://evil.example.com    → blocked  (no ACAO header)
     no Origin header           → passthrough (server-to-server, 200 returned)
     OPTIONS preflight allowed  → 204 with ACAO header

No existing source files are modified. New file only.
"""

import json
import os
import urllib.error
import urllib.request

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")
TIMEOUT  = float(os.getenv("API_TIMEOUT", "5"))


# ── low-level helpers ─────────────────────────────────────────────────────────

def _get_alerts(params: str = "", origin: str = None) -> tuple[int, dict, dict]:
    """
    GET /api/alerts with optional query string and Origin header.
    Returns (status, parsed_body, response_headers).
    """
    url = f"{BASE_URL}/api/alerts{('?' + params) if params else ''}"
    headers = {}
    if origin is not None:
        headers["Origin"] = origin
    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode()), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode()), dict(exc.headers)
    except urllib.error.URLError as exc:
        raise AssertionError(
            f"API unreachable at {BASE_URL}. Start the API first. ({exc})"
        ) from exc


def _options(path: str, origin: str) -> tuple[int, dict]:
    """OPTIONS preflight for CORS boundary tests."""
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method="OPTIONS", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers)
    except urllib.error.URLError as exc:
        raise AssertionError(f"API unreachable. ({exc})") from exc


# ── Boundary 1 : limit parameter ─────────────────────────────────────────────

class TestAlertsLimitBVA:
    """
    BVA for parseLimit(value, default=100, max=500) on GET /api/alerts.
    All calls expect HTTP 200 and a list under data[].
    The response row count is at most the effective limit.
    """

    def test_limit_missing_uses_default(self):
        """No limit param → default 100 applied. Must return 200 with list."""
        status, body, _ = _get_alerts()
        assert status == 200, f"Expected 200, got {status}"
        assert isinstance(body.get("data"), list)

    def test_limit_zero_uses_default(self):
        """limit=0 → parsePositiveInt returns null → default 100. Must return 200."""
        status, body, _ = _get_alerts("limit=0")
        assert status == 200, f"Expected 200 for limit=0, got {status}"
        assert isinstance(body.get("data"), list)

    def test_limit_1_accepted(self):
        """limit=1 — minimum valid positive value → at most 1 row returned."""
        status, body, _ = _get_alerts("limit=1")
        assert status == 200, f"Expected 200 for limit=1, got {status}"
        assert isinstance(body.get("data"), list)
        assert len(body["data"]) <= 1

    def test_limit_499_accepted(self):
        """limit=499 — one below max → accepted as-is, at most 499 rows."""
        status, body, _ = _get_alerts("limit=499")
        assert status == 200, f"Expected 200 for limit=499, got {status}"
        assert isinstance(body.get("data"), list)
        assert len(body["data"]) <= 499

    def test_limit_500_accepted(self):
        """limit=500 — exactly at max boundary → accepted, at most 500 rows."""
        status, body, _ = _get_alerts("limit=500")
        assert status == 200, f"Expected 200 for limit=500, got {status}"
        assert isinstance(body.get("data"), list)
        assert len(body["data"]) <= 500

    def test_limit_501_clamped_to_500(self):
        """limit=501 — one above max → clamped to 500, NOT rejected (still 200)."""
        status, body, _ = _get_alerts("limit=501")
        assert status == 200, f"Expected 200 for limit=501 (clamped), got {status}"
        assert isinstance(body.get("data"), list)
        assert len(body["data"]) <= 500

    def test_limit_non_numeric_uses_default(self):
        """limit=abc → parseInt returns NaN → default 100. Must return 200."""
        status, body, _ = _get_alerts("limit=abc")
        assert status == 200, f"Expected 200 for non-numeric limit, got {status}"
        assert isinstance(body.get("data"), list)

    def test_limit_negative_uses_default(self):
        """limit=-1 → parsePositiveInt returns null → default 100. Must return 200."""
        status, body, _ = _get_alerts("limit=-1")
        assert status == 200, f"Expected 200 for limit=-1, got {status}"
        assert isinstance(body.get("data"), list)


# ── Boundary 2 : backtest_id / session_id (parsePositiveInt) ─────────────────

class TestAlertsIntegerParamBVA:
    """
    BVA for parsePositiveInt on backtest_id and session_id.
    Rule: parsed <= 0 or NaN → null → filter ignored → full result set returned.
    All calls must return 200 with a list (filter is silently ignored when invalid).
    """

    def test_backtest_id_positive_int_applied(self):
        """backtest_id=1 — valid positive int → filter applied, 200 returned."""
        status, body, _ = _get_alerts("backtest_id=1")
        assert status == 200
        assert isinstance(body.get("data"), list)

    def test_backtest_id_zero_ignored(self):
        """backtest_id=0 — at boundary (≤ 0 → null) → filter ignored, 200 returned."""
        status, body, _ = _get_alerts("backtest_id=0")
        assert status == 200
        assert isinstance(body.get("data"), list)

    def test_backtest_id_negative_ignored(self):
        """backtest_id=-1 — below boundary → filter ignored, 200 returned."""
        status, body, _ = _get_alerts("backtest_id=-1")
        assert status == 200
        assert isinstance(body.get("data"), list)

    def test_backtest_id_non_numeric_ignored(self):
        """backtest_id=abc — non-numeric → filter ignored, 200 returned."""
        status, body, _ = _get_alerts("backtest_id=abc")
        assert status == 200
        assert isinstance(body.get("data"), list)

    def test_session_id_zero_ignored(self):
        """session_id=0 — at boundary → filter ignored, 200 returned."""
        status, body, _ = _get_alerts("session_id=0")
        assert status == 200
        assert isinstance(body.get("data"), list)


# ── Boundary 3 : CORS origin allow-list ──────────────────────────────────────

class TestCORSOriginBVA:
    """
    BVA for the CORS origin allow-list in apps/api/middleware/cors.js.

    Allowed set  : { 'http://localhost:5173', 'http://127.0.0.1:5173' }
    Boundary     : origin in set → Access-Control-Allow-Origin echoed back
                   origin NOT in set → header absent (browser would block)
    """

    def test_localhost_5173_allowed(self):
        """http://localhost:5173 — inside allowed set → ACAO header present."""
        status, _, headers = _get_alerts(origin="http://localhost:5173")
        assert status == 200
        assert "Access-Control-Allow-Origin" in headers, \
            "Expected ACAO header for allowed origin http://localhost:5173"

    def test_127_0_0_1_5173_allowed(self):
        """http://127.0.0.1:5173 — inside allowed set → ACAO header present."""
        status, _, headers = _get_alerts(origin="http://127.0.0.1:5173")
        assert status == 200
        assert "Access-Control-Allow-Origin" in headers, \
            "Expected ACAO header for allowed origin http://127.0.0.1:5173"

    def test_disallowed_origin_blocked(self):
        """http://evil.example.com — outside allowed set → no ACAO header."""
        status, _, headers = _get_alerts(origin="http://evil.example.com")
        assert status == 200  # request still served; browser enforces the block
        assert "Access-Control-Allow-Origin" not in headers, \
            "ACAO header must NOT be set for a disallowed origin"

    def test_no_origin_header_passthrough(self):
        """No Origin header (server-to-server / curl) → always passed through."""
        status, body, _ = _get_alerts()  # no origin kwarg
        assert status == 200
        assert isinstance(body.get("data"), list)

    def test_preflight_allowed_origin_204(self):
        """OPTIONS preflight from allowed origin → ACAO header present."""
        status, headers = _options("/api/alerts", origin="http://localhost:5173")
        assert status in (200, 204), f"Preflight expected 200/204, got {status}"
        assert "Access-Control-Allow-Origin" in headers, \
            "Preflight response must include ACAO header for allowed origin"
