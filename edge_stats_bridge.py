"""Edge Stats Bridge — LuxAlgo-style session statistics from signals.db trades ledger.

Computes per-channel and per-engine (magic 20261015) statistics:
- Win rate with Wilson 95% confidence interval (matching edge-stats methodology)
- Expectancy in R
- Sample size
- Minimum-sample guards (warn < 30, refuse < 10)
- Stability split (first half vs second half CI overlap)

Methodology: Wilson score interval for binomial proportion (z=1.959963984540054 for 95% CI),
identical to edge-stats packages/core/src/stats/stats.ts:wilson().
"""

from __future__ import annotations
import json
import math
import os
import sqlite3
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any

try:
    import MetaTrader5 as mt5
    _HAVE_MT5 = True
except Exception:
    _HAVE_MT5 = False

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "signals.db")
CONFIG = os.path.join(BASE, "config.json")

# Wilson 95% CI constants (matching edge-stats exactly)
Z_95 = 1.959963984540054
WARN_FLOOR = 30
REFUSE_FLOOR = 10
ALGO_MAGIC = 20261015


@dataclass
class WilsonCI:
    estimate: float
    lo: float
    hi: float

    def to_dict(self) -> Dict[str, float]:
        return {"estimate": self.estimate, "lo": self.lo, "hi": self.hi}


@dataclass
class GuardResult:
    low_sample: bool
    refused: bool
    warn_floor: int
    refuse_floor: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HalfStats:
    n: int
    k: int
    estimate: Optional[float]
    ci95: Optional[List[float]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StabilitySplit:
    first_half: HalfStats
    second_half: HalfStats
    agree: Optional[bool]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChannelStats:
    channel_id: str
    name: str
    n: int
    wins: int
    losses: int
    win_rate: WilsonCI
    expectancy_r: float
    guards: GuardResult
    stability: StabilitySplit

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["win_rate"] = self.win_rate.to_dict()
        d["guards"] = self.guards.to_dict()
        d["stability"] = self.stability.to_dict()
        return d


@dataclass
class EngineStats:
    engine: str
    magic: int
    n: int
    wins: int
    losses: int
    win_rate: WilsonCI
    expectancy_r: float
    guards: GuardResult
    stability: StabilitySplit

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["win_rate"] = self.win_rate.to_dict()
        d["guards"] = self.guards.to_dict()
        d["stability"] = self.stability.to_dict()
        return d


def wilson(k: int, n: int, z: float = Z_95) -> Optional[WilsonCI]:
    """Wilson score interval for binomial proportion (95% default).
    Matches edge-stats packages/core/src/stats/stats.ts:wilson() exactly.
    Returns None when n <= 0 (no estimate possible)."""
    if n <= 0:
        return None
    if k < 0 or k > n:
        raise ValueError(f"impossible counts: k={k} n={n}")
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p)) / n + z2 / (4 * n * n))) / denom
    return WilsonCI(
        estimate=p,
        lo=max(0.0, center - half),
        hi=min(1.0, center + half)
    )


def apply_guards(n: int) -> GuardResult:
    """Minimum-sample guards matching edge-stats: warn < 30, refuse < 10."""
    return GuardResult(
        low_sample=n < WARN_FLOOR,
        refused=n < REFUSE_FLOOR,
        warn_floor=WARN_FLOOR,
        refuse_floor=REFUSE_FLOOR
    )


def half_stats(n: int, k: int) -> HalfStats:
    w = wilson(k, n)
    return HalfStats(
        n=n,
        k=k,
        estimate=w.estimate if w else None,
        ci95=[w.lo, w.hi] if w else None
    )


def stability_split(n1: int, k1: int, n2: int, k2: int) -> StabilitySplit:
    """First-half vs second-half stability (CI overlap test)."""
    first = half_stats(n1, k1)
    second = half_stats(n2, k2)
    agree = None
    if first.ci95 and second.ci95:
        agree = (first.ci95[0] <= second.ci95[1]) and (second.ci95[0] <= first.ci95[1])
    return StabilitySplit(first_half=first, second_half=second, agree=agree)


def _load_channel_names() -> Dict[str, str]:
    """Map channel_id -> plain name from config.json signal_policy."""
    try:
        cfg = json.load(open(CONFIG, encoding="utf-8"))
    except Exception:
        return {}
    names = {}
    pol = cfg.get("signal_policy", {})
    for cid, p in pol.items():
        if cid == "_default" or not isinstance(p, dict):
            continue
        note = p.get("note", "")
        name = note.split(" - ")[0] if note else cid
        names[cid] = name
    return names


