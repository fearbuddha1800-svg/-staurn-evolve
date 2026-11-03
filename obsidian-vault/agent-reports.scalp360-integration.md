---
slug: agent-reports.scalp360-integration
type: note
graph: gitnexus
---

# scalp360 bridge integration into the live signal-relay

**Date:** 2026-10-16 · **Scope:** wire `scalp360_bridge.py` (verified v0.2 package, 32/32 tests) into the live relay, additively — no behavior change to the execution path.

## Changes (minimal, all verified)

### 1. `daemon.py` — bridge init at startup (additive, failsafe)
Inserted after the module constants (`_ENGINE_STARTED`), before the single-instance lock:

```python
try:
    import scalp360_bridge
    _bridge = scalp360_bridge.make_bridge()
except Exception as _e:
    _bridge = None
    print(f"scalp360 bridge unavailable (relay continues without it): ...")
```

- `make_bridge()` runs the bridge's idempotent `_ensure_schema()` over `signals.db`, adding lineage tables **intents, positions, event_claims, neural_labels** (plus `cursors`, `update_claims` from CursorStore/Console) alongside the existing `trades` ledger.
- Any failure → `_bridge = None`, one log line, daemon runs unbridged. Never blocks startup.
- Also added `_s360_log(msg)`: best-effort append to `daemon.log` (mirrors `news_fetcher.log_daemon`), never raises.

### 2. `daemon.py` — zone-aware parse probe in `on_message` (additive)
Inserted immediately BEFORE the existing `parsed = sigparser.parse_signal(raw)`:

```python
if _bridge is not None:
    try:
        _ev = _bridge.parse_signal(raw, str(event.chat_id), msg.id)
        if _ev.kind.name == "NEW_ENTRY":
            _s360_log(f"zone-aware parse OK {tag} {msg_id}")
    except Exception as _e:
        _s360_log(f"zone-aware parse error {msg_id}: ...")
```

- The existing parser stays the **sole input to execution** — this is a parallel audit probe only. The gold parser's zone-aware result (e.g. `ENTRY: 4184/90` → zone 4184–4190, not a collapsed price) is confirmed and logged, nothing else.
- Runs on every watched-channel text message; regex-only cost (microseconds), fully swallowed on error.

### 3. `executor.py` — `_compute_lot()` marker (comment-only)
```python
# TODO: route through scalp360_bridge.size_position() for floor sizing
```
No logic touched. `_compute_lot` behaves exactly as before (RiskGovernor's floor sizing / min-lot rejection / fee+slippage reserve is the future replacement, not wired yet).

### 4. New file `integration_status.py`
Reports which scalp360 subsystems are wired, checked against the real `signals.db` and real modules: bridge loads, lineage tables exist, gold parser works (msg-2243 anchor: entry zone (4184, 4190), TP zone (4120, 4145) preserved), risk governor instantiates (+ pure `size()` probe: APPROVE 0.09 lots @ 45.14 risk), cursor store initializes, daemon wiring (`import daemon` → `_bridge` live, `_s360_log` present). Exit 0 only when all PASS.

## Verification (all real runs, relay interpreter `C:\Users\voidk\miniconda3\python.exe`)
- `py_compile daemon.py executor.py` — OK under both the default and the live (miniconda3) interpreter.
- `test_suite.py` — **ALL PASS** (S1–S9 parser samples, N1–N6 news-filter/executor gate cases; N5/N6 attach to the running MT5 terminal, dry-run only). Live daemon (pid 441720) untouched and still running.
- `integration_status.py` — **6/6 wired**, exit 0.
- `signals.db` post-check: tables now `trades, intents, positions, event_claims, neural_labels, cursors, update_claims`; all new tables 0 rows (schema only, no data written).
- `_s360_log` end-to-end probe appended a `[scalp360 18:09:03]` line to `daemon.log`.

## Operational notes
- The running daemon (pid 441720) still executes the pre-edit code; the parse-logging probe activates on the **next daemon restart** (schema is already in signals.db now — created by the integration run). Restart was not performed unilaterally: the relay is live trading infra.
- Risk sizing (item 3) remains a TODO marker by design — activating RiskGovernor sizing changes trade sizes and is a separate decision.
- Later subsystems (lineage intent transitions, cursor gap-replay, AI extraction, neural labels) are exposed on `_bridge` but not yet called from the live path; each can be activated independently.

