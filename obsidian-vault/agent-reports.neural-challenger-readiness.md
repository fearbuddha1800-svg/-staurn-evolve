---
slug: agent-reports.neural-challenger-readiness
type: note
graph: gitnexus
---

# Neural Challenger Readiness — Drift & Calibration Review

**Date:** 2026-10-17  
**Author:** Hermes Agent (automated health check)  
**DB:** `C:\Users\voidk\.hermes\workspace\signal-relay\signals.db`  
**Status:** `NOT_TRAINED` — gate not met

---

## 1. Current Label Count

| Metric | Value |
|--------|-------|
| Total labels recorded | 3 |
| Complete (outcome set) | 2 |
| Pending (outcome NULL) | 1 |
| Wins (outcome=1) | 0 |
| Losses (outcome=0) | 2 |
| Gate (min_labels) | 300 |
| **Distance to gate** | **298** |

**Source:** `neural_labels` table, queried 2026-10-17T16:44:11Z.

---

## 2. What the Gate Requires

The evaluation harness (`scalp360.neural.evaluate`) refuses to train below
`min_samples=300` complete labels. The full promotion protocol requires:

1. **≥ 300 complete labels** — labels with a non-NULL `outcome` (0 or 1).
2. **Holdout AUC ≥ 0.58** — measured on the last 20% of chronological data,
   after purged k-fold cross-validation with embargo.
3. **After-cost net profit > baseline** — the challenger must beat the
   rules-based baseline on the holdout set after accounting for spread,
   commission, and slippage.
4. **Calibration review** — the model's predicted probabilities must be
   reasonably calibrated (no systematic over/under-confidence).

---

## 3. Evidence Still Missing

### 3.1 Quantity
- **298 more complete labels** are needed before any training can occur.
- At the current accumulation rate of **1.82 labels/day** (observed over a
  1.65-day window), reaching 300 labels would take approximately **163 days**
  (~5.4 months) if the rate holds. This is a lower bound — the rate may
  decrease if trade frequency drops.

### 3.2 Quality
- **Win rate is 0%** (0 wins / 2 complete labels). This is far too small a
  sample to assess whether the pipeline is systematically biased toward
  losing labels, but it means the baseline win rate is currently 0%.
- **Both complete labels are losses** with profit_r of -0.0020 and -0.0441.
  The first is essentially breakeven (spread cost), the second is a small
  loss. Neither hit the original SL, suggesting the positions were closed
  manually or by a trailing stop before the SL was reached.

### 3.3 Calibration
- **No calibration data exists.** Calibration requires a trained model's
  predicted probabilities on a validation set. With 0 training runs, there
  is nothing to calibrate.

### 3.4 Drift
- **No drift assessment is possible.** Drift detection requires comparing
  feature distributions across time windows. With 3 labels spanning 1.65
  days, there is no meaningful temporal distribution to compare.

### 3.5 Feature Integrity
- **All 3 labels have valid 25-dimensional feature vectors** (0 malformed).
- **Map consistency is clean** — all 3 tickets in `neural_label_map` have
  matching `neural_labels` rows and vice versa. No orphans.

---

## 4. Baseline Definition

The challenger must beat the **rules-based baseline** as defined in
`scalp360.neural.evaluate`:

- **Baseline strategy:** Take every signal from the existing pipeline
  (daemon → executor → manage) with the current risk management rules
  (ATR-based or channel-based SL/TP, 0.5% risk per trade, max 3 concurrent,
  2% daily cap, 4% drawdown halt).
- **Baseline win rate:** The fraction of trades that hit TP1 before SL
  (after costs) on the holdout set. Currently **0%** (0/2), but this is
  statistically meaningless at n=2.
- **Baseline net after cost:** `wins - losses - cost_per_trade * n_trades`
  on the holdout set. Currently **-2.0** (0 wins - 2 losses - 0 cost).
- **Challenger must achieve:** `model_net > baseline_net > 0` AND
  `holdout_auc >= 0.58` to be promoted.

### Concrete Baseline Numbers (from current data)

| Metric | Value |
|--------|-------|
| Baseline win rate | 0.0% (0/2) |
| Baseline net after cost | -2.0 R |
| Cost per trade | 0.0 (not yet configured) |
| Model win rate | N/A (not trained) |
| Model net after cost | N/A (not trained) |

---

## 5. Label Detail (Chronological)

| id | ts | symbol | side | entry | sl | outcome | profit_r |
|----|----|--------|------|-------|----|---------|----------|
| 3 | 1792045335 | EURUSD | buy | 1.1224 | 1.1174 | 0 (loss) | -0.0020 |
| 2 | 1792183227 | XAUUSD | buy | 4159.94 | 4144.07 | 0 (loss) | -0.0441 |
| 1 | 1792187662 | XAUUSD | buy | 4158.99 | 4143.32 | pending | — |

**Observation:** Label id=1 is still pending — the position has not yet closed.
Labels id=2 and id=3 are both losses, but neither hit the original SL
(profit_r > -1.0), indicating early/manual closes.

---

## 6. Pipeline Health Summary

| Check | Status |
|-------|--------|
| DB accessible | ✅ |
| neural_labels table exists | ✅ |
| neural_label_map table exists | ✅ |
| Map consistency (no orphans) | ✅ |
| Feature vector dimensions (25-dim) | ✅ All valid |
| Label accumulation rate | 1.82/day |
| Gate met (≥300) | ❌ — 298 short |
| Model trained | ❌ — gate not met |
| Promotion | ❌ — gate not met |

---

## 7. Recommendation

**Do not attempt to train or promote a challenger.** The pipeline is
structurally healthy (clean schema, consistent map, valid features) but
quantitatively insufficient (2/300 labels). The system is correctly
configured to refuse training below the gate.

**Next steps:**
1. Continue running `neural_label_collector.py watch 15` to accumulate labels.
2. Monitor `label_health.py` output periodically to track accumulation rate.
3. Once ≥300 complete labels exist, run `neural_label_collector.py` (status
   mode) to trigger the evaluation harness.
4. Review the EvalReport for holdout AUC, calibration, and baseline comparison.

---

## 8. Raw Command Output

### `neural_label_collector.py` (status mode)
```
neural labels: 2 complete / 3 recorded (1 pending close)
evaluation deferred: need 298 more complete labels (gate 300, holdout AUC gate 0.58)
```

### `test_neural_collector.py`
```
13 passed, 0 failed
```

### `test_label_health.py`
```
40 passed, 0 failed
```

### `label_health.py` (against live DB)
```
status: accumulating
total: 3, complete: 2, pending: 1
wins: 0, losses: 2
map: 3 rows, consistent: True
feature dims: 3 checked, 0 malformed
rate: 1.821 labels/day over 1.65 days
gate: 300, distance: 298, met: False
```

---

*Report generated by `label_health.py` + manual review. No model was trained.
No promotion occurred. No data was fabricated.*

