---
slug: agent-reports.signal-pipeline-audit-20261027
type: note
graph: gitnexus
---

# Signal ingestion and AI extraction audit — 2026-10-27

## Scope and verification

Read-only text/AST review of `parser.py`, `ai_filter.py`, `model_router.py`, `daemon.py`, `signal_source_audit.py`, related provenance/source intelligence code and existing tests. Only this report is authored. No service restart, live-module import, test execution, Telegram session, inference request, broker operation, configuration change or commit was performed. `.env` was not opened. This report identifies local source behavior, not verified running-service behavior.

Static validation returned `AST_OK` for 14 source/test files and counted 66 `test_*` functions in the seven inspected test files. That establishes syntax/readability only, not test passage. `test_suite.py:1-6,68-69` explicitly includes executor imports and MT5-attached cases; do not run the aggregate suite under this audit's constraints.

## Outcome

The highest-value work is reliable abstention, strict extraction contracts, replay/version evidence and attributable outcomes—not broader automatic entry authorization. Existing HALT/PAUSE, confirmation, execution authority, sizing, risk and shadow/live policies must remain unchanged. No provider or channel is recommended for promotion.

### 1. Provider endpoint mismatch is guarded now; OAuth is still unavailable to this transport

**Evidence:** `ai_filter.py:65-110` explicitly allowlists API-key chat providers, rejects unsupported providers/API modes and operation URLs, and resolves one coherent provider/model/key/base. `ai_filter.py:145-147` always appends `/chat/completions`. OAuth Hermes providers are explicitly excluded (`65-67`), so `openai-codex` or `xai-oauth` cannot transparently become valid relay extractors. Do not report the historical cross-provider credential mix as a current unfixed bug. `test_ai_provider_selection.py` includes unsupported-OAuth, missing-key, operation-URL and Responses-mode rejection cases.

**Remaining reliability gaps:** Empty candidates become the misleading message `no LLM key in .env` (`221-232`), including unsupported transport/model/base reasons. The singleton router retains the initial candidates and bounds (`194-218`), even though each extraction resolves configuration again (`228-234`). A changed mapping can therefore pass discovery but still invoke the old provider until process replacement. `_load_env` similarly caches file values (`34-45`). Neither configured keys nor the historical availability report establishes working inference today.

**Bounded proposal/tests:** Return sanitized structured resolution status (`unsupported_transport`, `missing_model`, `missing_key`, `invalid_base`) without key values. Pin one immutable effective configuration per process and report a configuration fingerprint/restart requirement, or deliberately rebuild on fingerprint change only when idle. Keep unsupported OAuth fail-closed; a future Hermes transport adapter needs its own approved contract, not an API-key substitution. Add offline configuration-change and reason-classification fixtures. Do not add automatic provider/model hopping.

### 2. AI extraction currently bypasses the deterministic parser's minimum contract

**Evidence:** `ai_filter.py:250-261` marks AI output `parse_ok=True` after only truthy `is_signal`, side and symbol checks. It does not require boolean `is_signal`, finite positive prices, bounded finite confidence, list-shaped TPs, allowed order type, explicit pending entry, or minimum protective geometry. Malformed structures can raise rather than abstain. In contrast, `parser.py:192-197` rejects pending orders without numeric entry and entries with neither TP nor SL. This is a normalization/contract gap; downstream executor behavior was not re-audited here and must not be assumed bypassed.

**Bounded proposal/tests:** A pure strict schema/normalizer shared by both extractors, preserving existing minimum protection rules without inventing levels. Reject booleans as prices, NaN/Infinity, negative/zero prices, non-object JSON, string `is_signal`, confidence outside [0,1], malformed TP arrays and unsupported order types. Preserve raw-text linkage, field evidence and extraction origin. Add adversarial fixtures for each invalid shape and ensure failure means review/abstain, never `parse_ok=True`.

### 3. Deterministic fallback is selective and can silently lose genuine signal candidates

**Evidence:** `parser.py:163-169` classifies missing direction/symbol as not-signal; the later missing-field review branches (`172-177`) are unreachable for those inputs. `daemon.py:613-620` asks AI only for incomplete signal-like parses or incomplete OCR parses; ordinary text classified not-signal gets no AI recovery and returns at `636-637`. AI failure leaves the original deterministic parse intact—useful safe fallback, but not universal extraction coverage. `parser.py:114-123` captures labeled targets only, then sorts them; a slash-separated unlabeled second target is not extracted by that loop. `test_suite.py:18-20` checks only that the first target is present, not completeness.

