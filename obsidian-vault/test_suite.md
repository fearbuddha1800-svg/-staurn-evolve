---
slug: test_suite
type: note
graph: gitnexus
---

"""Acceptance test: 9 signal samples + 6 news-filter cases -> strict field
assertions. Exit 0 = all pass. The news cases stub module paths (calendar,
config, DB, HALT, daemon log) into a temp dir so the LIVE ledger, config and
calendar are never touched; execute() is always called with dry_run=True so
no order can ever be sent. N5/N6 attach to the running MT5 terminal (read-only
guards + dry run), mirroring how the live relay runs."""
import sys

import parser as p

CASES = [
    ("S1 classic multi-line", "BUY XAUUSD @ 2650.5\nSL: 2640\nTP1: 2660 TP2: 2675",
     {"is_signal": True, "parse_ok": True, "action": "buy", "symbol": "XAUUSD",
      "order_type": "market", "entry": 2650.5, "sl": 2640.0, "tps": [2660.0, 2675.0]}),
    ("S2 emoji alias market", "\U0001f7e1 GOLD SELL NOW 2650 sl 2660 tp 2640",
     {"is_signal": True, "parse_ok": True, "action": "sell", "symbol": "XAUUSD",
      "order_type": "market", "entry": 2650.0, "sl": 2660.0, "tps": [2640.0]}),
    ("S3 pending slash-pair", "sell limit EUR/USD 1.0850 SL 1.0900 targets 1.0750 / 1.0700",
     {"is_signal": True, "parse_ok": True, "action": "sell", "symbol": "EURUSD",
      "order_type": "limit", "entry": 1.085, "sl": 1.09, "tp_contains": 1.075}),
    ("S4 crypto", "BTC buy 62000 SL 61000 TP 64000",
     {"is_signal": True, "parse_ok": True, "action": "buy", "symbol": "BTCUSD",
      "order_type": "market", "entry": 62000.0, "sl": 61000.0, "tps": [64000.0]}),
    ("S5 chatter no digits", "Good morning traders, gold looks bullish today!",
     {"is_signal": False}),
    ("S6 analysis chatter", "EurUsd is at 1.0850, resistance at 1.0900",
     {"is_signal": False}),
    ("S7 market no entry", "BUY NOW GBPUSD sl 1.26 tp 1.28",
     {"is_signal": True, "parse_ok": True, "action": "buy", "symbol": "GBPUSD",
      "order_type": "market", "entry": "market", "sl": 1.26, "tps": [1.28]}),
    ("S8 manage", "Close XAUUSD now",
     {"is_signal": True, "parse_ok": False, "action": "manage"}),
    ("S9 index alias", "US30 SELL @ 43250 SL 43350 TP 43150",
     {"is_signal": True, "parse_ok": True, "action": "sell", "symbol": "US30",
      "order_type": "market", "entry": 43250.0, "sl": 43350.0, "tps": [43150.0]}),
]

fails = 0
for name, sample, exp in CASES:
    r = p.parse_signal(sample)
    problems = []
    for k, want in exp.items():
        if k == "tp_contains":
            if want not in (r.get("tps") or []):
                problems.append(f"tps {r.get('tps')} missing {want}")
            continue
        got = r.get(k)
        if got != want:
            problems.append(f"{k}: got {got!r} want {want!r}")
    if problems:
        fails += 1
        print(f"FAIL {name}: " + "; ".join(problems))
        print(f"     full: {({k: v for k, v in r.items() if k != 'raw'})}")
    else:
        print(f"PASS {name}")

print()
print("-- news filter (news_fetcher + executor gate) --")
import io
import json
import os
import shutil
import sqlite3
import tempfile
import time as _t
from datetime import datetime, timedelta, timezone

import executor
import news_fetcher

news_fails = 0


def _case(name, fn):
    global news_fails
    try:
        fn()
        print(f"PASS {name}")
    except AssertionError as e:
        news_fails += 1
        print(f"FAIL {name}: {e}")
    except Exception as e:  # noqa: BLE001
        news_fails += 1
        print(f"FAIL {name}: {type(e).__name__}: {e}")


TMP = tempfile.mkdtemp(prefix="news_test_",
                       dir=os.path.dirname(os.path.abspath(__file__)))
TMP_CAL = os.path.join(TMP, "news_calendar.json")
TMP_CFG = os.path.join(TMP, "config.json")
TMP_DB = os.path.join(TMP, "signals.db")
TMP_LOG = os.path.join(TMP, "daemon.log")
TMP_HALT = os.path.join(TMP, "HALT")

