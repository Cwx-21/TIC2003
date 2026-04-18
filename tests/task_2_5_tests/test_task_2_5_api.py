"""
Design Pattern: COMMAND (Task 2.5)
─────────────────────────────────────────────────────────────────────────────
Each stream ingest is encapsulated as a StreamIngestCommand. The test function
is the Invoker — it calls cmd.execute() without knowing how the body or
headers for JSON, CSV, XML, TXT, or XLSX are assembled. StreamCommandBuilder
is the factory that creates the right command for each format.
─────────────────────────────────────────────────────────────────────────────
"""

import json
import os
import time
import urllib.error
import urllib.request

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")
TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT", "5"))
RUN_ID = str(int(time.time() * 1000))


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _request(method, path, body=None, headers=None):
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
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Invalid JSON for {context}.") from exc


# ── COMMAND ───────────────────────────────────────────────────────────────────

class StreamIngestCommand:
    """
    COMMAND — encapsulates a single stream ingest POST request.

    The Invoker (test function) calls execute() without knowing how the
    body or Content-Type header is assembled for each format. The result
    is cached in self._result so it can be inspected after execution.
    """

    def __init__(self, path: str, body: bytes, headers: dict):
        self._path    = path
        self._body    = body
        self._headers = headers
        self._result  = None

    def execute(self):
        """Run the ingest → returns (status, parsed_payload)."""
        status, _, response_body = _request(
            "POST", self._path, body=self._body, headers=self._headers
        )
        self._result = (status, _parse_json(response_body, self._path))
        return self._result

    @property
    def result(self):
        """Cached result after execute(). Raises if execute() not yet called."""
        if self._result is None:
            raise RuntimeError("StreamIngestCommand: execute() has not been called yet")
        return self._result


class StreamCommandBuilder:
    """
    Builds a StreamIngestCommand for each supported stream format.

    Centralises body + header construction. Tests pick a builder method and
    receive an executable command — they never construct bytes or Content-Type
    strings directly.
    """

    @staticmethod
    def json_ingest(run_id: str) -> StreamIngestCommand:
        body = json.dumps({
            "source": f"pytest-json-{run_id}",
            "stream_name": "task-2-5-json",
            "format": "json",
            "metadata": {"suite": "task_2_5"},
            "payload": [
                {"asset": "BTC", "score": 0.91},
                {"asset": "ETH", "score": 0.78},
            ],
        }).encode("utf-8")
        return StreamIngestCommand(
            "/api/streams/ingest", body, {"Content-Type": "application/json"}
        )

    @staticmethod
    def csv_ingest(run_id: str) -> StreamIngestCommand:
        body = "symbol,price\nBTC,65000\nETH,3000".encode("utf-8")
        path = f"/api/streams/ingest?source=pytest-csv-{run_id}&stream_name=csv-suite&format=csv"
        return StreamIngestCommand(path, body, {"Content-Type": "text/csv"})

    @staticmethod
    def xml_ingest(run_id: str) -> StreamIngestCommand:
        body = "<feed><asset symbol='BTC'>bullish</asset></feed>".encode("utf-8")
        path = f"/api/streams/ingest?source=pytest-xml-{run_id}&stream_name=xml-suite&format=xml"
        return StreamIngestCommand(path, body, {"Content-Type": "application/xml"})

    @staticmethod
    def text_ingest(run_id: str) -> StreamIngestCommand:
        body = "Trader notes\nPotential breakout\nWatch BTC volume".encode("utf-8")
        path = f"/api/streams/ingest?source=pytest-text-{run_id}&stream_name=text-suite&format=txt"
        return StreamIngestCommand(path, body, {"Content-Type": "text/plain"})

    @staticmethod
    def xlsx_ingest(run_id: str) -> StreamIngestCommand:
        body = b"PK\x03\x04mock-xlsx-payload"
        path = f"/api/streams/ingest?source=pytest-xlsx-{run_id}&stream_name=xlsx-suite&format=xlsx"
        return StreamIngestCommand(
            path,
            body,
            {"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        )


# ── Tests (Invoker — calls cmd.execute() only) ────────────────────────────────

def test_streams_health_endpoint():
    status, _, body = _request("GET", "/api/streams/health")
    assert status == 200
    payload = _parse_json(body, "streams health")
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), dict)
    assert "supported_formats" in payload["data"]


def test_json_stream_ingestion():
    status, payload = StreamCommandBuilder.json_ingest(RUN_ID).execute()
    assert status == 201
    assert payload["data"]["format"] == "json"
    assert payload["data"]["record_count"] == 2


def test_csv_stream_ingestion():
    status, payload = StreamCommandBuilder.csv_ingest(RUN_ID).execute()
    assert status == 201
    assert payload["data"]["format"] == "csv"
    assert payload["data"]["record_count"] == 2


def test_xml_stream_ingestion():
    status, payload = StreamCommandBuilder.xml_ingest(RUN_ID).execute()
    assert status == 201
    assert payload["data"]["format"] == "xml"
    assert payload["data"]["structure_kind"] == "semi_structured"


def test_text_stream_ingestion():
    status, payload = StreamCommandBuilder.text_ingest(RUN_ID).execute()
    assert status == 201
    assert payload["data"]["format"] == "txt"
    assert payload["data"]["structure_kind"] == "unstructured"


def test_binary_spreadsheet_ingestion():
    status, payload = StreamCommandBuilder.xlsx_ingest(RUN_ID).execute()
    assert status == 201
    assert payload["data"]["format"] == "xlsx"
    assert payload["data"]["record_count"] == 1


def test_streams_events_endpoint_lists_recent_records():
    status, _, body = _request(
        "GET", f"/api/streams/events?source=pytest-json-{RUN_ID}&include_payload=true&limit=5"
    )
    assert status == 200
    payload = _parse_json(body, "streams events")
    assert isinstance(payload.get("data"), list)
    assert any(row["source"] == f"pytest-json-{RUN_ID}" for row in payload["data"])
