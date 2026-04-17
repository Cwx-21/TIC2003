#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${API_BASE_URL:-http://localhost:3000}"
RUN_ID="$(date +%s)"

printf "\n[1] Streams Health\n"
curl -s -w '\nstatus=%{http_code}\n' "${BASE_URL}/api/streams/health"

printf "\n[2] JSON Ingest\n"
curl -s -w '\nstatus=%{http_code}\n' \
  -H "Content-Type: application/json" \
  --data-binary "{\"source\":\"cli-json-${RUN_ID}\",\"stream_name\":\"task-2-5-cli\",\"format\":\"json\",\"metadata\":{\"runner\":\"task_2_5_check.sh\"},\"payload\":[{\"asset\":\"BTC\",\"score\":0.73}]}" \
  "${BASE_URL}/api/streams/ingest"

printf "\n[3] CSV Ingest\n"
curl -s -w '\nstatus=%{http_code}\n' \
  -H "Content-Type: text/csv" \
  --data-binary $'symbol,price\nBTC,65000\nETH,3000' \
  "${BASE_URL}/api/streams/ingest?source=cli-csv-${RUN_ID}&stream_name=task-2-5-cli&format=csv"

printf "\n[4] XML Ingest\n"
curl -s -w '\nstatus=%{http_code}\n' \
  -H "Content-Type: application/xml" \
  --data-binary '<feed><asset symbol="BTC">bullish</asset></feed>' \
  "${BASE_URL}/api/streams/ingest?source=cli-xml-${RUN_ID}&stream_name=task-2-5-cli&format=xml"

printf "\n[5] Events Query\n"
curl -s -w '\nstatus=%{http_code}\n' \
  "${BASE_URL}/api/streams/events?source=cli-json-${RUN_ID}&include_payload=true&limit=5"
