# CORS Commands

This file records the exact commands used to verify that CORS is configured correctly for the API.

## 1) Start The API

This command starts the API on `http://localhost:3000`.

```bash
DATABASE_URL=postgres://user:password@localhost:5432/hypecheck npm run dev:api
```

What this checks:
- Confirms the Express server is running.
- Ensures the backend is listening on port `3000`.
- Makes the CORS middleware reachable for testing.

## 2) Full CORS Preflight Check

This command sends an `OPTIONS` preflight request from the allowed frontend origin.

```bash
curl -i -X OPTIONS "http://localhost:3000/api/alerts" \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET"
```

What this checks:
- Confirms the API accepts preflight requests.
- Confirms `http://localhost:5173` is treated as an allowed origin.
- Confirms the response contains CORS headers.

Expected response details:
- `HTTP/1.1 204 No Content` or `200`
- `Access-Control-Allow-Origin: http://localhost:5173`
- `Access-Control-Allow-Credentials: true`

## 3) Header-Only CORS Check

This command prints only the response headers and filters for the main CORS header.

```bash
curl -s -D - -o /dev/null -X OPTIONS "http://localhost:3000/api/alerts" \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" | grep "Access-Control-Allow-Origin"
```

What this checks:
- Confirms the exact origin returned by the server.
- Provides a faster pass/fail check than the full preflight output.

Expected output:

```text
Access-Control-Allow-Origin: http://localhost:5173
```

## 4) Disallowed-Origin Check

This command tests an origin that should not be allowed.

```bash
curl -s -D - -o /dev/null -X OPTIONS "http://localhost:3000/api/alerts" \
  -H "Origin: http://evil.com" \
  -H "Access-Control-Request-Method: GET" | grep "Access-Control-Allow-Origin"
```

What this checks:
- Confirms the middleware does not allow unapproved origins.
- Confirms the allowlist is working rather than permitting every origin.

Expected result:
- No output, or no `Access-Control-Allow-Origin` header for `http://evil.com`

## 5) Health Check Before CORS Testing

This command verifies that the API is reachable before running CORS checks.

```bash
curl -s -w '\nstatus=%{http_code}\n' http://localhost:3000/
```

What this checks:
- Confirms the API is running.
- Helps distinguish a CORS problem from a server-down problem.

Expected output:
- JSON response such as `{"message":"HypeCheck API is running"}`
- `status=200`

## 6) Failure Interpretation

If the terminal shows:

```text
curl: (7) Failed to connect to localhost port 3000
```

This does not indicate a CORS error.

It means:
- The API server is not running, or
- Nothing is listening on port `3000`
