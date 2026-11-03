"""Backtester for the algo strategy: pulls real H1 history from the running MT5
terminal, bar-by-bar simulation of the SAME Indicators/decide used live.

Conservative assumptions: fill at next bar open, SL checked before TP when both
hit in one bar, 0.07R round-trip cost haircut per trade, one position/symbol.

Run: python backtest.py   (read-only - places no orders)
"""
from broker_lifecycle import initialize_existing, broker_status
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import MetaTrader5 as mt5  # noqa: E402
from strategy import Indicators, decide  # noqa: E402

SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD"]
VARIANTS = [
    {"rsi": (35, 65), "sl": 2.0, "tp": 3.0, "strength": 0.5, "manage": True, "keep_tp": True},
    {"rsi": (35, 65), "sl": 2.0, "tp": 6.0, "strength": 0.5, "manage": True, "keep_tp": False},
    {"rsi": (35, 65), "sl": 2.0, "tp": 6.0, "strength": 1.0, "manage": True, "keep_tp": False},
    {"rsi": (30, 70), "sl": 2.0, "tp": 6.0, "strength": 0.5, "manage": True, "keep_tp": False},
]
COST_R = 0.07


def simulate(bars, rsi_buy, rsi_sell, slm, tpm, strength=0.0,
             manage=False, keep_tp=True):
    """manage=True simulates the live manager: SL->BE at +1R, trail 0.5R from
    +1.5R. keep_tp=False removes the fixed TP (pure trailing exit)."""
    ind = Indicators()
    trades = []
    pos = None
    for i, b in enumerate(bars):
        ind.update(b["high"], b["low"], b["close"])
        if pos is not None:
            d, sl, fill = pos["dir"], pos["sl"], pos["fill"]
            if d == 1:
                fav, adv = b["high"] - fill, fill - b["low"]
                hit_sl = b["low"] <= sl
                hit_tp = keep_tp and b["high"] >= pos["tp"]
            else:
                fav, adv = fill - b["low"], b["high"] - fill
                hit_sl = b["high"] >= sl
                hit_tp = keep_tp and b["low"] <= pos["tp"]
            if hit_sl:
                r_exit = (sl - fill) / (slm * pos["atr"]) * d
                trades.append(max(r_exit, -1.0) - COST_R)
                pos = None
                continue
            if hit_tp:
                trades.append(tpm / slm - COST_R)
                pos = None
                continue
            if manage and pos["atr"]:
                r_fav = fav / (slm * pos["atr"])
                if not pos["be"] and r_fav >= 1.0 and adv < slm * pos["atr"]:
                    pos["be"] = True
                    pos["sl"] = fill + d * 0.01 * pos["atr"]
                if r_fav >= 1.5:
                    cand = (fav - 0.5 * slm * pos["atr"]) * d + fill
                    if d == 1 and cand > pos["sl"]:
                        pos["sl"] = cand
                    if d == -1 and cand < pos["sl"]:
                        pos["sl"] = cand
            continue
        action, atr = decide(ind, rsi_buy, rsi_sell, strength)
        if action and i + 1 < len(bars):
            fill = bars[i + 1]["open"]
            if action == "buy":
                sl, tp = fill - slm * atr, fill + tpm * atr
            else:
                sl, tp = fill + slm * atr, fill - tpm * atr
            pos = {"dir": 1 if action == "buy" else -1, "sl": sl, "tp": tp,
                   "rr": tpm / slm, "fill": fill, "atr": atr, "be": False}
    return trades


def stats(trades):
    if not trades:
        return None
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    eq, peak, dd = 0.0, 0.0, 0.0
    for t in trades:
        eq += t
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    gross_w = sum(wins)
    gross_l = abs(sum(losses))
    return {"n": len(trades), "wr": 100.0 * len(wins) / len(trades),
            "r": round(eq, 1), "pf": round(gross_w / gross_l, 2) if gross_l else float("inf"),
            "dd": round(dd, 1), "avg": round(eq / len(trades), 2)}


def main():
    if not initialize_existing(mt5):
        print("MT5 connection unavailable:", broker_status())
        sys.exit(1)
    data = {}
    for s in SYMBOLS:
        r = mt5.copy_rates_from_pos(s, mt5.TIMEFRAME_H1, 0, 20000)
        if r is None or len(r) < 300:
            print(f"{s}: no data ({mt5.last_error()})")
        else:
            data[s] = r[:-1]
            import datetime as _dt

            a = _dt.datetime.utcfromtimestamp(r[0]["time"]).strftime("%Y-%m-%d")
            b_ = _dt.datetime.utcfromtimestamp(r[-1]["time"]).strftime("%Y-%m-%d")
            print(f"{s}: {len(r)-1} closed H1 bars  {a} -> {b_}")
    if not data:
        mt5.shutdown()
        sys.exit(1)
    print()
    for v in VARIANTS:
        allr = []
        tp_txt = "no-TP trail" if not v["keep_tp"] else "TP " + str(v["tp"]) + "xATR"
        print(f"== rsi {v['rsi'][0]}/{v['rsi'][1]} SL {v['sl']}xATR {tp_txt} "
              f"strength {v['strength']} managed={v['manage']} ==")
        for s, bars in data.items():
            st = stats(simulate(bars, v["rsi"][0], v["rsi"][1], v["sl"], v["tp"],
                                v["strength"], v["manage"], v["keep_tp"]))
            if st:
                allr.append(st["r"])
                print(f"   {s:<8} trades {st['n']:>4}  win% {st['wr']:>5.1f}  "
                      f"net {st['r']:>7}R  PF {st['pf']:>5}  maxDD {st['dd']:>5}R  avg {st['avg']}R/trade")
        if allr:
            print(f"   TOTAL net {round(sum(allr),1)}R across {len(allr)} symbols\n")
    mt5.shutdown()


if __name__ == "__main__":
    main()
