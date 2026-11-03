---
slug: signals.db.neural_eval
type: note
graph: gitnexus
---

{
  "baseline_winrate": 0,
  "cost_per_trade": 0.0,
  "decision": "CONTINUE",
  "evaluated_at": 1793686270.6203113,
  "evaluation_decision": "REJECT: insufficient labels (3 < 300)",
  "holdout_auc": 0.5,
  "limitations": [
    "purged_splits exists but evaluate does not invoke it",
    "validation threshold is selected before fitting again on full training slice",
    "binary win/loss net is not realized cash or R-multiple net"
  ],
  "model_winrate": 0,
  "n_test": 0,
  "n_train": 3,
  "n_val": 0,
  "net_after_cost_baseline": 0,
  "net_after_cost_model": 0,
  "promotion_blocker": "Only 3 labels match executed trades; remaining labels require provenance review. Diagnostic metrics cannot authorize promotion.",
  "scoring": "binary win/loss",
  "shadow_model_activated": false,
  "verified_executed_labels": 3
}

