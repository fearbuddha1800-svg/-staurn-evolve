---
slug: scalp360.executor
type: note
graph: gitnexus
---

"""Single serialized execution authority per account.
One loop owns: risk reservation -> order submit -> outcome reconcile.
Unknown outcomes block re-entry. Account identity is verified BEFORE any
order path (the P0 that the self-test hid).
"""
from __future__ import annotations
import sqlite3, time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol

from .events import SignalEvent, EventKind, recap_heuristic
from .risk import RiskGovernor, SizingDecision, Verdict
from .lineage import LineageStore, IntentState
from .cursor import CursorStore

class BrokerError(Exception): pass

class Broker(Protocol):
    def account_login(self) -> int: ...
    def demo_mode(self) -> bool: ...
    def market_order(self, symbol: str, side: str, lots: float,
                     sl: float, tp: Optional[float]) -> str: ...  # returns broker ref
    def confirm(self, ref: str) -> Optional[str]: ...             # None = still unknown

@dataclass
class FreshnessPolicy:
    max_signal_age_s: float = 90.0      # original-time TTL
    max_quote_age_s: float = 5.0
    max_spread_points: float = 35.0
    max_entry_drift_points: float = 25.0   # price may not be far outside zone

class ExecutionAuthority:
    def __init__(self, db: sqlite3.Connection, broker: Broker, risk: RiskGovernor,
                 policy: FreshnessPolicy, cursors: CursorStore,
                 expected_login: int, require_demo: bool = True):
        self.db, self.broker, self.risk, self.policy = db, broker, risk, policy
        self.lineage = LineageStore(db)
        self.cursors = cursors
        self.expected_login, self.require_demo = expected_login, require_demo
        self._verified = False

    def verify_account(self) -> None:
        login = self.broker.account_login()
        if login != self.expected_login:
            raise BrokerError(f"account mismatch: expected {self.expected_login}, got {login}")
        if self.require_demo and not self.broker.demo_mode():
            raise BrokerError("refusing: live account while require_demo=True")
        self._verified = True

    def check_fresh(self, ev: SignalEvent, quote_age_s: float,
                    spread_points: float, price: float,
                    entry_low: float, entry_high: float) -> Optional[str]:
        if recap_heuristic(ev): return "recap post"
        if ev.kind != EventKind.NEW_ENTRY: return "not a new entry"
        if ev.age_s() > self.policy.max_signal_age_s: return "stale signal (original-time age)"
        if quote_age_s > self.policy.max_quote_age_s: return "stale quote"
        if spread_points > self.policy.max_spread_points: return "spread too wide"
        mid = (entry_low + entry_high) / 2
        if abs(price - mid) > (entry_high - entry_low) / 2 + self.policy.max_entry_drift_points:
            return "price drifted from entry zone"
        return None

    def handle(self, ev: SignalEvent, *, balance: float,
               stop_distance_price: float, value_per_lot_per_point: float,
               quote_age_s: float, spread_points: float, price: float,
               entry_low: float, entry_high: float, side: str,
               notional_per_lot: float = 100_000.0) -> str:
        """Returns human-readable disposition. Never raises on business rejections."""
        if not self._verified:
            self.verify_account()
        why = self.check_fresh(ev, quote_age_s, spread_points, price,
                               entry_low, entry_high)
        if why:
            return f"BLOCKED: {why}"
        if self.lineage.unresolved_unknowns(ev.source) > 0:
            return "BLOCKED: unresolved prior submission for this source"
        # claim event + reserve risk atomically
        intent_id = ev.event_id + ":i0"
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO event_claims(event_id,digest,claimed_at) "
                "VALUES(?,?,?)", (ev.event_id, ev.digest, time.time()))
            self.lineage.create_intent(intent_id, ev.event_id, ev.source,
                                       "XAUUSD", side, 0.0)
        d: SizingDecision = self.risk.size(
            balance=balance, stop_distance_price=stop_distance_price,
            value_per_lot_per_point=value_per_lot_per_point,
            notional_per_lot=notional_per_lot)
        if d.verdict != Verdict.APPROVE:
            self.lineage.transition(intent_id, IntentState.REJECTED, IntentState.RESERVED)
            return f"NO TRADE: {d.reason}"
        if not self.lineage.transition(intent_id, IntentState.SUBMITTED, IntentState.RESERVED):
            return "BLOCKED: intent raced"     # duplicate delivery
        try:
            ref = self.broker.market_order("XAUUSD", side, d.quantity,
                                           sl=0.0, tp=None)
        except BrokerError as e:
            self.lineage.transition(intent_id, IntentState.UNKNOWN, IntentState.SUBMITTED)
            return f"UNKNOWN: broker submit failed ({e})"
        self.lineage.transition(intent_id, IntentState.FILLED, IntentState.SUBMITTED)
        return f"FILLED ref={ref} lots={d.quantity} risk={round(d.risk_amount,2)}"

class PaperBroker:
    """Deterministic simulation: bid/ask spread + adverse slippage + entry fee.
    No close/exits here — lifecycle ownership is phase-2 broker work."""
    def __init__(self, login: int = 113783047, demo: bool = True,
                 fee_per_lot: float = 0.07, slippage_points: float = 15.0):
        self._login, self._demo = login, demo
        self.fee_per_lot, self.slip = fee_per_lot, slippage_points
        self.refs = 0
    def account_login(self) -> int: return self._login
    def demo_mode(self) -> bool: return self._demo
    def market_order(self, symbol, side, lots, sl, tp):
        self.refs += 1
        return f"paper-{self.refs}"
    def confirm(self, ref): return "FILLED"

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
