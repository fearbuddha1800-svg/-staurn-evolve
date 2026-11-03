"""Tests for edge_stats_bridge.py — Wilson CI math, per-channel stats shape, empty-ledger handling."""

import json
import math
import os
import sys
import tempfile
import sqlite3

# Add signal-relay to path
BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import edge_stats_bridge as esb


def test_wilson_known_values():
    """Wilson 95% CI matches textbook values (from edge-stats test suite)."""
    # 5 successes in 10 trials -> estimate=0.5, CI=[0.2366, 0.7634]
    w = esb.wilson(5, 10)
    assert w is not None
    assert abs(w.estimate - 0.5) < 1e-10
    assert abs(w.lo - 0.2366) < 1e-4
    assert abs(w.hi - 0.7634) < 1e-4

    # 0 successes in 5 trials -> lo=0, hi=z²/(n+z²)
    w = esb.wilson(0, 5)
    assert w is not None
    assert w.lo == 0.0
    z2 = esb.Z_95 ** 2
    expected_hi = z2 / (5 + z2)
    assert abs(w.hi - expected_hi) < 1e-10

    # 5 successes in 5 trials -> hi=1, lo=1 - (zero hi)
    w = esb.wilson(5, 5)
    assert w is not None
    assert w.hi == 1.0
    zero_w = esb.wilson(0, 5)
    assert abs(w.lo - (1 - zero_w.hi)) < 1e-10

    # Interval tightens as n grows at fixed p=0.5
    small = esb.wilson(5, 10)
    large = esb.wilson(500, 1000)
    assert small is not None and large is not None
    assert (large.hi - large.lo) < (small.hi - small.lo)

    # Edge cases
    assert esb.wilson(0, 0) is None  # empty -> None
    try:
        esb.wilson(6, 5)
        assert False, "should raise for k > n"
    except ValueError:
        pass
    try:
        esb.wilson(-1, 5)
        assert False, "should raise for k < 0"
    except ValueError:
        pass

    print("PASS test_wilson_known_values")


def test_apply_guards():
    """Minimum-sample guards: warn < 30, refuse < 10."""
    g = esb.apply_guards(50)
    assert g.low_sample is False and g.refused is False

    g = esb.apply_guards(29)
    assert g.low_sample is True and g.refused is False

    g = esb.apply_guards(9)
    assert g.low_sample is True and g.refused is True

    g = esb.apply_guards(10)
    assert g.refused is False

    print("PASS test_apply_guards")


def test_stability_split():
    """Stability split: CI overlap test."""
    # Compatible halves
    s = esb.stability_split(50, 30, 50, 28)
    assert s.agree is True

    # Incompatible halves
    s = esb.stability_split(50, 5, 50, 45)
    assert s.agree is False

    # Empty half -> null agreement
    s = esb.stability_split(0, 0, 50, 25)
    assert s.agree is None

    print("PASS test_stability_split")


def test_get_edge_stats_shape_empty_ledger():
    """get_edge_stats() returns valid structure even with empty/no trades."""
    # This test runs against the actual signals.db which may have data
    # The function should never crash and always return the expected shape
    result = esb.get_edge_stats()
    assert isinstance(result, dict)
    assert "channels" in result
    assert "engines" in result
    assert "methodology" in result
    assert isinstance(result["channels"], list)
    assert isinstance(result["engines"], list)
    assert result["methodology"]["wilson_z"] == esb.Z_95
    assert result["methodology"]["confidence"] == 0.95
    assert result["methodology"]["warn_floor"] == 30
    assert result["methodology"]["refuse_floor"] == 10

    # Each channel has required fields
    for ch in result["channels"]:
        assert "channel_id" in ch
        assert "name" in ch
        assert "n" in ch
        assert "wins" in ch
        assert "losses" in ch
        assert "win_rate" in ch
        assert "expectancy_r" in ch
        assert "guards" in ch
        assert "stability" in ch
        # win_rate structure
        wr = ch["win_rate"]
        assert "estimate" in wr
        assert "lo" in wr
        assert "hi" in wr
        # guards structure
        g = ch["guards"]
        assert "low_sample" in g
        assert "refused" in g
        assert "warn_floor" in g
        assert "refuse_floor" in g
        # stability structure
        st = ch["stability"]
        assert "first_half" in st
        assert "second_half" in st
        assert "agree" in st

    # Each engine has required fields
    for eng in result["engines"]:
        assert "engine" in eng
        assert "magic" in eng
        assert "n" in eng
        assert "wins" in eng
        assert "losses" in eng
        assert "win_rate" in eng
        assert "expectancy_r" in eng
        assert "guards" in eng
        assert "stability" in eng

    print("PASS test_get_edge_stats_shape_empty_ledger")


def test_wilson_symmetry():
    """Wilson interval is symmetric: k=n mirrors k=0."""
    for n in [5, 10, 20, 100]:
        zero = esb.wilson(0, n)
        all_ = esb.wilson(n, n)
        assert zero is not None and all_ is not None
        assert abs(all_.hi - 1.0) < 1e-10
        assert abs(all_.lo - (1 - zero.hi)) < 1e-10
        assert abs(all_.estimate - 1.0) < 1e-10
        assert abs(zero.estimate - 0.0) < 1e-10

    print("PASS test_wilson_symmetry")


def test_channel_stats_structure():
    """ChannelStats dataclass serializes correctly."""
    ch = esb.ChannelStats(
        channel_id="test-channel",
        name="Test Channel",
        n=10,
        wins=6,
        losses=4,
        win_rate=esb.WilsonCI(0.6, 0.3, 0.85),
        expectancy_r=0.25,
        guards=esb.GuardResult(False, False, 30, 10),
        stability=esb.StabilitySplit(
            first_half=esb.HalfStats(5, 3, 0.6, [0.2, 0.9]),
            second_half=esb.HalfStats(5, 3, 0.6, [0.2, 0.9]),
            agree=True
        )
    )
    d = ch.to_dict()
    assert d["channel_id"] == "test-channel"
    assert d["win_rate"]["estimate"] == 0.6
    assert d["guards"]["warn_floor"] == 30
    assert d["stability"]["agree"] is True

    print("PASS test_channel_stats_structure")


def test_engine_stats_structure():
    """EngineStats dataclass serializes correctly."""
    eng = esb.EngineStats(
        engine="algo",
        magic=20261015,
        n=20,
        wins=12,
        losses=8,
        win_rate=esb.WilsonCI(0.6, 0.35, 0.8),
        expectancy_r=0.15,
        guards=esb.GuardResult(True, False, 30, 10),
        stability=esb.StabilitySplit(
            first_half=esb.HalfStats(10, 5, 0.5, [0.2, 0.8]),
            second_half=esb.HalfStats(10, 7, 0.7, [0.4, 0.9]),
            agree=True
        )
    )
    d = eng.to_dict()
    assert d["engine"] == "algo"
    assert d["magic"] == 20261015
    assert d["win_rate"]["lo"] == 0.35

    print("PASS test_engine_stats_structure")


def run_all_tests():
    """Run all tests."""
    test_wilson_known_values()
    test_apply_guards()
    test_stability_split()
    test_get_edge_stats_shape_empty_ledger()
    test_wilson_symmetry()
    test_channel_stats_structure()
    test_engine_stats_structure()
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    run_all_tests()