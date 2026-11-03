---
slug: agent-reports.2026-10-16-p0-manage-update-lineage
type: note
graph: gitnexus
---

# Audit P0 fixes — manage.py + daemon.py (MANAGER + UPDATE-LINEAGE)

Date: 2026-10-16 · Owner: subagent (files owned: manage.py, daemon.py ONLY)
Scope respected: no process starts/stops, no orders, executor.py/strategy.py untouched.

## Fix 1 — manage.py: positions_get() None (API error) vs [] (confirmed empty)

Audit finding (a): `mt5.positions_get() or []` conflated an API error (terminal
gone → None) with an empty account, so the manager pruned per-ticket state
(original SL / R basis) for positions that were still open.

Diff summary (manage_once, was lines 140/144 — the ONLY two call sites, both
inside manage_once; grep-verified):
- Collapsed the two calls into ONE snapshot `positions = mt5.positions_get()`
  (also kills the TOCTOU race between the old dual calls).
- `if positions is None:` → print `manage_once: positions_get() returned None
  (API error) - cycle skipped, state untouched` and return early with a SKIP
  marker. No state prune, no SL modify, no state save — the cycle is skipped
  entirely.
- `[]` (real list) flows through exactly as before: closed tickets pruned,
  BE/trail logic unchanged.

## Fix 2 — daemon.py: handle_channel_update lineage binding

Audit finding (b): a TP-hit recap from channel X could move the SL of a
position opened from channel Y (match was symbol+direction+magic only).

Diff summary:
- New helper `_ledger_tickets_for_chat(chat_id, db=None)`: runs the specified
  query `SELECT ticket, msg_id, side, symbol FROM trades WHERE status='executed'
  AND ticket IS NOT NULL AND ticket!=0 ORDER BY id DESC LIMIT 50` and keeps
  only rows whose msg_id starts with `"<chat_id>:"` (the daemon stamps executed
  trades msg_id = `<chat_id>:<msg num>`). Returns {ticket: row}. Fails CLOSED:
  missing/unreadable ledger or chat_id=None → empty map → nothing eligible.
- `handle_channel_update(tag, parsed, raw, chat_id=None)`: call site now passes
  `chat_id=event.chat_id`. Lineage gate runs FIRST; then:
  - MT5 not connected → report, nothing touched.
  - No eligible tickets from this channel → "no executed trade from this
    channel" skip, nothing touched (manual trades / algo magic 20261015 /
    other channels structurally excluded — absent from the eligible set).
  - `positions = mt5.positions_get(symbol=sym) if sym else []`; positions_get
    returning None is reported as an API error and touches nothing (no false
    "skip", same None-vs-[] discipline as manage.py).
  - Position must STILL EXIST: pos object is selected from the live
    positions_get snapshot, additionally requiring `p.ticket in eligible`
    (plus the old magic+type+symbol checks).
  - On match: notify now includes the lineage msg_id; TP-hit still routes to
    executor.sl_to_breakeven on the live position object.

## Validation (all run with `PYTHONPATH=` prefix, miniconda3 python, cwd=signal-relay)

1. `python -c "import manage, daemon"` → `IMPORT OK` (clean).
2. `python test_suite.py` → 9/9 PASS, `ALL PASS`, exit 0.
3. Inline P0 test (C:/Users/voidk/.hermes/cache/scratch/test_p0_fixes.py,
   mock ledger rows + fake mt5/notify — no real MT5/Telegram/DB touched):
   24/24 PASS, exit 0. Key checks:
   - manage None → skip marker returned, per-ticket orig-SL/R state preserved
     verbatim (also on 2nd pass); manage [] → stale ticket pruned as before.
   - lineage: chat A → only ticket 111; chat B → only ticket 222; unrelated
     chat → {}; chat_id None → {}; missing ledger → {} (fail closed);
     prefix trap (msg_id "-1001111111111:…" vs chat -100111111111) NOT matched
     (colon terminates the id); skipped/zero/NULL/broker_rejected rows never
     eligible; LIMIT 50 window → 60 rows give the 50 newest (9010..9059);
     db=None wiring reads executor.DB.
   - handle_channel_update end-to-end fakes: MT5 down → nothing touched;
     positions_get None → reported as API error, nothing touched;
     **channel B recap cannot touch channel A's open ticket 111** (the P0);
     same-channel recap moves only its own ticket, lineage msg_id surfaced;
     closed position → skipped untouched; unknown channel → nothing touched.
4. Guard grep: zero `positions_get() or []` left in either file; every
   positions_get call site now has an explicit None branch.

## Notes for orchestrator
- Engine restart needed for the live daemon/manage to pick up the fixes
  (watchdog owns lifecycle — per protocol I started/stopped nothing).
- Semantics worth knowing: lineage window = last 50 executed ledger rows; a
  same-channel position older than 50 executed trades is not eligible for
  channel-update SL moves (spec'd LIMIT 50). Cross-channel updates and manual/
  algo positions can no longer be modified by channel updates at all.
- Test artifacts: inline test kept at
  C:/Users/voidk/.hermes/cache/scratch/test_p0_fixes.py (self-contained,
  point-in-time; scratch is pruned after 24h).

