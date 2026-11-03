---
slug: pine_bridge
type: note
graph: gitnexus
---

"""Pine Script signal translator (offline only). No live broker connectivity.

Given a Pine Script signal string, extract symbol, side, entry price,
stop loss, and take profit using regex only. No external Pine compiler
or live broker connection is used.
"""

import re
from typing import Dict, Optional


def parse_signal(signal: str) -> Dict[str, Optional[float]]:
    """
    Parse a Pine Script signal string into a dict.

    Expected format (space-separated):
        SYMBOL SIDE ENTRY_PRICE [SL PRICE] [TP PRICE]

    where SIDE is 'BUY' or 'SELL'.

    Returns a dict with keys: symbol, side, entry_price, sl_price, tp_price.
    Values missing from the input are set to None.
    """
    pattern = r'([A-Z]+)\s+(BUY|SELL)\s+(\d+\.\d+)(?:\s+SL\s+(\d+\.\d+))?(?:\s+TP\s+(\d+\.\d+))?'
    m = re.match(pattern, signal.strip())
    if not m:
        return {"symbol": None, "side": None, "entry_price": None,
                "sl_price": None, "tp_price": None}
    symbol, side, entry_price, sl_price, tp_price = m.groups()
    return {
        "symbol": symbol,
        "side": side,
        "entry_price": float(entry_price),
        "sl_price": float(sl_price) if sl_price is not None else None,
        "tp_price": float(tp_price) if tp_price is not None else None,
    }

