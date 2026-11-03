# Cockpit API

Machine-readable contract: [openapi.json](openapi.json), OpenAPI 3.1 / JSON Schema 2020-12. Source: `cockpit_runtime.py` dispatch, `cockpit.py` adapters. Runtime is authoritative over older delivery-ledger line references.

## Boundary and authentication
Local base: `http://127.0.0.1:8490`. A single loopback Host header with the actual port is mandatory (403 otherwise). No remote exposure or CORS grant. Use bearer token or signed `cockpit_session` cookie; cookies last 8 hours. `GET /` injects a single-use 180-second nonce for POST `/api/bootstrap`. Alternatively POST `/api/session` with exactly `{"token":"<local secret>"}`. Both establish the cookie. POST and DELETE require an exact same-origin Origin header; Sec-Fetch-Site may be absent or same-origin. DELETE session only clears that browser's cookie. Token rotation requires coordinated server restart and invalidates all signed sessions. `/api/token` is authenticated and secret-bearing: do not archive responses.

JSON bodies require Content-Length and application/json. Maximum body 131072 bytes; Pine source 65536 UTF-8 bytes. Duplicate keys, nonfinite values, duplicate query parameters, invalid encoding and unknown fields are rejected. Query integers must use canonical decimal spelling. All responses use no-store. Unsupported POST/DELETE routes return 404, OPTIONS returns 405. Unauthenticated API requests are rejected before route lookup.

## Runtime differences from earlier documents
* Neural health is `/api/neural` (nested health), NOT `/api/neural.health` (authenticated 404).
* Pine series is `/api/pine_series`, NOT `/api/pine/series` (authenticated 404).
* Both valid `/api/pine_series` and POST `/api/pine/compile` fail closed with 503: a credential-free OS-isolated worker is not configured. Offline helpers are not an HTTP sandbox.
* `/api/prop_sim` is observational and reports unavailable; it does not invoke broker history simulation from HTTP.
* Events SSE is finite replay, not a live feed. Reconnect/poll explicitly; no resumable Last-Event-ID contract.
* `/api/strategy_registry` is a read-only registry refresh with cached backtest evidence, not execution; inspect revision/stale fields. It rejects query parameters.
* `/api/candles` returns 503 with its backend candle-error snapshot (not the standard `{ok:false,error}` envelope) when unavailable.
* `/api/trace/{ticket}` distinguishes ledger evidence and broker evidence; unknown does not mean closed.

## Schema scope
All implemented `/api/` routes and methods appear in the spec. Named schemas cover authentication, errors, neural progress, token and candles. Provider-dependent snapshots permit additional fields intentionally, rather than inventing stable requirements for external artifacts. An unavailable backend may return HTTP 200 with available=false/reason; clients must examine payload evidence and freshness. Arrays are not assumed to be empty-success. Integer/timeframe/count restrictions are explicit in the spec; timeframe inputs are normalized to uppercase by the runtime. Candles use rows of epoch-seconds/open/high/low/close/volume. Source URLs in intelligence records are provenance, not endorsements.

## Safe observation
From the repository with its approved interpreter:
```bash
python hq.py status
# Use the browser's local bootstrap rather than copying credentials into shell history.
```
Use an isolated test server with a dummy token for API examples and tests. Do not paste production tokens into a shared terminal, document, issue, or screenshot. HTTP never authorizes order placement, broker attachment, terminal restart, or enabling trading.
