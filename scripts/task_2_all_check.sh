#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${API_BASE_URL:-http://localhost:3000}"

printf "\n[0] Health\n"
curl -s -w '\nstatus=%{http_code}\n' "${BASE_URL}/"

printf "\n[1] Task 2.2 CLI Script\n"
API_BASE_URL="${BASE_URL}" bash scripts/task_2_2_check.sh

printf "\n[2] Task 2.4 CLI Script\n"
API_BASE_URL="${BASE_URL}" bash scripts/task_2_4_check.sh

printf "\n[3] Task 2.5 CLI Script\n"
API_BASE_URL="${BASE_URL}" bash scripts/task_2_5_check.sh

printf "\n[4] Task 2.2 Pytest\n"
pytest task_2_2_tests -q

printf "\n[5] Task 2.5 Unit Test\n"
npm run test:task2_5 --prefix apps/api

printf "\n[6] Task 2.5 Checker\n"
python3 task_2_5_tests/main.py

printf "\n[7] Task 2.5 Pytest\n"
pytest task_2_5_tests -q

printf "\n[8] Combined Checker\n"
python3 task_2_4_tests/main.py

# Run the Task 2.4 pytest suite last because it intentionally triggers rate limiting.
printf "\n[9] Task 2.4 Pytest\n"
pytest task_2_4_tests -q
