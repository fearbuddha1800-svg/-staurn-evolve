---
slug: signal_parser
type: note
graph: gitnexus
---

"""
signal_parser.py - Offline regex-based signal extractor.

All extraction is pure Python; no external API calls are made.
The placeholder `llm_extract` function mimics an LLM response parser
but operates on supplied text, not on any remote service.

Typical usage:
    parser = SignalParser(text)
    result = parser.extract()
    # result is dict with fields: symbol, side, entry, sl, tp
"""

import re
from typing import Dict, Optional, Any


class SignalParser:
    """Regex-based parser for trading signals embedded in free‑form text.

    The regex patterns are deliberately simple and tuned for common
    signal formats such as:

        AAPL BUY 150.2 SL 148 TP 155
        GOOGL SELL 2800 SL 2780 TP 2830

    Subclasses or instance configuration can adjust the patterns to
    match other brokers or formats.
    """

    # Default patterns — can be overridden per instance
    DEFAULT_PATTERN = re.compile(
        r"(?P<symbol>[A-Z0-9]+)\s+(?P<side>[A-Z]+)\s+(?P<entry>[\d.]+)\s+"
        r"SL\s+(?P<sl>[\d.]+)\s+TP\s+(?P<tp>[\d.]+)",
        re.IGNORECASE,
    )

    def __init__(self, text: str, pattern: Optional[re.Pattern] = None) -> None:
        self.text = text
        self.pattern = pattern or self.DEFAULT_PATTERN

    def extract(self) -> Dict[str, Optional[Any]]:
        """Run the regex against stored text and return parsed fields.

        Returns a dict with keys: symbol, side, entry, sl, tp.
        If the pattern does not match, each value is None.
        """
        m = self.pattern.search(self.text)
        if not m:
            return {"symbol": None, "side": None, "entry": None, "sl": None, "tp": None}
        return {
            "symbol": m.group("symbol"),
            "side": m.group("side"),
            "entry": float(m.group("entry")),
            "sl": float(m.group("sl")),
            "tp": float(m.group("tp")),
        }


# -----------------------------------------------------------------
# Placeholder LLM extractor — pure Python, no API calls
# -----------------------------------------------------------------
def llm_extract(text: str) -> Dict[str, Optional[str]]:
    """Parse a signal from *text* using the same regex as SignalParser.

    This function exists as a stand‑in for an LLM‑based extraction
    routine. It does **not** call any external model or API; it merely
    applies the identical regular‑expression logic so that callers can
    swap in a real LLM parser later without changing the interface.

    Args:
        text: Free‑form text that may contain a trading signal.

    Returns:
        Dict with keys: symbol, side, entry, sl, tp. Values are strings
        (or None if the pattern does not match).
    """
    parser = SignalParser(text)
    result = parser.extract()
    # Cast numeric fields back to strings for a uniform "LLM-style" output
    return {
        "symbol": result["symbol"],
        "side": result["side"],
        "entry": str(result["entry"]) if result["entry"] is not None else None,
        "sl": str(result["sl"]) if result["sl"] is not None else None,
        "tp": str(result["tp"]) if result["tp"] is not None else None,
    }


# -----------------------------------------------------------------
# Minimal CLI demo
# -----------------------------------------------------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python signal_parser.py '<signal text>'")
        sys.exit(1)
    text = sys.argv[1]
    parser = SignalParser(text)
    print("SignalParser result:", parser.extract())
    print("llm_extract result:", llm_extract(text))

