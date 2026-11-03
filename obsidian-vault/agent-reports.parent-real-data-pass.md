---
slug: agent-reports.parent-real-data-pass
type: note
graph: gitnexus
---

# Parent real-data integration checkpoint

Captured 2026-10-17; latest live API evidence timestamp: `2026-10-17T17:48:53.264263+00:00`.

## Verified directly by parent

- Replaced fictional mobile panel content with read-only MT5 account/positions, actual persisted events and flag-file states. Currency displayed, nonfinite figures suppressed, UTC request timestamp distinguished from quote freshness. Weekend prices explicitly not claimed fresh. Preserved old mockup as `mobile_view.fake-20261017.bak` (not imported).
- `event_journal.journal()` now matches cockpit's real import. Returns availability/events/source/captured_at metadata, persisted event/trace IDs and source timestamps. Uses actual ledger only when event table is absent. Does not infer fills from logs or compare timezone-unspecified ledger strings with UTC strings. Legacy `get_events()` list API retained.
- `scalp360_bridge` no longer contains the always-UNKNOWN `_llm_stub`. Default adapter delegates to `ai_filter`, validates finite/minimum confidence, preserves raw source evidence, and propagates abstention reasons. **No successful live LLM call is established.** The old stub was an abstention placeholder, not fabricated trades. The bridge remains additive and is not new execution authority.
- `test_real_data_views.py` first reproduced seven defects (7 failed/4 passed), then passed with fixes.
- Combined explicit offline regression: **294 passed + 16 subtests** in 16.83s across 17 named files. Includes cockpit, quant, research, intelligence, reconciliation, identities, bar parity, routers/providers, label health, portfolio, durable loss halt, stop legality, real-data views. Offline fixtures are isolated test data, NOT production observations. `test_loop.py` not invoked.
- Standalone runners: 8/9 exit 0. `test_prop_sim_bridge.py` currently fails because its old patched R-only helper no longer feeds the upgraded observed-trade source boundary (runtime correctly refused 2 records when minimum is 10). Retain production minimum; update offline fixture seam in follow-up and rerun. Evidence logs: `agent-reports/parent-real-data-runners/`.
- Live cookie-authenticated checks: **12/12 GETs 200**. Source evidence: `agent-reports/parent-live-real-data.json`. Snapshot: DEMO mode 0, balance 99,999.92, equity 100,011.13, floating P/L +11.21, four positions. These are broker snapshot values, not guaranteed fresh quotes or realised profits.
- Mobile API: zero known fictional strings detected, freshness warning present. Journal API: real source metadata available.
- Cockpit was down while four engines were up. Watchdog restart restored it. Follow-up used one-shot Task Scheduler `Hermes-QuantHQ-SourceRefresh` to invoke the existing watchdog outside agent job cleanup; port 8490 returned, scheduled task entry removed. No marker files changed, no broker orders sent, no trading engines deliberately stopped.

## Still open; do not call complete

1. Consolidated child reports for original five-workstream overhaul; verify them independently after delivery.
2. Prop simulator fixture compatibility plus new production source tests; Monte Carlo remains an estimate, not observed performance. Only 2 validated outcomes observed so far.
3. Whole-production-tree data audit and coverage manifest, plus independent roundtable SPEC review. Fix verified critical/important findings, then perform quality/integration review.
4. Desktop/tablet/mobile full browser verification of the final combined UI after edits settle.
5. New loss-halt and stop-legality library tests do not establish wiring into active executor/manage paths; verify before claiming protection is active.
6. Preserve hold/protection/risk settings and demo account boundary. No new paid calls authorized. Live AI-provider service availability remains unverified.

## Continuing review questions

- Can UNKNOWN/None still masquerade as a zero, empty account or healthy data source?
- Is source retrieval time being confused with the broker quote's timestamp?
- Which new guard is actually called by the live process rather than merely existing on disk?
- Does attribution distinguish current configuration labels from historical facts?
- Does every simulation expose observed inputs, sample size and explicit assumptions?

Next: consume child evidence, resolve fixture mismatch/remaining source defects, then run the final combined regression and browser checks. This checkpoint is not a completion claim.

