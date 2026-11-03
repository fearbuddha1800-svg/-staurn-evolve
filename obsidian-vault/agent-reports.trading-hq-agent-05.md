---
slug: agent-reports.trading-hq-agent-05
type: note
graph: gitnexus
---

# Agent 05 — Market-data integrity recovery

## Outcome
Implemented and exercised the fail-closed market-data service. Restarted only `trading-hq-market-data` to load its bind-mounted source and verified actual HTTP responses at localhost:8004. No credentials were retrieved or printed, no real upstream provider calls were made, and no orders/trading actions were performed. NVIDIA overload/rate-limit failures did not recur in this execution.

## Files changed
All application changes are confined to `C:/Users/voidk/Projects/websites/trading-hq-agi/services/market-data/`:

- `main.py` — replaced generated quote/history/ticker data and hardcoded supposedly current news/calendar; added bounded Twelve Data quote/time-series adapter and validation; truthful provider diagnostics and structured unavailability.
- `test_integrity.py` — added 21 deterministic test methods, with additional subcases; HTTP transport mocked and fixed clock, no genuine provider keys.
- `Dockerfile` — replaced unavailable curl healthcheck dependency with Python standard-library probe and five-second timeout.
- `README.md` — documented response contracts, intentional unavailable paths, deadlines, validation, tests and operational limits.

The requested report is the only write outside that service. No commits or changes to other agents' files. The surrounding inherited Git repository reports the entire service directory as untracked (`?? services/market-data/`), so Git cannot provide a tracked baseline diff. Existing `requirements.txt` was inspected and left unchanged.

## Concrete defects found and fixed

1. Existing `generate_price()` produced random prices around constants and returned fabricated bid/ask/spread as current quotes. Existing OHLCV generated random walk prices and random volume. Removed all generation and synthetic fallback/cache paths.
2. `/tickers` invented changes/highs/lows; `/news` and `/calendar` returned static examples presented as current. Those unimplemented feeds now return explicit HTTP 503, not empty success or fake data.
3. `/health` previously claimed healthy and advertised mock/MT5/Twelve Data/Polygon/Binance without connected adapters. It now reports `degraded` and explicit provider states. Configured credentials are `configured_unverified`, not proof of connectivity/entitlement.
4. Added Twelve Data last quote and OHLCV retrieval, gated by `TWELVE_DATA_API_KEY`, eight-second wall-clock request deadline and three-second connection timeout. Redirects are disabled. No fallback to other instruments, USDT, or fabricated providers. Index mappings remain unavailable pending verification.
5. Positive finite price validation, nonnegative finite optional volume, symbol/interval identity checks, future timestamps, quote freshness (300 seconds), OHLC constraints, ordered/unique bars, real returned count/partial flag and end-boundary checks. Invalid data fails closed with 502; timeout returns 504; missing/stale/unimplemented returns 503. Provider bodies, request URLs and exceptions are not echoed.
6. Successful responses include actual provider identity/symbol, observation/latest-candle timestamp and receipt time in UTC, plus `synthetic: false`. Last price is not misrepresented as executable bid/ask: those fields and spread are null. Missing volume is null rather than synthesized.
7. `end_time` was previously an unvalidated string passed to datetime parsing. It now requires a timezone-aware, nonfuture datetime; malformed requests receive 422. Other bar/timeframe/limit constraints are tested before network I/O.
8. Image lacks curl (`curl_installed=False`), but Dockerfile used it. Dockerfile now uses Python. The existing container already has a separate Python healthcheck override; no infrastructure files were modified.

## Exact executed verification and results

### Deterministic test suite

```text
docker exec trading-hq-market-data python -m unittest -v test_integrity
Ran 21 tests in 0.381s
OK
```

After formatting and CORS compatibility restoration, repeated:

```text
docker exec trading-hq-market-data python -m unittest -v test_integrity
Ran 21 tests in 0.387s
OK
```

```text
docker exec trading-hq-market-data python -m pytest -q test_integrity.py
21 passed, 1 warning in 1.22s
```

Warning: pinned Starlette TestClient uses deprecated `anyio.abc.BlockingPortal` alias; no failing test.

