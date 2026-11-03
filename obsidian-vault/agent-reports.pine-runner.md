---
slug: agent-reports.pine-runner
type: note
graph: gitnexus
---

# Pine Runner — signal-relay

**What shipped.** `pine_runner.py` — a dry-run TradingView Pine Script strategy runner that executes native `.pine` strategies on live MT5 data via LuxAlgo's PineTS bridge (`pinets_runner.run_pine_strategy` → `pinets_bridge.js` → Node.js). It never places an order: `record_signal()` writes only to `signals.db` (`trades` table, `status='pine_signal'`, `msg_id='pine_<name>_<ts>'`); `executor.py` is never imported and no MT5 order function exists in this module. `paper_mode` config flag (default `true`) gates the mode; runner is paper-only by construction regardless.

**API.** `load_strategy_config()` → list of `{name, enabled, paper, path, symbol, timeframe}` from `config.pine_strategies` (`[]` OK). `run_strategy(name)` → resolves registry entry (or `strategies/<name>.pine` fallback), runs `pinets_runner.run_pine_strategy(file, symbol, timeframe)`, returns enriched `latest_signal` (`{name, ok, action, price, sl, tp, reason, symbol, timeframe, error, ts}`). `run_all_strategies()` → `dict[name → signal]` over enabled strategies only. `run_forever(interval_s=60)` → 60s loop with `pine.lock` single-instance lock and HALT/PAUSE/STOP file checks (HALT/STOP stop; PAUSE skips a pass).

**Config change.** `config.json` gained `"paper_mode": true` and `"pine_strategies"` (a list — on disk it currently registers `ema_cross` and `RSI + EMA Trend`, both enabled + paper + dry-run note; an empty list `[]` is equally valid while the user has no `.pine` files), plus a `pine_note`. Entry shape the user adds:

```json
{ "name": "ema_cross", "enabled": true, "paper": true, "path": "strategies/ema_cross.pine", "symbol": "XAUUSD", "timeframe": "H1" }
```

**Test verdict.** `test_pine_runner.py`: 4 tests — (1) config block loads (`pine_strategies == []`, `paper_mode` present), (2) registry loads empty OK, (3) `run_strategy("ema_cross")` returns valid structure (action/price/sl/tp, correct file+symbol+timeframe forwarded to the bridge, MT5 stubbed since no terminal here), (4) dry-run records to a temp `signals.db` copy with `msg_id='pine_ema_cross_<ts>'`, `status='pine_signal'`, and confirms no MT5 order path (`executor` never imported). `py_compile` clean for both files; all 4 tests pass.

**How to add a strategy.** Drop a `strategies/<name>.pine` file (existing: `ema_cross.pine`, `rsi_ema_trend.pine`), then add a record to `config.pine_strategies` with `enabled: true`. Run manually: `python pine_runner.py ema_cross`; loop: `python pine_runner.py` (60s). Create `HALT`/`STOP` next to `pine_runner.py` to stop, `PAUSE` to skip passes.

**Dry-run guarantee.** Structural: `pine_runner.py` imports only `pinets_runner`, `sqlite3`, stdlib — never `executor`, never `mt5.order_send`/equivalent; `record_signal` performs a single `INSERT` into `signals.db.trades` and nothing else. Paper mode is on by default and cannot turn this runner into an execution path.

