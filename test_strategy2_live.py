"""Acceptance smoke test for strategy2_live.py (the LIVE London-open breakout,
XAUUSD only). Pure-function coverage only: no MT5 attach, no orders, nothing
outside this directory is modified. Exit 0 = all pass. Run from signal-relay/:

  C:/Users/voidk/miniconda3/python.exe test_strategy2_live.py

Covers the task spec:
  1. DST conversion correctness for a WINTER and a SUMMER date (offsets, both
     2026 transition Sundays, and full server-epoch -> UTC via bars_from_rates)
  2. daily range computation (7 bars 00:00..06:59 UTC, exact hi/lo, date isolation)
  3. signal detection on synthetic bars (BUY winter / SELL summer full pipeline,
     inside-buffer, strict boundary, out-of-window, early bar)
  4. no entry when the day's range is incomplete (6 of 7 bars)
Extras: flat-range invalidity, Wilder ATR14 math, SL edge-vs-cap geometry,
config.json strategy2 block matches the spec.
"""
import json
import os
import sys
from datetime import date, datetime, timezone

import strategy2_live as s2

fails = 0


def _case(name, fn):
    global fails
    try:
        fn()
        print(f"PASS {name}")
    except AssertionError as e:
        fails += 1
        print(f"FAIL {name}: {e}")
    except Exception as e:  # noqa: BLE001
        fails += 1
        print(f"FAIL {name}: {type(e).__name__}: {e}")


def _srv(y, m, d, h):
    """Server-time epoch for y-m-d h:00 (MT5 bars carry server-labeled epochs)."""
    return int(datetime(y, m, d, h, 0, tzinfo=timezone.utc).timestamp())


def _row(t, o, h, l, c):
    return {"time": t, "open": o, "high": h, "low": l, "close": c}


def _warmup(y, m, d, h0, n=16):
    """n warm-up bars with constant TR=2.0 (h=101,l=99,c=100,pc=100)."""
    return [_row(_srv(y, m, d, h0 + i), 100.0, 101.0, 99.0, 100.0) for i in range(n)]


def _range_rows(y, m, d, srv_h0, hi=101.5, lo=99.5):
    """7 range bars (UTC 00:00..06:59 after server->UTC conversion)."""
    return [_row(_srv(y, m, d, srv_h0 + i), 100.0, hi, lo, 100.0) for i in range(7)]


# ---- 1. EU DST calendar -------------------------------------------------------
def t_dst_offsets():
    # winter (EET, UTC+2) and summer (EEST, UTC+3)
    assert s2.server_offset_hours(date(2026, 1, 15)) == 2, "winter must be UTC+2"
    assert s2.server_offset_hours(date(2026, 7, 15)) == 3, "summer must be UTC+3"
    # transitions: last Sunday of March 2026 = Mar 29, of October 2026 = Oct 25
    assert s2.last_sunday(2026, 3) == date(2026, 3, 29)
    assert s2.last_sunday(2026, 10) == date(2026, 10, 25)
    assert s2.server_offset_hours(date(2026, 3, 28)) == 2, "day before spring switch"
    assert s2.server_offset_hours(date(2026, 3, 29)) == 3, "spring switch day"
    assert s2.server_offset_hours(date(2026, 10, 24)) == 3, "day before autumn switch"
    assert s2.server_offset_hours(date(2026, 10, 25)) == 2, "autumn switch day"


def t_dst_epoch_conversion():
    # server "10:00" is 07:00 UTC in summer (offset 3) and 08:00 UTC in winter (offset 2)
    bars = s2.bars_from_rates([_row(_srv(2026, 7, 15, 10), 1, 1, 1, 1)])
    assert bars[0]["utc"] == datetime(2026, 7, 15, 7, 0, tzinfo=timezone.utc), bars[0]["utc"]
    bars = s2.bars_from_rates([_row(_srv(2026, 1, 15, 10), 1, 1, 1, 1)])
    assert bars[0]["utc"] == datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc), bars[0]["utc"]
    # late-Sunday server bar keeps its own UTC date (week open Sun 21/22 UTC)
    bars = s2.bars_from_rates([_row(_srv(2026, 7, 20, 0), 1, 1, 1, 1)])  # Sun 00:00 srv
    assert bars[0]["utc"] == datetime(2026, 7, 19, 21, 0, tzinfo=timezone.utc), bars[0]["utc"]


