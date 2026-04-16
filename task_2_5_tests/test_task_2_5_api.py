import json
import os
import time
import urllib.error
import urllib.request

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")
TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT", "5"))
RUN_ID = str(int(time.time() * 1000))


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


def test_streams_health_endpoint():
    status, _, body = _request("GET", "/api/streams/health")
    assert status == 200
    payload = _parse_json(body, "streams health")
    assert isinstance(payload, dict)
    assert isinstance(payload.get("data"), dict)
    assert "supported_formats" in payload["data"]


def test_json_stream_ingestion():
    body = json.dumps(
        {
            "source": f"pytest-json-{RUN_ID}",
            "stream_name": "task-2-5-json",
            "format": "json",
            "metadata": {"suite": "task_2_5"},
            "payload": [
                {"asset": "BTC", "score": 0.91},
                {"asset": "ETH", "score": 0.78},
            ],
        }
    ).encode("utf-8")
    status, _, response_body = _request(
        "POST",
        "/api/streams/ingest",
        body=body,
        headers={"Content-Type": "application/json"},
    )
    assert status == 201
    payload = _parse_json(response_body, "json ingest")
    assert payload["data"]["format"] == "json"
    assert payload["data"]["record_count"] == 2


def test_csv_stream_ingestion():
    csv_body = "symbol,price\nBTC,65000\nETH,3000".encode("utf-8")
    status, _, response_body = _request(
        "POST",
        f"/api/streams/ingest?source=pytest-csv-{RUN_ID}&stream_name=csv-suite&format=csv",
        body=csv_body,
        headers={"Content-Type": "text/csv"},
    )
    assert status == 201
    payload = _parse_json(response_body, "csv ingest")
    assert payload["data"]["format"] == "csv"
    assert payload["data"]["record_count"] == 2


def test_xml_stream_ingestion():
    xml_body = "<feed><asset symbol='BTC'>bullish</asset></feed>".encode("utf-8")
    status, _, response_body = _request(
        "POST",
        f"/api/streams/ingest?source=pytest-xml-{RUN_ID}&stream_name=xml-suite&format=xml",
        body=xml_body,
        headers={"Content-Type": "application/xml"},
    )
    assert status == 201
    payload = _parse_json(response_body, "xml ingest")
    assert payload["data"]["format"] == "xml"
    assert payload["data"]["structure_kind"] == "semi_structured"


def test_text_stream_ingestion():
    text_body = "Trader notes\nPotential breakout\nWatch BTC volume".encode("utf-8")
    status, _, response_body = _request(
        "POST",
        f"/api/streams/ingest?source=pytest-text-{RUN_ID}&stream_name=text-suite&format=txt",
        body=text_body,
        headers={"Content-Type": "text/plain"},
    )
    assert status == 201
    payload = _parse_json(response_body, "text ingest")
    assert payload["data"]["format"] == "txt"
    assert payload["data"]["structure_kind"] == "unstructured"


def test_binary_spreadsheet_ingestion():
    binary_body = b"PK\x03\x04mock-xlsx-payload"
    status, _, response_body = _request(
        "POST",
        f"/api/streams/ingest?source=pytest-xlsx-{RUN_ID}&stream_name=xlsx-suite&format=xlsx",
        body=binary_body,
        headers={
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        },
    )
    assert status == 201
    payload = _parse_json(response_body, "xlsx ingest")
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
