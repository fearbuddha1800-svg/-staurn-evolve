import sqlite3
from scalp360.console import Console

def _c(core=None):
    db = sqlite3.connect(":memory:")
    return Console(db, {8877588890}, {8877588890}, core_set_halt=core)

def test_auth():
    c = _c()
    assert c.pause("t1", 1, 8877588890) == "unauthorized"
    assert c.pause("t1", 8877588890, 2) == "unauthorized"

def test_pause_idempotent_and_propagates():
    calls = []
    c = _c(core=lambda t, h: calls.append((t, h)) or True)
    assert c.pause("t1", 8877588890, 8877588890) == "paused"
    assert c.pause("t1", 8877588890, 8877588890) == "already processed"
    assert calls == [("t1", True)]
    assert c.is_halted("t1")
    assert c.resume("t1", 8877588890, 8877588890) == "resumed"
    assert calls[-1] == ("t1", False)

def test_core_failure_falls_back_to_local_latch():
    c = _c(core=lambda t, h: False)
    assert c.pause("t1", 8877588890, 8877588890) == "core halt failed - local latch only"
    assert not c.is_halted("t1")