GATE_CFG = {"news_filter": {"enabled": True, "pre_minutes": 5, "post_minutes": 3},
            "risk": {"max_trades_per_day": 20, "max_open_positions": 99,
                     "min_free_margin_pct": 0, "require_sl": True, "allowed_symbols": []}}
with open(TMP_CFG, "w", encoding="utf-8") as f:
    json.dump(GATE_CFG, f)

_SAVED = (news_fetcher.CALENDAR, news_fetcher.DAEMON_LOG, news_fetcher._urlopen,
          news_fetcher._sleep, executor.CONFIG, executor.DB, executor.HALT_FILE)


def _restore():
    (news_fetcher.CALENDAR, news_fetcher.DAEMON_LOG, news_fetcher._urlopen,
     news_fetcher._sleep, executor.CONFIG, executor.DB, executor.HALT_FILE) = _SAVED


class _FakeResp:
    def __init__(self, data):
        self._buf = io.BytesIO(data)

    def read(self):
        return self._buf.read()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def n1():
    """Bad JSON from the feed: refresh fails, existing calendar untouched."""
    with open(TMP_CAL, "w", encoding="utf-8") as f:
        f.write('[{"dt_utc": "2999-01-01T00:00:00+00:00", "title": "sentinel", "impact": "High"}]')
    before = open(TMP_CAL, encoding="utf-8").read()
    news_fetcher.CALENDAR = TMP_CAL
    news_fetcher.DAEMON_LOG = TMP_LOG
    news_fetcher._urlopen = lambda req, timeout=None: _FakeResp(b'{"title": "broken json')
    ok, n = news_fetcher.refresh()
    assert ok is False and n == 0, f"refresh returned {(ok, n)} for bad JSON"
    assert open(TMP_CAL, encoding="utf-8").read() == before, "calendar overwritten after bad JSON"


def n2():
    """Network dead: 3 retries, then failure with calendar kept."""
    before = open(TMP_CAL, encoding="utf-8").read()
    hits = {"n": 0}

    def _boom(req, timeout=None):
        hits["n"] += 1
        raise OSError("test network down")

    news_fetcher._urlopen = _boom
    news_fetcher._sleep = lambda s: None
    ok, n = news_fetcher.refresh()
    assert ok is False, "refresh must fail when every attempt errors"
    assert hits["n"] == 3, f"expected 3 attempts, got {hits['n']}"
    assert open(TMP_CAL, encoding="utf-8").read() == before, "calendar overwritten after failed fetch"


_NOW_FIXED = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
_FEED = [
    {"title": "Fed Interest Rate Decision", "country": "USD",
     "date": "2026-10-16T18:00:00+00:00", "impact": "High"},
    {"title": "Core CPI m/m", "country": "USD",
     "date": "2026-10-17T08:30:00-04:00", "impact": "High"},  # offset form -> 12:30Z
    {"title": "Unemployment Claims", "country": "USD",
     "date": "2026-10-16T12:30:00Z", "impact": "Medium"},  # not High -> dropped
    {"title": "ECB Rate Decision", "country": "EUR",
     "date": "2026-10-16T13:00:00+00:00", "impact": "High"},  # not USD -> dropped
    {"title": "CPI y/y (already out)", "country": "USD",
     "date": "2026-10-16T10:00:00+00:00", "impact": "High"},  # past -> purged
    {"event": "Drifted Schema Event", "currency": "USD",
     "datetime": "2026-10-16T20:00:00+00:00", "importance": "High"},  # drift keys -> kept
    {"title": "Broken date", "country": "USD", "date": "not-a-date", "impact": "High"},
]


def n3():
    """Filter keeps only High USD, purges the past, tolerates key drift."""
    news_fetcher._urlopen = lambda req, timeout=None: _FakeResp(json.dumps(_FEED).encode())
    ok, n = news_fetcher.refresh(now=_NOW_FIXED)
    assert ok is True and n == 3, f"refresh returned {(ok, n)}"
    evs = news_fetcher.load_events()
    titles = [e["title"] for e in evs]
    assert titles == ["Fed Interest Rate Decision", "Drifted Schema Event", "Core CPI m/m"], titles
    assert all(e["impact"] == "High" for e in evs), evs
    assert all(str(e["dt_utc"]).endswith("+00:00") for e in evs), "dt_utc must be UTC ISO"


