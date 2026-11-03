---
slug: agent-reports.evolve-entry-learning-audit
type: note
graph: gitnexus
---

# EVOLVE: recovered read-only entry and learning audit

## Scope and status

Recovered locally after delegated task `deleg_2f73d463` task 2/2 failed before performing its audit. Its transcript reports an OpenCode HTTP 403 `FreeTierError`: free models are unavailable from the current network/IP. This is a provider restriction, not evidence of an EVOLVE or trading-account failure. The delegation tool reported no currently live children when checked; no replacement batch was dispatched and no provider settings were changed.

Project: `C:/Users/voidk/.hermes/workspace/signal-relay`.

Primary SQLite snapshot: **2026-10-19 06:08:07.006988 UTC**. Local-day queries start at **2026-10-19 04:00:00 UTC** (midnight EDT). Later log/process observations extend through approximately 06:09:44 UTC. These are bounded observations, not continuously current account values.

This pass read source/configuration, process metadata, log tails, and SQLite with URI `mode=ro` plus `PRAGMA query_only=on`. It exercised function-signature binding using AST-derived signatures, without importing the executor, daemon, manager, event bus, or collector. It did not initialize MT5, submit/modify/close orders, refresh data, run services, change configuration, or run project tests. This report is the only project file written by the recovery audit.

## Executive findings

1. **Confirmed entry call-contract defect:** `daemon.py:690` passes `trace_id`, but `executor.execute` at `executor.py:319` does not accept it. Offline argument binding reproduces `TypeError`. Any invocation of this exact call fails before executor guards, shadow-policy recording, or broker execution.
2. **Current protection blocker:** the live manager log repeatedly reports break-even changes rejected as `stale or future tick`. The newer manager source on disk forwards `broker_utc_offset_s`, but the current stop assessor does not accept that argument. Do not deploy/restart the newer manager alone.
3. **Learning is data-starved:** 3 labels total, 2 completed losses, 1 pending. The configured 300-completed-label threshold leaves **298 more completed labels required**. No meaningful trained/promoted model can be claimed from these data.
4. **The supervised watch path is collection-only:** it does not invoke evaluation; evaluation is called from the non-watch CLI path. The inspected watchdog supervises `watch`, not an evaluator/promotion service.
5. **Several dashboard/status signals overstate functionality:** bridge parsing treats unmatched non-recap text as `NEW_ENTRY`; `paper_mode` is read by Pine runner, not a global executor safety switch; the evaluator's purge/cost/promotion claims exceed the inspected implementation.

## Snapshot: what was and was not blocking entries

| Evidence | Observed value | Interpretation |
|---|---|---|
| `STOP`, `HALT`, `PAUSE` | All absent | These file gates were not active at discovery time. |
| Config `mode` | `auto` | Confirm mode was not the configured gate. |
| Persisted loss policy | Daily limit 50.00, UTC calendar | Do not infer a percentage limit. |
| Persisted loss state | P/L -8.30; loss 8.30; `halted=false` | This stored latch was not tripped. This audit did not reconcile broker history itself. |
| `trades` rows for the local day | 0 | No new entry is recorded in this ledger for the bounded day window. This is not a fresh broker-history audit. |
| All-time ledger statuses | 3 `executed`, 2 `broker_rejected`, 1 `pine_signal` | Historical records, not six new trades today. |
| `intents` table | 0 rows | The inspected lineage store has no recorded intent chain. |
| `signal_received` events in snapshot | 39 | Receipt count is not an executable-signal count. |
| Parsed receipt classifications | 36 non-signals; 1 parse-valid signal; 2 signal-like parse failures | One failure lacked channel SL/TP; one was a management message. |
| Sole parse-valid candidate | XAUUSD buy, source `-1001588519179`, received 04:13:04 UTC | Its configured policy is `shadow`; it should not become a live order merely by repairing the call contract. |
| Running collection | Collector process has `watch` argument | Process existence establishes liveness, not successful new labels or model training. |

