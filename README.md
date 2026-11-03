# Quant HQ — Professional Trading Command Center v1.0.0

> Live MT5 signal relay • Pine Script strategy engine • Neural learning loop • Matrix Terminal dashboard
> **One entry point. One auth layer. One event bus. End-to-end on localhost.**

A local, **read-only** trading command centre for a Telegram → MetaTrader 5 signal relay.
It monitors the live account, executes Pine Script research against real broker candles,
runs quant risk analytics, and records every signal, decision and outcome so the system can
learn from its own trades.

**The dashboard never places, modifies or closes orders.** Order execution belongs to
`daemon.py` / `executor.py`; the dashboard only reads and reports.

- **Dashboard:** http://localhost:8490 — opens straight in, no token prompt
- **Control CLI:** `python hq.py status | start | stop | token | restart`
- **Installer:** `install.bat` (Windows) | `start.bat` | `stop.bat`
- **Quick start:** [`QUICKSTART.md`](QUICKSTART.md)
- **Package:** `setup.py` / `pyproject.toml` / `requirements.txt` (pip-installable)


---

## Architecture at a glance

```
Telegram chats ──► daemon.py ──► parser.py ──► executor.py ──► MT5 (orders)
                      │                            │
                      │                            └──► signals.db (trades ledger)
                      ▼
                 event_bus.py  ◄── manage.py, strategy.py, strategy2_live.py,
                      │              scalp360/neural.py, luxalgo_orchestrator.py
                      ▼
              signals.db (events table, WAL, persistent)
                      │
                      ▼
        cockpit.py + cockpit_runtime.py  ──►  http://localhost:8490
                      ▲
                      │
        neural_label_collector.py (watch)  ──► neural_labels (training data)
```

| Layer | Component | Role |
|---|---|---|
| Ingest | `daemon.py` | Telegram listener (Telethon, your account) |
| Parse | `parser.py` | free text → structured trade |
| Execute | `executor.py` | MT5 order placement + risk guard + ledger |
| Manage | `manage.py` | break-even + trailing stop |
| Strategy | `strategy.py`, `strategy2_live.py` | algo engines (RSI/EMA trend, London breakout) |
| Nervous system | `event_bus.py` | pub/sub, persisted to SQLite |
| Learning | `neural_label_collector.py` | feature labels + realised outcomes |
| Analytics | `quant_analytics.py` | VaR, ES, correlation, stop-risk |
| Dashboard | `cockpit.py` + `cockpit_runtime.py` | read-only HTTP surface |
| Identity | `strategy_identity.py` | configured magic → strategy ID/version; unknown stays unknown |
| Broker reconciliation | `reconciliation.py` | read-only lost-ack checks after a failed send acknowledgement |
| Bar parity | `bar_parity.py` | explicit same-basis closure checks + in-memory per-bar idempotency |
| AI bounds | `model_router.py` | deadline, concurrency and budget bounds; abstains on failure |
| Label health | `label_health.py` | completed/pending counts, map integrity, feature validity, accumulation rate |
| Portfolio diagnostics | `portfolio_risk.py` | aggregate stop risk, concentration and native FX exposure; diagnostics, not an entry guard |
| Loss latch | `loss_halt.py` | durable daily net-realised-loss latch library; not automatically an engine gate |
| Stop planning | `stop_legality.py` | fresh-tick/stop-distance preflight, widen opt-in and exact broker read-back; additive library, not a replacement for live manager |
| Watchdog | `C:/Users/voidk/.hermes/scripts/signal-relay-watchdog.py` | supervises engines, dashboard, LuxAlgo orchestrator and label collector |

---

## Prerequisites

| Requirement | Version used | Notes |
|---|---|---|
| Python | 3.13.13 | `C:\Users\voidk\miniconda3\python.exe` |
| Node.js | v24.15.0 | required by the PineTS bridge (`pine_series_bridge.js`) |
| MetaTrader 5 | — | terminal must be running and logged in |
| Python packages | `MetaTrader5`, `psutil`, `Telethon`, `PyYAML`; `pytest` for tests | requirements vary by component; the HTTP/auth layer uses stdlib, but live broker reads require MT5 |

