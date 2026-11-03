"""Source-typed parser for the XAUHQ gold format.
Regression anchor: message 2243 from the 2026-10-14 export:
  ENTRY: 4184/90  -> zone (4184.0, 4190.0), NOT a single price 4184
  TP4 ->4145/4120 -> zone target [4145, 4120] preserved
Rules-first, deterministic. Ambiguity -> abstain (None), never guess.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

@dataclass(frozen=True)
class Zone:
    low: float
    high: float

@dataclass
class GoldSignal:
    symbol: str            # always XAUUSD for this source
    side: str              # "BUY" | "SELL"
    entry: Zone            # preserved zone, never collapsed
    stop: float
    targets: List[Tuple[str, Zone]] = field(default_factory=list)  # ("TP1", Zone) ...
    raw: str = ""

NUM = r"(\d{3,6})(?:[.,](\d+))?"
SHY = "[\u2010\u2011\u2012\u2013\u2014-]"   # every dash variant seen in the wild
ARROW = r"(?:->|\u2192|=>|>)"                    # ->, unicode arrow, =>

def _f(intpart: str, frac: Optional[str]) -> float:
    v = float(intpart)
    if frac:
        v += float("0." + frac)
    return v

def _parse_zone(token: str) -> Optional[Zone]:
    """'4184/90' -> Zone(4184, 4190); '4175' -> Zone(4175, 4175); else None."""
    token = token.strip().rstrip(".")
    m = re.fullmatch(NUM + r"/(\d{1,4})", token)
    if m:
        base = _f(m.group(1), m.group(2))
        tail = m.group(3)
        # shorthand: 4184/90 means 4184..4190 (same leading digits)
        hi = float(str(int(base))[:-len(tail)] + tail) if tail else base
        return Zone(min(base, hi), max(base, hi))
    m = re.fullmatch(NUM, token)
    if m:
        v = _f(m.group(1), m.group(2))
        return Zone(v, v)
    return None

def parse_gold(text: str) -> Optional[GoldSignal]:
    """Parse XAUHQ-style signal. Returns None (abstain) on anything ambiguous."""
    t = re.sub(r"[\U0001F6E1\U0001F7E1\uFE0F]", " ", text)   # shield, circles, VS16
    t = t.replace("\u00a0", " ")
    side_m = re.search(r"\b(BUY|SELL)\s+NOW\b", t, re.I)
    if not side_m:
        return None
    side = side_m.group(1).upper()
    ent_m = re.search(r"ENTRY\s*:\s*([0-9][0-9/.,]*)", t, re.I)
    sl_m  = re.search(r"STOP\s*LOSS\s*:\s*([0-9][0-9/.,]*)", t, re.I)
    if not ent_m or not sl_m:
        return None
    entry = _parse_zone(ent_m.group(1))
    sl_z  = _parse_zone(sl_m.group(1))
    if entry is None or sl_z is None or sl_z.low != sl_z.high:
        return None
    stop = sl_z.low
    if side == "SELL" and not stop > entry.high:
        return None     # geometry broken: sell SL must sit above entry zone
    if side == "BUY" and not stop < entry.low:
        return None
    targets: List[Tuple[str, Zone]] = []
    for m in re.finditer(r"(TP\d)\s*" + ARROW + r"\s*([0-9][0-9/.,]*)", t, re.I):
        z = _parse_zone(m.group(2))
        if z is not None:
            targets.append((m.group(1).upper(), z))
    if not targets:
        return None     # a signal with no targets is not actionable -> abstain
    return GoldSignal(symbol="XAUUSD", side=side, entry=entry, stop=stop,
                      targets=targets, raw=text)
