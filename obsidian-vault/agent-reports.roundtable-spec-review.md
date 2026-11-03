---
slug: agent-reports.roundtable-spec-review
type: note
graph: gitnexus
---

# Quant HQ roundtable SPEC review

## Scope and verification boundary

Read-only source review of the current checkout, including mobile_view.py, event_journal.py, scalp360_bridge.py, scalp360/ai_extract.py, portfolio_risk.py, portfolio_attribution.py, loss_halt.py, stop_legality.py, and relevant production callers/rendering. Only this report was written. No services restarted, flags changed, production databases modified, model requests made, or broker sends performed. Files were under concurrent parent/child development; line references describe the source read in this review, not a deployed-build attestation.

**Outcome: partial compliance, not ready for an all-integrated safety claim.** Real-data presentation improved materially, but durable loss protection and the new stop guard remain library-only. UNKNOWN-to-zero/empty leakage survives outside the repaired mobile/journal paths. This review found critical integration gaps, not evidence that any live loss breach or illegal modification occurred.

## Requirement compliance

| Requirement | Verdict | Source evidence and qualification |
|---|---|---|
| Mobile: missing account/positions must not become zero/flat | PASS | mobile_view.py:56-72,75-96 preserve None; :128-153 distinguish unavailable from confirmed empty; :37-44 reject nonfinite numeric display. No illustrative account/trade records remain in this renderer. |
| Mobile: fetch time must not imply fresh market quotes | PASS, limited | mobile_view.py:208,219,222 labels snapshot-fetch time and explicitly says quote freshness is unverified. Does not prove current session/quote freshness. |
| Journal: unavailable distinct from confirmed empty, with real provenance | PASS on primary API | event_journal.py:76-86,97-116 returns available/events/source/captured_at and recorded timestamp basis; event_journal.py:56-64 does not guess timezone. cockpit.py:235-238,273-277 uses the envelope. No log-derived fills. |
| Journal: source/type must not be treated as independently confirmed fill | GAP in producer semantics / consumer contract | event_journal.py:97-104 faithfully forwards source/type but has no broker-confirmation classification; executor.py:601-610 emits placed/filled/opened together from one acknowledgement; manage.py:176-182 calls a disappeared ticket position_closed without history confirmation. See important defects below. |
| UNKNOWN must never become a fabricated zero/empty success anywhere in reviewed callers | GAP | strategy_identity.py:122-134 coerces missing/None money to zero; portfolio_attribution.py:23-36 can then return available=True. cockpit.py:425-436 converts failed/unavailable position reads into available=True/open_positions=[]. cockpit.py:280-284 fallback discards journal availability/provenance. |
| Bridge AI must abstain rather than fabricate successful extraction | PASS for configured adapter path; live call unverified | scalp360_bridge.py:193-218 requires a real adapter dict, is_signal=True, successful to_parsed, and finite configured confidence. :204-215 produces UNKNOWN on unavailable/invalid extraction. Offline transport tests only. The old UNKNOWN stub was abstention, not fabricated trades. |
| Bridge AI wrapper guarantees all advertised bounds and all-failure abstention | GAP | scalp360/ai_extract.py:38-46 checks a spend counter that is never incremented/reset; :55 delegates timeout without enforcing it; :59 counts successful returns, not failed attempts; :61-65 accesses malformed provider output outside the try/except. Shared ai_filter/router may supply additional bounds, but those are not proof of the bridge wrapper's advertised daily-budget/8-second semantics (bridge :199 explicitly delegates deadline). |
| Durable loss latch participates in every active entry | GAP — critical | loss_halt.py:3-5 explicitly requires caller integration. Source search found imports only in test_loss_halt.py, not production entry modules. executor.py:195-231 shared guards have no LossHalt consultation; actual sends :406,:526 remain downstream. |
| Stop legality participates in active management and confirms application | GAP — critical | stop_legality.py:10-12 explicitly says additive/unwired. manage.py:147-151 sends directly and trusts retcode; :197-215,:225-231 do not consult freshness/stops/freeze/grid guard or exact readback. executor.py:584-597 uses a legacy partial BE check, not the new guard. |
| Loss latch persists incidents across restart/day rollover, read-only broker, explicit recovery | PASS at library contract tested | loss_halt.py:62-75 uses transactional FULL synchronous SQLite; :96-104 resets counters without unlatching; :154-180 latches; :196-226 requires fresh unchanged recovery evidence. Explicit offline tests passed, including separate-interpreter restart. This is not entry enforcement. |
| Stop library rejects missing/stale/future quotes, separates tighten/widen and confirmation | PASS at library contract tested | stop_legality.py:41-54 classifies removal as WIDEN; :100-133 checks metadata, tick age, bid/ask, grid, stops/freeze; :138-178 binds exact ticket and verifies broker-read SL. No send function. |
| Portfolio stop-risk math matches quant_analytics, unknown totals remain unknown | PASS | portfolio_risk.py:11,34-40 delegates stop_risk; :67-91 preserves incomplete totals/caps. quant_analytics.py:140-184 distinguishes None, unprotected/unpriced positions, known subtotal and complete total. |
| Portfolio currency exposure/caps have honest units and scope | PASS | portfolio_risk.py:55-66 limits two-currency decomposition to FX contract modes; :87-97 distinguishes unknown/subtotal and native units, labels caps diagnostic only. No maximum-loss/enforcement claim is justified. |
| Attribution respects identity + version limits | PASS for grouping/limitations; GAP for monetary completeness/reconciliation | portfolio_attribution.py:18-36 partitions (id,version), uses collision-safe JSON keys, states current mapping/deal-count/shared-magic limits. cockpit.py:178-191 filters BUY/SELL deals and labels 90-day UTC/account currency. Monetary null/default and rounding defects survive in legacy helper. |
| New panels prove operational integration, not merely importability | GAP if claimed | daemon.py:589-609 says bridge parse is parallel audit only; execution uses sigparser. cockpit.py:309-326 builds a separate in-memory bridge/timer. integration_status.py:49-58,102-112 verifies instantiation/pure sizing, not live governance. Do not interpret import/table/parse success as enforced execution or a verified model connection. |

