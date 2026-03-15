#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${API_BASE_URL:-http://localhost:3000}"

printf "\n[1] Health\n"
curl -s -w '\nstatus=%{http_code}\n' "${BASE_URL}/"

printf "\n[2] Backtests\n"
curl -s -w '\nstatus=%{http_code}\n' "${BASE_URL}/api/backtests?limit=10"

printf "\n[3] Sessions\n"
curl -s -w '\nstatus=%{http_code}\n' "${BASE_URL}/api/sessions?limit=10"

printf "\n[4] Alerts\n"
curl -s -w '\nstatus=%{http_code}\n' "${BASE_URL}/api/alerts?limit=20"

printf "\n[5] CORS Preflight\n"
curl -i -X OPTIONS "${BASE_URL}/api/alerts" \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" | sed -n '1,12p'
