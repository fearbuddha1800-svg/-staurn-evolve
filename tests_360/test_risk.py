from scalp360.risk import RiskGovernor, RiskConfig, Verdict

# XAUUSD-like contract: $1 per point per 0.01 lot for demo math
VPP = 1.0        # account-ccy per point per lot
NOTIONAL = 100_000.0

def _g(**kw):
    return RiskGovernor(RiskConfig(**kw))

def test_rounds_down():
    # notional cap raised so the risk budget is the binding constraint
    d = _g(max_notional=10_000_000).size(balance=100_000, stop_distance_price=10,
           value_per_lot_per_point=VPP, notional_per_lot=NOTIONAL)
    assert d.verdict == Verdict.APPROVE
    # budget = 500; per-lot = 10 + 0.07 + 1.5 = 11.57 -> 43.21... raw -> floored to step
    assert abs(d.quantity - 43.21) < 1e-9, d.quantity
    assert abs(d.quantity/0.01 - round(d.quantity/0.01)) < 1e-6

def test_notional_cap_limits_size():
    # max_notional 50k / 100k per lot = 0.5 lots cap
    d = _g().size(balance=100_000, stop_distance_price=10, value_per_lot_per_point=VPP,
                  notional_per_lot=NOTIONAL)
    assert d.verdict == Verdict.APPROVE and abs(d.quantity - 0.5) < 1e-9

def test_min_lot_rejected_not_clamped():
    d = _g().size(balance=100, stop_distance_price=50, value_per_lot_per_point=VPP,
                  notional_per_lot=NOTIONAL)
    assert d.verdict == Verdict.REJECT and "min_lot" in d.reason

def test_daily_risk_cap():
    g = _g(max_daily_risk_pct=1.0)
    d = g.size(balance=100_000, stop_distance_price=10, value_per_lot_per_point=VPP,
               notional_per_lot=NOTIONAL, pending_risk=900, open_risk=100)
    assert d.verdict == Verdict.REJECT and d.reason == "daily risk cap"

def test_drawdown_halt():
    d = _g().size(balance=100_000, stop_distance_price=10, value_per_lot_per_point=VPP,
                  notional_per_lot=NOTIONAL, day_pnl=-4500)
    assert d.verdict == Verdict.REJECT and "drawdown" in d.reason

def test_notional_cap():
    # 500 / 100000 = 0.005 lots < min_lot 0.01 -> NO TRADE (reject, never clamp up)
    d = _g(max_notional=500).size(balance=10_000_000, stop_distance_price=5,
           value_per_lot_per_point=VPP, notional_per_lot=NOTIONAL)
    assert d.verdict == Verdict.REJECT and "min_lot" in d.reason
    d2 = _g(max_notional=10_000).size(balance=10_000_000, stop_distance_price=5,
            value_per_lot_per_point=VPP, notional_per_lot=1_000)
    assert d2.verdict == Verdict.APPROVE and d2.quantity == 10.0
