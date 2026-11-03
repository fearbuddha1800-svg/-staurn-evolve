---
slug: ARCHITECTURE
type: note
graph: gitnexus
---

# Quant HQ — Runtime Architecture

Source review/read-only verification: 2026-10-17. This map does not assert that every
library is activated or the whole codebase was audited. See [README](README.md) for
commands, full API and executed tests; [Operator Guide](HQ_USER_GUIDE.md) for the UI.

## Component map

```text
Telegram watched channels                   Owner DM console
          |                                       |
          +-------------- daemon.py --------------+
                          |
               parser.py / OCR / ai_filter.py
                          |             |
                          |       model_router.py (bounded AI calls)
                          v
                    executor.py <---- strategy.py / strategy2_live.py
                    execute()          execute_algo() (enabled in config)
                          |
              policy + guards + sizing + news gate
                          |
                     MT5 order_send
                          |          lost acknowledgement
                          +--------------> reconciliation.py (read-only checks)
                          v
                 broker position + trades ledger
                          |
                       manage.py ---> protective BE/trailing requests to MT5
                          |
                   event_bus.py publications
                (process-local callbacks + SQLite persistence)
                          v
       signals.db: trades / events / lineage / neural_labels
                 |                             |
                 v                             v
     cockpit.py read adapters        neural_label_collector.py watch
                 |                   entry features + close outcomes
     cockpit_runtime.py HTTP/auth              |
                 |                      label_health.py
     cockpit_ui.html + cockpit_assets          |
                 |                 status/evaluation at >=300 usable labels
      localhost:8490 six-view UI                |
                                   scalp360/neural.py EvalReport
                                   (not automatic live activation)
```

The browser never sends orders, modifies stops or closes positions. Ledger and broker
evidence differ: ticket trace reads ledger rows and independently seeks broker-confirmed
position status. Each process using MT5 attaches for itself; the daemon does not own a
machine-wide MT5 attachment. Telethon's writable session must not be shared by concurrent
ingest clients.

## Signal → parse → execute → manage

| Component | Responsibility/state |
|---|---|
| `daemon.py` | Watch-list ingestion; owner-only DM console separate from signals; notifications; `daemon.lock` |
| `parser.py` | Regex text-to-signal fast path; ambiguous messages must not become guessed entries |
| `ai_filter.py`, `ocr.ps1` | OCR/provider extraction, recap screening, confidence, price sanity and cross-channel dedupe |
| `model_router.py` | AI deadline, concurrency and budget bounds; explicit abstention on failure |
| `executor.py` | `execute()` for relay and `execute_algo()` for algos; policy, shared guards, sizing, news, broker send and ledger |
| `reconciliation.py` | Read-only reconciliation after a missing send acknowledgement, never another sender |
| `manage.py` | Protective management for relay/algo magics; original R in `manage-state.json`; `manage.lock` |
| `strategy.py` | Closed-H1 EMA/RSI pullback; configured XAUUSD/EURUSD; `strategy.lock` |
| `strategy2_live.py` | London H1 breakout; XAUUSD only; `strategy2_state.json`, `strategy2.lock` |
| `news_fetcher.py` | High-impact USD cache `news_calendar.json`; failed refresh retains old cache |
| `notify.py`, `report.py` | Notifications/reporting, not browser controls |

Both algorithmic configurations enable `algo_entry_authority`: entries use
`executor.execute_algo()` and its HALT/dedupe/daily-count, allowed-symbol, max-open,
free-margin and news guards. Direct-send legacy rollback branches remain: shared guards
must not be claimed if that switch is disabled. News filtering is fail-open on errors.
Configured management is BE at +1R, trailing from +1.5R at 0.5R distance, every 10 seconds.
Broker legality may defer a stop. Stopping manage stops future automated updates, not
existing native broker stops, and does not close positions.

`_reconcile_lost_ack()` invokes `reconcile_send()` on a missing-ack failure branch, not
normal success. Results include `CONFIRMED_FILLED`, `CONFIRMED_PLACED`, `CONFIRMED_ABSENT`
and `UNKNOWN`, plus native-stop/partial-fill evidence. **UNKNOWN is not permission to
retry.** A stateful `(magic,msg_id)` reconciler also exists; that does not prove every
caller uses its persistent registry.

## Event bus → dashboard

`event_bus.py` combines process-local subscriptions with persisted SQLite `events`.
Callbacks are not cross-process transport; the dashboard reads history written by other
processes. WAL/busy timeouts support concurrent readers/writers. Relay trace IDs use
`<chat_id>:<msg_id>`; order/fill/open and management close/P&L events retain linkage where
available. `/api/events` accepts trace_id, stream, limit 1–500 and one exclude type.
The UI excludes `pnl_update` at read time; storage/writers remain intact. SSE is finite
replay ending in `[DONE]`, not a live subscription.

