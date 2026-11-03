---
slug: agent-reports.redevelop-intelligence
type: note
graph: gitnexus
---

# Offline shadow evidence engine

## Delivered

Owned files only:
- `signal_evidence.py`: stdlib-only, frozen validated evidence models, shadow replay ledger, cost-aware outcome attribution, uncertainty-aware descriptive source reports and JSON/JSONL CLI.
- `test_signal_evidence.py`: synthetic offline tests including actual CLI subprocesses.
- This report.

No broker/execution imports, database reads/writes, network calls, service starts, order calls, credentials, account/config changes or changes to existing source-audit/intelligence modules. These three paths were new; there were no pre-existing owned files to snapshot under `backups/redevelop-20261027T174250Z/intelligence`.

The existing receipt dataset is not converted into fabricated quote/publication/outcome records. Its receipt and parse counts cannot establish source profitability. Existing audit/intelligence reports remain separate observation-health reports; this module does not change their interfaces or approve any source.

## Public interfaces

```python
SignalEvidence(...)                 # frozen, strict runtime validation
OutcomeEvidence(...)                # frozen, strict runtime validation
Policy(...)                         # positive integer bounds
ShadowDecision(...)                 # engine always emits approved_for_live=False
decode(SignalEvidence, raw_dict)     # exact schema, no unknown/missing fields
decode(OutcomeEvidence, raw_dict)
ShadowEngine(policy: Policy | None = None)
engine.decide(signal, *, now: datetime) -> ShadowDecision
engine.record_outcome(outcome, *, now: datetime) -> str
engine.source_report(*, as_of: datetime, split_at: datetime) -> dict
replay(records: list, *, as_of: datetime, split_at: datetime) -> dict
strict_json(raw: str)                # reject duplicate object keys and NaN/Infinity
```

`SignalEvidence` requires source, message_id, source_version, integer version, original_at, version_at, received_at, feature_at, quote_at, provenance, parser_version, content_hash, category, symbol, side, entry, stop, target, bid, ask and correlation_id. Category is entry/recap/management/ambiguous; side is buy/sell. Numeric identity strings are not repaired. SHA256 is lowercase 64-character hex; provenance/hash are supplied assertions, not cryptographic verification of raw content.

`OutcomeEvidence` requires outcome_id, decision_id, mode, status, opened_at, closed_at, observed_at, gross_pnl, costs, initial_risk, currency, evidence_ref and costs_complete. Mode is paper/broker; status is completed/open/censored. Optional monetary fields and closed_at must be explicitly null when unavailable, not omitted. All monetary amounts must share the declared currency. Costs are the nonnegative all-in cash deduction from gross P&L, including whatever fees/slippage/funding are required by the supplied accounting convention. Completeness remains an externally supplied assertion.

Python constructors require aware datetime and finite Decimal instances, exact int/bool types, nonempty unpadded text, valid chronology and price geometry. JSON timestamps require explicit offsets and prices/cash are canonical decimal strings, not JSON floats. Decimal evidence is bounded to 38 digits and exponent -18..18; R uses a local 128-digit decimal context. No silent type coercion, side guessing or timestamp repair.

## Decision/evidence controls

- Identity: `(source, source_version, message_id, version)`; deterministic SHA256 decision IDs.
- Replay and conflicting versions cannot overwrite the first ledger decision or create another candidate.
- Edits are never new entries, even when the original was not observed. Recaps, management and ambiguous categories abstain.
- Require publication <= version <= receipt; original version dates must agree. Refuse future receipts and receipt-order reversals.
- Default limits: publication-to-receipt latency 60 seconds; decision-time publication age 120 seconds; quote and feature age 10 seconds. Future feature/quote availability abstains. These are explicit testable conservative defaults, not empirically calibrated trading thresholds.
- Same source/message, declared correlation ID, or exact symbol/side/entry/stop/target geometry within a 600-second rolling receipt window suppress independent candidates. Every matched cluster is unioned, including bridge evidence. If later evidence merges multiple prior candidates, their completed outcomes are quarantined from source scoring rather than counted as independent observations. Historical reports rebuild correlation with information available at their cutoff only.
- Outcomes require an accepted shadow decision and cannot predate its decision or be observed in the future. A completed outcome requires final close, complete gross P&L/cost/risk evidence, and positive initial cash risk. Realized R is `(gross_pnl - costs) / initial_risk`, never target distance or an open mark.
- Open/censored records have no realized-R label. Open-to-completed revisions preserve open time, currency, evidence reference and known initial risk. Completed outcomes are immutable; IDs cannot replay and evidence references cannot be reused for another decision in the same mode.
- Paper and broker-asserted evidence are stored and reported in separate groups. A broker mode label does not cause any broker access or prove that a fill happened. Outcome observation history is retained for historical as-of reporting.

