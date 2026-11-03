---
slug: scalp360.risk
type: note
graph: gitnexus
---

"""One serialized risk authority per account.
Fixes P0: floor-lot rounding, fee/slippage reserves, min-lot rejection,
aggregate pending+open risk, daily drawdown halt. All in account currency.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class Verdict(str, Enum):
    APPROVE = "APPROVE"
    REJECT  = "REJECT"

@dataclass(frozen=True)
class SizingDecision:
    verdict: Verdict
    quantity: float = 0.0          # lots, floored to broker step AND caps
    reason: str = ""
    risk_amount: float = 0.0       # account-ccy worst case incl. costs

@dataclass
class RiskConfig:
    risk_per_trade_pct: float = 0.5    # % of balance risked per trade
    max_concurrent: int = 3
    max_daily_risk_pct: float = 2.0    # hard cap on sum(open+worst-case)/day
    max_notional: float = 50_000.0     # per-position notional cap (account ccy)
    daily_halt_drawdown_pct: float = 4.0
    lot_step: float = 0.01
    min_lot: float = 0.01
    fee_per_lot: float = 0.07          # round-trip fee per lot, account ccy
    slippage_per_lot: float = 1.5      # modeled adverse slip per lot, account ccy

class RiskGovernor:
    def __init__(self, cfg: RiskConfig):
        self.cfg = cfg

    def size(self, *, balance: float, stop_distance_price: float,
             value_per_lot_per_point: float,
             notional_per_lot: float,
             pending_risk: float = 0.0, open_risk: float = 0.0,
             open_count: int = 0, day_pnl: float = 0.0) -> SizingDecision:
        c = self.cfg
        if open_count >= c.max_concurrent:
            return SizingDecision(Verdict.REJECT, reason="max_concurrent reached")
        if stop_distance_price <= 0 or value_per_lot_per_point <= 0:
            return SizingDecision(Verdict.REJECT, reason="invalid pricing inputs")
        if balance <= 0:
            return SizingDecision(Verdict.REJECT, reason="no balance")
        if day_pnl <= -balance * c.daily_halt_drawdown_pct / 100.0:
            return SizingDecision(Verdict.REJECT, reason="daily drawdown halt")
        budget = balance * c.risk_per_trade_pct / 100.0
        # per-lot worst case: stop distance + fee + modeled slippage reserve
        per_lot_risk = (stop_distance_price * value_per_lot_per_point
                        + c.fee_per_lot + c.slippage_per_lot)
        if per_lot_risk <= 0:
            return SizingDecision(Verdict.REJECT, reason="non-positive per-lot risk")
        # candidate lot counts from each cap; final = floor of ALL of them
        lots_by_risk = budget / per_lot_risk
        lots_by_notional = (c.max_notional / notional_per_lot
                            if notional_per_lot > 0 else float("inf"))
        raw = min(lots_by_risk, lots_by_notional)
        lots = int(raw / c.lot_step) * c.lot_step
        lots = round(lots, 6)
        if lots < c.min_lot:
            return SizingDecision(Verdict.REJECT,
                                  reason=f"min_lot {c.min_lot} exceeds risk budget "
                                         f"(raw {round(raw,4)} lots)")
        risk_amount = lots * per_lot_risk
        if pending_risk + open_risk + risk_amount > balance * c.max_daily_risk_pct / 100.0:
            return SizingDecision(Verdict.REJECT, reason="daily risk cap")
        return SizingDecision(Verdict.APPROVE, quantity=lots,
                              risk_amount=risk_amount, reason="ok")

## Links from
- [[event_bus]]
- [[integration_status]]
- [[neural_pipeline]]
- [[scalp360_bridge]]
- [[test_intelligence_integration]]
- [[test_neural_watch_gate]]
- [[tests_360.test_ai_neural]]
- [[tests_360.test_console]]
- [[tests_360.test_cursor]]
- [[tests_360.test_executor]]
- [[tests_360.test_gold_parser]]
- [[tests_360.test_lineage]]
- [[tests_360.test_risk]]
