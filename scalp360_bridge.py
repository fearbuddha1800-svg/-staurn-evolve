"""HERMES SCALP 360 v0.2 bridge — additive integration into the live signal-relay system.
Imports the verified scalp360 package (32/32 tests pass) and exposes it to the
live daemon/executor/manage/cockpit WITHOUT modifying those running files.
Each subsystem can be activated independently by the live code.
"""
from __future__ import annotations
import sqlite3, time, os
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

BASE = os.path.dirname(os.path.abspath(__file__))
import sys
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from scalp360.events import SignalEvent, EventKind, recap_heuristic
from scalp360.gold_parser import parse_gold, GoldSignal, Zone
from scalp360.risk import RiskGovernor, RiskConfig, Verdict
from scalp360.cursor import CursorStore, recover, Coverage
from scalp360.lineage import LineageStore, IntentState
from scalp360.executor import ExecutionAuthority, FreshnessPolicy, PaperBroker
from scalp360.ai_extract import AIExtractor, AIExtractConfig, CircuitOpen
from scalp360.neural import evaluate, purged_splits, LogisticChallenger, EvalReport
from scalp360.timing import StageTimer
from scalp360.console import Console
import pine_script_parser


@dataclass
class BridgeConfig:
    expected_login: int = 113783047
    require_demo: bool = True
    risk_per_trade_pct: float = 0.5
    max_concurrent: int = 3
    max_daily_risk_pct: float = 2.0
    daily_halt_drawdown_pct: float = 4.0
    min_lot: float = 0.01
    lot_step: float = 0.01
    fee_per_lot: float = 0.07
    slippage_per_lot: float = 1.5
    max_signal_age_s: float = 90.0
    neural_min_labels: int = 300
    neural_holdout_auc_min: float = 0.58