## Source uncertainty and leakage handling

Reports are by source + source_version + outcome mode, not ranked by parse yield. They expose receipts, candidates, missing/open/censored outcomes, completed/scored counts, correlation exclusions, independent clusters, train/holdout counts and means, and an approximate 95% normal interval for the descriptive mean R. One observation has no interval.

Default minimum: 30 independent completed clusters, at least 10 fully observed before the split and 10 originating/decided on or after it, no split-boundary leakage, no correlation exclusions and complete candidate outcome coverage for that mode. Passing this changes only `insufficient_evidence` to `descriptive_only`; it never authorizes live trading or asserts profitability. Every decision and report has `approved_for_live=False`.

Train outcomes must be observed strictly before the split. Holdout entries must originate and be decided on or after the split. Boundary-spanning outcomes are excluded from train/holdout statistics and block sufficient-evidence status; the overall descriptive mean is explicitly the completed uncorrelated population, not a fitted-model holdout score. As-of filtering excludes future labels, preserves earlier open observations and prevents later bridge evidence leaking into earlier snapshots. No model is fitted and no source is selected using these statistics.

## CLI / verified execution

```bash
python -m unittest test_signal_evidence -v
python -m py_compile signal_evidence.py test_signal_evidence.py
python signal_evidence.py --demo --as-of 2026-01-01T13:00:00Z --split-at 2026-01-01T11:00:00Z
python signal_evidence.py --input evidence.jsonl --as-of 2026-10-27T17:00:00Z --split-at 2026-10-01T00:00:00Z
```

The last command documents the interface; it is not a claim that such a live evidence file exists. `--demo` is explicitly `test_fixture_only=true` and contains TEST-marked synthetic signal and completed paper-outcome evidence only. The fixture's realized 2R is test arithmetic, not observed performance.

Input `.json` is an array; other extensions are JSONL. Every record is exactly `{"kind":"signal"|"outcome","data":{...}}`. Signal records must be receipt-ordered; outcomes must follow their linked decision, and revisions must be observation-ordered per decision/mode. Replay uses historical receipt time as the decision clock, not the report cutoff. To test late consumption, call `decide(..., now=actual_consumption_time)` directly. Malformed evidence envelopes/models are returned as explicit abstentions. Malformed JSON syntax/duplicate keys fail the CLI without producing an approving result. No output files are written by the CLI.

Verification: 25 tests passed, including exact schema/type/decimal rejection, timezone/geometry validation, duplicate/conflict protection, edits/categories, latency/freshness/future abstention, correlation suppression and transitive bridge quarantine, as-of correlation and outcome history, cost-aware R, paper/broker isolation, missing/open/censored labels, immutable completed evidence, risk-preserving revisions, split-boundary purge, sample thresholds, no-outcome insufficiency, JSON and JSONL real subprocess round trips, fixture-only demo, and absence of broker/network/database imports. Python compilation passed. Tests use temporary TEST fixtures under the Hermes scratch directory and clean them up.

## Remaining limitations

- No performance conclusions about the stored receipt dataset; no attributed cost-complete real outcomes were manufactured or inferred.
- Correlation is conservative exact/declared matching, not proof of authorship, copying or economic independence; near-matches and correlated instruments can escape it. Quarantine may discard legitimate independent entries.
- Ledger is in memory and correlation matching is quadratic; replay the complete record history to restore identity protection. It is not a production durable queue or distributed ingestion service.
- Single explicit entry/stop/target geometry only; no partial fills/exits, multiple targets, risk recomputation, FX cash conversion or independent cost reconciliation. Upstream must provide trustworthy final accounting and evidence provenance.
- Normal intervals are descriptive and can be misleading for small, heavy-tailed or regime-correlated samples. No bootstrap, multiple-testing adjustment, calibration, regime stability, Sharpe, risk deployment model, ML accuracy or profitability certification is claimed.
- Split time is supplied explicitly; this module cannot prove it was preregistered or that upstream extraction/classification was free of hindsight. No source promotion, account integration or execution wiring was added.

