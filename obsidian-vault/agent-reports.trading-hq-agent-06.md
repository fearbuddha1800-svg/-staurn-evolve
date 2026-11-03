---
slug: agent-reports.trading-hq-agent-06
type: note
graph: gitnexus
---

# Agent 06 — Pine runner robustness completed

## Outcome
Implemented and executed the offline indicator runner against the actual bundled PineTS library in `trading-hq-pine-runner`. No live orders, synthetic market fallback, Compose edits, frontend edits or commits.

## Concrete implementation
- Correct CommonJS import (`PineTS`, `Indicator`) through a Node bridge; the minified library is not a CLI. Assets resolve relative to service files; Docker now includes runtime.py.
- Execute only explicit validated, strictly ordered finite OHLCV candles; no implicit market provider or generated candles. Enforce script size, bar count, supported timeframe and OHLC/volume ranges.
- Reject strategies, imports/external request data, runtime warnings and unsupported parameter overrides instead of returning plausible fabricated strategy/backtest results. Successful indicator output carries caller-supplied provenance; strategy/stats stay empty and no actionable signal is invented.
- Real compiler-backed syntax validation explicitly labels syntax-only scope. Health imports and compiles with actual PineTS; missing library returns 503.
- Ten-second wall timeout, 128 MiB V8 old-space, 10000 Pine loop limit, two children per worker, one-second admission wait and 2 MiB stdout/stderr cap per stream. Shell-free subprocess, stripped application-secret environment, cancellation/error cleanup, POSIX process-group kill/reap, strict versioned JSON envelope.
- Preserve warmup nulls and plot alignment, derive closeTime using the requested Pine timeframe, never hardcode an hour.

## Exact changed/created project files
- Modified `services/pine-runner/main.py`: thin app entrypoint preserving port 8001.
- Modified `services/pine-runner/pinets_bridge.js`: actual library adapter and strict JSON protocol.
- Modified `services/pine-runner/Dockerfile`: copy main.py and runtime.py together.
- Created `services/pine-runner/runtime.py`: validation, bounded child execution and API routes.
- Created `services/pine-runner/test_runtime.py`: 24 deterministic offline tests with real Node/PineTS and process-failure fixtures.
- Created `services/pine-runner/smoke_http.py`: isolated real HTTP uvicorn verification.
- Created `services/pine-runner/README.md`: contract, limits, security caveats, integration/deployment recommendations and commands.

Existing bundled library and requirements were retained. The whole service directory was already untracked in the inherited checkout; no attribution to other agents or unrelated checkout edits is claimed.

## Executed verification
Environment: Node v20.19.2, Python 3.11.17 inside the existing container; bundled CommonJS asset is 716206 bytes.

Command:
`docker exec trading-hq-pine-runner python -m unittest -q test_runtime`

Exact final summary:
```
----------------------------------------------------------------------
Ran 24 tests in 12.487s

OK
```
Tests cover exact close/SMA values and warmup alignment; tail bars; absent candles; strategies; parameter overrides; schema bounds/ranges/order/nonfinite values; real syntax compile and invalid syntax; offline policy; missing library/degraded health; missing node; nonzero/empty/malformed/forged output; stdout/stderr overflow; actual heap exhaustion; timeout; cancellation/temp/slot cleanup; stripped secret environment; loop guard; per-timeframe close time; bounded busy queue.

Command: `docker exec trading-hq-pine-runner python smoke_http.py`

Observed output:
```
GET /health: 200 {'status': 'healthy', 'engine': 'PineTS', 'strategy_backtest_supported': False}
POST /execute: success, SMA= [None, 11, 13, 15] provenance= {'engine': 'PineTS', 'data_source': 'caller_supplied', 'bars': 4, 'symbol': 'TEST', 'timeframe': 'M1', 'strategy_backtest_supported': False}
POST /execute strategy: False Strategy backtests are unsupported; no trades or stats are produced
HTTP smoke passed; isolated server stopped
```

Also passed with exit 0:
- `docker exec trading-hq-pine-runner python -m compileall -q main.py runtime.py test_runtime.py smoke_http.py`
- `docker exec trading-hq-pine-runner node --check /app/pinets_bridge.js`

## Issues resolved and limitations
- A cancellation-future warning seen during failure testing was fixed by retaining and retrieving the aggregate reader/process future. Final test output is clean.
- Initial whole-file write attempts were refused by the tool; targeted patches plus a new runtime module were used. Final source and real HTTP behavior were exercised.
- No full image rebuild/redeployment was performed. Tests use current service source in the existing container; the HTTP smoke starts/stops a separate listener on 18006. Do not assume the already-running production listener reloaded Python modules.
- Indicator-only: no strategy backtest parity, market-data authenticity or live-trading readiness is claimed. Bundled PineTS version is unversioned rather than an invented package version.
- Trusted scripts only: PineTS evaluates generated JS. V8 heap limits are not full native-process memory isolation. Need non-root/read-only per-job isolation, no secrets/mounts/network, cgroup CPU/RAM/PID limits and ingress body/auth/rate limits before hostile multi-tenant use. Windows kills direct child only; production Windows needs Job Objects. Limits multiply by uvicorn worker count.
- API callers must explicitly supply candles. Frontend integration should expose unsupported strategy/parameter capabilities and syntax-only validation. These recommendations were documented without editing Compose/frontend-owned files.