# ---- 2. range computation -----------------------------------------------------
def _winter_bars(signal_close=101.9, drop_range_bar=None, flat=False):
    """16 warm-up bars (Jan 14) + 7 range bars + 1 signal bar (Jan 15, UTC 07:00).
    Winter offset 2: range bars open server 02:00..08:00 = UTC 00:00..06:59,
    signal bar opens server 09:00 = UTC 07:00."""
    rows = _warmup(2026, 1, 14, 6)
    rr = _range_rows(2026, 1, 15, 2, hi=100.0 if flat else 101.5, lo=100.0 if flat else 99.5)
    if drop_range_bar is not None:
        rr.pop(drop_range_bar)
    rows += rr
    rows.append(_row(_srv(2026, 1, 15, 9), 100.0, 102.5, 100.0, signal_close))
    return s2.bars_from_rates(rows)


def t_range_valid():
    bars = _winter_bars()
    rng = s2.range_for_day(bars, date(2026, 1, 15))
    assert rng == {"hi": 101.5, "lo": 99.5, "n": 7}, rng
    # the warm-up day (Jan 14) has only 3 bars in UTC hours < 7 -> invalid,
    # proving bars from other UTC dates never pollute this day's range
    assert s2.range_for_day(bars, date(2026, 1, 14)) is None
    # the signal bar itself (UTC 07:00) is not part of the range
    assert rng["hi"] < bars[-1]["c"]


def t_range_incomplete_no_entry():
    # 6 of 7 range bars (UTC 05:00 bar missing) -> day invalid -> a closing
    # price far beyond the range must NOT trigger an entry
    bars = _winter_bars(drop_range_bar=3)
    assert s2.range_for_day(bars, date(2026, 1, 15)) is None
    d, rng, atr, bar = s2.decide_newest_closed(bars)
    assert d == 0 and rng is None, f"incomplete range must not trade: {(d, rng)}"


def t_range_flat_invalid():
    bars = _winter_bars(flat=True)
    assert s2.range_for_day(bars, date(2026, 1, 15)) is None, "hi==lo must invalidate the day"


# ---- 3. signal detection on synthetic bars ------------------------------------
def t_signal_buy_winter():
    # close 101.9 > hi + 0.10*ATR = 101.5 + ~0.2036 -> BUY on the full pipeline
    bars = _winter_bars(signal_close=101.9)
    d, rng, atr, bar = s2.decide_newest_closed(bars)
    assert d == 1, f"expected BUY, got {d}"
    assert rng == {"hi": 101.5, "lo": 99.5, "n": 7}
    assert bar["utc"] == datetime(2026, 1, 15, 7, 0, tzinfo=timezone.utc), bar["utc"]
    assert abs(atr - 2.0357142857142856) < 1e-9, atr  # (2.0*13+2.5)/14


def t_signal_sell_summer():
    # summer offset 3: range bars server 03:00..09:00 = UTC 00:00..06:59,
    # signal bar server 10:00 = UTC 07:00; close 98.9 < lo - 0.10*ATR -> SELL
    rows = _warmup(2026, 7, 14, 6)
    rows += _range_rows(2026, 7, 15, 3)
    rows.append(_row(_srv(2026, 7, 15, 10), 100.0, 100.2, 97.6, 98.9))
    bars = s2.bars_from_rates(rows)
    d, rng, atr, bar = s2.decide_newest_closed(bars)
    assert d == -1, f"expected SELL, got {d}"
    assert rng == {"hi": 101.5, "lo": 99.5, "n": 7}
    assert bar["utc"] == datetime(2026, 7, 15, 7, 0, tzinfo=timezone.utc), bar["utc"]


def t_signal_inside_buffer_and_boundary():
    # close 101.6 < 101.5 + 0.1*ATR -> no signal
    d, _, _, _ = s2.decide_newest_closed(_winter_bars(signal_close=101.6))
    assert d == 0, f"inside the buffer must not signal, got {d}"
    # strict '>' at the exact buffered edge (fixed atr=2.0 -> edge 101.7 / 99.3)
    rng = {"hi": 101.5, "lo": 99.5}
    mk = lambda h, c: {"utc": datetime(2026, 1, 15, h, 0, tzinfo=timezone.utc), "c": c}
    assert s2.signal_on_bar(mk(7, 101.7), rng, 2.0) == 0, "close == edge must NOT signal"
    assert s2.signal_on_bar(mk(7, 101.71), rng, 2.0) == 1
    assert s2.signal_on_bar(mk(7, 99.3), rng, 2.0) == 0, "close == low edge must NOT signal"
    assert s2.signal_on_bar(mk(7, 99.29), rng, 2.0) == -1
    # no range / no ATR -> never a signal
    assert s2.signal_on_bar(mk(7, 105.0), None, 2.0) == 0
    assert s2.signal_on_bar(mk(7, 105.0), rng, None) == 0


