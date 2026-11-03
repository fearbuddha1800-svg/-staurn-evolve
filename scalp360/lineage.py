"""Signal -> intent -> order -> position lineage.
Fixes P0: updates must never touch positions by symbol/side alone.
Every mutation is bound to (source, message_id, intent_id). Original R is immutable.
"""
from __future__ import annotations
import sqlite3, time, json
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class IntentState(str, Enum):
    RESERVED = "RESERVED"     # risk reserved, order not yet sent
    SUBMITTED = "SUBMITTED"   # sent to broker, outcome unknown
    FILLED    = "FILLED"
    REJECTED  = "REJECTED"
    UNKNOWN   = "UNKNOWN"     # submission outcome never confirmed -> blocks re-entry

class LineageStore:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS intents(
          intent_id TEXT PRIMARY KEY, event_id TEXT NOT NULL, source TEXT NOT NULL,
          symbol TEXT NOT NULL, side TEXT NOT NULL, state TEXT NOT NULL,
          risk_amount REAL NOT NULL, original_r REAL NOT NULL,
          created_at REAL NOT NULL, meta TEXT DEFAULT '{}');
        CREATE TABLE IF NOT EXISTS positions(
          position_key TEXT PRIMARY KEY, intent_id TEXT NOT NULL, ticket TEXT,
          symbol TEXT NOT NULL, side TEXT NOT NULL, state TEXT NOT NULL,
          original_r REAL NOT NULL, opened_at REAL);
        """)

    def create_intent(self, intent_id: str, event_id: str, source: str,
                      symbol: str, side: str, risk_amount: float) -> None:
        """Atomically claim the event and reserve risk. Caller runs inside
        the same transaction as the event-claim insert (see executor)."""
        self.db.execute(
            "INSERT OR IGNORE INTO intents VALUES(?,?,?,?,?,?,?,?,?,?)",
            (intent_id, event_id, source, symbol, side, IntentState.RESERVED.value,
             risk_amount, risk_amount, time.time(), '{}'))

    def transition(self, intent_id: str, to: IntentState,
                   expect: Optional[IntentState] = None) -> bool:
        cur = self.db.execute("SELECT state FROM intents WHERE intent_id=?",
                              (intent_id,)).fetchone()
        if not cur:
            return False
        if expect and cur[0] != expect.value:
            return False     # stale writer lost the race -> refuse
        self.db.execute("UPDATE intents SET state=? WHERE intent_id=?",
                        (to.value, intent_id))
        return True

    def bind_position(self, position_key: str, intent_id: str, ticket: str,
                      symbol: str, side: str) -> bool:
        """Position keys are ticket-scoped. Refuses to bind an intent that is
        not FILLED, or a position_key already claimed by another intent."""
        row = self.db.execute("SELECT state,symbol,side FROM intents WHERE intent_id=?",
                              (intent_id,)).fetchone()
        if not row or row[0] != IntentState.FILLED.value:
            return False
        if (row[1], row[2]) != (symbol, side):
            return False     # symbol/side mismatch -> never link
        try:
            self.db.execute(
                "INSERT INTO positions VALUES(?,?,?,?,?,?,?,?)",
                (position_key, intent_id, ticket, symbol, side, "OPEN",
                 self.original_r(intent_id), time.time()))
            return True
        except sqlite3.IntegrityError:
            return False     # position already bound elsewhere

    def original_r(self, intent_id: str) -> float:
        row = self.db.execute("SELECT original_r FROM intents WHERE intent_id=?",
                              (intent_id,)).fetchone()
        return float(row[0]) if row else 0.0

    def unresolved_unknowns(self, source: str) -> int:
        """SUBMITTED intents older than N minutes with no terminal state block
        new entries from that source (crash safety)."""
        row = self.db.execute(
            "SELECT COUNT(*) FROM intents WHERE source=? AND state IN (?,?)",
            (source, IntentState.SUBMITTED.value, IntentState.UNKNOWN.value)).fetchone()
        return int(row[0])

    def update_position_via_signal(self, position_key: str, event_id: str) -> bool:
        """The ONLY sanctioned update path: caller must resolve event_id ->
        intent_id -> position_key first. Positions are never selected by
        symbol/side for automated updates."""
        row = self.db.execute(
            "SELECT 1 FROM positions p JOIN intents i ON p.intent_id=i.intent_id "
            "WHERE p.position_key=? AND i.event_id=?", (position_key, event_id)).fetchone()
        return row is not None
