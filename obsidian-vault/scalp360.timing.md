---
slug: scalp360.timing
type: note
graph: gitnexus
---

"""Stage latency distributions. Claimed speed without p50/p95/p99 is fiction."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class StageTimer:
    samples: Dict[str, List[float]] = field(default_factory=dict)
    def record(self, stage: str, dt: float) -> None:
        self.samples.setdefault(stage, []).append(dt)
    def time(self, stage: str):
        class _Ctx:
            def __enter__(self_): self_.t0 = time.perf_counter(); return self_
            def __exit__(self_, *a): timer.record(stage, time.perf_counter() - self_.t0)
        timer = self
        return _Ctx()
    @staticmethod
    def _pct(xs: List[float], p: float) -> float:
        if not xs: return 0.0
        xs = sorted(xs); i = min(len(xs)-1, int(round((p/100.0)*(len(xs)-1))))
        return xs[i]
    def snapshot(self) -> Dict[str, Dict[str, float]]:
        out = {}
        for k, xs in self.samples.items():
            out[k] = {"n": len(xs), "p50": round(self._pct(xs,50),4),
                      "p95": round(self._pct(xs,95),4),
                      "p99": round(self._pct(xs,99),4),
                      "max": round(max(xs),4)}
        return out

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