def t_signal_window():
    rng = {"hi": 101.5, "lo": 99.5}
    mk = lambda h, c: {"utc": datetime(2026, 7, 15, h, 0, tzinfo=timezone.utc), "c": c}
    # eligible window = bars opening 07:00..14:59 UTC
    assert s2.signal_on_bar(mk(7, 105.0), rng, 2.0) == 1
    assert s2.signal_on_bar(mk(14, 105.0), rng, 2.0) == 1
    assert s2.signal_on_bar(mk(15, 105.0), rng, 2.0) == 0, "bar opening 15:00 UTC is out"
    assert s2.signal_on_bar(mk(6, 105.0), rng, 2.0) == 0, "range bar (06:00) never signals"
    # full pipeline: breakout close on a bar opening 15:00 UTC -> no entry
    rows = _warmup(2026, 7, 14, 6)
    rows += _range_rows(2026, 7, 15, 3)
    rows.append(_row(_srv(2026, 7, 15, 18), 100.0, 100.2, 97.6, 98.9))  # UTC 15:00
    d, _, _, _ = s2.decide_newest_closed(s2.bars_from_rates(rows))
    assert d == 0, f"out-of-window close must not signal, got {d}"


# ---- extras -------------------------------------------------------------------
def t_atr_math():
    bars = _winter_bars()
    atrs = s2.atr_series(bars)
    assert atrs[13] is None, "ATR14 needs 14 TRs -> undefined before index 14"
    assert atrs[14] == 2.0, atrs[14]           # seed = mean of 14 constant TRs
    assert atrs[15] == 2.0                     # Wilder keeps constant series flat
    assert abs(atrs[-1] - 2.0357142857142856) < 1e-12, atrs[-1]  # (2*13+2.5)/14


def t_sl_geometry():
    rng = {"hi": 101.5, "lo": 99.5}
    # opposite edge wins when it is CLOSER than 1.5*ATR (cap 3.0)
    assert s2.sl_for(1, 101.9, rng, 2.0) == 99.5, "buy SL must be the range low here"
    assert s2.sl_for(-1, 98.9, rng, 2.0) == 101.5, "sell SL must be the range high here"
    # cap wins when the opposite edge is farther than 1.5*ATR
    assert s2.sl_for(1, 105.0, rng, 2.0) == 102.0, "buy SL capped at entry-1.5*ATR"
    assert s2.sl_for(-1, 95.0, rng, 2.0) == 98.0, "sell SL capped at entry+1.5*ATR"


def t_config_block():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "config.json"), "r", encoding="utf-8") as f:
        cfg = json.load(f)  # whole file must still parse
    s2cfg = cfg.get("strategy2")
    assert s2cfg, "config.json must have a strategy2 block"
    assert s2cfg.get("enabled") is True
    assert s2cfg.get("symbols") == ["XAUUSD"], "XAUUSD ONLY per the verified variant"
    assert s2cfg.get("risk_pct") == 0.5
    assert s2cfg.get("max_positions") == 1
    assert cfg.get("algo", {}).get("daily_loss_cap_pct") == 2.0, "algo block untouched"


_case("DST offsets: winter UTC+2, summer UTC+3, 2026 transitions", t_dst_offsets)
_case("DST server-epoch -> UTC conversion (winter/summer/sunday)", t_dst_epoch_conversion)
_case("range: 7 bars 00:00..06:59 UTC, exact hi/lo, date isolation", t_range_valid)
_case("no entry when range incomplete (6 of 7 bars)", t_range_incomplete_no_entry)
_case("range flat day (hi==lo) invalid", t_range_flat_invalid)
_case("signal BUY on synthetic winter bars (full pipeline)", t_signal_buy_winter)
_case("signal SELL on synthetic summer bars (full pipeline)", t_signal_sell_summer)
_case("signal: inside buffer + strict boundary edges", t_signal_inside_buffer_and_boundary)
_case("signal window: 07:00..14:59 UTC only (early/late bars)", t_signal_window)
_case("ATR14: Wilder seed, warmup, recursion", t_atr_math)
_case("SL geometry: opposite edge vs 1.5*ATR cap", t_sl_geometry)
_case("config.json strategy2 block matches spec", t_config_block)

print()
print("ALL PASS" if fails == 0 else f"{fails} FAILURE(S)")
sys.exit(0 if fails == 0 else 1)