The audit does **not** conclude that the signature defect alone explains every historical missed trade. The sole parsed candidate is shadow-only, pre-executor daemon returns are not fully journaled, and the event timestamp precedes the current daemon process start. Existing strategy loops also require actual strategy conditions; this pass did not compute fresh trading signals.

## F1 — entry caller and callee disagree (confirmed on disk)

Evidence:

- `daemon.py:38` directly imports `execute` from `executor`.
- `daemon.py:690` calls `execute(parsed, msg_id=msg_id, channel_id=event.chat_id, trace_id=msg_id)`.
- `executor.py:319` defines:

```python
def execute(parsed, msg_id=None, lot=None, dry_run=False, channel_id=None, magic=None):
```

- `executor.py:328` already derives the trace ID from `msg_id`.

Executed offline reproduction, using the exact AST-derived signature:

```text
(parsed, msg_id=None, lot=None, dry_run=False, channel_id=None, magic=None)
TypeError("got an unexpected keyword argument 'trace_id'")
```

The current daemon process was created at 04:59:04 UTC; current daemon/executor file modification times precede that start. This is consistent with the mismatch being loaded, but no live frame inspection was performed.

**Minimal safe next change:** remove the redundant caller keyword, or explicitly evolve and test the callee contract. Prefer preserving `msg_id` as the canonical trace identifier. Add an offline daemon-to-executor signature/behavior regression test and durable rejection/error events. Keep channel shadow policy, demo identity, stops, deduplication, and loss controls unchanged. Do not replay the old signal as a new order.

## F2 — live stop rejection plus an incompatible pending deployment (confirmed)

Live `manage.log` at approximately 06:09:43 UTC shows repeated break-even failures for XAUUSD and USDCAD:

```text
stop legality rejected: stale or future tick
```

The active manager process started at 05:53:42 UTC. `manage.py` was subsequently modified at 05:58:57 UTC, so current disk source must not be equated with the running process.

Current disk source `manage.py:179-182` passes `broker_utc_offset_s` to `plan_position_stop`. `stop_legality.py:151-152` forwards options into `assess_stop_change`; the latter's signature at lines 75-76 has no such keyword. AST binding independently reproduced:

```text
TypeError("got an unexpected keyword argument 'broker_utc_offset_s'")
```

The planner catches that exception and returns an unavailable-position decision, so the pending combination fails closed rather than providing a working normalization fix. Config contains an explicit 10800-second broker offset, but this audit did not remeasure broker timestamps and that configuration alone does not implement support.

**Minimal safe next change:** implement and test clock normalization in the guard together with its callers. Retain the unchanged five-second freshness rule after normalization; reject stale/future/malformed ticks, invalid offsets, unknown account identity, and unconfirmed protection. Test manager functions offline before a coordinated restart. Never disable freshness checks to make the error disappear. Broker readback of the exact stop remains required before claiming success.

## F3 — label coverage and automatic evaluation are incomplete (confirmed)

Read-only database counts:

```text
labels_total=3
labels_complete=2
labels_pending=1
completed_wins=0
completed_losses=2
remaining_to_300=298
label_map_rows=3
orphan_maps=0
unmapped_labels=0
```

All three stored labels identify relay magic 20261014. Their market-feature snapshots have 80 bars and populated RSI/ATR. The newest stored entry timestamp is 2026-10-16 21:54:22 UTC. Entry timestamp is not proof of last collector reconciliation time.

`neural_label_collector.py:543-546` selects only the latest 500 ledger rows with `status='executed'` and a nonzero ticket. Therefore positions absent from that ledger, including manually adopted positions and legacy direct-entry paths, are not covered by this reconciliation path. No claim is made that every current broker position is covered.

`watch()` at lines 608-626 calls `backfill_once()` and sleeps. It never calls `run_evaluation()`. `main()` returns immediately from its watch branch at lines 635-638; the evaluation threshold check is in the later non-watch branch, lines 647-651. The inspected watchdog starts `neural_label_collector.py watch`.