Pine also needs the locally built LuxAlgo PineTS runtime used by `pine_series_bridge.js`
and `pinets_bridge.js`. Telegram ingestion requires an authorised Telethon session and
the configured watch list. Do not copy another running process's writable session.
Run commands below from `C:/Users/voidk/.hermes/workspace/signal-relay`.

> **Environment note.** The agent shell injects a `PYTHONPATH` that shadows the real venv.
> When running anything by hand, clear it first:
> `PYTHONPATH= C:/Users/voidk/miniconda3/python.exe ...`
> `hq.bat` already handles this.

---

## Start / stop everything

```bash
# status of every component, the flags and the URL
PYTHONPATH= C:/Users/voidk/miniconda3/python.exe hq.py status

# start the five CLI-managed components not already running
PYTHONPATH= C:/Users/voidk/miniconda3/python.exe hq.py start

# graceful STOP window, then terminate remaining managed PIDs
PYTHONPATH= C:/Users/voidk/miniconda3/python.exe hq.py stop

# print the dashboard token and URL
PYTHONPATH= C:/Users/voidk/miniconda3/python.exe hq.py token

# stop then start
PYTHONPATH= C:/Users/voidk/miniconda3/python.exe hq.py restart
```

Or the wrapper: `hq.bat status` (in bash, `./hq.bat status`). The five CLI components are
cockpit, daemon, manage, strategy and strategy2. This is **not** the watchdog's entire
fleet: the neural collector and LuxAlgo services/orchestrator are supervised separately.
`status --strict` returns 1 if any managed component is down; ordinary `status` can
return 0 with DOWN components, but unknown checks return 1.

`stop` waits up to 60 seconds by default, then uses verified lock/listener PIDs;
`--force` skips the grace period. A STOP file created by that command is removed on
completion; an existing STOP file is preserved. Consequently the watchdog can restart
the stack on its next tick. For a deliberate maintenance hold, keep `MAINTENANCE`
present. **Stopping manage removes automated protection updates; this does not close
positions or remove broker-native stops.** `start` refuses an existing STOP unless
forced; inspect its reason instead of bypassing it. Detached starts attempt job
breakaway, with a fallback that may not survive agent-job cleanup.

The dashboard alone, without the rest of the stack:

```bash
PYTHONPATH= C:/Users/voidk/miniconda3/python.exe cockpit.py
```

`signal-relay-watchdog.py` runs every 15 minutes and restarts anything dead — including
`neural_label_collector.py watch`. It holds off entirely while a `MAINTENANCE` or `STOP`
file is present.

---

## Opening the dashboard

Open **http://localhost:8490**. It **logs you in automatically** — there is no token prompt.

The page is served with a single-use, 180-second, loopback-only nonce that the client
exchanges for a session cookie (`HttpOnly; SameSite=Strict`, 8 hours). The token remains the
root secret and still works via `POST /api/session` as a fallback.

**Where the token lives**

| Source | How |
|---|---|
| Dashboard | **System → Dashboard credential** |
| File | `.cockpit-token` next to `cockpit.py` (32-byte hex) |
| CLI | `hq token` |
| Environment | `COCKPIT_TOKEN` overrides the file |

`GET /api/token` requires authentication. The server validates a loopback Host; this
is not a supported LAN dashboard. A token does not bypass Host/origin restrictions.
Keep it private. Note: the server gives `COCKPIT_TOKEN` precedence, whereas `hq token`
prints the file first and only falls back to the environment when the file is absent.

---

## API

API and Vela routes require a bearer token or session cookie, except the session/bootstrap
operations below. All routes validate Host; POST operations also require same-origin.
`401` means unauthenticated, `403` invalid Host/origin, `400` malformed input. Some
unavailable sources return `available:false` inside HTTP 200; candles can return 503.
Do not equate HTTP 200 with source health. DELETE session clears the caller's cookie
without requiring an authenticated session.

