---
slug: parser
type: note
graph: gitnexus
---

"""Signal parser: free-text Telegram signal -> structured trade dict (or None).

Pure stdlib. Deterministic regex rules; conservative by design:
- If it doesn't look like a trade signal -> returns None (message is just relayed, never executed).
- If a required piece (side or symbol) is missing -> returns dict with "parse_ok": False.
"""
import re
import unicodedata

# ---- symbol aliases -------------------------------------------------------
SYMBOL_ALIASES = {
    "GOLD": "XAUUSD", "XAU": "XAUUSD", "GOLDSPOT": "XAUUSD",
    "SILVER": "XAGUSD", "XAG": "XAGUSD",
    "BTC": "BTCUSD", "BITCOIN": "BTCUSD", "BTCUSD": "BTCUSD",
    "ETH": "ETHUSD", "ETHEREUM": "ETHUSD",
    "DOW": "US30", "US30": "US30", "DJ30": "US30", "DJI": "US30",
    "NASDAQ": "US100", "NAS100": "US100", "US100": "US100", "USTEC": "US100", "TEC100": "US100",
    "SPX": "US500", "SP500": "US500", "US500": "US500", "S&P": "US500",
    "DAX": "GER40", "GER40": "GER40", "DE40": "GER40", "DE30": "GER40", "GER30": "GER40",
    "UKOIL": "UKOIL", "WTI": "XTIUSD", "USOIL": "XTIUSD", "OIL": "XTIUSD", "CRUDE": "XTIUSD",
    "CABLE": "GBPUSD", "FIBER": "EURUSD", "GUPPY": "GBPJPY", "KIWI": "NZDUSD",
    "LOONIE": "USDCAD", "AUSSIE": "AUDUSD", "MATT": "AUDUSD",
}

SIDE_WORDS = {
    "BUY": "buy", "LONG": "buy", "BULLISH": "buy", "BULL": "buy",
    "SELL": "sell", "SHORT": "sell", "BEARISH": "sell", "BEAR": "sell",
}

ENTRY_TYPES = {"LIMIT": "limit", "STOP": "stop", "NOW": "market", "MARKET": "market",
               "INSTANT": "market", "CMP": "market", "CURRENT": "market"}

MANAGE_WORDS = ("close", "cancel", "delete", "move sl", "move stop", "breakeven", "be ", "tp hit",
                 "sl hit", "modify", "remove")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u200b", " ").replace("\u202f", " ").replace("\xa0", " ")
    return text


def _find_symbol(text: str):
    """Look for a tradable symbol token in the message. Returns canonical name or None."""
    words = re.findall(r"[A-Za-z&+][A-Za-z&+\d/]*", text.upper())
    for w in words:
        if w in SYMBOL_ALIASES:
            return SYMBOL_ALIASES[w]
    # 6-letter forex pairs like EURUSD / XAUUSD / GBPJPY
    m = re.search(r"\b([A-Z]{6})\b", text.upper())
    if m:
        return m.group(1)
    # pairs written EUR/USD
    m = re.search(r"\b([A-Z]{3})\s*/\s*([A-Z]{3})\b", text.upper())
    if m:
        return m.group(1) + m.group(2)
    return None


def _find_side(text: str):
    t = text.upper()
    for w, side in SIDE_WORDS.items():
        if re.search(r"\b" + re.escape(w) + r"\b", t):
            return side
    m = re.search(r"^\s*(B|S)\s*[!:@]?\b", t) if len(t) < 400 else None
    return ("buy" if m.group(1) == "B" else "sell") if m else None


def _order_type(text: str):
    t = text.upper()
    if re.search(r"\bBUY\s*STOP\b|\bSELL\s*STOP\b|\bSTOP\s*ENTRY\b", t):
        return "stop"
    if re.search(r"\bBUY\s*LIMIT\b|\bSELL\s*LIMIT\b|\bLIMIT\b", t):
        return "limit"
    if re.search(r"\b(NOW|MARKET|INSTANT|CMP|CURRENT)\b", t):
        return "market"
    return "market"  # default: assume market


def _numbers(text: str):
    return [float(x) for x in re.findall(r"\d+(?:[.,]\d+)?", text)]


def _extract_side_price(side: str, text: str):
    """Entry price near the side keyword, e.g. 'BUY 2350', 'SELL XAU @ 1930.5', 'buy now'.
    Never crosses an SL/TP keyword while hunting the number (would swallow SL as entry)."""
    t = text.upper()
    alt = "BUY|LONG|BULL" if side == "buy" else "SELL|SHORT|BEAR"
    m = re.search(r"\b(?:" + alt + r")\b"
                  r"(?:(?!\bSL\b|\bTP\b|\bT\.P\b|\bTARGETS?\b|\bSTOP\s*LOSS\b)[^0-9]){0,40}?"
                  r"(\d+(?:[.,]\d+)?)", t)
    return _f(m)


def _f(m):
    return float(m.group(1).replace(",", ".")) if m else None


_SL_ALT = r"SL|S\.L|STOP\s*LOSS|STOPLOSS"


def _extract_sl(text: str):
    t = text.upper()
    # attached index first (SL1: 2640), guarded so a plain 'sl 2640' keeps its first digit
    m = re.search(r"(?:" + _SL_ALT + r")[1-9](?=[\s:=@\-])[\s:=@\-]*(\d+(?:[.,]\d+)?)", t)
    if not m:
        m = re.search(r"(?:" + _SL_ALT + r")(?![1-9][\s:=@\-])\s*[:=@\-]?\s*(\d+(?:[.,]\d+)?)", t)
    return _f(m)


