---
slug: scalp360.events
type: note
graph: gitnexus
---

"""Immutable event envelope + identity. Every downstream decision keys off this."""
from __future__ import annotations
import hashlib, time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

class EventKind(str, Enum):
    NEW_ENTRY = "NEW_ENTRY"   # fresh actionable signal
    UPDATE    = "UPDATE"      # modification of a previously seen signal (edit/reply)
    RESULT    = "RESULT"      # outcome post (TP hit / SL hit / closed)
    UNKNOWN   = "UNKNOWN"     # not classifiable -> abstain, never guess

@dataclass(frozen=True)
class SignalEvent:
    source: str                 # tenant-scoped channel key, e.g. "t1:xauhq"
    message_id: int             # telegram message id (monotonic per channel)
    edit_id: int = 0            # 0 = original post; increments on edits
    text: str = ""
    original_at: float = 0.0    # sender time (epoch s); 0 if unknown
    received_at: float = field(default_factory=time.time)
    kind: EventKind = EventKind.UNKNOWN

    @property
    def event_id(self) -> str:
        return f"{self.source}:{self.message_id}:{self.edit_id}"

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8", "replace")).hexdigest()[:16]

    def age_s(self, now: Optional[float] = None) -> float:
        now = time.time() if now is None else now
        if self.original_at <= 0:
            return now - self.received_at      # fall back to receipt age, flagged by caller
        return now - self.original_at

def recap_heuristic(ev: SignalEvent) -> bool:
    """Detect channel recap/digest posts that must never become entries.
    Returns True if the event looks like a recap."""
    t = ev.text.lower()
    recap_markers = ("recap", "summary", "today's results", "results so far",
                     "closed trades", "week in review", "performance update")
    return any(m in t for m in recap_markers)


# ---- signal-relay event bus types (extend SignalEvent/EventKind, do not replace) ----
# Canonical set of event types the central EventBus (workspace root event_bus.py)
# accepts. event_bus.py imports this when available and falls back to its own
# frozenset otherwise; both must stay in sync.
BUS_EVENT_TYPES = frozenset({
    "signal_received", "zone_parsed", "risk_approved", "order_placed",
    "order_filled", "position_opened", "position_closed", "pnl_update",
    "neural_prediction", "channel_score_update", "engine_status", "alert",
    "halt_triggered", "pine_signal", "breakout_signal",
    "luxalgo_regime_shift", "luxalgo_whale_options", "luxalgo_edge_stats",
})

__all__ = ["EventKind", "SignalEvent", "recap_heuristic", "BUS_EVENT_TYPES"]

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