| Endpoint | Method | Returns |
|---|---|---|
| `/` | GET | The dashboard page (carries the auto-login nonce) |
| `/assets/quant.css`, `/assets/quant.js` | GET | Allow-listed static assets |
| `/api/bootstrap` | POST | `{nonce}` → session cookie (single-use, 180 s TTL) |
| `/api/session` | POST / DELETE | Token → session cookie / end session |
| `/api/token` | GET | The local dashboard credential |
| `/api/identity` | GET | Configured strategy registry and magic-based ownership of each open position |
| `/api/portfolio` | GET | Read-only aggregate stop-risk, concentration, native FX exposure and diagnostic caps |
| `/api/attribution` | GET | Strategy ID/version P/L attribution from broker deals |
| `/api/state` | GET | Full aggregate: account, positions, engines, ledger, channels |
| `/api/quant` | GET | VaR95, ES95, volatility, drawdown, correlation, stop-risk |
| `/api/inbox` | GET | Signal inbox |
| `/api/journal` | GET | Decision journal |
| `/api/mobile` | GET | Phone-sized HTML fragment |
| `/api/neural` | GET | Complete/collected/pending labels, 300-label readiness, last evaluation and `health` from `label_health` |
| `/api/latency` | GET | p50/p95/p99 per pipeline stage |
| `/api/lineage` | GET | Recent signal → intent → order → position chain |
| `/api/pine` | GET | Registered Pine strategies |
| `/api/strategies` | GET | Strategy engine state |
| `/api/health` | GET | Process liveness, ports, flags |
| `/api/channels` | GET | Signal channels + policy |
| `/api/news` | GET | News risk window |
| `/api/luxalgo` | GET | LuxAlgo services and library repos |
| `/api/edge` | GET | Edge statistics |
| `/api/events` | GET | Event history — params `trace_id`, `stream`, `limit` (1–500), `exclude` |
| `/api/trace/<ticket>` | GET | Full lifecycle for one ticket |
| `/api/candles` | GET | MT5 candles — `symbol`, `timeframe`, `count` |
| `/api/pine_series` | GET | Pine overlay series — `strategy`, `symbol`, `timeframe`, `count` |
| `/api/prop_sim` | GET | Prop-firm Monte Carlo — `paths` |
| `/api/market_intel` | GET | Congress / insider / contracts / lobbying / short volume |
| `/api/pine/compile` | POST | Compile Pine source → plot series + entry marks |
| `/vela/vela.global.js`, `/vela/vela-pinets.global.min.js` | GET | Authenticated, allow-listed local Vela bundles if built |

Simple endpoints take no query parameters. Chart endpoints accept `M1`, `M5`, `M15`,
`M30`, `H1`, `H4`, `D1` and `count=20..1500`. `/api/market_intel` accepts `kind`
(`congress`, `insider`, `contracts`, `lobbying`, `short_volume`) and `limit=1..50`;
`/api/prop_sim` accepts `paths=100..20000`. Compile JSON fields are `script`, `symbol`,
`timeframe`, `count`. Pine source is bounded to 65536 UTF-8 bytes (request body 128 KiB),
two concurrent runs and a 30-second bridge timeout. Compiler rejection is 422,
busy is 429, runtime missing is 503, timeout is 504. Scripts are owner-trusted, **not sandboxed**.

`/api/events?stream=1` (or an SSE Accept header) returns a **finite replay snapshot**
ending in `[DONE]`, not a continuous subscription. `exclude` is one event type
matching `[a-z_]{1,40}`. Unknown routes return 404; duplicate/unknown query fields are rejected.

The UI requests `/api/events?limit=30&exclude=pnl_update` to keep frequent position-P/L
updates from burying signals. This is a read filter: the writer and persisted history
are unchanged, and nothing is deleted.

### Scripted auth (no browser)