| Table | Meaning |
|---|---|
| `trades` | Recorded decisions/executions; paper `pine_signal` rows are not fills |
| `events` | Timestamped event envelopes with source, payload and trace ID |
| `intents`, `positions` | Bridge reservation/lineage, not universal legacy coverage |
| `event_claims`, `update_claims`, `cursors` | Bridge idempotency/recovery |
| `neural_labels`, `neural_label_map` | Features/outcomes and ticket linkage |

`scalp360_bridge.py` exposes additive lineage, risk, timing, Pine and evaluation utilities;
it is not proof that its alternative executor/guards govern all legacy paths. Production
panels must use observed data or report unavailable; test/example/paper records are not
production observations.

Dashboard file ownership:
- `cockpit.py`: defensive MT5/SQLite/config/research read adapters.
- `cockpit_runtime.py`: routes, authentication, Host/origin and strict input validation,
  bounded Pine runtime.
- `cockpit_ui.html`: six-view shell and chart/scratchpad controls.
- `cockpit_assets/quant.js`, `quant.css`: local rendering/polling/styles.

Opening `http://localhost:8490` injects a single-use, in-memory 180-second nonce. JS posts
it to `/api/bootstrap` and receives an eight-hour HttpOnly, SameSite=Strict session cookie.
`POST /api/session` with `{token}` is the fallback. `.cockpit-token` persists the secret;
`COCKPIT_TOKEN` overrides it in the server. Authenticated `/api/token` supplies System →
Dashboard credential; `hq token` prefers the file and only falls back to the environment
when it is missing. Host validation restricts supported access to loopback; a token does
not enable direct LAN access. DELETE session clears the caller's cookie.

Core state/activity refresh roughly every 15 seconds; other views cache 60 seconds and
reload on entry/Refresh. Failed reads may retain visibly stale previous data. An unavailable
broker snapshot is not a zero balance or proof that exposure is flat.

## Identity and portfolio observations

`strategy_identity.py` resolves configured magic → ID/version/label. Relay `20261014`,
combined algo `20261015`, manual/other `0` are configured; others remain unknown.
`/api/identity` returns registry plus open-position ownership. The two algo engines share
legacy magic, so this cannot distinguish their individual positions.

`portfolio_attribution.py` groups by ID **and version**, using the current registry.
`/api/attribution` reads a 90-day UTC window of trading deals, including profit, commission,
swap and fee, excluding funding/balance types. Counts are deals, not round-trip trades;
current magic mappings cannot infer historical versions.

`portfolio_risk.py` reuses quant mark-to-stop valuation and reports native FX exposure,
symbol lots, concentration and explicit unknowns through `/api/portfolio`. Caps are
**diagnostics**, not entry enforcement. Stop risk is an estimate, not maximum loss; gaps,
fees, slippage and execution uncertainty remain. Unlike currency units must not be summed;
metals/CFDs may have stop valuation while FX decomposition is unknown.

## Pine and closed bars

`/api/candles` returns real MT5 OHLCV with the newest live/forming bar retained. It reports
`timestamp_basis="broker as supplied"`, `forming_bar_excluded` and `last_bar_closed`.
The reviewed chart path uses exclusion false/closure null; closed-only reads use exclusion
true and `last_bar_closed=false` about the excluded final received bar, not an independently
measured venue-close timestamp.

`/api/pine_series` and `/api/pine/compile` use `cockpit_runtime.run_pine()` →
`candles_data(...,closed_only=True)` → `pine_series_bridge.js` → local PineTS. The final
received bar is conservatively dropped. Broker epochs have no guaranteed timezone:
**never compare them with local now to infer closure**. `bar_parity.py` separately offers
arithmetic closure checks and in-memory bar-key idempotency; callers must supply `now`
on the same epoch basis. It is not a global DST converter or persistent replay database.

Pine source is owner-trusted, not sandboxed; bytes, candles, concurrency and runtime are
bounded. PineTS v5/v6 compatibility varies. Registered files are `rsi_ema_trend.pine` and
`ema_cross.pine` under `strategies/`; scratchpad compilation does not overwrite them.
The separate `pine_runner.py` → `pinets_runner.py` → `pinets_bridge.js` path records paper
signals with no broker-order switch. The Python transpiler is not the dashboard compiler.

## Learning loop: collection ≠ training ≠ activation

`neural_label_collector.py watch [seconds]` polls ledger/broker history without sending
orders. Entry snapshots yield 25-dimensional vectors (indicators, spread/missingness,
stop distance, session, weekday, symbol and policy). Close reconciliation preserves
original stop risk and sets outcome 1 for positive realised R, otherwise 0: realised-profit
classification, not independent TP-before-SL classification despite an older module comment.

The watchdog supervises watch mode; HALT/PAUSE do not stop it, STOP exits it. Status mode
evaluates once enough completed labels exist; watch mode collects, not automatically
trains every pass. At the 2026-10-17T17:31Z read-only probe: **3 recorded, 2 complete,
1 pending**, no last evaluation. The 300-complete-label gate is unmet. `/api/neural.health`
comes from `label_health.build_report()` for DB/map/feature integrity and accumulation rate.

