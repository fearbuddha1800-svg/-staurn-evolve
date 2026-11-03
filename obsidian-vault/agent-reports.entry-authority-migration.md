---
slug: agent-reports.entry-authority-migration
type: note
graph: gitnexus
---

# Entry Authority Migration — ONE account execution authority

**Compiled:** 2026-10-17 UTC · **Owner:** integration owner · **Status:** ACTIVE (verified live)

## What changed

Before this migration the two algorithmic engines each built their own MT5 request
and called `mt5.order_send` directly, so algo entries **skipped every shared guard**:
the HALT check, duplicate-msg_id dedupe, daily trade cap, `allowed_symbols`,
max-open, free-margin, and the High-USD news gate. They also carried their own
copies of the fill-type / volume / stop-validation helpers (drift risk).

Now every entry origin submits through one function.

## Order-send inventory — before → after

| Site | Class | Before | After |
|---|---|---|---|
| `executor.py` `execute()` | ENTRY (Telegram) | authority | authority (unchanged) |
| `executor.py` `execute_algo()` | ENTRY (algo) | — | **NEW: the algo authority** |
| `strategy.py` | ENTRY (RSI pullback) | own `order_send` | ✅ calls `execute_algo()` |
| `strategy2_live.py` | ENTRY (London breakout) | own `order_send` | ✅ calls `execute_algo()` |
| `manage.py` | exit (BE/trail) | own `order_send` | unchanged (protective, §6) |
| `daemon.py` `_close_position` | exit (owner console) | own `order_send` | unchanged (owner-authorized, §12) |
| `executor.py` `close_all_positions` | exit | authority helper | unchanged |

The legacy direct `order_send` blocks remain in both strategies **behind the flag**
so the migration is a one-line rollback, not a rewrite.

## `execute_algo()` contract

`executor.execute_algo(symbol, side, lot, sl, tp, msg_id=None, magic=20261015,
comment="algo", dry_run=False, strategy_name=None)`

Applies, in order: MT5 attach → symbol resolution → volume normalization →
`_guards()` (HALT · dedupe · daily cap · symbol visibility · allowed_symbols ·
max-open · free-margin) → **news gate** → symbol_select → `_validate_stops()` →
send → ledger row → `order_placed`/`order_filled`/`position_opened` events.

It deliberately does **not** apply channel `signal_policy` — algo callers have
already computed their own SL/TP from ATR/range geometry.

The magic is stamped on the broker request (`magic=20261015`) so `manage.py`
trails algo positions exactly as before.

## Rollback

```bash
# disable the authority, revert both engines to their legacy direct path
python -c "import json;c=json.load(open('config.json'));c['algo']['algo_entry_authority']=False;c['strategy2']['algo_entry_authority']=False;json.dump(c,open('config.json','w'),indent=2)"
# then restart the two entry engines
taskkill /F /PID $(cat strategy.lock) ; taskkill /F /PID $(cat strategy2.lock)
PYTHONPATH= C:/Users/voidk/miniconda3/python.exe C:/Users/voidk/.hermes/scripts/signal-relay-watchdog.py
```

No code edit is needed to roll back.

## Verification (real output)

| Check | Result |
|---|---|
| `py_compile` on executor.py, strategy.py, strategy2_live.py | OK |
| `test_entry_authority.py` | **8/8 PASS** |
| `test_suite.py` | ALL PASS |
| `tests_360/run_tests.py` | 43/43 |
| `test_strategy2_live.py` | ALL PASS |
| `test_pine_runner.py` | 4/4 |
| `test_neural_collector.py` | 13/13 |
| `test_edge_stats_bridge.py` | PASS |
| engine imports (executor, strategy, strategy2_live, daemon, manage, cockpit, parser, news_fetcher) | OK |
| live fleet after restart | all 6 UP |
| protection during migration | manage.py never stopped; 4 open positions unchanged |

The 8 authority tests prove the guards are consulted and honored: daily cap blocks,
news window blocks, unknown symbol rejects, duplicate msg_id refuses, dry-run never
sends, a filled entry writes a ledger row and emits events, a broker reject is
recorded not hidden, and the Telegram `execute()` remains separate and unchanged.

## Honest limitations

- The guard tests patch the helpers; the live path has not yet been exercised by a
  real algo signal since the restart (no London breakout signal has fired yet today).
  First real fire will confirm end-to-end.
- The ledger has no `magic` column, so algo attribution is by `detail` (`[engine=...]`)
  and by the broker-side magic. A schema migration for a `magic` column is milestone 5.
- Durable intent → reconciliation states (PROPOSED→RESERVED→SUBMITTING→ACK→FILLED→CLOSED)
  are still not implemented; an ambiguous broker outcome is not yet reconciled.