## Critical defects / highest safety impact

### C1. Durable loss protection exists but cannot block production entries

Evidence: loss_halt.py:3-5; executor.py:195-231,406,469-475,526. Neither entry authority calls LossHalt.observe(), checks its halted state, or blocks on its exceptions. The daily trade-count cap is not a realised-loss incident latch. A bridge RiskGovernor object is not a substitute: daemon.py:589-609 only uses bridge parsing as an additive audit event; no bridge size_position call governs the shared executor.

Production entry inventory: executor.py:406 (relay entry), :526 (algo entry); strategy.py:284-301 and strategy2_live.py:412-435 retain direct-send rollback entry branches. Protective/exit sends are manage.py:150, executor.py:557,:593, daemon.py:417. No production import/call of loss_halt or stop_legality was found; matching test imports are not runtime integration. Backup copies and live test_loop.py were excluded from the operational conclusion, and no such runner was executed.

**Consequence:** a passing durable-latch suite cannot justify saying daily-loss halting is active. This is a critical integration gap, not a report of an observed breach. Rollback entry branches must not silently bypass any future latch.

### C2. Protective management bypasses the new legality and exact-confirmation contract

Evidence: manage.py:147-151 treats TRADE_RETCODE_DONE as success; :197-215 accepts any non-None tick, assumes symbol_info exists, and sends the BE candidate without age/freeze/grid checks; :216-218 marks be_done=True on acknowledgement; :225-231 similarly trails. executor.py:576-593 allows sending when metadata/tick are absent (tick guard is conditional), does not check freshness/freeze/grid, and :596-597 calls retcode DONE a moved stop without readback.

**Consequence:** illegal/stale modifications can be attempted, and local management state can claim applied protection without independently reading the exact position SL. Broker rejection is not equivalent to local safety preflight. The new module is suitable groundwork but not active protection.

