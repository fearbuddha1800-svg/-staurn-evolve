---
slug: strategy2_backtest
type: note
graph: gitnexus
---

"""Strategy 2 backtester: LONDON-OPEN BREAKOUT on H1 (XAUUSD + EURUSD).

Complements the RSI-pullback engine (strategy.py/backtest.py) with an intraday
range-breakout strategy. Harness conventions are IDENTICAL to backtest.py:
  - one position per symbol; signals on a closed bar fill at the NEXT bar open
  - SL is checked FIRST within a bar; BE/trail updates only move the stop for
    FUTURE bars -> a bar touching both SL and a BE/trail arm level counts as
    the LOSS (conservative same-bar rule); no entry on a bar where a position
    exited; no entry while a position is open
  - 0.07R round-trip cost haircut per trade (R = initial SL distance)
  - exits mirror manage.py as simulated in backtest.py: SL->BE (+0.01*ATR
    buffer) at +1R; from +1.5R trail 0.5R behind the bar extreme, tighten-only

Strategy rules (per UTC day):
  - range = H1 bars opening 00:00..06:59 UTC (day valid only if all 7 present)
  - from 07:00 UTC: first H1 close beyond range_high+buf*ATR14 (long) or below
    range_low-buf*ATR14 (short) is the day's one signal
  - fill at next H1 open (must be the contiguous next hour - no weekend fills)
  - SL = opposite range edge, distance capped at cap*ATR14
  - no fixed TP; exit via SL / BE / trail only
  - optional skip_hours: signals whose decision hour (= close hour) is in the
    set are ignored, mirroring the live algo's skip_hours_utc gate

Bar times in the cached CSVs are MT5 SERVER time. The server follows EET/EEST:
UTC+2 in winter, UTC+3 during EU DST (verified: every week opens Mon 00:00
server time = Sun 22:00/21:00 UTC). Conversion to UTC uses the EU DST calendar
(last Sunday of March / last Sunday of October); all bars are labeled Mon-Sat
server-side and DST transitions fall on barless Sundays, so per-bar-date offset
evaluation is exact.

Run (read-only, no MT5, no orders, no process starts):
  C:/Users/voidk/miniconda3/python.exe strategy2_backtest.py --round 1
  C:/Users/voidk/miniconda3/python.exe strategy2_backtest.py --round 2
  C:/Users/voidk/miniconda3/python.exe strategy2_backtest.py --round 1 --select r1-spec
Writes/updates strategy2_results.json next to this file.
"""
import argparse
import csv
import json
import os
from datetime import date, datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
SYMBOLS = ["XAUUSD", "EURUSD"]
COST_R = 0.07
ATR_P = 14

DEFAULTS = {
    "buffer": 0.10,        # breakout buffer, in ATR14, beyond the range edge
    "cap": 1.50,           # max SL distance in ATR14 (SL = opposite range edge)
    "be_at_r": 1.00,       # SL -> BE when favorable excursion reaches this (R)
    "be_buffer_atr": 0.01, # BE stop offset beyond entry (backtest.py convention)
    "trail_from_r": 1.50,   # start trailing when favorable excursion reaches this (R)
    "trail_dist_r": 0.50,  # trail distance behind bar extreme (R)
    "sig_start_hour": 7,   # first UTC hour (bar open) eligible to signal
    "sig_end_hour": 24,    # signal bars must open BEFORE this UTC hour (24 = no cutoff)
    "range_hours": 7,      # bars opening 00:00..range_hours-1 UTC form the range
    "min_range_atr": 0.0,  # skip the day if range width < this * ATR14 (0 = off)
    "skip_hours": (),      # decision (= close) hours skipped, mirrors skip_hours_utc
}

