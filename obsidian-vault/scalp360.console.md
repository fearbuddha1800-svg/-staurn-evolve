---
slug: scalp360.console
type: note
graph: gitnexus
---

"""Idempotent Telegram console actions.
Claim-before-send + ack-after-send so an uncertain delivery never replays
into a second order action. Pause propagates to the real core halt when wired.
"""
from __future__ import annotations
import sqlite3, time, hashlib
from typing import Callable, Optional, Set

class Console:
    def __init__(self, db: sqlite3.Connection, allowed_user_ids: Set[int],
                 allowed_chat_ids: Set[int], core_set_halt: Optional[Callable[[str,bool],bool]]=None):
        self.db = db
        self.allowed_u, self.allowed_c = allowed_user_ids, allowed_chat_ids
        self.core_set_halt = core_set_halt
        self.halted: Set[str] = set()
        self.db.execute("""CREATE TABLE IF NOT EXISTS update_claims(
            claim_id TEXT PRIMARY KEY, action TEXT NOT NULL, claimed_at REAL)""")

    def authorized(self, user_id: int, chat_id: int) -> bool:
        return user_id in self.allowed_u and chat_id in self.allowed_c

    def _claim(self, action: str, payload: str) -> str:
        cid = hashlib.sha256(f"{action}|{payload}".encode()).hexdigest()[:16]
        try:
            with self.db:
                self.db.execute("INSERT INTO update_claims VALUES(?,?,?)",
                                (cid, action, time.time()))
            return cid
        except sqlite3.IntegrityError:
            return ""     # already claimed -> do not re-execute side effects

    def pause(self, tenant: str, user_id: int, chat_id: int) -> str:
        if not self.authorized(user_id, chat_id):
            return "unauthorized"
        cid = self._claim("pause", tenant)
        if not cid:
            return "already processed"
        ok = self.core_set_halt(tenant, True) if self.core_set_halt else None
        if ok is False:
            return "core halt failed - local latch only"
        self.halted.add(tenant)
        return "paused"

    def resume(self, tenant: str, user_id: int, chat_id: int) -> str:
        if not self.authorized(user_id, chat_id):
            return "unauthorized"
        if self.core_set_halt:
            self.core_set_halt(tenant, False)
        self.halted.discard(tenant)
        return "resumed"

    def is_halted(self, tenant: str) -> bool:
        return tenant in self.halted

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
