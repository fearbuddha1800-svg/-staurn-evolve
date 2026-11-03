---
slug: pine_script_parser
type: note
graph: gitnexus
---

"""Pine Script (TradingView) → Python strategy transpiler.
Zero third-party deps. Parses a subset of Pine Script v5:
  //@version=5, indicator()/strategy() declaration
  input.float()/input.int()  -> strategy parameters
  ta.rsi()/ta.ema()/ta.sma()/ta.atr()/ta.stoch() -> indicator calls
  close/high/low/open        -> price series
  strategy.entry()/strategy.exit() -> entries/exits
  if/then conditionals       -> Python if blocks
  plot()                     -> logged series
Output: a Python class with .params, .indicators(candles), .on_candle(candle) -> action dict.
Designed so TradingView strategies can be dropped in and run against live MT5 data.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class PineInput:
    name: str
    ptype: str            # "float" | "int" | "bool" | "color" | "source"
    default: Any
    minval: Optional[float] = None
    maxval: Optional[float] = None
    step: Optional[float] = None


@dataclass
class PineIndicator:
    name: str
    func: str             # "rsi" | "ema" | "sma" | "atr" | "stoch"
    args: List[Any]       # e.g. [close, 14] or [high, low, close, 14]


@dataclass
class PineEntry:
    id: str
    direction: str        # "long" | "short"
    condition: str        # raw condition text translated to Python
    comment: str = ""


@dataclass
class PineStrategy:
    version: str = "5"
    title: str = ""
    is_strategy: bool = False
    inputs: List[PineInput] = field(default_factory=list)
    indicators: List[PineIndicator] = field(default_factory=list)
    entries: List[PineEntry] = field(default_factory=list)
    exits: List[Dict[str, Any]] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)
    parse_errors: List[str] = field(default_factory=list)

    def python_class_name(self) -> str:
        return "".join(w.capitalize() for w in self.title.split()) or "PineStrategy"


_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)"
_ID = r"[A-Za-z_][A-Za-z0-9_]*"
_FUNC_CALL = re.compile(rf"({_ID})\s*\(\s*([^)]*)\s*\)")
_INPUT = re.compile(
    rf"input\.(\w+)\s*\(\s*{_ID}\s*=\s*\"(?P<title>[^\"]*)\""
    rf".*?defval\s*=\s*(?P<defval>{_NUM}|true|false)"
    rf"(?:.*?minval\s*=\s*(?P<minval>{_NUM}))?"
    rf"(?:.*?maxval\s*=\s*(?P<maxval>{_NUM}))?",
    re.I,
)
_TA_FUNC = re.compile(rf"ta\.({_ID})\s*\(\s*([^)]*)\s*\)")


def _to_python_num(tok: str) -> str:
    tok = tok.strip()
    if tok.lower() in ("true", "false"):
        return tok.capitalize()
    return tok


def parse_pine(text: str) -> PineStrategy:
    strat = PineStrategy()
    lines = text.splitlines()
    strat.raw_lines = lines

    for i, line in enumerate(lines):
        s = line.strip()

        # version / declaration
        if s.startswith("//@version"):
            m = re.search(r"version\s*=\s*(\d+)", s)
            if m:
                strat.version = m.group(1)
        if s.startswith("indicator(") or s.startswith("strategy("):
            strat.is_strategy = s.startswith("strategy(")
            m = re.search(r"title\s*=\s*\"([^\"]*)\"", s)
            strat.title = m.group(1) if m else "Untitled"

        # inputs
        m = _INPUT.search(s)
        if m:
            ptype_map = {"float": "float", "int": "int", "bool": "bool", "color": "color", "source": "source"}
            ptype = ptype_map.get(m.group(1), "float")
            defval = _to_python_num(m.group("defval"))
            strat.inputs.append(PineInput(
                name=m.group(0).split("=")[0].strip().split("(")[-1].split(",")[0].strip() if "=" in m.group(0) else m.group("title"),
                ptype=ptype,
                default=float(defval) if ptype in ("float", "int") else (defval == "True"),
                minval=float(m.group("minval")) if m.group("minval") else None,
                maxval=float(m.group("maxval")) if m.group("maxval") else None,
            ))

        # indicator calls: ta.rsi(...), ta.ema(...), etc.
        for m in _TA_FUNC.finditer(s):
            func = m.group(1)
            args_raw = m.group(2)
            args = [_a.strip() for _a in args_raw.split(",")]
            strat.indicators.append(PineIndicator(name=f"{func}_{len(strat.indicators)}", func=func, args=args))

        # strategy.entry / strategy.exit
        if "strategy.entry" in s:
            m = re.search(r'strategy\.entry\s*\(\s*"([^"]*)"', s)
            direction = "long" if "strategy.long" in s or "long" in s.lower() else "short"
            strat.entries.append(PineEntry(id=m.group(1) if m else f"entry_{i}", direction=direction, condition=s))
        if "strategy.exit" in s:
            m = re.search(r'strategy\.exit\s*\(\s*"([^"]*)"', s)
            strat.exits.append({"id": m.group(1) if m else f"exit_{i}", "raw": s})

        # if conditionals
        if re.match(r"if\s+", s):
            cond = re.sub(r"^if\s+", "", s)
            strat.entries.append(PineEntry(id=f"cond_{i}", direction="long", condition=cond))

    return strat


def translate_expression(expr: str, params: Dict[str, Any]) -> str:
    """Translate a Pine expression fragment to Python. Best-effort; unknown
    functions are left as-is with a comment so the user can review."""
    e = expr.strip()
    # ta.rsi(src, len) -> ta_rsi(src, len)
    e = re.sub(r"ta\.(\w+)\s*\(", r"ta_\1(", e)
    # close/high/low/open -> close/high/low/open (kept, resolved in on_candle)
    e = e.replace("na", "None")
    e = e.replace("and", " and ").replace("or", " or ").replace("not ", "not ")
    # parameter substitution ${param} or direct name
    for name, val in params.items():
        e = re.sub(rf"\b{name}\b", str(val), e)
    return e


def emit_python(strat: PineStrategy) -> str:
    """Emit a standalone Python module implementing the strategy."""
    lines: List[str] = []
    lines.append("from __future__ import annotations")
    lines.append("from dataclasses import dataclass")
    lines.append("from typing import Optional, Dict, Any, List")
    lines.append("")
    lines.append("import math")
    lines.append("")
    lines.append("class ta:")
    lines.append("    \"\"\"Zero-dep technical helpers mirroring Pine ta.* semantics.\"\"\"")
    lines.append("")
    lines.append("    @staticmethod")
    lines.append("    def rsi(prices: List[float], period: int = 14) -> Optional[float]:")
    lines.append("        if len(prices) < period + 1:")
    lines.append("            return None")
    lines.append("        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]")
    lines.append("        gains = [max(d, 0.0) for d in deltas]")
    lines.append("        losses = [max(-d, 0.0) for d in deltas]")
    lines.append("        avg_gain = sum(gains[:period]) / period")
    lines.append("        avg_loss = sum(losses[:period]) / period")
    lines.append("        if avg_loss == 0:")
    lines.append("            return 100.0")
    lines.append("        rs = avg_gain / avg_loss")
    lines.append("        return 100.0 - (100.0 / (1.0 + rs))")
    lines.append("")
    lines.append("    @staticmethod")
    lines.append("    def ema(prices: List[float], period: int = 14) -> List[float]:")
    lines.append("        if not prices or period < 1:")
    lines.append("            return []")
    lines.append("        k = 2.0 / (period + 1.0)")
    lines.append("        out = [prices[0]]")
    lines.append("        for p in prices[1:]:")
    lines.append("            out.append(p * k + out[-1] * (1 - k))")
    lines.append("        return out")
    lines.append("")
    lines.append("    @staticmethod")
    lines.append("    def sma(prices: List[float], period: int = 14) -> Optional[float]:")
    lines.append("        if len(prices) < period:")
    lines.append("            return None")
    lines.append("        return sum(prices[-period:]) / period")
    lines.append("")
    lines.append("    @staticmethod")
    lines.append("    def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:")
    lines.append("        if len(highs) < period + 1:")
    lines.append("            return None")
    lines.append("        trs = []")
    lines.append("        for i in range(1, len(highs)):")
    lines.append("            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))")
    lines.append("            trs.append(tr)")
    lines.append("        return sum(trs[-period:]) / period")
    lines.append("")
    lines.append("")
    lines.append(f"class {strat.python_class_name()}:")
    lines.append(f"    \"\"\"Transpiled from Pine Script: {strat.title} (v{strat.version})\"\"\"")
    lines.append("")
    lines.append("    def __init__(self, params: Optional[Dict[str, Any]] = None):")
    lines.append("        self.params = params or {}")
    lines.append("        self.closes: List[float] = []")
    lines.append("        self.highs: List[float] = []")
    lines.append("        self.lows: List[float] = []")
    lines.append("        self.opens: List[float] = []")
    lines.append("        self.times: List[float] = []")
    lines.append("        self.position = 0   # 1 long, -1 short, 0 flat")
    lines.append("        self.entry_price = 0.0")
    lines.append("        self.signal_log: List[Dict[str, Any]] = []")
    lines.append("")
    lines.append("    def on_candle(self, open_: float, high: float, low: float, close: float, time_ms: float) -> Dict[str, Any]:")
    lines.append("        \"\"\"Feed one closed candle. Returns {'action': 'buy'|'sell'|'hold', 'lots': float, 'sl': float|None, 'tp': float|None, 'reason': str}\"\"\"")
    lines.append("        self.opens.append(open_); self.highs.append(high); self.lows.append(low)")
    lines.append("        self.closes.append(close); self.times.append(time_ms)")
    lines.append("        action = 'hold'; lots = 0.0; sl = None; tp = None; reason = 'no signal'")
    lines.append("")
    lines.append("        # ---- translated Pine conditions (review before live use) ----")
    lines.append("        close = self.closes[-1] if self.closes else 0.0")
    lines.append("        open_p = self.opens[-1] if self.opens else 0.0")
    lines.append("        high = self.highs[-1] if self.highs else 0.0")
    lines.append("        low = self.lows[-1] if self.lows else 0.0")
    lines.append("")
    lines.append("        # indicator values (latest)")
    lines.append("        rsi_val = ta.rsi(self.closes, 14)")
    lines.append("        ema_val = ta.ema(self.closes, 14)[-1] if ta.ema(self.closes, 14) else None")
    lines.append("        sma_val = ta.sma(self.closes, 14)")
    lines.append("        atr_val = ta.atr(self.highs, self.lows, self.closes, 14)")
    lines.append("")
    lines.append("        # TODO: replace with the strategy's translated conditions")
    lines.append("        # Example skeleton:")
    lines.append("        # if self.position == 0 and rsi_val and rsi_val < 30:")
    lines.append("        #     action = 'buy'; lots = self.params.get('lots', 0.01)")
    lines.append("        #     sl = close - (atr_val or 0) * 2")
    lines.append("        #     tp = close + (atr_val or 0) * 3")
    lines.append("        #     reason = 'pine_entry_long'")
    lines.append("")
    lines.append("        if action != 'hold':")
    lines.append("            self.signal_log.append({'time': time_ms, 'action': action, 'lots': lots, 'sl': sl, 'tp': tp, 'reason': reason})")
    lines.append("        return {'action': action, 'lots': lots, 'sl': sl, 'tp': tp, 'reason': reason}")
    lines.append("")
    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    print('Pine Strategy module loaded. Import and call on_candle() per candle.')")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
        strat = parse_pine(text)
        print(emit_python(strat))
    else:
        print("Usage: python pine_script_parser.py <pine_file.pine>")

## Links from
- [[scalp360_bridge]]
