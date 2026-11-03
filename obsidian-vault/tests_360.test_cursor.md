---
slug: tests_360.test_cursor
type: note
graph: gitnexus
---

import sqlite3
from scalp360.cursor import CursorStore, recover

def _db():
    return sqlite3.connect(":memory:")

def test_full_gap_recovery():
    db = _db(); cs = CursorStore(db)
    cs.advance("t1:xauhq", 100)
    # outage: messages 101..457 exist; fetch_page returns full truth
    truth = list(range(101, 458))
    pages = {}
    for i in range(0, len(truth), 50):
        pages[truth[i]-1] = truth[i:i+50]
    def fetch(after, limit):
        return [m for m in truth if m > after][:limit]
    cov = recover("t1:xauhq", fetch, cs, page_size=50)
    assert cs.last("t1:xauhq") == 457
    assert cov.fetched == len(truth) and cov.gaps == 0
    assert cov.pct == 100.0

def test_coverage_flags_page_cap():
    db = _db(); cs = CursorStore(db)
    truth = list(range(1, 5000))
    def fetch(after, limit): return [m for m in truth if m > after][:limit]
    cov = recover("s", fetch, cs, page_size=200, max_pages=3)
    assert cov.gaps == 1 and cov.fetched == 600   # flagged: window unrecovered