```python
import re, json, urllib.request, http.cookiejar
BASE = 'http://localhost:8490'
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
page = op.open(BASE + '/').read().decode()
nonce = re.search(r'window\.__hqBootstrap="([0-9a-f]{32})"', page).group(1)
op.open(urllib.request.Request(BASE + '/api/bootstrap',
        data=json.dumps({'nonce': nonce}).encode(),
        headers={'Content-Type': 'application/json', 'Origin': BASE}, method='POST'))
print(json.loads(op.open(BASE + '/api/state').read())['account'])
```

---

## Pine Script workflow

Strategies live in `strategies/` and are registered in `config.json`. Execution uses the
real **PineTS** runtime (Node) against live MT5 candles — not a reimplementation.

Registered: `strategies/rsi_ema_trend.pine`, `strategies/ema_cross.pine`.

In the dashboard: **Chart Lab** → choose symbol/timeframe → **Load chart**, then either pick a
registered strategy and **Render registered Pine**, or edit the scratchpad and **Compile & render**.
Compiling the scratchpad never changes registered strategies.

For scripts, use the cookie bootstrap example above, then request
`/api/pine_series?strategy=strategies/rsi_ema_trend.pine&symbol=XAUUSD&timeframe=H1&count=220`.
The path must identify a `.pine` file directly under `strategies/`; traversal is refused.
Register additional reviewed files in `config.json` under `pine_strategies`; this
documentation refresh does not change that configuration.

**Closed-bar rule:** `/api/candles` retains the newest live/forming bar for display and
returns `timestamp_basis`, `forming_bar_excluded` and `last_bar_closed`. The research
`run_pine` path instead calls `candles_data(..., closed_only=True)` and drops the final
received bar before invoking `pine_series_bridge.js`. MT5 broker epochs have no guaranteed
timezone, so closure is **never inferred by comparing them to local time**. The metadata
currently uses `last_bar_closed=null` on the chart path and `false` when the final received
bar was excluded; do not reinterpret this as independent proof about a returned bar's clock.

The separate `pine_runner.py` → `pinets_runner.py` → `pinets_bridge.js` path records paper
signals only; it contains no live-order switch, even if a paper flag is changed. The optional
`pine_script_parser.py` transpiler is a separate best-effort utility, not the dashboard runtime.

---

## The learning loop

`neural_label_collector.py` is the system's memory of its own decisions:

1. **On entry** — captures a 25-dim feature snapshot (RSI14, ATR14, spread, SL distance,
   session, day-of-week, symbol, channel policy) into `neural_labels`.
2. **On close** — sets `outcome` from the realised R multiple against the *original* channel SL.
3. **At 300 complete usable labels** — status/evaluation mode may train the challenger;
   `PROMOTE` requires holdout AUC ≥ 0.58 and `model_net > baseline_net > 0`.
   This is an evaluation recommendation, not automatic activation in the execution engine.

```bash
PYTHONPATH= C:/Users/voidk/miniconda3/python.exe neural_label_collector.py          # status
PYTHONPATH= C:/Users/voidk/miniconda3/python.exe neural_label_collector.py backfill  # one pass
PYTHONPATH= C:/Users/voidk/miniconda3/python.exe neural_label_collector.py watch 15  # live sidecar
```

It is read-only with respect to trading — it never calls `order_send`. **It must be
supervised** or no labels accumulate; the watchdog starts it with `watch`. Watch mode
collects; it does not automatically train on every pass. The 2026-10-17T17:31Z read-only
probe found **2 complete / 3 recorded (1 pending)** and no last evaluation. `/api/neural`
also returns `health` from `label_health` (DB/map/feature validity and accumulation rate).

Evaluation currently uses a final 20% holdout and training-tail validation threshold.
A purged-splits helper exists but `evaluate()` does not invoke it; do not claim a verified
purged-k-fold training run. Net is binary win/loss scoring less `cost_per_trade`, which
defaults to zero, not a complete broker-cost cashflow replay. Collector outcomes use
realised profit R, not independently proven TP-before-SL hits. Review these limitations
before interpreting a recommendation as deployment evidence.

---

## Tests