A production-source AST scan across project-root Python files and `scalp360/*.py` found evaluation entry calls only in this non-watch collector flow. External cron definitions and external services were not exhaustively audited, so absence of every possible scheduler is not asserted.

**Minimal safe next changes:**

1. Keep the 300-label gate; do not train/promote on two same-class outcomes.
2. Ensure every authorized execution origin writes a canonical, account-bound trade/position record with original risk and immutable entry features.
3. Add a read-only collector heartbeat/coverage view so a live-but-idle collector is distinguishable from a healthy learning pipeline.
4. Add a separately supervised, threshold-driven shadow evaluator with safe locking and immutable evaluation/model artifacts. Promotion must remain a separate verified action.

## F4 — evaluation claims exceed implementation (confirmed source gaps)

`scalp360/neural.py` defines `purged_splits()` at lines 45-55, but `evaluate()` at lines 77-119 does not call it. The current evaluation uses chronological train/validation/holdout slices without the advertised purge/embargo in that path.

The evaluation fits a local challenger and returns an `EvalReport`. `PROMOTE` is a decision string, not demonstrated persistence, registry activation, or live inference wiring.

`scalp360_bridge.py:235-238` does not supply a cost parameter, so `evaluate` uses its `cost_per_trade=0.0` default. Its net calculations count binary wins/losses in unit amounts rather than actual realized R magnitudes. Consequently the report cannot be described as validated after-cost profitability for the live trailing strategy.

**Minimal safe next change:** validate leakage-free split boundaries using actual label close times, retain an untouched holdout, evaluate realized after-cost returns, and persist reproducible shadow artifacts before any model promotion/inference integration. Do not lower the AUC threshold or fabricate samples to bypass this work.

## F5 — telemetry and configuration have misleading meanings

### Bridge parser

`scalp360_bridge.py:109-117` returns `NEW_ENTRY` both when `parse_gold` succeeds and when it fails, except for the earlier recap screen. `daemon.py:594-605` publishes `zone_parsed` on that classification. Snapshot contains 39 `zone_parsed` and 39 receipts although 36 receipts are non-signals under the authoritative parser.

**Safe next change:** return an honest unknown/non-entry classification for unmatched content and test promos, credential solicitations, recaps, and real signals. This is a telemetry repair, not permission to execute the bridge's classifications.

### Paper-mode flag

Config has `paper_mode=true`. A scan of the inspected active root and `scalp360` Python sources found reads of that key in `pine_runner.py`, not in `executor.execute` or `execute_algo`. Those functions depend on their explicit `dry_run` argument. The flag therefore must not be presented as a global no-order guarantee.

**Safe next change:** publish per-engine execution state and verify it against the actual entry authority. Do not silently change trading modes as part of this audit.

### Provenance and sensitive source content

Some received source messages contain account-access solicitations and credential-like material. This audit neither uses those details nor reproduces them here. Redact such material from operator-facing evidence and keep it in a non-executable quarantine path if retention is required.

## Recommended work order / next-agent handoff

1. **Protection first:** finish the explicit broker-clock guard implementation and run its offline regression suite together with manager caller tests; only then coordinate deployment and exact broker stop readback.
2. Repair the daemon/executor keyword contract and journal pre-executor skip/error reasons. Test with an offline broker double; preserve channel shadow policy and do not replay old candidates.
3. Verify current demo identity and canonical execution/lineage coverage before expanding autonomous entries.
4. Complete collector heartbeat/coverage, threshold-driven shadow evaluation, leakage/cost validation, and reproducible artifacts. No model activation until adequate independent outcomes and verified evaluation exist.
5. Audit UI claims against these per-engine facts. Chart repair, licensing, dashboard deployment, and current broker equity/positions were outside this recovery pass.

## Verification boundary

Confirmed by execution: read-only SQLite queries, process metadata/log reads, and the two AST signature-binding failures. Source paths and line references were read directly. No unit/integration suite or live broker write was run; no repair or deployment is claimed. The failed OpenCode child produced no substantive audit findings; this report is the locally recovered deliverable.