def n4():
    """Window math: pre/post edges inclusive, disabled filter never blocks."""
    now = datetime.now(timezone.utc)
    ev2m = [{"dt_utc": (now + timedelta(minutes=2)).isoformat(),
             "title": "Near Event", "impact": "High"}]
    ev2h = [{"dt_utc": (now + timedelta(hours=2)).isoformat(),
             "title": "Far Event", "impact": "High"}]
    r = news_fetcher.block_reason(GATE_CFG, now, ev2m)
    assert r and "Near Event" in r, f"event 2min away must block: {r!r}"
    assert news_fetcher.block_reason(GATE_CFG, now, ev2h) is None, "event 2h away must not block"
    off = {"news_filter": {"enabled": False, "pre_minutes": 5, "post_minutes": 3}}
    assert news_fetcher.block_reason(off, now, ev2m) is None, "disabled filter must never block"
    edge = [{"dt_utc": (now + timedelta(minutes=5)).isoformat(),
             "title": "Edge Event", "impact": "High"}]
    assert news_fetcher.block_reason(GATE_CFG, now, edge), "now at event-pre must block"
    late = [{"dt_utc": (now - timedelta(minutes=4)).isoformat(),
             "title": "Late Event", "impact": "High"}]
    assert news_fetcher.block_reason(GATE_CFG, now, late) is None, "now past event+post must not block"


def _exec_setup(event_dt):
    """Point executor + news_fetcher at the temp calendar/config/DB/LOG/HALT."""
    news_fetcher.CALENDAR = TMP_CAL
    news_fetcher.DAEMON_LOG = TMP_LOG
    executor.CONFIG = TMP_CFG
    executor.DB = TMP_DB
    executor.HALT_FILE = TMP_HALT
    with open(TMP_CAL, "w", encoding="utf-8") as f:
        json.dump([{"dt_utc": event_dt.astimezone(timezone.utc).isoformat(),
                    "title": "NFP Test Event", "impact": "High"}], f)


def _sample_signal():
    tick = executor.mt5.symbol_info_tick("XAUUSD")
    px = tick.bid if tick else 4000.0  # SL/TP far from any plausible gold price
    return {"is_signal": True, "parse_ok": True, "action": "buy", "symbol": "XAUUSD",
            "order_type": "market", "entry": "market",
            "sl": round(px - 50.0, 2), "tps": [round(px + 100.0, 2)]}


def n5():
    """Event 2 minutes out: execute() skips with the ledger skip-row."""
    _exec_setup(datetime.now(timezone.utc) + timedelta(minutes=2))
    mid = f"testsuite-news-block-{int(_t.time())}"
    res = executor.execute(_sample_signal(), msg_id=mid, lot=0.01, dry_run=True)
    assert res.get("status") == "skipped_news_window", f"got {res.get('status')}: {res.get('detail')}"
    assert "NFP Test Event" in (res.get("detail") or ""), res.get("detail")
    con = sqlite3.connect(TMP_DB)
    rows = con.execute("SELECT status, ticket FROM trades WHERE msg_id=?", (mid,)).fetchall()
    con.close()
    assert rows and rows[0] == ("skipped_news_window", 0), f"ledger skip row: {rows}"


def n6():
    """Event 2 hours out: normal flow - the filter stays transparent."""
    _exec_setup(datetime.now(timezone.utc) + timedelta(hours=2))
    res = executor.execute(_sample_signal(), msg_id=f"testsuite-news-far-{int(_t.time())}",
                           lot=0.01, dry_run=True)
    st = res.get("status")
    assert st != "skipped_news_window", f"news filter blocked a far event: {res.get('detail')}"
    print(f"     (far-event flow reached: {st}: {res.get('detail') or 'guards clean'})")


try:
    _case("N1 fetcher keeps calendar on bad JSON", n1)
    _case("N2 fetcher retries 3x, keeps calendar on total failure", n2)
    _case("N3 feed filter: High USD only, past purged, schema drift ok", n3)
    _case("N4 gate window math (pre/post edges, disable, 2h away)", n4)
    _case("N5 execute() -> skipped_news_window for event 2min out", n5)
    _case("N6 execute() normal flow for event 2h out", n6)
finally:
    _restore()
    shutil.rmtree(TMP, ignore_errors=True)

fails += news_fails
print()
print("ALL PASS" if fails == 0 else f"{fails} FAILURE(S)")
sys.exit(0 if fails == 0 else 1)

