import sqlite3, time
from scalp360.executor import ExecutionAuthority, PaperBroker, FreshnessPolicy
from scalp360.risk import RiskGovernor, RiskConfig
from scalp360.cursor import CursorStore
from scalp360.events import SignalEvent, EventKind
from scalp360.gold_parser import parse_gold

GOLD = ("XAUHQ DIRECTION: SELL NOW ENTRY: 4184/90 STOP LOSS: 4195 "
        "TAKE PROFIT: TP1 → 4175 TP2 → 4165")

def _ex(demo=True, login=113783047):
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE IF NOT EXISTS event_claims(event_id TEXT PRIMARY KEY,"
               " digest TEXT, claimed_at REAL)")
    ex = ExecutionAuthority(db, PaperBroker(login=login, demo=demo),
                            RiskGovernor(RiskConfig()), FreshnessPolicy(),
                            CursorStore(db), expected_login=113783047)
    return ex

def _ev(age=10):
    return SignalEvent(source="t1:xauhq", message_id=1, text=GOLD,
                       original_at=time.time()-age, kind=EventKind.NEW_ENTRY)

def test_account_verification_blocks_wrong_login():
    ex = _ex(login=999)
    try:
        ex.handle(_ev(), balance=100_000, stop_distance_price=11,
                  value_per_lot_per_point=1.0, notional_per_lot=100_000,
                  quote_age_s=1, spread_points=10, price=4187,
                  entry_low=4184, entry_high=4190, side="SELL")
        assert False, "must raise"
    except Exception as e:
        assert "account mismatch" in str(e)

def test_live_account_refused_in_demo_mode():
    ex = _ex(demo=False)
    try:
        ex.handle(_ev(), balance=100_000, stop_distance_price=11,
                  value_per_lot_per_point=1.0, notional_per_lot=100_000,
                  quote_age_s=1, spread_points=10, price=4187,
                  entry_low=4184, entry_high=4190, side="SELL")
        assert False
    except Exception as e:
        assert "require_demo" in str(e)

def test_stale_signal_blocked():
    ex = _ex()
    r = ex.handle(_ev(age=500), balance=100_000, stop_distance_price=11,
                  value_per_lot_per_point=1.0, notional_per_lot=100_000,
                  quote_age_s=1, spread_points=10, price=4187,
                  entry_low=4184, entry_high=4190, side="SELL")
    assert r.startswith("BLOCKED: stale signal")

def test_recap_never_trades():
    ex = _ex()
    ev = SignalEvent(source="t1:xauhq", message_id=2,
                     text="Today's recap: closed trades summary, results so far",
                     kind=EventKind.NEW_ENTRY)
    r = ex.handle(ev, balance=100_000, stop_distance_price=11,
                  value_per_lot_per_point=1.0, notional_per_lot=100_000,
                  quote_age_s=1, spread_points=10, price=4187,
                  entry_low=4184, entry_high=4190, side="SELL")
    assert "recap" in r

def test_duplicate_delivery_no_double_fill():
    ex = _ex()
    kw = dict(balance=100_000, stop_distance_price=11, value_per_lot_per_point=1.0,
              notional_per_lot=100_000, quote_age_s=1, spread_points=10,
              price=4187, entry_low=4184, entry_high=4190, side="SELL")
    r1 = ex.handle(_ev(), **kw)
    r2 = ex.handle(_ev(), **kw)
    assert r1.startswith("FILLED"), r1
    assert not r2.startswith("FILLED")