## Important defects / integrity gaps

### I1. Identity endpoint still reports unavailable exposure as an empty success

cockpit.py:425-436 initializes live=[], uses positions_get() or [], swallows exceptions, and returns available=True. The registry can be valid while the position read is unknown. quant.js:23-27 relies partly on a separately fetched state.mt5.positions_available; an older successful state read cannot establish availability of this later identity read. It can consequently say no open positions from this source even though this source failed.

Bounded offline AST-isolated invocation of the production identity_data function with injected positions_get()->None returned available=true, open_positions=[]. No cockpit import, broker access, or production config read was needed; the nonexistent config path produced an empty registry. Fix with independent registry/positions availability and null position data, not a successful empty list.

### I2. Attribution converts missing monetary evidence to zero and can disagree with its own total

strategy_identity.py:125-133 uses float(value or 0) for profit/commission/swap/fee. portfolio_attribution.py:25 checks only the resulting aggregate for finiteness, not source-field presence/completeness. A None profit is thereby accepted as an observed zero.

strategy_identity.py:195 rounds each addition inside a bucket; :198 rounds the unrounded aggregate at the end. portfolio_attribution.py:30-33 carries this mismatch through. Offline injected-fixture probes returned:

- All monetary fields None: available=true, count=1, pl=0.0 (not unavailable).
- Three profit=.004 deal fixtures in one bucket: total.pl=0.01 but bucket.pl=0.0.

These are deliberately injected test inputs, not observed broker data. Full MT5 deal objects usually contain these fields, but this permissive API also accepts dictionaries and explicitly claims source-integrity guarantees. Validate required money, define which truly optional fields default, accumulate without intermediate display rounding, and assert displayed bucket reconciliation. Current id/version grouping itself is correct.

### I3. A persisted event is evidence of a recorded assertion, not necessarily a broker-confirmed lifecycle

The primary journal preserves provenance correctly, and cockpit.py:753-784 is a positive example: ledger evidence is labeled independently from broker position/history evidence. However:

- event_journal.py:97-104 passes event names through without confirmation level. executor.py:601-610 records three lifecycle names from one DONE response; it does not independently verify the position/history at each stage.
- manage.py:176-182 emits position_closed because a state ticket is missing from one confirmed positions list; this is absence-based detection, not a confirmed exit deal or realised close P/L.
- Journal's trades fallback explicitly warns not broker fill confirmation (:112-113), but its event-table envelope has no comparable general note. Mobile recent activity (mobile_view.py:189-195) shows type/source/time only. Do not label its source column or payload_available as a broker-verification badge.
- cockpit.py:280-284 falls back to a legacy list when the journal module fails, losing availability and source semantics; event_journal.get_events() also intentionally loses the envelope (:119-121).

Recommended bounded contract: separate recorded event kind, producer evidence, and broker confirmation level/timestamp/ticket. Preserve original events; never rewrite historical assertions as stronger evidence. This gap does not imply every emitted order_filled is fabricated: current executor emits it only after DONE (:413-422,:533-544), which is real acknowledgement evidence.

### I4. Bridge parse audit can falsely claim a zone-aware parse succeeded

scalp360_bridge.py:110-117 returns NEW_ENTRY whether parse_gold succeeds or fails (unless recap heuristic blocks). daemon.py:596-605 treats that kind as zone-aware parse OK and publishes zone_parsed. An offline in-memory probe with an explicitly nonsignal fixture returned NEW_ENTRY. This is a misleading working-parser/integration observation, NOT a proven order-permission bypass: daemon.py:589-590,609 uses the separate parser for actual execution. Make the audit depend on an actual typed parse, not the generic NEW_ENTRY fallback.

### I5. AI wrapper claims exceed what that wrapper implements

