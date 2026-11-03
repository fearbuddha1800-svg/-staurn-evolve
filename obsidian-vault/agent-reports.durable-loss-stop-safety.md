---
slug: agent-reports.durable-loss-stop-safety
type: note
graph: gitnexus
---

# Durable loss halt and stop legality — offline delivery

Created: loss_halt.py, test_loss_halt.py, stop_legality.py, test_stop_legality.py.
No existing project source/config/UI was edited. No flag files were created or removed. No broker orders were submitted. Modules import no MT5 and contain no order_send or TRADE_ACTION_* references (verified with AST scan).

## LossHalt
- Dedicated SQLite path, FULL synchronous transactions; state and append-only audit commit atomically. Stale instances reload inside transaction.
- Full-day broker deal snapshot computes NET realised P/L (profit+swap+commission+fee), excludes funding, deduplicates deal tickets, rejects malformed/unknown data. Limit is positive absolute account currency and latches at >= limit.
- Aware explicit now and fixed timezone (UTC default) define calendar day. Midnight resets counters but never latch. Backward clock, account/policy mismatch and corrupt storage fail closed.
- observe(now) refreshes broker history and is the entry-gating API; status(now) is local persisted state only, not a broker freshness assertion.
- reconcile(now, operator=..., reason=...) returns a persisted receipt recording history/account/open positions/pending orders, including pending volume. recover(now, reconciliation_id=..., operator=..., reason=...) requires an unchanged <=60s receipt, active latch and daily loss below limit; commits recovery evidence before clearing latch. Same-day active breach cannot be overridden.
- Caller must catch SafetyError/storage failures and block entries; caller authenticates operator identity. State-file deletion/tampering and completeness guarantees of an MT5 history response are outside scope.

## Stop guards
- BUY vs bid / SELL vs ask; stops/freeze points scaled by point, grid checked exactly with Decimal; no auto-rounding or widening.
- Fresh tick requires 0 <= supplied now - tick timestamp <= max_tick_age_s (default 5), using time_msc preferentially. Missing/stale/future/malformed data refuse permission.
- TIGHTEN/WIDEN/UNCHANGED; stop removal is WIDEN, adding missing protection TIGHTEN. WIDEN always explicitly flagged and refused unless allow_widen=True (actual bool). UNCHANGED never applies.
- plan_position_stop obtains exact broker position; assess_stop_change can assess caller-supplied baseline.
- confirm_stop_change separately reads back exact broker ticket/symbol/side/SL. Local preflight alone is not broker-confirmed protection. No submission callback or send path exists.

## Real verification output

Command: PYTHONPATH= C:/Users/voidk/miniconda3/python.exe -m pytest test_loss_halt.py test_stop_legality.py -q

.........................................................                [100%]
57 passed in 1.06s

Command: PYTHONPATH= C:/Users/voidk/miniconda3/python.exe -m pytest test_cockpit_api.py test_entry_authority.py -q

.................                                                        [100%]
17 passed in 1.24s

Command: PYTHONPATH= C:/Users/voidk/miniconda3/python.exe -m pytest test_loss_halt.py test_stop_legality.py test_cockpit_api.py test_entry_authority.py -q

........................................................................ [ 97%]
..                                                                       [100%]
74 passed in 2.56s

All commands exit 0. Tests include actual separate-interpreter restart persistence, midnight/calendar timezone behavior, recovery/audit rollback, receipt changes/staleness, both stop sides, metadata/quote failures, opt-in and fake broker read-back.

## Remaining integration / limitations
These are additive safety libraries only. Existing executor/manage/strategy call sites are not wired because existing file edits are outside delegated scope. Existing manage.py still sends directly and executor.py's current BE helper allows missing tick to bypass its local distance check. Parent must integrate the new guards, call observe before entries, handle unknowns fail-closed and only mark management success after confirm_stop_change. No live MT5 history completeness, server clock calibration, freeze-level behavior or live stop modification was verified. New position/history snapshots are sequential broker reads, not a broker-side atomic transaction; callers must serialize account actions/reconcile again on changes. No guarantee against market gaps or externally changing risk.