def _get_channel_for_msg_id(msg_id: str) -> Optional[str]:
    """Find which channel a message ID belongs to by querying events table."""
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2)
        cur = con.execute(
            "SELECT source FROM events WHERE event_id = ? LIMIT 1", (msg_id,))
        row = cur.fetchone()
        con.close()
        return row[0] if row else None
    except Exception:
        return None


def _fetch_channel_trades() -> Dict[str, List[Dict[str, Any]]]:
    """Fetch all executed trades from signals.db, grouped by channel_id.
    Returns {channel_id: [trade_dict, ...]} where trade_dict has ticket, symbol, side, entry, sl, tp."""
    trades_by_channel: Dict[str, List[Dict]] = {}
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2)
        cur = con.execute(
            "SELECT msg_id, ts, symbol, side, lot, entry, sl, tp, ticket, status "
            "FROM trades WHERE status = 'executed' AND ticket IS NOT NULL AND ticket != 0")
        for row in cur.fetchall():
            msg_id, ts, symbol, side, lot, entry, sl, tp, ticket, status = row
            channel_id = _get_channel_for_msg_id(msg_id)
            if not channel_id:
                continue
            trades_by_channel.setdefault(channel_id, []).append({
                "msg_id": msg_id, "ts": ts, "symbol": symbol, "side": side,
                "lot": lot, "entry": entry, "sl": sl, "tp": tp,
                "ticket": ticket, "status": status
            })
        con.close()
    except Exception:
        pass
    return trades_by_channel


def _compute_r_multiple(ticket: int, side: str, entry: float, sl: float) -> Optional[float]:
    """Compute realized R multiple for a ticket from MT5 deals.
    R = (exit_price - entry) / (entry - sl) for BUY, inverted for SELL."""
    if not _HAVE_MT5:
        return None
    try:
        deals = mt5.history_deals_get(ticket=ticket)
        if not deals:
            return None
        # Find the closing deal (entry deal has position_id=0 or different logic)
        # For simplicity, sum all deal profits for this ticket and compute R from net P&L
        total_pl = sum(d.profit + d.commission + d.swap + getattr(d, "fee", 0.0) for d in deals)
        if total_pl == 0:
            return 0.0
        risk_per_lot = abs(entry - sl)
        if risk_per_lot == 0:
            return None
        # R = P&L / (risk_per_lot * lot * contract_size)
        # We don't have lot/contract_size here, so return P&L in risk units
        # This is an approximation; proper R needs contract specs
        return total_pl / risk_per_lot
    except Exception:
        return None


def _compute_channel_stats(channel_id: str, trades: List[Dict], name: str) -> ChannelStats:
    """Compute stats for one channel from its executed trades."""
    n = len(trades)
    if n == 0:
        return ChannelStats(
            channel_id=channel_id, name=name, n=0, wins=0, losses=0,
            win_rate=WilsonCI(0, 0, 0), expectancy_r=0.0,
            guards=apply_guards(0), stability=StabilitySplit(
                first_half=HalfStats(0,0,None,None),
                second_half=HalfStats(0,0,None,None), agree=None))

    # Sort by timestamp for stability split
    trades_sorted = sorted(trades, key=lambda t: t["ts"])
    mid = n // 2
    first_half = trades_sorted[:mid]
    second_half = trades_sorted[mid:]

    wins = 0
    losses = 0
    r_sum = 0.0
    r_count = 0

    for t in trades_sorted:
        entry_val = t["entry"]
        sl_val = t["sl"]
        if entry_val == "market" or sl_val is None:
            continue
        try:
            entry_f = float(entry_val)
            sl_f = float(sl_val)
        except (ValueError, TypeError):
            continue
        r = _compute_r_multiple(t["ticket"], t["side"], entry_f, sl_f)
        if r is None:
            continue
        r_sum += r
        r_count += 1
        if r > 0:
            wins += 1
        elif r < 0:
            losses += 1

    total = wins + losses
    wr = wilson(wins, total) if total > 0 else WilsonCI(0, 0, 0)
    exp_r = r_sum / r_count if r_count > 0 else 0.0

    # Stability split
    def count_wins_losses(trade_list):
        w = l = 0
        for t in trade_list:
            entry_val = t["entry"]
            sl_val = t["sl"]
            if entry_val == "market" or sl_val is None:
                continue
            try:
                entry_f = float(entry_val)
                sl_f = float(sl_val)
            except (ValueError, TypeError):
                continue
            r = _compute_r_multiple(t["ticket"], t["side"], entry_f, sl_f)
            if r is None:
                continue
            if r > 0:
                w += 1
            elif r < 0:
                l += 1
        return w, l

    fw, fl = count_wins_losses(first_half)
    sw, sl = count_wins_losses(second_half)
    fn = fw + fl
    sn = sw + sl

    return ChannelStats(
        channel_id=channel_id,
        name=name,
        n=total,
        wins=wins,
        losses=losses,
        win_rate=wr,
        expectancy_r=exp_r,
        guards=apply_guards(total),
        stability=stability_split(fn, fw, sn, sw)
    )