_TP_ALT = r"TP|T\.P|TARGETS?|TAKE\s*PROFIT|TGT"


def _extract_tps(text: str):
    t = text.upper()
    tps = []
    # 1) attached index digit claimed only when followed by separator/space: 'TP1: 2660', 'TP2 2675', 'TP1 → 2660'
    for m in re.finditer(r"(?:" + _TP_ALT + r")[1-9](?=[\s:=@\-\u2192\u27a1\u00bb\u25b6\u21d2\u203a])[\s:=@\-\u2192\u27a1\u00bb\u25b6\u21d2\u203a]*(\d+(?:[.,]\d+)?)", t):
        tps.append(_f(m))
    # 2) plain form: 'tp 2640', 'tp: 2640', 'targets 1.0750', 'TP → 2640' - guarded so the first price digit survives
    for m in re.finditer(r"(?:" + _TP_ALT + r")(?![1-9][\s:=@\-\u2192\u27a1\u00bb\u25b6\u21d2\u203a])\s*[:=@\-\u2192\u27a1\u00bb\u25b6\u21d2\u203a]?\s*(\d+(?:[.,]\d+)?)", t):
        tps.append(_f(m))
    return sorted(set(tps))


def _is_manage(text: str):
    t = text.lower()
    return any(t.startswith(w) or re.search(r"\b" + re.escape(w.strip()) + r"\b", t) for w in MANAGE_WORDS)


def _entry_zone(text, entry):
    """'ENTRY: 4184/90' -> [4184.0, 4190.0]. The /NN shorthand replaces the
    trailing digits of the first price (audit P0: entry ranges must not
    collapse into a single point)."""
    try:
        e = int(entry)
    except (TypeError, ValueError):
        return None
    m = re.search(rf"\b{e}\s*/\s*(\d{{1,4}})(?!\d)", text)
    if not m:
        return None
    tail = m.group(1)
    s = str(e)
    hi = int(tail) if len(tail) >= len(s) else int(s[: len(s) - len(tail)] + tail)
    return [float(min(e, hi)), float(max(e, hi))]


def parse_signal(text: str):
    """Return dict: {is_signal, parse_ok, action, order_type, symbol, entry, sl, tps, raw}
    is_signal=False -> not a trade signal (relay only)."""
    if not text or not text.strip():
        return {"is_signal": False, "raw": text}
    n = _norm(text)

    side = _find_side(n)
    symbol = _find_symbol(n)

    # manage instructions (close/BE/move-SL) may carry no digits -> check before the digit filter
    if _is_manage(n) and symbol:
        return {"is_signal": True, "parse_ok": False, "action": "manage", "raw": n,
                "reason": "management message (close/BE/move-SL) - manual action recommended"}

    # chatter filter: a trade signal always contains at least one number
    if not re.search(r"\d", n):
        return {"is_signal": False, "raw": n}

    # executable signals need BOTH a direction and a symbol; anything else is chatter
    if not side or not symbol:
        return {"is_signal": False, "raw": n}

    out = {"is_signal": True, "raw": n}
    if not side:
        return {**out, "parse_ok": False, "action": "unknown", "symbol": symbol,
                "reason": "no buy/sell direction found"}
    if not symbol:
        return {**out, "parse_ok": False, "action": side, "symbol": None,
                "reason": "no recognizable symbol found"}

    order_type = _order_type(n)
    entry = _extract_side_price(side, n)
    if entry is None and order_type == "market":
        entry = "market"
    sl = _extract_sl(n)
    tps = _extract_tps(n)

    out.update(parse_ok=True, action=side, order_type=order_type, symbol=symbol,
               entry=entry, sl=sl, tps=tps)
    if isinstance(entry, float):
        zone = _entry_zone(n, entry)
        if zone:
            out["entry_zone"] = zone
    if order_type in ("limit", "stop") and not isinstance(entry, float):
        out["parse_ok"] = False
        out["reason"] = f"{order_type} order without an entry price"
    if not tps and sl is None:
        out["parse_ok"] = False
        out["reason"] = "no TP and no SL found (refusing unbounded trade)"
    return out


# ---- self-test ------------------------------------------------------------
if __name__ == "__main__":
    samples = [
        "BUY XAUUSD @ 2650.5\nSL: 2640\nTP1: 2660 TP2: 2675",
        "🟡 GOLD SELL NOW 2650 sl 2660 tp 2640",
        "sell limit EUR/USD 1.0850 SL 1.0900 targets 1.0750 / 1.0700",
        "BTC buy 62000 SL 61000 TP 64000",
        "Good morning traders, gold looks bullish today!",
        "BUY NOW GBPUSD sl 1.26 tp 1.28",
        "Close XAUUSD now",
        "US30 SELL @ 43250 SL 43350 TP 43150",
    ]
    for s in samples:
        r = parse_signal(s)
        print("---", s.replace("\n", " | "))
        print("   ", {k: v for k, v in r.items() if k != "raw"})

## Links from
- [[analyze_channels]]
- [[channel_verify]]
- [[channel_verify2]]
- [[channel_verify3]]
- [[channel_verify_mass]]
- [[channel_verify_scout]]
- [[daemon]]
- [[telegram_deduper]]
- [[test_loop]]
- [[test_suite]]
