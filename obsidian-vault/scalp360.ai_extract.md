---
slug: scalp360.ai_extract
type: note
graph: gitnexus
---

"""Bounded AI extraction. AI reduces ambiguity; it never owns permission,
sizing, freshness or submission. Any failure -> UNKNOWN, never a guess.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any

@dataclass
class AIExtractConfig:
    provider: str = "nvidia"             # fixed by tenant config, not per-call
    model: str = "z-ai/glm-5.3"
    timeout_s: float = 8.0               # hard ceiling; scalping can't wait
    max_calls_per_min: int = 30
    circuit_breaker_fails: int = 5       # opens after N consecutive failures
    spend_budget_usd_per_day: float = 1.0

@dataclass
class AIExtractResult:
    kind: str = "UNKNOWN"                # NEW_ENTRY | UPDATE | RESULT | UNKNOWN
    symbol: Optional[str] = None
    side: Optional[str] = None
    evidence: Dict[str, str] = field(default_factory=dict)  # field -> raw span
    confidence: float = 0.0              # NOT calibrated; ranking input only
    abstained_reason: str = ""

class CircuitOpen(Exception): pass

class AIExtractor:
    """wraps an llm callable: fn(prompt:str, timeout:float) -> dict.
    The callable MUST be provider-pinned by config; never model-shopping per call."""
    def __init__(self, cfg: AIExtractConfig, llm: Callable[[str, float], Dict[str, Any]]):
        self.cfg, self.llm = cfg, llm
        self.fails = 0
        self.calls: list[float] = []
        self.spend = 0.0

    def _admit(self) -> None:
        if self.fails >= self.cfg.circuit_breaker_fails:
            raise CircuitOpen()
        now = time.time()
        self.calls = [t for t in self.calls if now - t < 60]
        if len(self.calls) >= self.cfg.max_calls_per_min:
            raise CircuitOpen("rate limit")
        if self.spend >= self.cfg.spend_budget_usd_per_day:
            raise CircuitOpen("budget")

    def extract(self, text: str) -> AIExtractResult:
        try:
            self._admit()
        except CircuitOpen as e:
            return AIExtractResult(abstained_reason=f"circuit: {e}")
        t0 = time.time()
        try:
            out = self.llm(text, self.cfg.timeout_s)
        except Exception as e:
            self.fails += 1
            return AIExtractResult(abstained_reason=f"model error: {type(e).__name__}")
        self.calls.append(t0); self.fails = 0
        r = AIExtractResult()
        r.kind = str(out.get("kind", "UNKNOWN")).upper()
        if r.kind not in ("NEW_ENTRY", "UPDATE", "RESULT"):
            r.kind = "UNKNOWN"
        r.symbol = out.get("symbol"); r.side = out.get("side")
        r.evidence = {k: str(v) for k, v in (out.get("evidence") or {}).items()}
        try:
            r.confidence = min(1.0, max(0.0, float(out.get("confidence", 0))))
        except (TypeError, ValueError):
            r.confidence = 0.0
        if r.kind == "UNKNOWN":
            r.abstained_reason = str(out.get("abstained_reason") or "model could not classify")
        return r

## Links from
- [[event_bus]]
- [[integration_status]]
- [[neural_pipeline]]
- [[scalp360_bridge]]
- [[test_intelligence_integration]]
- [[test_neural_watch_gate]]
- [[tests_360.test_ai_neural]]
- [[tests_360.test_console]]
- [[tests_360.test_cursor]]
- [[tests_360.test_executor]]
- [[tests_360.test_gold_parser]]
- [[tests_360.test_lineage]]
- [[tests_360.test_risk]]