scalp360/ai_extract.py:55-65 catches callable exceptions but not malformed return/evidence shapes. Its spend counter never advances; rate accounting excludes raised calls; circuit breaker has no timed recovery. scalp360_bridge.py:199 acknowledges the wrapper's timeout is not the real network deadline. The production daemon itself calls ai_filter.llm_extract (:615-620), not bridge.ai_extract. Therefore the adapter change is useful tested code, not proof that the bridge's advertised governance or model integration governs production. Do not repeat the old docstring's test count (scalp360_bridge.py:2) as current execution evidence.

## Stated limitations, not defects by themselves

- Mobile quote freshness is explicitly unverified, including closed-market prices (mobile_view.py:222). A snapshot fetch timestamp is not a quote timestamp; no live quote was verified here.
- Portfolio caps are diagnostics, not entry controls; unknown CFD/metals currency decomposition is deliberately null, not zero. Native FX units cannot be added across currencies. Stop valuation excludes execution gaps/costs and is not maximum possible loss (portfolio_risk.py:92-97).
- Attribution uses current magic mapping, counts deals not round trips, and cannot recover historical versions or distinguish engines sharing legacy magic (portfolio_attribution.py:36). Version partitioning does not invent missing historical identity.
- LossHalt assumes broker history for the requested window is complete (loss_halt.py:10). It detects None/malformed rows but cannot independently prove a nonempty partial history is complete. Persisted status() explicitly does not assert current broker freshness (:166-172). Clock protection currently rejects prior calendar days (:98-99), not all backward instants within the same day; do not claim a general monotonic-clock guarantee.
- Stop library preflight and confirmation are separate; applying the decision still requires an authorized production sender. Offline tests cannot prove broker behavior or deployment.
- No real LLM request, live model configuration success, current account health, or running-process version was verified. Importability and test doubles do not establish those facts.

## Cosmetic preference (not a safety blocker)

The journal's generic object renderer may require expanding nested events rather than giving a first-class table (quant.js:17,50). This is usability, not fabricated evidence. Color treatment and panel layout are not reasons to defer the execution-contract fixes above.

## Next highest-value bounded fix

**Wire the durable loss latch into the single entry authority; do not add another feature.** This is a production-code gap with existing offline library coverage and a small, testable acceptance boundary. Parent owns this change; this review did not implement it.

Acceptance questions to settle before enabling it:

1. What explicit account-currency daily realised NET-loss threshold and fixed trading calendar should be persisted? Do not infer a money limit from a percentage without defining balance/equity basis and reset semantics.
2. Which persistent account-bound path owns the incident latch, and who may reconcile/recover it? A HALT flag toggle alone must not unlatch an incident.
3. Must legacy rollback entry branches be disabled, or routed through the same pre-send latch? Every exposure-increasing branch must fail closed on UNKNOWN/error/halted; exits/protective management must remain available.

Offline acceptance: instrument each explicit entry authority/rollback branch with fake broker and injected clock; prove loss at threshold, history None, malformed money, DB failure, account switch, restart and next-day rollover all suppress order_send; verify exactly one authorized post-reconciliation entry can proceed in a controlled fake and failed/blocked paths do not mutate unrelated flags. Resolve threshold/account/calendar config before live activation. Do not run test_loop.py.

Next separate bounded patch after that: integrate stop_legality at both manage._modify_sltp and executor.sl_to_breakeven, preserving original R and requiring exact readback before be_done/success reporting. It should not be bundled with new analytics/features.

## Executed verification

Explicit offline command (no discovery):

```text
PYTHONPATH= C:/Users/voidk/miniconda3/python.exe -m pytest test_real_data_views.py test_loss_halt.py test_stop_legality.py test_portfolio_risk.py -q -p no:cacheprovider --basetemp=C:/Users/voidk/.hermes/cache/scratch/roundtable-spec-pytest
```

**Result: 79 passed in 1.30s, exit 0.** Existing suites use injected brokers/transports and temporary/in-memory DBs. Separate command probes used only injected fixture inputs, an in-memory bridge and an AST-isolated identity function; observed outputs are documented under I1/I2/I4. Passing suites validate the covered library/adapter contracts, not the missing production wiring. No fabricated fixture output has been presented as production observations.