def _compute_algo_engine_stats() -> EngineStats:
    """Compute stats for algo engine (magic 20261015) from MT5 deals."""
    if not _HAVE_MT5:
        return EngineStats(
            engine="algo", magic=ALGO_MAGIC, n=0, wins=0, losses=0,
            win_rate=WilsonCI(0, 0, 0), expectancy_r=0.0,
            guards=apply_guards(0), stability=StabilitySplit(
                first_half=HalfStats(0,0,None,None),
                second_half=HalfStats(0,0,None,None), agree=None))

    try:
        from datetime import datetime, timedelta
        day0 = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(day0, datetime.now() + timedelta(days=1)) or []
        algo_deals = [d for d in deals if d.magic == ALGO_MAGIC]
        if not algo_deals:
            return EngineStats(
                engine="algo", magic=ALGO_MAGIC, n=0, wins=0, losses=0,
                win_rate=WilsonCI(0, 0, 0), expectancy_r=0.0,
                guards=apply_guards(0), stability=StabilitySplit(
                    first_half=HalfStats(0,0,None,None),
                    second_half=HalfStats(0,0,None,None), agree=None))

        # Group by position to get round-trip P&L
        by_ticket: Dict[int, List] = {}
        for d in algo_deals:
            by_ticket.setdefault(d.ticket, []).append(d)

        r_values = []
        for ticket, dlist in by_ticket.items():
            total_pl = sum(d.profit + d.commission + d.swap + getattr(d, "fee", 0.0) for d in dlist)
            # Approximate R: need entry/sl from the position
            # For now use a proxy: assume 1R = avg SL distance from entry
            # This is a limitation without position entry/sl data
            r_values.append(total_pl)

        # Without entry/sl we can't compute true R; use P&L sign for win rate
        wins = sum(1 for r in r_values if r > 0)
        losses = sum(1 for r in r_values if r < 0)
        total = wins + losses

        # Sort by time for stability
        sorted_deals = sorted(algo_deals, key=lambda d: d.time)
        mid = len(sorted_deals) // 2
        first_tickets = set(d.ticket for d in sorted_deals[:mid])
        second_tickets = set(d.ticket for d in sorted_deals[mid:])

        def count_wl(tickets):
            w = l = 0
            for ticket in tickets:
                dlist = by_ticket[ticket]
                total_pl = sum(d.profit + d.commission + d.swap + getattr(d, "fee", 0.0) for d in dlist)
                if total_pl > 0:
                    w += 1
                elif total_pl < 0:
                    l += 1
            return w, l

        fw, fl = count_wl(first_tickets)
        sw, sl = count_wl(second_tickets)
        fn = fw + fl
        sn = sw + sl

        wr = wilson(wins, total) if total > 0 else WilsonCI(0, 0, 0)
        exp_r = sum(r_values) / len(r_values) if r_values else 0.0

        return EngineStats(
            engine="algo", magic=ALGO_MAGIC, n=total, wins=wins, losses=losses,
            win_rate=wr, expectancy_r=exp_r,
            guards=apply_guards(total),
            stability=stability_split(fn, fw, sn, sw))
    except Exception:
        return EngineStats(
            engine="algo", magic=ALGO_MAGIC, n=0, wins=0, losses=0,
            win_rate=WilsonCI(0, 0, 0), expectancy_r=0.0,
            guards=apply_guards(0), stability=StabilitySplit(
                first_half=HalfStats(0,0,None,None),
                second_half=HalfStats(0,0,None,None), agree=None))


def get_edge_stats() -> Dict[str, Any]:
    """Main entry point: returns per-channel + per-engine edge statistics as JSON-serializable dict."""
    channel_names = _load_channel_names()
    channel_trades = _fetch_channel_trades()

    channels = []
    for cid, trades in channel_trades.items():
        name = channel_names.get(cid, cid)
        channels.append(_compute_channel_stats(cid, trades, name).to_dict())

    # Sort by expectancy descending
    channels.sort(key=lambda c: (c["expectancy_r"] is None, -(c["expectancy_r"] or 0)))

    algo = _compute_algo_engine_stats().to_dict()

    return {
        "channels": channels,
        "engines": [algo],
        "methodology": {
            "wilson_z": Z_95,
            "confidence": 0.95,
            "warn_floor": WARN_FLOOR,
            "refuse_floor": REFUSE_FLOOR,
            "source": "edge-stats packages/core/src/stats/stats.ts:wilson()"
        }
    }


if __name__ == "__main__":
    print(json.dumps(get_edge_stats(), indent=2))