# Round 1 = spec exactly as given, plus the spec's conditional skip_hours toggle
# (result: skip_hours does NOT improve PF -> kept OFF from round 2 on).
# Round 2 = robustness grid informed by round-1 diagnostics: post-London signals
# (bar open >= 15:00 UTC) are collectively negative on BOTH symbols, so grid
# over a session cutoff (sig_end_hour) x buffer x SL cap, skip OFF.
# Round 3 = refinement around the best plateau (added after round 2 results).
ROUNDS = {
    1: [
        {"name": "r1-spec", "buffer": 0.10, "cap": 1.50, "skip_hours": ()},
        {"name": "r1-spec-skip2223", "buffer": 0.10, "cap": 1.50, "skip_hours": (22, 23)},
    ],
    2: [
        {"name": "r2-cut%d-buf%03d-cap%03d" % (cut, int(b * 100), int(c * 100)),
         "buffer": b, "cap": c, "skip_hours": (), "sig_end_hour": cut}
        for cut in (15, 16) for b in (0.10, 0.15, 0.20) for c in (1.00, 1.50, 2.00)
    ],
    3: [
        # dead-day filter (range-width floor) x buffer, at the cap-1.5 plateau
        {"name": "r3-mr%03d-buf%03d" % (int(mr * 100), int(b * 100)), "buffer": b,
         "cap": 1.50, "skip_hours": (), "sig_end_hour": 15, "min_range_atr": mr}
        for b, mr in ((0.10, 0.75), (0.15, 0.75), (0.10, 1.00), (0.15, 1.00))
    ] + [
        # buffer interpolation + cap plateau check (no floor)
        {"name": "r3-buf012-cap150", "buffer": 0.12, "cap": 1.50, "skip_hours": (), "sig_end_hour": 15},
        {"name": "r3-buf010-cap125", "buffer": 0.10, "cap": 1.25, "skip_hours": (), "sig_end_hour": 15},
        {"name": "r3-buf010-cap175", "buffer": 0.10, "cap": 1.75, "skip_hours": (), "sig_end_hour": 15},
    ] + [
        # spec-ambiguity branch: 8-bar range 00:00-07:59, signals from 08:00
        {"name": "r3-range8-buf%03d" % int(b * 100), "buffer": b, "cap": 1.50,
         "skip_hours": (), "sig_end_hour": 15, "range_hours": 8, "sig_start_hour": 8}
        for b in (0.10, 0.15)
    ],
}


# ---- EU DST calendar (server EET/EEST) ---------------------------------------
def last_sunday(y, m):
    nxt = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    last = nxt - timedelta(days=1)
    return last - timedelta(days=(last.weekday() + 1) % 7)  # Mon=0..Sun=6


def server_offset_hours(d):
    """EEST (UTC+3) between the last Sundays of March/October, else EET (UTC+2).
    Transitions happen on barless Sundays; every bar date maps exactly."""
    return 3 if last_sunday(d.year, 3) <= d < last_sunday(d.year, 10) else 2


# ---- data --------------------------------------------------------------------
def load_bars(sym):
    """Read the cached H1 CSV; convert server-time epochs to UTC."""
    path = os.path.join(BASE, "strategy2_data_%s.csv" % sym)
    bars = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            sdt = datetime.fromtimestamp(int(row["time"]), tz=timezone.utc)
            off = server_offset_hours(sdt.date())
            bars.append({"srv": sdt, "utc": sdt - timedelta(hours=off),
                         "o": float(row["open"]), "h": float(row["high"]),
                         "l": float(row["low"]), "c": float(row["close"])})
    for a, b in zip(bars, bars[1:]):
        if not b["srv"] > a["srv"]:
            raise SystemExit("%s: bar times not strictly increasing" % sym)
    return bars


def atr_series(bars):
    """Wilder ATR(14), identical math to strategy.Indicators (no MT5 import).
    atrs[i] = ATR through bar i's close (None until 14 TRs have accumulated)."""
    atrs = [None] * len(bars)
    prev_close = None
    atr = None
    trs = []
    for i, b in enumerate(bars):
        pc = prev_close
        if pc is not None:
            tr = max(b["h"] - b["l"], abs(b["h"] - pc), abs(b["l"] - pc))
            if atr is None:
                trs.append(tr)
                if len(trs) == ATR_P:
                    atr = sum(trs) / ATR_P
            else:
                atr = (atr * (ATR_P - 1) + tr) / ATR_P
        atrs[i] = atr
        prev_close = b["c"]
    return atrs


