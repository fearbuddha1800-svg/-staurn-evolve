---
slug: agent-reports.architecture-before-refresh
type: note
graph: gitnexus
---

# Signal-Relay — Complete System Documentation

Living document — update when components change. Regenerated 2026-10-16 from source: daemon.py, executor.py, manage.py, strategy.py, strategy2_live.py, cockpit.py, news_fetcher.py, parser.py, scalp360_bridge.py, pinets_runner.py, pinets_bridge.js, pine_script_parser.py, config.json, event_bus.py, signal_inbox.py, test_suite.py, test_strategy2_live.py, scalp360/{events,gold_parser,risk,lineage,cursor,executor,ai_extract,neural,timing,console}.py, agent-reports/*.md.

---

## 1. SYSTEM MAP

```
Telegram channels (watch list in config.json)
        │  Telethon userbot session (daemon.py owns the only live MT5 attach)
        ▼
daemon.py  (ingest + console, magic 20261014)
        ├─ console branch: DMs from owner 8877588890 only (status/close/closeall/pause/resume/help)
        ├─ channel branch: new messages → parser.py (regex fast path)
        │      ├─ OCR (ocr.ps1) for image-only posts
        │      ├─ ai_filter.py (LLM extraction, min_confidence 0.65) — results/recap screen
        │      ├─ freshness gates: result-language screen, live-price sanity (±0.15% market / ±1.0% pending),
        │      │      cross-channel dedupe (10-min window)
        │      └─ scalp360 bridge zone-aware parse probe (gold_parser zones preserved, additive only)
        │
        ▼ executor.py  (risk gate → MT5 order_send, magic 20261014)
        ├─ policy: signal_policy[channel] (shadow / sl_mode atr|channel / tp_mode none)
        ├─ news gate: High-USD [pre, post] window → skipped_news_window (fail-open)
        ├─ guards: HALT, dedupe (msg_id), daily cap 20, allowed symbols, max 5 open,
        │      free margin ≥30%, require_sl
        ├─ sizing: risk_pct % of balance on SL distance (fallback fixed lot 0.10, cap 0.10)
        └─ stops validation: SL/TP not closer than stops_level, correct side of entry
        │
        ▼ MT5 (MetaQuotes-Demo, "Algo Trading" toolbar must be ON)
        │
        ▼ manage.py  (BE at +1R, trail 0.5R from +1.5R, magic 20261014 + algo magic 20261015)
        │      interval 10s, state in manage-state.json, STOP file halts
        │
        ▼ signals.db  (trades ledger + events + lineage tables + neural_labels)
        │
        ▼ notify.py  → DM chat 8877588890 (user); daily 21:00 report cron (af95658ab7f2)
        │
strategy.py  (RSI pullback, EMA50/200 trend, ATR SL/TP, magic 20261015) ───┐
strategy2_live.py (London breakout H1 XAUUSD, magic 20261015, comment "strat2") ─┤→ manage.py trails both
pinets_runner.py → Node pinets_bridge.js → PineTS dist → JSON signals (paper/parallel build) ─┘
        │
        ▼ trade-relay (external Node, :8484)  ◄── shadow feed of every executed signal
        ├─ dashboard http://localhost:8484
        ├─ independent risk rails + kill switch (sim account)
        └─ MCP server → Hermes agent tools (mcp_trade-relay_*)
        │
cockpit.py  (dashboard http://localhost:8490, read-only)
        ├─ /api/state → account, positions, day P/L, engines, ledger, channels, inbox, journal,
        │      neural_labels, pine_count, halt/pause/stop, trade_relay_up
        ├─ /api/events (last 100, ?trace_id=, ?stream=1 SSE) → full signal→intent→order→position chain
        ├─ /api/neural / /api/latency / /api/lineage / /api/pine / /api/inbox / /api/journal /
        │      /api/mobile / /api/trace/<ticket>
        └─ polls every 5s
        │
event_bus.py (in-process pub/sub, SQLite-persisted table `events`, 15 types, trace_id queryable)
        │
scalp360 layer  (bridge: intents/positions/event_claims/neural_labels/cursors/update_claims tables)
```

Data flow end-to-end: Telegram message → daemon on_message → trace_id=`<chat_id>:<msg_id>` → `signal_received` event → parser → policy/news guards → `execute()` → MT5 fill → `order_placed/order_filled/position_opened` events → trades ledger row → manage.py BE/trail passes → `position_closed`/`pnl_update` events → cockpit `/api/events?trace_id=` replays the chain.

---

## 2. EACH ENGINE

### daemon.py — ingest + Telegram console
- **What it does:** Telethon userbot watches configured channels; parses signals; executes via executor; reports via notify. Owns the only live MT5 attach in the relay process.
- **Process file:** `daemon.py` (915 lines). Runs `python daemon.py`.
- **Lock file:** `daemon.lock` — single-instance via PID file + live-process check; stale locks overwritten.
- **Config keys:** `mode` (auto/confirm), `channels`, `notify_chat_id`, `signal_policy`, `news_filter`, `ai`.
- **Start/stop:** Start with `python daemon.py`. Stop: create `STOP` file (clean exit of serve loop) — also creates `HALT` to stop new entries only. Restart: delete STOP/HALT/PAUSE and relaunch; single-instance lock evicts a dead predecessor.
- **Risk controls:** HALT/PAUSE pre-execute gates (daemon-side only), dedupe, price-sanity freshness, `require_sl`, news window skip, channel shadow policy.
- **Console auth:** DM only, from Telegram user id 8877588890 in the daemon's own DM chat (chat_id==sender_id==OWNER_ID). All other DMs ignored silently, never parsed as signals. Commands: `status`, `close <ticket>`, `closeall`, `pause`, `resume`, `help`. Replies via `notify._send_sync` to notify_chat_id.
- **Files:** `telethon.session` (session), `daemon.log`, `PAUSE`/`STOP`/`HALT` switch files.

### executor.py — MT5 execution + risk
- **What it does:** Takes a parsed signal dict, attaches to the running MT5 terminal, applies policy + guards + news gate + sizing, sends `order_send`, records to `trades` in signals.db, emits bus events.
- **Process file:** `executor.py` (419 lines). Library — imported by daemon.py; no standalone loop.
- **Lock file:** none.
- **Config keys:** `risk.*`, `sizing.*`, `news_filter.*`, `signal_policy.*`, `require_sl`.
- **Start/stop:** No process of its own — starts with daemon. MT5 "Algo Trading" toggle must be ON (resets OFF on terminal restart → retcode 10027).
- **Risk controls:** HALT file; `trade_allowed` terminal check; duplicate msg_id; daily cap 20 (skips don't count); max 5 open positions; free margin ≥30%; allowed_symbols list; require_sl; stops_level validation; news-window skip (fail-open); lot cap 0.10; fallback lot when no SL/market data.
- **Magic:** 20261014 (relay). `close_all_positions()`, `sl_to_breakeven(position)` used by manage/console.

### manage.py — break-even + trailing engine
- **What it does:** 10s loop over open positions with magic 20261014 (relay) or 20261015 (algo). SL→entry at +1R (be_at_r), then trails 0.5R behind price from +1.5R (trail_from_r/trail_dist_r). Ratchet-only, never widens. Original SL (R basis) preserved in manage-state.json.
- **Process file:** `manage.py` (261 lines). Run `C:/Users/voidk/miniconda3/python.exe manage.py`.
- **Lock file:** `manage.lock`.
- **Config keys:** `manage.be_at_r`, `manage.trail_from_r`, `manage.trail_dist_r`, `manage.interval_s` (+ `be_buffer_points` default 10).
- **Start/stop:** `STOP` file next to daemon.py halts it too. Reads config each pass. HALT does NOT stop it (protecting open trades is always allowed).
- **Risk controls:** BE buffer 10 points; `positions_get() is None` (API error) skips the cycle and touches no state; single-instance lock; read-only-ish MT5 attach (no shutdown mid-trade).

### strategy.py — algo engine (RSI pullback)
- **What it does:** Multi-factor trend-pullback on closed H1 bars. EMA50 vs EMA200 trend; RSI(14) crosses back up through `rsi_buy` (buy) / down through `rsi_sell` (sell). SL = `atr_sl_mult`×ATR, TP = `atr_tp_mult`×ATR (config `use_tp` false → manage trails). risk_pct sizing, skip_hours_utc, one position per symbol, max `max_positions_total` algo positions, daily loss cap 2% → ALGO-HALT-<date> file.
- **Process file:** `strategy.py` (344 lines). Run `python strategy.py` (persistent loop). Backtest without trading: `backtest.py` imports Indicators/decide.
- **Lock file:** `strategy.lock`.
- **Config keys:** `algo.*` (symbols XAUUSD+EURUSD, risk_pct 1.0, max_positions_total 3, daily_loss_cap_pct 2.0, rsi_buy 35, rsi_sell 65, atr_sl_mult 2.0, atr_tp_mult 3.0, use_tp false, strength 1.0, skip_hours_utc [22,23]).
- **Magic:** 20261015 — managed by manage.py identically to relay trades.
- **Risk controls:** daily loss cap writes ALGO-HALT-<date> (shared with strategy2_live); skip dead hours; max positions; single-instance lock; STOP file.
- **Backtest stats:** XAUUSD +11.3R PF 1.12; EURUSD +10.2R PF 1.10 (SL-first conservative sim, 0.07R costs). GBPUSD excluded (negative).

### strategy2_live.py — London breakout (strategy 2)
- **What it does:** H1 London-open breakout, XAUUSD only. Range = H1 bars opening 00:00–06:59 UTC (all 7 required, hi>lo). Signal window 07:00–14:59 UTC: first close beyond range ±0.10×ATR14 = entry. SL = opposite range edge capped at 1.50×ATR14. No TP — manage.py trails (magic 20261015, comment "strat2"). One entry per UTC day in strategy2_state.json. Daily loss cap 2% → ALGO-HALT-<date>.
- **Process file:** `strategy2_live.py` (480 lines). Run `python strategy2_live.py`. Stop: STOP file or `strategy2.enabled=false`.
- **Lock file:** `strategy2.lock`.
- **Config keys:** `strategy2.enabled true`, `symbols ["XAUUSD"]`, `risk_pct 0.5`, `max_positions 1`. Frozen variant r2-cut15-buf010-cap150.
- **Risk controls:** one entry/day, max 1 open strat2 position, daily loss cap (shared ALGO-HALT file with strategy.py), HALT/PAUSE/STOP respected for new entries, stops_level validation, single-instance lock.
- **Backtest stats (verified):** XAUUSD 1052 trades, PF 1.113, +64.0R, maxDD 28.3R, win% 34.9, exits SL 518 / BE 167 / Trail 367. EURUSD failed acceptance (PF 1.045, DD 31.8R) — deliberately NOT traded.
- **Tests:** `test_strategy2_live.py` — 14 pure-function cases (DST offsets, range computation, signal detection, buffer/boundary edges, ATR math, SL geometry, config block) — ALL PASS.

### news_fetcher.py — High-impact USD news gate
- **What it does:** Fetches ForexFactory weekly calendar (free, no key), keeps High USD events, writes `news_calendar.json` atomically. `block_reason(cfg, now, events)` returns a reason string when now ∈ [event−pre, event+post]. Fail-open: any error → trade proceeds.
- **Process file:** `news_fetcher.py` (270 lines). Standalone `python news_fetcher.py` (exit 0 refreshed / 1 failed). Watchdog (`scripts/signal-relay-watchdog.py`) refreshes every ~15 min.
- **Lock file:** none.
- **Config keys:** `news_filter.enabled`, `news_filter.pre_minutes` (5), `news_filter.post_minutes` (3).
- **Risk controls:** past events purged (post window +5 min slack); skips don't consume daily cap (`NOT LIKE 'skipped%'`); fail-open; calendar never overwritten on failure.

### cockpit.py — dashboard
- **What it does:** Stdlib-only HTTP dashboard on http://localhost:8490. Read-only for MT5 and all databases. GET / (dark UI, polls /api/state every 5s), /api/state, /api/inbox, /api/journal, /api/mobile, /api/neural, /api/latency, /api/lineage, /api/pine, /api/events (SSE), /api/trace/<ticket>.
- **Process file:** `cockpit.py` (860 lines). Run `python cockpit.py`.
- **Lock file:** none.
- **Config keys:** reads `config.json` (channels, signal_policy notes, pine_strategies); PORT 8490 hardcoded.
- **Panels:** Signal Inbox, Execution Lifecycle, Simulation (Paper Mode), Entry block, Sources, Account (gauge), Open positions (with TRACE drill-down), Event Journal, Mobile mockup, Neural Readiness, Latency, Lineage, Pine Strategies. Footer shows engines status (daemon/manage/strategy/trade-relay), HALT/STOP/PAUSE, trade-relay :8484 up/down.
- **Risk controls:** read-only URI connections to signals.db; bridge on `:memory:`; defensive imports (empty states when scalp360 missing); esc() sanitizer on all innerHTML.

### trade-relay — external shadow relay + rails
- **What it does:** Independent Node service on :8484. Consumes shadow feed of every executed signal; flight recorder (payload → parse → risk verdicts → order → fill); dashboard http://localhost:8484; streams fill/reject/error/kill events to Telegram channel "Signal Relay Feed" (-1004403985547); MCP server → Hermes agent tools. Runs on a sim account. No local source in this repo.
- **Start/stop:** restart via Task Manager / manual.
- **Risk controls:** allowlist, max daily loss $2k, kill switch (survives restarts).
- **Cockpit panel:** `trade_relay_up` badge via socket connect to localhost:8484.

### watchdog
- **What it does:** Restarts dead engines (daemon/manage/strategy), refreshes news calendar every 15 min via news_fetcher subprocess (guarded, never kills watchdog). Covers turn interruptions that kill agent-spawned processes.
- **Process file:** `C:/Users/voidk/.hermes/scripts/signal-relay-watchdog.py` (outside repo). Cron-driven.
- **Config keys:** none in repo.

### event_bus — central pub/sub
- **What it does:** In-process pub/sub with SQLite persistence (table `events`, WAL, 30s timeout, indexes on trace_id/type/ts). 15 event types. Subscriber exceptions never break publishing. `bus` singleton shared by all components.
- **Process file:** `event_bus.py` (197 lines). `publish`/`subscribe`/`history` module-level helpers.
- **Lock file:** none.
- **Event types:** signal_received, zone_parsed, risk_approved, order_placed, order_filled, position_opened, position_closed, pnl_update, neural_prediction, channel_score_update, engine_status, alert, halt_triggered, pine_signal, breakout_signal.
- **Traceability contract:** daemon trace_id=`<chat_id>:<msg_id>`; executor emits order_placed/order_filled/position_opened keyed by trace_id; manage emits position_closed/pnl_update with trace_id recovered from trades.msg_id by ticket; engines emit breakout_signal; cockpit `/api/events?trace_id=` replays the chain.

### neural collector (scalp360/neural.py)
- **What it does:** Honest ML challenger harness. Zero-dep logistic regression (swappable). Purged chronological k-fold splits with embargo; calibration on val slice; untouched holdout (last 20%); after-cost shadow comparison vs rules baseline. Publish `neural_prediction` event on each evaluate().
- **Process file:** `scalp360/neural.py` (107 lines). Called via `bridge.neural_evaluate(X, y)`.
- **Eval protocol:** `min_samples=300` required (REJECT below). Holdout AUC ≥0.58 AND model net > baseline net > 0 → PROMOTE; AUC ≥0.55 → KEEP_SHADOW; else REJECT. EvalReport {n_train, n_val, n_test, holdout_auc, baseline_winrate, model_winrate, net_after_cost_baseline, net_after_cost_model, decision}.
- **Config keys:** `BridgeConfig.neural_min_labels=300`, `neural_holdout_auc_min=0.58`.
- **Cockpit:** `/api/neural` shows labels collected vs 300, progress bar, last eval AUC + decision badge.

---

## 3. scalp360 LAYER (v0.2 bridge)

Wired into the live relay via `scalp360_bridge.py` (additive — no change to execution path). `make_bridge()` runs idempotent `_ensure_schema()` over signals.db.

### events (`scalp360/events.py`)
- `EventKind`: NEW_ENTRY, UPDATE, RESULT, UNKNOWN. `SignalEvent` frozen envelope {source, message_id, edit_id, text, original_at, received_at, kind}; `event_id` = "source:msg_id:edit_id"; `digest` = sha256(text)[:16]; `age_s()`.
- `recap_heuristic(ev)` — True for recap/summary/digest posts (never become entries).
- `BUS_EVENT_TYPES` frozenset (15 types, synced with event_bus.py).

### gold_parser (`scalp360/gold_parser.py`)
- Source-typed parser for XAUHQ gold format. `Zone{low, high}`, `GoldSignal{symbol, side, entry:Zone, stop, targets:[(label,Zone)], raw}`.
- `ENTRY: 4184/90` → zone (4184.0, 4190.0), never collapsed to a single price. `TP4 ->4145/4120` → zone targets preserved.
- Abstains (None) on ambiguity: missing side/sl/tp, broken geometry (sell SL not above entry zone, buy SL not below), no targets.

### risk governor (`scalp360/risk.py`)
- `RiskGovernor.size(...)` → `SizingDecision{verdict APPROVE|REJECT, quantity lots, reason, risk_amount}`.
- Floor sizing with min-lot reject (never clamps up), fee+slippage reserve per lot, aggregate pending+open risk vs `max_daily_risk_pct`, `daily_halt_drawdown_pct` halt, `max_concurrent`, `max_notional`.
- `RiskConfig{risk_per_trade_pct 0.5, max_concurrent 3, max_daily_risk_pct 2.0, max_notional 50000, daily_halt_drawdown_pct 4.0, lot_step 0.01, min_lot 0.01, fee_per_lot 0.07, slippage_per_lot 1.5}`.

### lineage tables (`scalp360/lineage.py`)
Signal → intent → order → position. Updates bound to (source, message_id, intent_id) — never by symbol/side alone.
- `intents(intent_id PK, event_id, source, symbol, side, state, risk_amount, original_r, created_at, meta)` — states RESERVED/SUBMITTED/FILLED/REJECTED/UNKNOWN. `original_r` immutable.
- `positions(position_key PK, intent_id, ticket, symbol, side, state, original_r, opened_at)` — bind requires FILLED intent + symbol/side match; position_key unique (never double-bound).
- `event_claims(event_id PK, digest, claimed_at)` — idempotent event claiming (with cursor advance in same transaction).
- `IntentState.transition(intent_id, to, expect)` — CAS; stale writer refused.
- `unresolved_unknowns(source)` — SUBMITTED/UNKNOWN intents block re-entry from that source (crash safety).
- `update_position_via_signal(position_key, event_id)` — only sanctioned update path.

### cursor recovery (`scalp360/cursor.py`)
- `cursors(source PK, last_msg_id, updated_at)`. `last(source)` / `advance(source, msg_id)`.
- `recover(source, fetch_page, cursors, page_size=200, max_pages=50)` → `Coverage{expected, fetched, gaps, pct}` — full-gap pagination after outages (not just 10-min catch-up); hits page cap → gap flagged.
- Committed with event claim in the same transaction.

### AI extraction bounds (`scalp360/ai_extract.py`)
- `AIExtractor` wraps a provider-pinned llm callable (never model-shopping per call). `AIExtractConfig{provider nvidia, model z-ai/glm-5.3, timeout_s 8.0, max_calls_per_min 30, circuit_breaker_fails 5, spend_budget_usd_per_day 1.0}`.
- Circuit open after N consecutive failures / rate limit / spend budget → `AIExtractResult{kind UNKNOWN|NEW_ENTRY|UPDATE|RESULT, symbol, side, confidence, evidence, abstained_reason}`. Any failure → UNKNOWN, never a guess. Confidence not calibrated — ranking input only.

### neural eval protocol (`scalp360/neural.py`)
- Requires ≥300 labels in `neural_labels` (else REJECT "insufficient labels").
- Purged splits (embargo=5), calibration threshold on train tail, untouched holdout (last 20%).
- Promote: holdout AUC ≥0.58 AND model net after cost > baseline net > 0. KEEP_SHADOW: AUC ≥0.55. Else REJECT.
- `EvalReport` published as `neural_prediction` bus event.

### timing (`scalp360/timing.py`)
- `StageTimer` — p50/p95/p99/max per pipeline stage. Powers cockpit `/api/latency`.

### console (`scalp360/console.py`)
- `Console{allowed_user_ids, allowed_chat_ids}` — claim-before-send (`update_claims` table) + ack-after-send idempotency. `pause`/`resume`/`is_halted`/`authorized`. `core_set_halt` callback propagates to real core halt when wired.

---

## 4. PINETS PIPELINE

Python `pinets_runner.py` → Node `pinets_bridge.js` → LuxAlgo PineTS `dist/pinets.min.cjs` → JSON signals.

**Flow:** `run_pine_strategy(pine_file, symbol, timeframe, count)`:
1. `mt5.initialize()` → `copy_rates_from_pos(sym, TF, 0, count+1)` → drop still-forming bar → candles JSON `{openTime(epoch ms), open, high, low, close, volume}`.
2. Write candles to temp JSON in repo dir.
3. `subprocess.run(["node", BRIDGE, pine_file, candles_path, symbol, tf_str], cwd=BASE, timeout=30, NODE_PATH=PineTS dist dir)`.
4. Bridge instantiates `PineTS(provider, symbol, tf, bars)` with `MT5Provider extends BaseProvider` (24x7 UTC, filters by date/limit), runs `pine.run(pineCode)`.
5. stdout JSON `{ok, symbol, timeframe, bars, plots, open_trades, closed_trades, ledger, position, stats, latest_signal, last_close, error}`.
6. `extract_signal(result)` → `{action buy|sell, price, sl, tp, reason}` or None.

**How to add a .pine strategy:**
1. Place `strategies/your_strategy.pine` (TradingView Pine Script v5, `strategy()` declaration, `ta.*` indicators, `strategy.entry`/`strategy.exit`).
2. `bridge.load_pine_strategy("strategies/your_strategy.pine")` → `pine_script_parser.parse_pine(text)` + `emit_python(strat)` writes `your_strategy_transpiled.py` alongside (Python class with `on_candle(open_, high, low, close, time_ms)` → action dict). Zero third-party deps; best-effort translation, unknown constructs flagged for review.
3. Register in `config.json` `pine_strategies` (list of records or name→map; each {name, enabled, paper, path}). Cockpit `/api/pine` normalizes both shapes.
4. Run `python pinets_runner.py strategies/your_strategy.pine XAUUSD H1` — returns `{ok, plots, trades, latest_signal, ...}`; `extract_signal()` for the actionable signal.

**Existing strategies:** `strategies/ema_cross.pine` (EMA 9/21 crossover), `strategies/rsi_ema_trend.pine` (RSI 14 pullback vs EMA 50, ATR SL/TP 2×/3×).

---

## 5. DATABASE SCHEMA — signals.db

All tables (WAL mode via event_bus; `_db()` in executor creates `trades`):

| Table | Columns | Notes |
|---|---|---|
| `trades` | id INTEGER PK, msg_id TEXT, ts TEXT, symbol TEXT, side TEXT, lot REAL, entry TEXT, sl REAL, tp REAL, order_type TEXT, ticket INTEGER, status TEXT, detail TEXT | Relay ledger (executor `_db()`). 4 rows present. |
| `events` | event_id TEXT PK, ts TEXT, type TEXT, source TEXT, payload TEXT, trace_id TEXT | Event bus persistence. Indexes: `idx_events_trace`, `idx_events_type`, `idx_events_ts`. 4 rows. |
| `intents` | intent_id TEXT PK, event_id TEXT, source TEXT, symbol TEXT, side TEXT, state TEXT, risk_amount REAL, original_r REAL, created_at REAL, meta TEXT DEFAULT '{}' | scalp360 lineage. |
| `positions` | position_key TEXT PK, intent_id TEXT, ticket TEXT, symbol TEXT, side TEXT, state TEXT, original_r REAL, opened_at REAL | scalp360 lineage. |
| `event_claims` | event_id TEXT PK, digest TEXT, claimed_at REAL | Idempotent event claiming. |
| `cursors` | source TEXT PK, last_msg_id INTEGER, updated_at REAL | Per-source message cursors. |
| `neural_labels` | id INTEGER PK AUTOINCREMENT, ts REAL, symbol TEXT, side TEXT, entry REAL, sl REAL, tp REAL, outcome INTEGER, features TEXT | Neural training labels (target ≥300). 0 rows. |
| `update_claims` | claim_id TEXT PK, action TEXT, claimed_at REAL | Console idempotency claims. |
| `sqlite_sequence` | name, seq | Autoincrement bookkeeping. |

`trades` columns read by cockpit `ledger()`: ts, symbol, action(side), status, detail, magic — note cockpit queries `magic` which is NOT in the executor's `trades` DDL → defensive try/except returns [].

---

## 6. CONFIG REFERENCE — config.json (181 lines)

Top-level:
- `mode` — "auto" (parse + execute immediately, risk-guarded) or "confirm" (parse + post, execute only after user approval via agent).
- `notify_chat_id` — "8877588890".
- `channels` — array of 20 numeric Telegram chat IDs (-100...). Empty = nothing watched.
- `notes.mode`, `notes.kill_switch` (HALT file), `notes.mt5_account` (MetaQuotes-Demo).

`risk`:
- `max_lot_per_trade` 0.10, `max_open_positions` 5, `max_trades_per_day` 20, `allowed_symbols` [] (empty = all), `min_free_margin_pct` 30, `require_sl` true.

`sizing`:
- `mode` "risk_pct", `risk_pct` 1.0, `fallback_lot` 0.10.

`manage`:
- `be_at_r` 1.0, `trail_from_r` 1.5, `trail_dist_r` 0.5, `interval_s` 10.

`news_filter`:
- `enabled` true, `pre_minutes` 5, `post_minutes` 3.

`algo`:
- `symbols` ["XAUUSD","EURUSD"], `risk_pct` 1.0, `max_positions_total` 3, `daily_loss_cap_pct` 2.0, `rsi_buy` 35, `rsi_sell` 65, `atr_sl_mult` 2.0, `atr_tp_mult` 3.0, `use_tp` false, `strength` 1.0, `skip_hours_utc` [22,23].

`strategy2`:
- `enabled` true, `symbols` ["XAUUSD"], `risk_pct` 0.5, `max_positions` 1.

`ai`:
- `enabled` true, `min_confidence` 0.65, `openrouter_model` "meta-llama/llama-3.3-70b-instruct:free", `timeout_s` 12, `price_tolerance_pct` 0.6.

`signal_policy`:
- `_default`: {mode: "shadow"}.
- Per-channel overrides keyed by channel id string: {sl_mode: "atr"|"channel", atr_mult, tp_mode: "none", mode: "shadow", note}. 18 channels mapped (see §9).

`pine_strategies` — absent in current file (panel renders empty); list-of-records or {name: {...}} shape accepted by cockpit.

---

## 7. TELEGRAM CONSOLE

- **URL / access:** DM chat with the relay's Telethon account; owner Telegram user id 8877588890 (@v01dkrawl7er). No URL — it's a Telegram DM.
- **Auth model (fail-closed):** command only when `event.chat_id > 0` (private) AND `chat_id == OWNER_ID` AND `sender_id == OWNER_ID`. The Telethon session is a dedicated relay account, not the owner's. Strangers/bots/owner-in-other-chats ignored silently (one log line, no reply). DMs are never parsed as signals. Channel messages (negative ids) never enter console branch.
- **Commands** (case-insensitive, leading '/' tolerated, extra whitespace):
  - `status` — MT5 account balance/equity/free margin, every open position (#ticket SYMBOL DIR lots SL P/L + total P/L), engine uptime, mode + HALT/PAUSE state, last 3 ledger rows.
  - `close <ticket>` — close that exact position (`mt5.positions_get(ticket=…)`). Reply: filled detail or "no open position #N".
  - `closeall` — `executor.close_all_positions()` with per-ticket fallback. Reply: "closed n/m | P/L at close ±X.XX".
  - `pause` — touch `PAUSE` file; new signal entries blocked (open positions keep managing).
  - `resume` — delete `PAUSE`.
  - `help` — command list.
  - unknown → "unknown command: '…' - DM 'help' for the list".
- **Replies:** via `notify._send_sync` → notify_chat_id (same channel as relay reports).
- **PAUSE semantics:** daemon-side pre-execute gate only (checked right after HALT). executor.py and manage.py never read PAUSE — open positions keep being managed and can be closed via close/closeall while paused.
- **Files:** `daemon.py` (console block ~lines 252-557), `PAUSE` switch file, `test_console.py` (48 checks, ALL PASS).

---

## 8. OPERATIONS RUNBOOK

### Start everything
1. MT5 terminal running and logged in (MetaQuotes-Demo); "Algo Trading" toolbar ON.
2. `python daemon.py` — ingest + relay (single-instance lock; `--login`/`--list-dialogs` first-time).
3. `python manage.py` — BE/trail engine.
4. `python strategy.py` — algo engine (RSI pullback).
5. `python strategy2_live.py` — London breakout (XAUUSD).
6. `python cockpit.py` — dashboard http://localhost:8490.
7. Watchdog cron (every 15 min): restarts dead engines + `news_fetcher.py` refresh.

### Restart safely
- Any engine: create `STOP` file → loop exits cleanly → release lock → relaunch. Single-instance lock evicts a dead predecessor (stale PID overwritten).
- Daemon restart: console activates on next serve attempt; ONLINE message lists `console: DM 'help' for commands`.
- Do NOT restart mid-edit (half-finished file risk) — wait for parallel work to land.
- Cockpit serves stale code until restarted.

### Watchdog
- Cron every 15 min. Checks engine liveness via PowerShell `Get-CimInstance Win32_Process` command-line match; restarts dead ones. Runs `news_fetcher.py` subprocess (timeout 240s, fully try/wrapped) — failure never kills watchdog; old calendar kept.

### Emergency stop
- `HALT` file (next to daemon.py) — stops NEW executions instantly; relay/notify keep running. Delete to resume. (Also settable by agent.)
- `PAUSE` file (or DM `pause`) — daemon-side new-entry gate only; open positions keep managing.
- `STOP` file — clean exit of daemon serve loop (also halts manage.py and strategy loops which poll STOP).
- `ALGO-HALT-<YYYYMMDD>` — written by strategy.py/strategy2_live.py when daily loss cap (2%) hit; stops algo entries until tomorrow.
- Kill switch: trade-relay independent rails (allowlist, max daily loss $2k, kill switch survives restarts).
- MT5 "Algo Trading" toolbar OFF also halts all new orders (retcode 10027).

---

## 9. VERIFIED EDGES

### 18 channel policies (config.json signal_policy) with verified expectancies (R after costs, 0.07R round-trip haircut; manage.py trailing exits; V2/V3 exit-geometry method):

| # | Channel (id) | Policy | Verified expectancy | Trades | Win% | maxDD | Note |
|---|---|---|---|---|---|---|---|
| 1 | XAUUSD FREE SIGNALS (-1002165799093) | sl_mode atr, atr_mult 2.0, tp none | **+0.963R** (best) | 11 | 90.9 | 1.07 | go-live |
| 2 | Best Signal Forex (-1002369502254) | sl_mode atr, atr_mult 2.0, tp none | **+0.267R** | 32 | 65.6 | 8.69 | go-live |
| 3 | XAUUSD PRO SIGNAL (-1002692333123) | sl_mode channel, tp none | **+0.096R** | 30 | 51.7 | 5.43 | go-live (V2-A) |
| 4 | Gold Signals VIP (-1001868019139) | sl_mode atr, atr_mult 2.0, tp none | **+0.124R** | 25 | 56.0 | 5.61 | go-live |
| 5 | XAUUSD TRADING MASTER (-1002010239852) | sl_mode channel, tp none | **+0.279R** | 30 | 66.7 | 5.68 | go-live (archive) |
| 6 | XAUUSD GOLD PRO TRADER (-1002620653001) | sl_mode channel, tp none | **+0.248R** | 36 | 61.1 | 6.00 | go-live (archive) |
| 7 | FX SIGNAL TEAM (-1003924380674) | sl_mode channel, tp none | **+0.161R** | 20 | 60.0 | 2.42 | go-live (archive) |
| 8 | GOLD PRO TRADER (-1002520344727) | sl_mode channel, tp none | **+0.149R** | 18 | 55.6 | 3.27 | go-live (archive) |
| 9 | xauusd_signalsq (-1003576321949) | sl_mode atr, atr_mult 2.0, tp none | **+0.303R** | 14 | 71.4 | 2.14 | mass-verify, promote |
| 10 | Forex GDP Free (-1001713690419) | sl_mode atr, atr_mult 2.0, tp none | **+0.281R** | 10 | 60.0 | 2.14 | mass-verify, promote |
| 11 | GOLD FOREX SIGNALS VIP (-1003196282951) | sl_mode atr, atr_mult 2.0, tp none | **+0.161R** | 47 | 57.4 | 5.43 | mass-verify, promote (largest sample) |
| 12 | Gold Signals Daily (-1003762554260) | sl_mode atr, atr_mult 2.0, tp none | **+0.147R** | 11 | 63.6 | 3.27 | mass-verify, promote |
| 13 | FOREX GOLD SIGNALS XAUUSD (-1003723702011) | sl_mode channel, tp none | **+0.126R** | 15 | 46.7 | 3.41 | mass-verify, promote |
| 14 | PRO TRADER (-1002639725270) | shadow | +0.037R best (flat/thin) | 27 | — | 5.53 | shadow (record only) |
| 15 | PREMIUM VVIP FX SIGNAL (-1002647890905) | shadow | -0.029R | 35 | — | 10.57 | shadow (record only) |
| 16 | XAUHQ (-1001207746934) | shadow | +0.002R best (flat) | 32 | — | — | shadow (record only) |
| 17 | SureShotFX (-1001588519179) | shadow | -0.112R (negative) | — | — | — | shadow / do-not-add |
| 18 | Grow Trading (-1001920020352) | shadow | negative | 3 | — | 3.21 | shadow (insufficient data) |
| — | Easy Forex OFFICIAL (-1001284268486) | shadow | 0 verifiable signals | 0 | — | — | shadow |

Mirror clusters: FX PREMIERE (-1001912261779) mirrors Forex GDP (-1001713690419) — promote at most one. Gold Xauusd Trader Signals (-1003011435611) cluster (4 mirrors) — n=8, stay shadow, promote at most one.

### 2 algo strategies with backtest stats
- **strategy.py RSI pullback (EMA50/200 trend filter):** XAUUSD +11.3R PF 1.12 (2023-2026 H1, SL-first sim, 0.07R costs); EURUSD +10.2R PF 1.10; GBPUSD excluded (negative). Exits via manage.py trailing.
- **strategy2_live.py London breakout (r2-cut15-buf010-cap150):** XAUUSD 1052 trades, PF 1.113, +64.0R, maxDD 28.3R, win% 34.9, avg +0.061R/trade, exits SL 518 / BE 167 / Trail 367. EURUSD PF 1.045 DD 31.8R — FAILED acceptance, deliberately NOT traded. 3 rounds / 32 cells tested; EURUSD shortfall structural.

### Honest caveats
- M15 granularity in channel verification; conservative same-bar rule takes worst fill ordering (live manage.py trails on 10s ticks — at least as good).
- Small samples: 10–47 trades per channel; treat as small-sample evidence, reduce risk_pct on promotion, re-verify after 2 weeks shadow.
- No slippage modeling; 0.07R haircut covers spread/commission (same as backtest).
- 48h horizon leaves freshest ~2 days of signals `pending` (excluded from stats).
- MT5 "Algo Trading" toggle resets OFF on terminal restart → retcode 10027 until re-enabled manually.
- Past performance ≠ future results; expectancy is after simulated costs, not guaranteed live.
- EURUSD strategy2 fails acceptance — do not enable for EURUSD.
- Console `close`/`closeall` were unit-tested to the MT5 boundary only; live close not exercised on real positions in tests.
- News filter: algo engines (strategy.py, strategy2_live.py) do NOT go through executor.execute() — they are not gated by news windows (flagged decision item).
- Cockpit `ledger()` queries column `magic` not present in executor's `trades` DDL → returns [] gracefully (defensive).

---

*End of ARCHITECTURE.md.*