**Bounded proposal/tests:** Distinguish chatter from `candidate_needs_review` using explicit source templates/evidence, without granting entry authority. Add a bounded review-only recovery path for missing side/symbol and unsupported layouts. Preserve ordered labeled targets and explicit zones; reject ambiguous number lists rather than guessing. Add exact-array assertions for target lists, fractional FX ranges, pending layouts and missing-field cases. Track recoverable false negatives independently of trade eligibility.

### 4. Recap screening has inconsistent geometry and receipt semantics

**Evidence:** `daemon.py:649-655` accepts AI confirmation but copies only confidence, leaving the original regex geometry in use even if AI identified a different side/symbol/entry. Screening is skipped when `used_ai=True`. The `signal_received` event is emitted before screening and downstream gates (`627-634` versus `649-691`); it therefore cannot be interpreted as accepted fresh-entry evidence. `ai_filter.py:270-304` treats common emojis as recap suspicion, increasing reliance on AI even for legitimate emoji-bearing entries.

**Bounded proposal/tests:** Give classification (`new_entry`, `recap`, `management`, `ambiguous`) a separate typed result. A recap screen should never certify unrelated regex geometry: require exact canonical agreement or quarantine disagreement. Keep ambiguous/outage cases out of new entries. Emit a linked terminal decision with screening result, parse origin and reason; retain the initial receipt unchanged. Fixtures: recap/new-entry mixed post, emoji live entry during provider outage, contradictory AI geometry, already-AI-extracted recap, and receipt-before-rejection accounting.

### 5. Staleness means price distance here, not message or quote age

**Evidence:** Live `on_message` has no posted-time TTL check (`560-691`). Reconnect recovery accepts up to 20 messages per channel from the last ten minutes (`875-880`), without an explicit chronological sort. Price sanity runs only for float entries (`682-684`); market strings and AI integer entries skip it. `ai_filter.price_sane:309-324` permits import failure, does not check tick time or finite/positive bid/ask, and only compares midpoint distance. Old signals can still match today's price. This does not establish that downstream execution accepts every such input.

**Bounded proposal/tests:** Before expensive extraction and again before entry submission, attach posted/received/processed age evidence and explicitly reject or quarantine stale/future/missing timestamps according to an approved TTL policy. Validate quote timestamp/quality through the existing executor authority; do not introduce a second broker owner. Canonical numeric normalization should prevent integer/float divergence. Missing price-check dependencies should yield unknown/unavailable, not healthy. TTL changes require explicit parent approval; do not silently alter pending-order tolerances. Fixtures: old matching-price signal, fresh message/stale tick, future date, missing date, market entry, integer entry, reconnect ordering.

### 6. Online dedupe and research echo fingerprints answer different questions

**Evidence:** `ai_filter.py:327-351` rounds every numeric entry to two decimals and keys only symbol/side/entry. Distinct FX prices and different stop/TP/order geometries collide; all market entries for a side/symbol share one key. State is read/written as an unlocked JSON file with errors suppressed. `daemon.py:676-687` records dedupe before price rejection or execution outcome, potentially suppressing a later valid attempt after a rejected first observation. Source research already preserves Decimal precision and entry/SL/ordered TP/order geometry (`signal_source_audit.py:20-43`); receipt identity replay is separately counted (`69-75`). Research equality is not an execution-idempotency guarantee.

**Bounded proposal/tests:** Separate persistent atomic message/version idempotency, geometry echo evidence and execution attempts/outcomes. Keep market-only or incomplete geometry explicitly incomparable for exact-echo research. Reserve message claims transactionally; release/retain retry eligibility only by explicit outcome policy, never incidental JSON writes. Include stop, target order and order type in precision-preserving echo keys. Tests: adjacent five-decimal FX entries, changed stops, market-only ambiguity, concurrent claims, corrupted state, stale first observation, execution skip/retry and same-message replay after window expiry.

### 7. Edits and management updates lack exact message-version/parent binding