def daily_ranges(bars, range_hours=DEFAULTS["range_hours"]):
    """Per UTC date: high/low over bars opening 00:00..range_hours-1.
    Only days with the full set of range bars (and a non-zero range) are valid."""
    rng = {}
    for b in bars:
        h = b["utc"].hour
        if h < range_hours:
            r = rng.setdefault(b["utc"].date(), {"hi": -1e300, "lo": 1e300, "n": 0})
            if b["h"] > r["hi"]:
                r["hi"] = b["h"]
            if b["l"] < r["lo"]:
                r["lo"] = b["l"]
            r["n"] += 1
    return {d: r for d, r in rng.items()
            if r["n"] == range_hours and r["hi"] > r["lo"]}


def load_pack(sym):
    bars = load_bars(sym)
    return {"bars": bars, "atrs": atr_series(bars), "ranges": daily_ranges(bars)}


def data_report(data):
    """Sanity checks: week-open server-time finding, hour coverage, range days."""
    for sym in SYMBOLS:
        p = data[sym]
        bars = p["bars"]
        weeks = {}
        for b in bars:
            y, w, _ = b["srv"].isocalendar()
            k = (y, w)
            if k not in weeks or b["srv"] < weeks[k]["srv"]:
                weeks[k] = b
        ok_weeks = sum(1 for b in weeks.values()
                       if b["utc"].weekday() == 6 and b["utc"].hour in (21, 22))
        hours = {}
        for b in bars:
            hours[b["utc"].hour] = hours.get(b["utc"].hour, 0) + 1
        rare = sorted(h for h in range(24) if hours.get(h, 0) < 50)
        tot_days = len({b["utc"].date() for b in bars})
        print("%s: %d bars  %s -> %s UTC | week-opens Sun 21/22 UTC: %d/%d | "
              "valid range days %d/%d | rare utc hours %s" % (
                  sym, len(bars), bars[0]["utc"].strftime("%Y-%m-%d %H:%M"),
                  bars[-1]["utc"].strftime("%Y-%m-%d %H:%M"), ok_weeks, len(weeks),
                  len(p["ranges"]), tot_days, rare))


