---
slug: GOLDEN_EDGE_AI
type: note
graph: gitnexus
---

# Golden Edge AI: feature and evaluation contract

## Runtime behavior

`AIOverlay.evaluate(signal, pine_result, context=None)` returns an annotation for
**every** setup. `setup_confidence` (also `confidence`) describes the proposed
signal's eventual net-positive outcome, not confidence in a new direction.
No direction reversal, entry authorization, rules veto or automatic promotion.
`min_confidence` only sets an advisory `passes_threshold`; it cannot filter signals.
The default stub returns exactly 0.5, `untrained`, `passes_threshold=False`.
That number is an explicit neutral placeholder, NOT an estimated win rate.
Invalid models fail back to neutral with `invalid`, not a fake trained prediction.

`regime` is transition/trend/range/expansion/compression/unknown from Golden Eye.
`regime_bias` is signed `(plusDI-minusDI)/(plusDI+minusDI)` in [-1,1]: positive
bullish, negative bearish. It is descriptive DMI bias, NOT another probability.
Its missing mask distinguishes unknown bias from measured zero.

Injected models must declare `is_trained=True`, `feature_version=golden_edge_v1`.
A category-aware adapter implements `predict_setup(features, categories)` returning
`confidence` and optional `rationale`; numeric-only adapters can implement `predict`.
Any category ablation must be explicit in its artifact/evaluation report.
Fit encoders/scalers/calibration on development data only; freeze feature order,
category vocabulary and unknown bucket with the model. Never encode symbols by
Python hash or arbitrary numeric ordinal. `trained_shadow` is not approved/live.

`signal_watcher.py` publishes the complete annotation (features, masks, categories,
regime, bias, schema, model status) inside the existing `pine_signal.ai` envelope.
It supplies assignment symbol, timeframe and setup identity. AI-disabled behavior
is retained. No collector, broker process, DB or trading configuration is modified.

## Inputs and feature list

Producer priority: merged explicit `context` > `signal.golden_eye` >
`pine_result.golden_eye` > `pine_result.plots`. Context maps in signal/result are
merged first; the explicit context wins. A present missing input does NOT fall
back to an older/lower-priority observation.

- Golden Eye: regime (raw enum + five one-hot columns), strength, consensus,
  persistence, acceleration, disagreement/disagreement_index, +DI, -DI, ADX,
  MTF agreement, displacement/ATR, efficiency ratio (ER).
- Market: RSI, positive ATR, nonnegative executable spread **in price units**,
  UTC hour or timezone-aware ISO `bar_close_time`, policy_allowed (0/1).
- Derived: proposed direction (+1/-1/0), signed acceleration/displacement aligned
  to that direction, DMI balance and alignment, spread/ATR, UTC hour sine/cosine.
- Categories: symbol, session, policy/version, timeframe, setup_id. Unknown stays
  `unknown`; session must come from a versioned calendar (including DST), not
  an assumed broker/server timezone.
- Every nullable numeric/derived input has `<name>_missing`; absent/nonfinite or
  invalid inputs become zero **with mask=1**, never an invented observation.
  Strength/consensus/persistence/disagreement/MTF/ER must be [0,1]; RSI [0,100].
- Canonical keys and exact Golden Eye Pine data-window plot titles are supported;
  plot scalars, `{latest:...}`, arrays and `{data:[{value:...}]}` are accepted.
  Last missing array elements are not replaced by prior valid values.
- Price, historical bar count, outcomes, broker P&L and signal `active` do not
  become predictive confidence. No wall-clock hour enters historical scoring.

### Producer limitations (not claimed solved)

The current watcher runs each **assigned strategy**, not a separate time-aligned
Golden Eye context pass. Strategies without these plots/context therefore produce
missing masks, not complete Golden Eye inputs. Attach `golden_eye` snapshots for
the same symbol, timeframe and confirmed bar before collecting training rows.
The Golden Eye alert JSON currently omits ER and displacement/ATR; use its plots
or extend the producer rather than invent those fields. RSI/ATR/spread/session/
policy are additional producer context, not supplied by Golden Eye's alert JSON.

`pinets_bridge.js` currently sets `latest` to the last **finite** plot value, which
may predate the last bar. The overlay cannot recover discarded timestamps. Before
accepting training snapshots, upgrade/validate that producer to preserve terminal
missing values and timestamps and reject stale/unconfirmed/mismatched MTF data.
Do not treat the bridge's summary as proof of point-in-time freshness. Confirmed
HTF values must have been available at setup time (no lookahead/repaint). Current
runtime remains diagnostic shadow while these collection prerequisites are open.

## Honest label-collection plan

1. Pre-register setup definition/version, rules baseline, policy, entry/exit rules,
   maximum holding horizon H (in time), cost assumptions, split dates, embargo,
   probability threshold selection rule and minimum coverage before collection.
