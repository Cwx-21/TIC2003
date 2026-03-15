#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${API_BASE_URL:-http://localhost:3000}"

printf "\n[1] Assets\n"
curl -s -w '\nstatus=%{http_code}\n' "${BASE_URL}/api/assets?limit=10"

printf "\n[2] Sentiment\n"
curl -s -w '\nstatus=%{http_code}\n' "${BASE_URL}/api/sentiment/BTC?limit=10"

printf "\n[3] Prices\n"
curl -s -w '\nstatus=%{http_code}\n' "${BASE_URL}/api/prices/BTC?limit=10"

printf "\n[4] Correlation\n"
curl -s -w '\nstatus=%{http_code}\n' "${BASE_URL}/api/correlation/BTC?limit=10"