# ---- simulation ---------------------------------------------------------------
def simulate(bars, atrs, ranges, prm):
    """Bar-by-bar sim, backtest.py ordering. Returns (trades, diag)."""
    p = dict(DEFAULTS)
    p.update(prm)
    skip = set(p["skip_hours"])
    sig_start = p["sig_start_hour"]
    buf, cap = p["buffer"], p["cap"]
    trades = []
    pos = None
    consumed = set()
    diag = {"signals": 0, "entries": 0, "invalid_r": 0, "noncontig_fill": 0,
            "exit_sl": 0, "exit_be": 0, "exit_trail": 0, "open_at_end": 0}

    def _sig(b, atr):
        """+1/-1 if this bar's close is the day's first close beyond a level
        and the decision hour is not skipped; 0 otherwise."""
        rng = ranges.get(b["utc"].date())
        if not rng or atr is None or b["utc"].hour < sig_start:
            return 0
        if b["utc"].hour >= p["sig_end_hour"]:
            return 0
        if p["min_range_atr"] and rng["hi"] - rng["lo"] < p["min_range_atr"] * atr:
            return 0  # dead-day filter: range too narrow for a quality breakout
        if skip and (b["utc"].hour + 1) % 24 in skip:
            return 0
        if b["c"] > rng["hi"] + buf * atr:
            return 1
        if b["c"] < rng["lo"] - buf * atr:
            return -1
        return 0

    for i, b in enumerate(bars):
        atr = atrs[i]
        if pos is not None:
            d, fill, sl, R = pos["dir"], pos["fill"], pos["sl"], pos["R"]
            if d == 1:
                fav = b["h"] - fill
                hit = b["l"] <= sl
            else:
                fav = fill - b["l"]
                hit = b["h"] >= sl
            if hit:
                # conservative same-bar rule: current SL decides, manage levels
                # armed this bar never rescue it -> count the loss
                r_exit = (sl - fill) * d / R
                kind = "SL" if r_exit < -0.5 else ("BE" if r_exit < 0.5 else "TRAIL")
                diag["exit_" + kind.lower()] += 1
                trades.append({"net": max(r_exit, -1.0) - COST_R, "dir": d,
                               "year": b["utc"].year, "kind": kind,
                               "entry": pos["t0"].isoformat(),
                               "exit": b["utc"].isoformat()})
                pos = None
                continue  # no entry evaluation on the exit bar (backtest.py)
            r_fav = fav / R
            if not pos["be"] and r_fav >= p["be_at_r"]:
                pos["be"] = True
                pos["sl"] = fill + d * p["be_buffer_atr"] * pos["atr"]
            if r_fav >= p["trail_from_r"]:
                cand = (fav - p["trail_dist_r"] * R) * d + fill
                if (d == 1 and cand > pos["sl"]) or (d == -1 and cand < pos["sl"]):
                    pos["sl"] = cand
            # while a position is open the day's breakout is consumed unseen
            d0 = b["utc"].date()
            if d0 not in consumed and _sig(b, atr):
                consumed.add(d0)
            continue

        # flat at bar start: evaluate this day's first close beyond
        s = _sig(b, atr)
        d0 = b["utc"].date()
        if s and d0 not in consumed:
            consumed.add(d0)
            diag["signals"] += 1
            if i + 1 >= len(bars) or (bars[i + 1]["utc"] - b["utc"]) != timedelta(hours=1):
                diag["noncontig_fill"] += 1  # weekend/data-end: no realistic fill
            else:
                fill = bars[i + 1]["o"]
                rng = ranges[d0]
                if s == 1:
                    sl = max(rng["lo"], fill - cap * atr)
                    R = fill - sl
                else:
                    sl = min(rng["hi"], fill + cap * atr)
                    R = sl - fill
                if R <= 0:
                    diag["invalid_r"] += 1  # gapped through the range: invalidated
                else:
                    pos = {"dir": s, "fill": fill, "sl": sl, "R": R, "atr": atr,
                           "be": False, "t0": b["utc"]}
                    diag["entries"] += 1
    if pos is not None:
        diag["open_at_end"] += 1
    return trades, diag


# ---- stats (mirrors backtest.py stats) ----------------------------------------
def stats(trades):
    if not trades:
        return None
    nets = [t["net"] for t in trades]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x <= 0]
    eq = peak = dd = 0.0
    for x in nets:
        eq += x
        if eq > peak:
            peak = eq
        if peak - eq > dd:
            dd = peak - eq
    gw, gl = sum(wins), -sum(losses)
    out = {"n": len(nets),
           "wr": round(100.0 * len(wins) / len(nets), 1),
           "net_r": round(eq, 1),
           "pf": round(gw / gl, 3) if gl > 0 else None,
           "max_dd_r": round(dd, 1),
           "avg_r": round(eq / len(nets), 3),
           "exits": {k: sum(1 for t in trades if t["kind"] == k)
                     for k in ("SL", "BE", "TRAIL")},
           "by_dir": {}, "by_year": {}}
    for dirn, key in ((1, "long"), (-1, "short")):
        sel = [t for t in trades if t["dir"] == dirn]
        w = sum(1 for t in sel if t["net"] > 0)
        out["by_dir"][key] = {"n": len(sel),
                              "wr": round(100.0 * w / len(sel), 1) if sel else None,
                              "net_r": round(sum(t["net"] for t in sel), 1)}
    yrs = {}
    for t in trades:
        y = yrs.setdefault(t["year"], [0, 0.0])
        y[0] += 1
        y[1] += t["net"]
    out["by_year"] = {str(k): {"n": v[0], "net_r": round(v[1], 1)}
                      for k, v in sorted(yrs.items())}
    return out