2. At every confirmed Golden Edge candidate, append an immutable snapshot before
   any outcome is known: unique candidate ID/hash, original bar close and decision
   timestamps, symbol/timeframe, direction, setup/rules/policy versions, full
   Golden Eye snapshot with timestamps/confirmation, features/masks/categories,
   model/schema version, baseline accept/reject and reason, entry/SL/TP, spread,
   executable bid/ask, expected commission/slippage and original cash risk.
   Preserve candidates rejected by the shadow model to avoid selection bias.
3. Maintain separate executed-trade and paper-candidate provenance. Real labels
   require unique signal->order->position linkage, all entry/exit deals, fully
   closed volume, broker timestamps, realized P&L including commission/swap/fees.
   Store `y = 1 iff realized net P&L > 0` (zero is 0) and `net_R=net_P&L/original
   cash risk`. Do not subtract spread/slippage a second time from realized P&L.
4. For non-executed opportunities, use a separately marked paper/replay dataset
   with executable quotes and frozen fill/exit/cost rules; pessimistically resolve
   same-bar SL/TP ambiguity or quarantine it. No claim these are executed labels.
   Never combine paper and executed metrics as independent broker evidence.
5. Persist label start/end interval (decision through final outcome), immutable
   snapshot hash, source evidence IDs and audit status. Pending/open, stale,
   unmatched, partial-close, duplicate, revised/lookahead or ambiguous rows are
   quarantined, not wins/losses. Multiple fills of one setup are one observation;
   correlated/repeated alerts share a group. Reconcile legacy labels before use.
   Never fabricate labels or manufacture count by resampling/oversampling.
6. Use a new versioned Golden Edge dataset; existing neural labels do not qualify
   merely because they exist. Collector cadence/process changes need separate
   operational approval. This change does not start one or write the live DB.

## Pre-registered evaluation and promotion criteria

**No training/performance result is asserted by this implementation.** Tests use
synthetic fixtures only, never counted as labels. Start with regularized logistic
regression as a low-capacity challenger; neural complexity must earn its place.

- At least **300 completed, unique, audited usable labels per proposed setup**,
  not 300 pooled across unrelated setups. Enough labels of both outcomes and
  regimes are required; 300 is a floor, not proof of significance.
- Chronological development/train 60%, validation 20%, untouched final holdout 20%
  by decision time (at least 60 holdout rows after purging; extend collection if
  fewer). Freeze dates once selected. Both classes must exist in every scored
  fold; insufficient counts mean unavailable, never AUC=0.5 by convention.
- Use expanding-window development folds. **Purge** any training row whose
  decision->label-end interval overlaps the scored validation/holdout interval;
  group duplicate setups/positions across symbols/TFs and keep groups together.
  Require training outcome end < test start minus pre-registered embargo >= H;
  rows in embargo are excluded. Keep the final holdout unseen by preprocessing,
  model selection, calibration and threshold tuning. Purging is interval-aware,
  not random train/test splitting or merely dropping a fixed row count.
- Tune regularization, train-only imputers/scalers/category encoders and the
  advisory score threshold on development/validation only. Refit on eligible
  development data with held-out calibration, freeze artifact and hashes, then
  score holdout once. A failed attempt needs a new future holdout, not retuning.
- Required holdout **ROC AUC >= 0.58**, report tie-aware ROC AUC, PR AUC, class
  balance, Brier score and calibration bins. Report day/setup-group block-bootstrap
  95% uncertainty (not IID row bootstrap), purged counts and sample coverage.
- Compare **the same candidate cohort, sizing/risk budget, policy and cost model**
  with frozen rules-only baseline. Compare AI-selected net R summed / all eligible
  opportunities (rejected trades contribute zero) and total net R; do not claim
  improvement solely from win rate or mean R per selected trade. Report selected
  trade count, coverage, drawdown, costs and symbol/regime/session breakdowns.
  A pre-registered cost stress test must not erase the improvement.
- Promote **that setup only** if AUC gate passes AND paired holdout net-R uplift
  over rules baseline is positive with the block-bootstrap 95% lower bound > 0,
  positive net expectancy, and no worse holdout max drawdown at matched risk.
  Require at least 30 selected holdout trades and 25% coverage (pre-register
  stricter limits if needed); otherwise collect more data. Adjust multiplicity
  across setup/model searches; never promote a weak subgroup from pooled AUC.
- Record dataset/artifact hashes, code/schema/rules versions, split boundaries,
  purging/embargo, all attempted models and approval rationale. Separate audited
  evaluation recommendation from operational activation. Prospective shadow
  validation and explicit owner approval are required; existing HALT/STOP, policy,
  sizing and execution safety guards retain authority. Drift/missingness/cost
  deterioration means return to rules-only, never loosen gates to hit a quota.

Existing `scalp360.neural.evaluate` must not be assumed to meet this protocol:
its legacy evaluation can omit purged splitting and use zero-cost binary scoring.
`neural_pipeline.py` provides broker reconciliation infrastructure, but its model
and schema are not automatically the Golden Edge model or an approved artifact.

## Offline verification

Run `python -m unittest test_golden_edge_overlay -v` from the relay directory.
No MT5 connection, real orders, collector execution, live ledger writes, model
training or performance certification is needed or permitted by these tests.