Run the explicit pytest set, then **each standalone runner in its own interpreter**.
Do not run bare `pytest`: `test_loop.py` attempts live broker sends, and some runners
call `sys.exit()` at import time. No live trading test was run for this refresh.

```bash
PYTHONPATH= C:/Users/voidk/miniconda3/python.exe -m pytest \
  test_cockpit_api.py test_cockpit_contracts.py test_cockpit_new_features.py \
  test_quant_analytics.py test_research_contracts.py test_intelligence_integration.py \
  test_reconciliation.py test_strategy_identity.py test_bar_parity.py \
  test_model_router.py test_label_health.py test_ai_router_integration.py \
  test_watchdog_recovery.py test_ai_provider_selection.py test_loss_halt.py \
  test_portfolio_risk.py test_stop_legality.py test_prop_sim_real_data.py \
  test_real_data_views.py -q

# bash/MSYS: independent interpreters, preserve every runner's result
for suite in test_suite.py test_neural_collector.py test_pine_runner.py \
  test_strategy2_live.py test_edge_stats_bridge.py test_prop_sim_bridge.py \
  test_market_intel_bridge.py test_entry_authority.py test_console.py; do
  PYTHONPATH= C:/Users/voidk/miniconda3/python.exe "$suite"
  printf '%s exit=%s\n' "$suite" "$?"
done
```

**Executed 2026-10-17:** expanded pytest set returned **330 passed, 2 failed,
16 subtests passed**. Failures:
1. `test_real_data_views.py::test_journal_uses_persisted_event_ids_not_log_inference`
   expects a list while `journal()` now returns an availability/provenance envelope.
2.
`test_watchdog_recovery.py::test_one_component_failure_does_not_kill_others`:
its one-argument fake launcher is incompatible with the supervisor's `_start(script,args)`
call; it also expects six components while the supervisor lists seven. This is not an
all-green verification claim. See `agent-reports/doc-refresh-pytest.log`.

| Pytest file | Passed (separate from subtests) |
|---|---:|
| `test_cockpit_api.py` | 9 |
| `test_cockpit_contracts.py` | 9 |
| `test_cockpit_new_features.py` | 6 |
| `test_quant_analytics.py` | 18 |
| `test_research_contracts.py` | 21 (+16 subtests) |
| `test_intelligence_integration.py` | 24 |
| `test_reconciliation.py` | 27 |
| `test_strategy_identity.py` | 31 |
| `test_bar_parity.py` | 16 |
| `test_model_router.py` | 15 |
| `test_label_health.py` | 13 |
| `test_ai_router_integration.py` | 8 |
| `test_watchdog_recovery.py` | 9; 1 failed |
| `test_ai_provider_selection.py` | 18 |
| `test_loss_halt.py` | 21 |
| `test_portfolio_risk.py` | 11 |
| `test_stop_legality.py` | 36 |
| `test_prop_sim_real_data.py` | 28 |
| `test_real_data_views.py` | 10; 1 failed |

| Standalone runner | Observed result |
|---|---|
| `test_suite.py` | 15 PASS cases: S1–S9, N1–N6; exit 0 |
| `test_neural_collector.py` | 13 passed, 0 failed; exit 0 |
| `test_pine_runner.py` | Runner says 4 grouped tests; 12 printed PASS checks; exit 0 |
| `test_strategy2_live.py` | 12 PASS cases; exit 0 |
| `test_edge_stats_bridge.py` | 7 PASS functions; exit 0 |
| `test_prop_sim_bridge.py` | Exit 1 at the sixth of 7 runner invocations: old mocks do not replace the new observed-trade reader; it sees only 2 validated closes, below 10. No all-pass count claimed. |
| `test_market_intel_bridge.py` | 7 unittest tests, OK; exit 0 |
| `test_entry_authority.py` | 8 unittest tests, OK; exit 0 |
| `test_console.py` | 49 printed PASS checks; exit 0 |