`scalp360/neural.py.evaluate()` refuses fewer than 300 usable labels. The challenger is
small logistic regression, not a deployed neural policy. It uses a final 20% holdout and
training-tail validation threshold. PROMOTE requires AUC >= 0.58 and
`model_net > baseline_net > 0`; KEEP_SHADOW uses AUC >= 0.55. A purged-splits helper exists
but evaluate does not currently invoke it: complete purged-k-fold evaluation is not
verified. `cost_per_trade` defaults to zero and net uses binary win/loss scoring minus
that parameter, not complete broker-cost cashflows. Review these limitations before
relying on a recommendation. An EvalReport does not replace the live entry engine.

## Safety libraries and lifecycle

`loss_halt.py` is a durable SQLite daily net-realised-loss latch/audit library. Day rollover
does not clear a latch; recovery needs fresh broker reconciliation, operator and reason.
It is not the dated algo flag and is **library-only until entry integration is proven**.
`stop_legality.py` provides fresh-tick/side/distance/grid/freeze preflight, widening opt-in
and exact broker-position read-back. It sends nothing and does not automatically patch
the existing manager/executor: also library-only until integration is proven.

`hq.py` / `hq.bat` control cockpit, daemon, manage, strategy and strategy2. The watchdog at
`C:/Users/voidk/.hermes/scripts/signal-relay-watchdog.py` has a wider list including
`luxalgo_orchestrator.py` and `neural_label_collector.py watch`, and calls the unified
LuxAlgo manager. It holds on STOP/MAINTENANCE, serializes checks and syntax-checks source.

HALT blocks shared new entries while management continues. PAUSE is not universal:
daemon and strategy2 consult it; the reviewed RSI strategy/shared executor path does not.
STOP exits polling loops and suppresses watchdog launches. MAINTENANCE suppresses watchdog
work but does not stop running processes. Dated `ALGO-HALT-YYYYMMDD` flags are separate
algorithmic controls. Review cause before clearing any flag.

The LuxAlgo manager presents services/libraries as one ecosystem. Trade-relay (:8484)
is shadow/audit, not MT5 execution; local MCP (:3333) is a tool surface. Source/sample
constraints apply to research. Monte Carlo outputs are **simulated estimates from observed
trade inputs**, not observed returns. Missing inputs stay unavailable, never synthetic
production history.

## What changed in this doc refresh

Removed obsolete line counts, frozen DB totals, old flat-panel/polling claims and unrerun
profitability tables. Added auth, CLI/watchdog scope, identity/portfolio, closed bars,
learning gates and library-only safety boundaries. README and `agent-reports/docs-refresh.md`
record executed tests and limitations. The previous architecture is preserved in
`agent-reports/architecture-before-refresh.md` as historical, not current, documentation.

## LuxAlgo cockpit integration (verified 2026-11-02)

All six read-only routes returned HTTP 200 on authenticated localhost:8490 probes:

| Package | Cockpit route | Current boundary |
| --- | --- | --- |
| luxalgo-mcp-server | `/api/luxalgo` | Ecosystem health, local MCP :3333 and hosted MCP status |
| edge-stats | `/api/edge` | Sample-aware estimates; low-sample refusal remains intact |
| trade-journal | `/api/journal` | Existing decision journal; no write surface |
| prop-firm-sim | `/api/prop_sim` | Explicitly unavailable: broker-backed HTTP simulation remains disabled |
| whale-options | `/api/whale` | Bounded read-only adapter to :8787 status/events; unavailable until a feed service runs |
| market-trackers | `/api/market_intel` | Source-backed records with provenance |

`cockpit_assets/quant.js` exposes these modules in Intelligence. `whale_bridge.py`
never launches fixtures or synthetic tapes, retains upstream feed metadata, and returns
empty rows with an explicit reason on unavailable/malformed upstream responses. An
HTTP 200 means the integration boundary responded, not that live market inputs exist.
Prop simulation is not merely gated by ten trades: current observational HQ policy
forbids invoking its broker-backed offline bridge over HTTP. Pine HTTP execution also
remains disabled until an isolated worker exists; this integration does not weaken it.

Hermes default config already registers enabled `luxalgo_local` through the local
`luxalgo-mcp-server/mcp-launcher.bat`, plus the hosted `luxalgo` endpoint. No config
rewrite or gateway restart was required here. Local MCP health :3333 and relay health
:8484 returned 200. Authenticated relay status confirmed simulator-only account `sim`.
The existing relay notification config selects fill/reject/error/kill/flatten events;
its configured Telegram target matches Signal Relay Feed `-1004403985547`, and the bot
credential is present. **End-to-end Telegram delivery was not exercised or confirmed**;
no orders, kill-switch transitions, or test chat messages were created for verification.

Verification: Node syntax check passed; ten bridge unit tests passed (seven existing,
three new Whale tests). Exact live route status evidence is recorded in
`agent-reports/luxalgo-endpoints-live.json`. Only cockpit was restarted; relay and
broker/strategy engines were not restarted.

