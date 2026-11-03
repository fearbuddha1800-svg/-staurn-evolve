"""Neural/ML challenger harness with honest evaluation.
No training happens until enough independent labels exist. Purged chronological
splits with embargo, calibration on validation, untouched holdout, after-cost
shadow comparison vs. the rules baseline.
"""
from __future__ import annotations
import math, random
from dataclasses import dataclass
from typing import List, Tuple, Sequence, Callable

from event_bus import bus

Row = Tuple[float, ...]     # frozen features at decision time
Label = int                 # 1 = would have hit TP1 before SL (after costs), 0 otherwise

@dataclass
class EvalReport:
    n_train: int; n_val: int; n_test: int
    holdout_auc: float
    baseline_winrate: float
    model_winrate: float
    net_after_cost_baseline: float
    net_after_cost_model: float
    decision: str            # PROMOTE | KEEP_SHADOW | REJECT

def _auc(scores: List[float], labels: List[int]) -> float:
    if len(scores) != len(labels) or any(y not in (0, 1) for y in labels):
        raise ValueError("AUC requires equally sized scores and binary labels")
    if any(not math.isfinite(s) for s in scores):
        raise ValueError("AUC scores must be finite")
    pairs = sorted(zip(scores, labels))
    pos = sum(labels); neg = len(labels) - pos
    if pos == 0 or neg == 0: return 0.5
    # Mann-Whitney ranks: tied scores share their average rank (half credit).
    rank_sum = 0.0
    i = 0
    while i < len(pairs):
        j = i + 1
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        rank_sum += ((i + 1 + j) / 2) * sum(y for _, y in pairs[i:j])
        i = j
    return (rank_sum - pos*(pos+1)/2) / (pos*neg)

def purged_splits(n: int, k: int = 5, embargo: int = 5) -> List[Tuple[List[int], List[int]]]:
    """Chronological k-fold with purge+embargo: no train sample within `embargo`
    rows of a validation boundary leaks across."""
    fold = n // k
    out = []
    for i in range(k):
        lo, hi = i*fold, (i+1)*fold if i < k-1 else n
        test = list(range(lo, hi))
        train = list(range(0, max(0, lo-embargo))) + list(range(min(n, hi+embargo), n))
        out.append((train, test))
    return out

class LogisticChallenger:
    """Tiny numpy-free logistic regression (SGD). Exists so the harness is
    runnable with zero deps; swap in MLP/TCN later through the same contract."""
    def __init__(self, dim: int, lr: float = 0.1, epochs: int = 200, seed: int = 7):
        rng = random.Random(seed)
        self.w = [rng.uniform(-0.01, 0.01) for _ in range(dim)]
        self.b = 0.0; self.lr = lr; self.epochs = epochs
    def fit(self, X: Sequence[Row], y: Sequence[int]) -> None:
        for _ in range(self.epochs):
            for xi, yi in zip(X, y):
                z = sum(w*v for w, v in zip(self.w, xi)) + self.b
                p = 1/(1+math.exp(-max(-30, min(30, z))))
                g = p - yi
                for j in range(len(self.w)):
                    self.w[j] -= self.lr * g * xi[j]
                self.b -= self.lr * g
    def score(self, xi: Row) -> float:
        z = sum(w*v for w, v in zip(self.w, xi)) + self.b
        return 1/(1+math.exp(-max(-30, min(30, z))))

def evaluate(X: Sequence[Row], y: Sequence[Label],
             model_factory: Callable[[int], object] = None,
             cost_per_trade: float = 0.0, min_samples: int = 300) -> EvalReport:
    """Full protocol. Abstains (REJECT) below min_samples - no validating on
    a handful of trades."""
    n = len(X)
    if n < min_samples:
        return EvalReport(n,0,0,0.5,0,0,0,0,
            f"REJECT: insufficient labels ({n} < {min_samples})")
    mf = model_factory or (lambda d: LogisticChallenger(d))
    # walk-forward: last 20% is the untouched holdout
    cut = int(n*0.8)
    Xtr, ytr = list(X[:cut]), list(y[:cut])
    Xho, yho = list(X[cut:]), list(y[cut:])
    # calibration threshold chosen on the tail of train (val slice)
    vcut = int(len(Xtr)*0.8)
    model = mf(len(Xtr[0])); model.fit(Xtr[:vcut], ytr[:vcut])
    val_scores = [model.score(x) for x in Xtr[vcut:]]
    thr = sorted(val_scores)[int(0.7*len(val_scores))] if val_scores else 0.5
    model.fit(Xtr, ytr)
    ho_scores = [model.score(x) for x in Xho]
    pred = [1 if s >= thr else 0 for s in ho_scores]
    m_win = sum(1 for p, yi in zip(pred, yho) if p == 1 and yi == 1)
    m_cnt = sum(pred)
    b_win = sum(yho); b_cnt = len(yho)
    m_net = m_win - (m_cnt - m_win) - cost_per_trade*m_cnt
    b_net = b_win - (b_cnt - b_win) - cost_per_trade*b_cnt
    auc = _auc(ho_scores, yho)
    decision = ("PROMOTE" if auc >= 0.58 and m_net > b_net > 0 else
                "KEEP_SHADOW" if auc >= 0.55 else "REJECT")
    try:
        bus.publish({"type": "neural_prediction", "source": "neural",
                     "payload": {"auc": auc, "decision": decision,
                                 "model_winrate": round(m_win / max(1, m_cnt), 4),
                                 "baseline_winrate": round(b_win / max(1, b_cnt), 4),
                                 "n_train": len(Xtr), "n_holdout": len(Xho),
                                 "cost_per_trade": cost_per_trade},
                     "trace_id": None})
    except Exception:  # noqa: BLE001 - the bus must not break the evaluation harness
        pass
    return EvalReport(len(Xtr), len(Xtr)-vcut, len(Xho), round(auc,4),
        round(b_win/max(1,b_cnt),4), round(m_win/max(1,m_cnt),4),
        round(b_net,1), round(m_net,1), decision)