def acceptance(per_sym):
    acc = {}
    for sym, st in per_sym.items():
        acc[sym] = {"pf_ok": st["pf"] is not None and st["pf"] >= 1.10,
                    "trades_ok": st["n"] >= 100,
                    "dd_ok": st["max_dd_r"] <= 30.0}
    acc["PASS"] = all(all(v.values()) for v in
                      [acc[s] for s in per_sym]) if per_sym else False
    return acc


# ---- runner -------------------------------------------------------------------
def run_variant(data, prm):
    out = {"name": prm["name"],
           "params": {k: (list(prm[k]) if isinstance(prm.get(k, DEFAULTS[k]), tuple)
                          else prm.get(k, DEFAULTS[k])) for k in DEFAULTS}}
    sts = {}
    for sym in SYMBOLS:
        p = data[sym]
        trades, diag = simulate(p["bars"], p["atrs"], p["ranges"], prm)
        st = stats(trades)
        if st is None:
            out[sym] = None
            continue
        out[sym] = {"stats": st, "diag": diag}
        sts[sym] = st
    out["acceptance"] = acceptance(sts)
    return out


def print_variant(r):
    print("-- %s  params=%s" % (r["name"], json.dumps(r["params"])))
    for sym in SYMBOLS:
        if not r[sym]:
            print("   %-8s no trades" % sym)
            continue
        st, dg = r[sym]["stats"], r[sym]["diag"]
        print("   %-8s trades %4d  win%% %5.1f  net %7.1fR  PF %6s  maxDD %5.1fR  "
              "avg %6.3fR  exits SL/BE/TR %d/%d/%d  skippedfill %d invalid %d" % (
                  sym, st["n"], st["wr"], st["net_r"], st["pf"], st["max_dd_r"],
                  st["avg_r"], st["exits"]["SL"], st["exits"]["BE"], st["exits"]["TRAIL"],
                  dg["noncontig_fill"], dg["invalid_r"]))
    print("   acceptance: %s %s" % ("PASS" if r["acceptance"]["PASS"] else "FAIL",
                                    json.dumps({k: v for k, v in r["acceptance"].items() if k != "PASS"})))


def save_results(doc_update):
    path = os.path.join(BASE, "strategy2_results.json")
    doc = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                doc = json.load(f)
        except Exception:  # noqa: BLE001
            doc = {}
    if "rounds" in doc_update:
        # merge per-round lists instead of replacing the whole history
        rounds = doc.setdefault("rounds", {})
        if not isinstance(rounds, dict):
            rounds = doc["rounds"] = {}
        rounds.update(doc_update["rounds"])
        doc_update = {k: v for k, v in doc_update.items() if k != "rounds"}
    doc.update(doc_update)
    doc["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
    return path


def main():
    ap = argparse.ArgumentParser(description="strategy2 London-open breakout backtest")
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--select", default=None,
                    help="variant name to select as final (reruns it, records verdict)")
    a = ap.parse_args()
    if a.round not in ROUNDS:
        raise SystemExit("round %d not defined" % a.round)
    data = {s: load_pack(s) for s in SYMBOLS}
    data_report(data)
    print()
    if a.select:
        prm = next((v for v in ROUNDS[a.round] if v["name"] == a.select), None)
        if prm is None:
            raise SystemExit("variant %r not in round %d" % (a.select, a.round))
        r = run_variant(data, prm)
        print_variant(r)
        sel = {"round": a.round, "name": r["name"], "params": r["params"],
               "per_symbol": {s: r[s] for s in SYMBOLS},
               "acceptance": r["acceptance"]}
        path = save_results({"selected": sel})
        print("selected written:", path)
        return
    res = [run_variant(data, prm) for prm in ROUNDS[a.round]]
    for r in res:
        print_variant(r)
    path = save_results({"rounds": {str(a.round): res}})
    print("round %d results written: %s" % (a.round, path))


if __name__ == "__main__":
    main()