**Evidence:** `daemon.py:856,868` registers NewMessage only. Provenance is recorded (`630-632`), but edited versions have no explicit event handler here. `signal_source_audit.py:69-75` keeps only the first observed identity, discarding any later changed content under that identity as replay. Reconnect/live delivery share a path but not an ingestion-version ledger. Management is restricted to same-channel ledger tickets and live matching symbol/side (`760-803`), which is a valuable existing guard; however it selects the first eligible position (`793-796`), not an exact reply-parent signal. An unrelated recap from that channel can therefore target an ambiguous same-symbol position.

**Bounded proposal/tests:** Append-only message versions with edit timestamp/content hash, explicit receipt kind and separate immutable decision history. Edits default to review, never replayed entry authority. Resolve management against validated reply-parent lineage; ambiguous/no-parent matches should remain informational unless an existing explicitly approved policy resolves them. Preserve cross-peer safeguards (`test_signal_provenance.py:21-24`). Add edit-after-execution, old-recap/new-position, multiple same-channel positions, cross-peer reply and catch-up/live double-delivery fixtures.

### 8. Router bounds constrain caller wait, not actual outstanding provider work or reserved budget

**Evidence:** `model_router.py:151-160` times out `future.result` without stopping the provider task; `277-278` releases the concurrency slot while work may continue. Budget eligibility and recording are separate (`229-251`), allowing concurrent checks against the same remaining budget. `_LLMProvider.cost` returns a flat unit (`ai_filter.py:187-191`), not measured currency/token spend. The direct fallback bypasses router bounds (`235-239`), and its current behavior is explicitly required by `test_ai_router_integration.py:128-137`. Blocking OCR and synchronous extraction occur directly in the async handler (`daemon.py:575,616,650`; `ai_filter.py:113-133`), delaying unrelated ingestion despite worker-based provider calls.

**Bounded proposal/tests:** Retain in-flight capacity until underlying work actually ends; bound queued submissions; propagate remaining deadline to network calls. Use atomic budget reservations/reconciliation and label flat units accurately. On router construction/import failure, abstain rather than remove bounds (update the existing direct-fallback test intentionally). Move only pure extraction/OCR orchestration behind a bounded async worker interface; leave broker execution authority untouched. Extend tests beyond prompt return time (`test_model_router.py:314-329`) to assert peak unfinished provider tasks after repeated timeouts, concurrent budget reservations and event-loop responsiveness. Timed-out requests must not be treated as canceled billing.

## Source evidence and outcomes

Existing artifact `agent-reports/source-intelligence-20261027.md:3-7` reports a snapshot generated at `2026-10-27T17:40:11.576604+00:00`: 1,017 receipts, 1,013 unique messages and 20 sources. These are previously generated observations, not a fresh database query by this audit. Its source table (`11-30`) shows old receipt ages and sparse comparable geometry; two cross-source echoes are recorded for one source. This is evidence of observed reposting only, not authorship, complete-channel duplication rates, feed cessation, or profitability. Its learning evidence (`46-50`) contains three global finite outcomes but no demonstrated source-attributed realized-R linkage (`41-43`).

`source_intelligence.py:128,144-149` explicitly keeps profitability unknown, distinguishes receipt health from entry TTL and declines training-eligibility inference. Preserve these limits. Next high-value research artifact is an immutable source/message-version → extraction decision → shadow candidate → execution/fill → cost-adjusted realized-R chain, with rejected/unfilled/censored cases, spread/slippage/fees and chronological holdout evaluation. Deduplicate geometry across sources before train/test splitting to avoid echo leakage. More scraped channels or higher parse yield is not deeper edge evidence.

## Suggested bounded parent work packages

1. **Offline extraction contract and observability:** strict schema; sanitized provider status; receipt/decision separation; exact fixture corpus. No execution changes.
2. **Replay/version and source-evidence model:** precision-preserving geometry, append-only edits, transactional identities, shadow-only attribution. Explicit migration/retry semantics before deployment.
3. **Bounded extraction runtime:** fail-closed router unavailability, true outstanding-work/budget bounds, async-safe extraction queue. No broker ownership changes.
4. **Separate approval review:** posted-time/quote freshness enforcement and exact-parent management policy. These affect eligibility/management and require explicit approval plus regression checks of existing risk and execution controls.

Acceptance should emphasize zero false fresh-entry approvals on recap/replay/ambiguous fixtures, deterministic outage abstention, exact field preservation, reproducible source/outcome evidence and no relaxation of existing execution/risk policy—not a target number of trades.

