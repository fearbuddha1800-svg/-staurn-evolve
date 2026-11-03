---
slug: tests_360.test_gold_parser
type: note
graph: gitnexus
---

"""Regression fixtures straight from export message 2243 (2026-10-14)."""
from scalp360.gold_parser import parse_gold, _parse_zone, Zone

GOLD_2243 = ("🏛 XAUHQ | XAU SIGNAL 🟡  DIRECTION: 📉 SELL NOW "
             "ENTRY: 4184/90 STOP LOSS: 4195🛡  TAKE PROFIT:  TP1 → 4175  "
             "TP2 → 4165  TP3 → 4155  TP4 →4145/4120")

def test_zone_shorthand():
    z = _parse_zone("4184/90")
    assert z == Zone(4184.0, 4190.0), f"zone collapsed: {z}"

def test_zone_single():
    assert _parse_zone("4175") == Zone(4175.0, 4175.0)

def test_full_signal_2243():
    s = parse_gold(GOLD_2243)
    assert s is not None, "must parse the exact production signal"
    assert s.side == "SELL" and s.symbol == "XAUUSD"
    assert s.entry == Zone(4184.0, 4190.0)
    assert s.stop == 4195.0
    labels = [t[0] for t in s.targets]
    assert labels == ["TP1", "TP2", "TP3", "TP4"]
    assert s.targets[3][1] == Zone(4120.0, 4145.0)   # TP4 →4145/4120 preserved

def test_buy_geometry():
    txt = "XAUHQ | XAU SIGNAL 🟢 DIRECTION: 📈 BUY NOW ENTRY: 4170/75 " \
          "STOP LOSS: 4160 TAKE PROFIT: TP1 → 4180 TP2 → 4190"
    s = parse_gold(txt)
    assert s is not None and s.side == "BUY"
    assert s.entry == Zone(4170.0, 4175.0) and s.stop == 4160.0

def test_broken_geometry_abstains():
    # sell with SL below entry is nonsense -> abstain, never guess
    assert parse_gold("DIRECTION: SELL NOW ENTRY: 4184/90 STOP LOSS: 4100 TP1 → 4175") is None

def test_no_direction_abstains():
    assert parse_gold("XAUHQ recap of the day, results summary") is None

def test_no_targets_abstains():
    assert parse_gold("DIRECTION: BUY NOW ENTRY: 4170 STOP LOSS: 4160") is None