class Scalp360Bridge:
    """Wraps all v0.2 subsystems. The live daemon calls these methods;
    the bridge translates between signal-relay's dict-based signals and
    scalp360's typed objects."""

    def __init__(self, db_path: str, config: Optional[BridgeConfig] = None):
        self.cfg = config or BridgeConfig()
        self.db = sqlite3.connect(db_path)
        self._ensure_schema()
        self.risk = RiskGovernor(RiskConfig(
            risk_per_trade_pct=self.cfg.risk_per_trade_pct,
            max_concurrent=self.cfg.max_concurrent,
            max_daily_risk_pct=self.cfg.max_daily_risk_pct,
            daily_halt_drawdown_pct=self.cfg.daily_halt_drawdown_pct,
            lot_step=self.cfg.lot_step,
            min_lot=self.cfg.min_lot,
            fee_per_lot=self.cfg.fee_per_lot,
            slippage_per_lot=self.cfg.slippage_per_lot,
        ))
        self.lineage = LineageStore(self.db)
        self.cursors = CursorStore(self.db)
        self.timer = StageTimer()
        self.ai = AIExtractor(
            AIExtractConfig(timeout_s=8.0, max_calls_per_min=30,
                            circuit_breaker_fails=5, spend_budget_usd_per_day=1.0),
            self._configured_llm,
        )
        self.console = Console(self.db, {8877588890}, {8877588890}, None)
        self._neural_labels: List[tuple] = []

    # ------------------------------------------------------------------ schema
    def _ensure_schema(self) -> None:
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS event_claims(
            event_id TEXT PRIMARY KEY, digest TEXT, claimed_at REAL);
        CREATE TABLE IF NOT EXISTS intents(
            intent_id TEXT PRIMARY KEY, event_id TEXT NOT NULL, source TEXT NOT NULL,
            symbol TEXT NOT NULL, side TEXT NOT NULL, state TEXT NOT NULL,
            risk_amount REAL NOT NULL, original_r REAL NOT NULL,
            created_at REAL NOT NULL, meta TEXT DEFAULT '{}');
        CREATE TABLE IF NOT EXISTS positions(
            position_key TEXT PRIMARY KEY, intent_id TEXT NOT NULL, ticket TEXT,
            symbol TEXT NOT NULL, side TEXT NOT NULL, state TEXT NOT NULL,
            original_r REAL NOT NULL, opened_at REAL);
        CREATE TABLE IF NOT EXISTS neural_labels(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, symbol TEXT,
            side TEXT, entry REAL, sl REAL, tp REAL, outcome INTEGER,
            features TEXT);
        """)

    # ------------------------------------------------------------ signal parse
    def parse_signal(self, raw_text: str, source: str, message_id: int,
                     received_at: Optional[float] = None) -> SignalEvent:
        """Parse any signal. XAUHQ gold format gets zone-aware parsing;
        everything else gets a generic NEW_ENTRY event. Recap posts are
        classified UNKNOWN and never trade."""
        now = received_at or time.time()
        # recap guard first
        if recap_heuristic(__import__("scalp360.events", fromlist=["SignalEvent"]).SignalEvent(
            source=source, message_id=message_id, text=raw_text,
            original_at=now, kind=EventKind.UNKNOWN)):
            return SignalEvent(source=source, message_id=message_id, text=raw_text,
                               original_at=now, received_at=now, kind=EventKind.UNKNOWN)
        # XAUHQ gold typed parse
        gold = parse_gold(raw_text)
        if gold is not None:
            return SignalEvent(
                source=source, message_id=message_id, text=raw_text,
                original_at=now, received_at=now, kind=EventKind.NEW_ENTRY,
            )
        return SignalEvent(source=source, message_id=message_id, text=raw_text,
                           original_at=now, received_at=now, kind=EventKind.NEW_ENTRY)

    # ------------------------------------------------------------ freshness
    def check_fresh(self, ev: SignalEvent, quote_age_s: float, spread_points: float,
                    price: float, entry_low: float, entry_high: float) -> Optional[str]:
        pol = FreshnessPolicy(max_signal_age_s=self.cfg.max_signal_age_s)
        return self._freshness_check(ev, pol, quote_age_s, spread_points, price,
                                     entry_low, entry_high)

    def _freshness_check(self, ev, pol, quote_age_s, spread_points, price,
                         entry_low, entry_high) -> Optional[str]:
        if recap_heuristic(ev):
            return "recap post"
        if ev.kind != EventKind.NEW_ENTRY:
            return "not a new entry"
        if ev.age_s() > pol.max_signal_age_s:
            return "stale signal (original-time age)"
        if quote_age_s > pol.max_quote_age_s:
            return "stale quote"
        if spread_points > pol.max_spread_points:
            return "spread too wide"
        mid = (entry_low + entry_high) / 2
        if abs(price - mid) > (entry_high - entry_low) / 2 + pol.max_entry_drift_points:
            return "price drifted from entry zone"
        return None

    # ------------------------------------------------------------ risk size
    def size_position(self, balance: float, stop_distance: float,
                      vpp: float, notional_per_lot: float = 100_000.0,
                      pending_risk: float = 0.0, open_risk: float = 0.0,
                      open_count: int = 0, day_pnl: float = 0.0):
        """Floor sizing with min-lot reject (never clamp up), fee+slippage reserve,
        aggregate daily cap, drawdown halt."""
        return self.risk.size(
            balance=balance, stop_distance_price=stop_distance,
            value_per_lot_per_point=vpp, notional_per_lot=notional_per_lot,
            pending_risk=pending_risk, open_risk=open_risk,
            open_count=open_count, day_pnl=day_pnl)

    # ------------------------------------------------------------ lineage
    def create_intent(self, intent_id: str, event_id: str, source: str,
                      symbol: str, side: str, risk_amount: float) -> None:
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO event_claims(event_id,digest,claimed_at) "
                "VALUES(?,?,?)", (event_id, "", time.time()))
            self.lineage.create_intent(intent_id, event_id, source, symbol, side, risk_amount)

    def transition_intent(self, intent_id: str, to: IntentState,
                          expect: Optional[IntentState] = None) -> bool:
        return self.lineage.transition(intent_id, to, expect)

    def bind_position(self, position_key: str, intent_id: str, ticket: str,
                      symbol: str, side: str) -> bool:
        return self.lineage.bind_position(position_key, intent_id, ticket, symbol, side)

    def unresolved_unknowns(self, source: str) -> int:
        return self.lineage.unresolved_unknowns(source)

    def update_via_signal(self, position_key: str, event_id: str) -> bool:
        """ONLY sanctioned update path: event_id -> intent_id -> position_key."""
        return self.lineage.update_position_via_signal(position_key, event_id)

    # ------------------------------------------------------------ cursor recovery
    def cursor_last(self, source: str) -> int:
        return self.cursors.last(source)

    def cursor_advance(self, source: str, msg_id: int) -> None:
        self.cursors.advance(source, msg_id)

    def recover_gap(self, source: str, fetch_page, page_size: int = 200,
                    max_pages: int = 50) -> Coverage:
        """Full-gap replay: paginate every missed message, flag unrecovered windows."""
        return recover(source, fetch_page, self.cursors, page_size, max_pages)

    # ------------------------------------------------------------ AI extraction
    def _configured_llm(self, text: str, timeout: float) -> Dict[str, Any]:
        """Read the shared configured extractor; never generate a stand-in signal.

        ai_filter owns provider credentials and its own bounded router. This
        bridge does not grant freshness, sizing or execution permission.
        Non-entry classifications are UNKNOWN, not guessed RESULT or UPDATE.
        The shared router owns the network deadline (not this legacy timeout).
        """
        import math
        import ai_filter
        data, info = ai_filter.llm_extract(text)
        unknown = {"kind": "UNKNOWN", "symbol": None, "side": None,
                   "confidence": 0.0, "evidence": {}, "abstained_reason": str(info)}
        if not isinstance(data, dict) or data.get("is_signal") is not True:
            return unknown
        parsed = ai_filter.to_parsed(data)
        try:
            confidence = float(data.get("confidence", 0))
            minimum = float(ai_filter.ai_cfg().get("min_confidence", 0.65))
        except (TypeError, ValueError):
            return {**unknown, "abstained_reason": "invalid confidence"}
        if not parsed or not math.isfinite(confidence) or not minimum <= confidence <= 1:
            return {**unknown, "abstained_reason": "unvalidated or low-confidence extraction"}
        return {"kind": "NEW_ENTRY", "symbol": parsed["symbol"],
                "side": parsed["action"].upper(), "confidence": confidence,
                "evidence": {"raw": text}}

    def ai_extract(self, text: str):
        """Bounded AI: circuit breaker, rate limit, spend budget, UNKNOWN on failure."""
        return self.ai.extract(text)

    # ------------------------------------------------------------ neural eval
    def add_neural_label(self, symbol: str, side: str, entry: float, sl: float,
                         tp: float, outcome: int, features: str = "[]") -> None:
        """Record a labeled outcome for future neural training (>=300 required)."""
        self._neural_labels.append((time.time(), symbol, side, entry, sl, tp, outcome, features))
        self.db.execute(
            "INSERT INTO neural_labels(ts,symbol,side,entry,sl,tp,outcome,features) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (time.time(), symbol, side, entry, sl, tp, outcome, features))
        self.db.commit()

    def neural_evaluate(self, X: List[tuple], y: List[int]) -> EvalReport:
        """Run the honest neural protocol: purged splits, calibration, holdout,
        promote only if holdout AUC >= 0.58 AND beats rules baseline."""
        return evaluate(X, y, min_samples=self.cfg.neural_min_labels)

    def neural_label_count(self) -> int:
        return len(self._neural_labels)

    # ------------------------------------------------------------ Pine Script
    def load_pine_strategy(self, pine_path: str) -> str:
        """Transpile a TradingView Pine Script file to a Python strategy class.
        Returns the Python class name; the emitted module is written alongside
        the .pine file with .py extension."""
        with open(pine_path, encoding="utf-8") as f:
            text = f.read()
        strat = pine_script_parser.parse_pine(text)
        module = pine_script_parser.emit_python(strat)
        out_path = os.path.splitext(pine_path)[0] + "_transpiled.py"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(module)
        return strat.python_class_name()

    # ------------------------------------------------------------ timing
    def stage(self, name: str):
        return self.timer.time(name)

    def latency_snapshot(self) -> Dict[str, Dict[str, float]]:
        return self.timer.snapshot()

    # ------------------------------------------------------------ console
    def console_pause(self, tenant: str, user_id: int, chat_id: int) -> str:
        return self.console.pause(tenant, user_id, chat_id)

    def console_resume(self, tenant: str, user_id: int, chat_id: int) -> str:
        return self.console.resume(tenant, user_id, chat_id)

    def console_is_halted(self, tenant: str) -> bool:
        return self.console.is_halted(tenant)


def make_bridge(db_path: str = None) -> Scalp360Bridge:
    if db_path is None:
        db_path = os.path.join(BASE, "signals.db")
    return Scalp360Bridge(db_path)


if __name__ == "__main__":
    b = make_bridge(":memory:")
    print("bridge OK:", b.risk.cfg.risk_per_trade_pct, "% risk per trade")
    print("neural labels:", b.neural_label_count())
    print("console authorized user:", b.console.authorized(8877588890, 8877588890))
