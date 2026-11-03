import sqlite3
from scalp360.lineage import LineageStore, IntentState

def _s():
    db = sqlite3.connect(":memory:"); return db, LineageStore(db)

def test_no_unlinked_update():
    db, ls = _s()
    ls.create_intent("i1", "src:1:0", "src", "XAUUSD", "SELL", 100.0)
    ls.transition("i1", IntentState.FILLED, IntentState.RESERVED)
    assert ls.bind_position("pos-900", "i1", "900", "XAUUSD", "SELL")
    # an UPDATE event for a different message must not reach the position
    assert not ls.update_position_via_signal("pos-900", "src:2:0")
    # the bound signal path works
    assert ls.update_position_via_signal("pos-900", "src:1:0")

def test_symbol_side_mismatch_refused():
    db, ls = _s()
    ls.create_intent("i1", "src:1:0", "src", "XAUUSD", "SELL", 100.0)
    ls.transition("i1", IntentState.FILLED, IntentState.RESERVED)
    assert not ls.bind_position("pos-901", "i1", "901", "EURUSD", "SELL")

def test_original_r_immutable():
    db, ls = _s()
    ls.create_intent("i1", "src:1:0", "src", "XAUUSD", "SELL", 100.0)
    assert ls.original_r("i1") == 100.0
    db.execute("UPDATE intents SET risk_amount=5 WHERE intent_id='i1'")
    assert ls.original_r("i1") == 100.0   # original column untouched

def test_transition_race():
    db, ls = _s()
    ls.create_intent("i1", "src:1:0", "src", "XAUUSD", "SELL", 100.0)
    assert ls.transition("i1", IntentState.SUBMITTED, IntentState.RESERVED)
    assert not ls.transition("i1", IntentState.FILLED, IntentState.RESERVED)