Counts are intentionally not added across runners: grouped tests, checks and pytest items
are different units. `agent-reports/doc-refresh-verify.py` reproduces this explicit run and
saves per-suite logs plus `doc-refresh-tests.json`. Mock/dry-run passing does not prove live
fills, live protective modifications, or provider credit/model availability.

---

## Emergency controls

Marker files next to `daemon.py`. The dashboard reports their state but never sets them.

| File | Effect |
|---|---|
| `HALT` | Blocks shared executor new entries; open positions remain managed |
| `PAUSE` | Daemon/strategy2 entry gate, **not universal**: reviewed RSI strategy/shared executor does not consult it |
| `STOP` | Polling loops exit, including manager/collector; watchdog launches suppressed |
| `MAINTENANCE` | Watchdog launch/refresh hold only; existing processes keep running |
| `ALGO-HALT-YYYYMMDD` | Dated algorithmic daily-loss flag, distinct from the new durable loss-latch library |

Review the cause and broker exposure/protection before an authorised operator clears a
flag. Do not delete flags merely to make the status green. `hq status` reports five core
components; it is not full-fleet verification. Neither HALT nor stopping flattens exposure.

---

## Known limitations

- **Neural model needs 300 complete labels** before it will promote anything. It is honest about
  this rather than shipping an untrained model.
- **Broker timestamp basis is not guaranteed UTC.** Old-data warnings and closure metadata
  are not interchangeable; closure is never established by comparing broker epochs to local now.
- **PineTS Pine v5/v6 compatibility varies** — some scripts won't compile.
- **The broker account is a DEMO account.**
- **The dashboard is read-only by design** — it has no order controls.
- `pnl_update` dominates the event table; use `exclude=pnl_update` for a readable feed.
- **New safety modules are not assumed activated.** `loss_halt.py` and `stop_legality.py`
  are additive libraries until callers demonstrably consult them. Portfolio caps are
  read-only diagnostics, not enforced new-entry limits.
- **Magic-only attribution is coarse:** both algo engines share legacy magic 20261015;
  current registry versions do not establish historical version provenance.
- **AI provider availability is not certified by unit tests.** Candidate configuration was
  present during this refresh, but no live provider request/credit/model check was performed.
  Unsupported OAuth transports or provider errors cause abstention, not invented extraction.
- **Research is not observed performance.** Monte Carlo probabilities are explicitly
  simulated estimates from observed trade inputs, not observed returns. Unavailable inputs
  must not be replaced with demo/example records in production panels.
- **Source can be newer than the running server.** `/api/portfolio` and `/api/attribution`
  are present in the reviewed route map; the 17:31Z live probe returned 404 for portfolio.
  No service was restarted by this documentation task; service lifecycle belongs to its owner.

---

## Troubleshooting

**Dashboard won't load** — `netstat -ano | findstr :8490`. Nothing listening? `hq start`.

**Connect form appeared instead of auto-login** — the 180 s nonce expired or was consumed.
Reload locally, or use the token from **System → Dashboard credential**. Direct LAN access
is not supported and a token does not bypass the loopback Host restriction.

**"Session expired"** — sessions last 8 h. Reload; auto-login re-establishes it.

**"Activity: Request failed"** — check **System → Process & guard health**. Cached data stays
visible and is marked stale.

**Pine compile fails** — try a registered strategy first to confirm the runtime is healthy.

**Labels aren't accumulating** — confirm the collector is running:
`neural_label_collector.py` with no arguments prints the counts.

**Everything empty but "Connected"** — MT5 isn't attached. `Account: —` means the broker
snapshot couldn't be read, not that the account is flat.

## What changed in this doc refresh

Updated the existing entry point with CLI/watchdog scope, auto-login/token details, complete
route coverage (identity/portfolio/attribution included), closed-bar Pine semantics and
completed-label health/gates. Replaced stale test totals with executed per-suite results,
including current journal/watchdog/legacy prop-suite failures; documented library-only safety, demo account and
observed-vs-simulated research limits. Evidence is under `agent-reports/doc-refresh-*` and
the handoff is `agent-reports/docs-refresh.md`.