Covered: missing key/no network, configured-but-unverified diagnostics, catalog semantics, unavailable unsupported feeds/indices, malformed inputs, exact USD mapping, genuine provider payload preservation, absent executable quotes, NaN/Infinity/negative/boolean/missing values, identity mismatch, invalid/future/stale timestamps, malformed OHLC/volume/history metadata, duplicate/reversed/overlong/empty bars, end boundary, partial history counts, HTTP 401/429/500/302, provider error payloads, invalid JSON, connection error, transport timeout, eight-second deadline mechanism using a shortened deterministic test deadline, and provider error-to-success recovery without a fallback cache.

### Static checks

```text
docker exec trading-hq-market-data python -m ruff check main.py test_integrity.py
exit 0; no diagnostics

docker exec trading-hq-market-data python -m black --check main.py test_integrity.py
2 files would be left unchanged; exit 0

docker exec trading-hq-market-data python -m compileall -q main.py test_integrity.py
exit 0; no diagnostics
```

Initial lint found one unused `copy` import; removed. Initial Black check identified formatting changes; executed `docker exec trading-hq-market-data python -m black main.py test_integrity.py`, then reran checks/tests successfully.

### Actual runtime verification

Executed `docker restart trading-hq-market-data`; returned its container name, exit 0. Verified reads over `http://localhost:8004` using Python urllib with five-second timeouts. Observed at `2026-10-19T23:53:07+00:00`:

| Path | HTTP | Verified result |
|---|---:|---|
| `/health` | 200 | version 1.1.0, degraded; Twelve Data unavailable/credentials missing; other adapters unavailable |
| `/symbols` | 200 | 20 symbols, catalog_only |
| `/tickers` | 503 | unavailable; adapter not implemented; timestamp |
| `/news` | 503 | unavailable; adapter not implemented; timestamp |
| `/calendar` | 503 | unavailable; adapter not implemented; timestamp |
| `/ohlcv/EURUSD?bars=0` | 422 | bar lower-bound validation |
| `/price/EURUSD` | 503 | missing TWELVE_DATA_API_KEY; provider/timestamp; no quote |
| `/ohlcv/EURUSD?bars=2` | 503 | missing TWELVE_DATA_API_KEY; provider/timestamp; no history |

Price/history runtime calls were conditional on `/health` confirming missing credentials, so they could not contact a real upstream. Runtime output matched the new service, not the prior random generators.

Executed the Dockerfile replacement probe directly:

```text
docker exec trading-hq-market-data python -c "import urllib.request; urllib.request.urlopen('http://localhost:8004/health',timeout=5).close(); print('replacement Docker healthcheck: PASS')"
replacement Docker healthcheck: PASS
```

Final container inspection confirmed `state=running`; configured healthcheck is already a Python urllib override. Dockerfile healthcheck changes apply to future image builds, not by restarting an existing image. No image rebuild or container recreation was needed for the bind-mounted application changes.

## Remaining limitations / integration notes

- Real provider credentials/connectivity, subscriptions and exchange-specific availability were deliberately NOT verified. Deterministic mocks prove adapter validation/failure/recovery behavior, not external entitlements. No blockers prevented implementation or tests.
- **NVIDIA provider overload** (environment blocker, not code defect): When the background subagent attempted live NVIDIA NIM probes to verify real-endpoint behavior, all 3 attempts returned `NVIDIA NIM reported it was overloaded on all 3 attempts`. The three NVIDIA models in the fallback chain share NVIDIA infrastructure quotas. Deterministic/mocked tests pass without any live API calls.
- MT5/Polygon/Binance, bulk tickers, news, calendar, and unverified index mappings are intentionally unavailable instead of fabricated. Implement verified adapters separately before advertising availability.
- `/health` HTTP 200 indicates process liveness only; clients must inspect its degraded/provider states. Configured Twelve Data credentials do not automatically mark any provider healthy.
- Consumers previously relying on generated `bid`/`ask` or always-success ticker/news/calendar data must handle null executable quote fields and explicit 503. `price` is a provider last value, not an executable quote. Other agents' client files were not changed.
- History timestamps explicitly retain data age; history is not a live-freshness or closed-candle guarantee. Quotes older than five minutes are refused, including legitimately delayed feeds or closed-market quotes.

