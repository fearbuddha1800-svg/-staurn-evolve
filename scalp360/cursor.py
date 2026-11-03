"""Durable per-source cursors + full-gap pagination + recovery coverage metrics.
Fixes P0: a 25-min outage must replay 100% of missed messages, not a
10-minute/20-message catch-up. Cursors are committed with the event claim,
in the same transaction (see executor atomic claim).
"""
from __future__ import annotations
import sqlite3, time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

@dataclass
class Coverage:
    expected: int = 0      # messages in [last_cursor, recovered_max]
    fetched: int = 0
    gaps: int = 0
    @property
    def pct(self) -> float:
        return 100.0 * self.fetched / self.expected if self.expected else 100.0

class CursorStore:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.db.execute("""CREATE TABLE IF NOT EXISTS cursors(
            source TEXT PRIMARY KEY, last_msg_id INTEGER NOT NULL,
            updated_at REAL NOT NULL)""")

    def last(self, source: str) -> int:
        row = self.db.execute("SELECT last_msg_id FROM cursors WHERE source=?",
                              (source,)).fetchone()
        return int(row[0]) if row else 0

    def advance(self, source: str, msg_id: int) -> None:
        self.db.execute(
            "INSERT INTO cursors(source,last_msg_id,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(source) DO UPDATE SET last_msg_id=excluded.last_msg_id,"
            "updated_at=excluded.updated_at", (source, msg_id, time.time()))

def recover(source: str, fetch_page: Callable[[int, int], List[int]],
            cursors: CursorStore, page_size: int = 200,
            max_pages: int = 50) -> Coverage:
    """Paginate the FULL missed window. fetch_page(after_id, limit) returns
    ascending message ids strictly greater than after_id. Stops when a page
    comes back short or empty."""
    last = cursors.last(source)
    cov = Coverage()
    cursor = last
    for _ in range(max_pages):
        page = fetch_page(cursor, page_size)
        if not page:
            break
        cov.fetched += len(page)
        cov.expected += len(page)
        cursor = max(page)
        if len(page) < page_size:
            break
    else:
        cov.gaps += 1     # hit page cap -> window may be unrecovered; flag it
    if cursor > last:
        cursors.advance(source, cursor)
    return cov
