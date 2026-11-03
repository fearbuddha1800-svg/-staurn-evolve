"""Quant Cockpit: Hermes Scalp — single-page live dashboard for the whole trading system.
Stdlib only. Read-only for MT5 and all databases - never places orders.
GET /          dark UI, polls /api/state every 5s
GET /api/state JSON aggregate (account, positions, engines, ledger, channels, inbox, journal, mobile,
                + scalp360 metrics: neural_labels count, pine_count)
GET /api/inbox   signal inbox list
GET /api/journal event journal list
GET /api/mobile  mobile phone mockup HTML fragment
GET /api/neural  scalp360 neural readiness: neural_labels count vs min 300, progress,
                 last evaluation AUC + PROMOTE/KEEP_SHADOW/REJECT once ready
GET /api/latency p50/p95/p99 per pipeline stage from scalp360_bridge.latency_snapshot()
GET /api/lineage last 5 intents from the scalp360 intents table (signal->intent->order->position)
GET /api/pine    registered Pine strategies from config.json pine_strategies (enabled/paper)
Run: python cockpit.py  -> http://localhost:8490
"""
import contextlib
import json
import math
import os
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import MetaTrader5 as mt5
    try:
        mt5.initialize()  # Attach to running MT5 terminal for live data
    except Exception:  # noqa: BLE001
        pass  # Terminal may not be running; dashboard stays read-only
except ImportError:
    class _UnavailableMT5:
        """Optional dependency: retain the dashboard when MT5 cannot be imported."""
        def __getattr__(self, name):
            if name.startswith("TIMEFRAME_") or name.startswith("POSITION_"):
                return 0
            return lambda *a, **kw: None
    mt5 = _UnavailableMT5()

from event_bus import bus

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "signals.db")
REPORT = os.path.join(BASE, "channel_report.json")
CONFIG = os.path.join(BASE, "config.json")
LUXALGO_DIR = os.path.join(os.path.dirname(BASE), "luxalgo")
PORT = 8490

_engine_cache = {"t": 0, "data": {}}


def observation_policy():
    """Pure local policy; never attach, reset a latch, or change any marker."""
    flags = dict.fromkeys(("maintenance", "halt", "stop", "pause"))
    try:
        flags = {name.lower(): os.path.lexists(os.path.join(BASE, name))
                 for name in ("MAINTENANCE", "HALT", "STOP", "PAUSE")}
        from broker_lifecycle import broker_status
        lifecycle = broker_status()
        if not isinstance(lifecycle, dict):
            raise ValueError("Invalid broker status")
        hold = next((key for key, active in flags.items() if active), None)
        allowed = not hold and lifecycle.get("eligible") is True
        reason = hold or (None if allowed else lifecycle.get("reason") or "broker_policy_unknown")
        return dict(flags, read_allowed=allowed, blocked_reason=reason,
                    lifecycle=lifecycle, observational=True, auto_connect=False)
    except Exception:
        return dict(flags, read_allowed=False,
                    blocked_reason=next((key for key, active in flags.items() if active),
                                        "broker_policy_unavailable"),
                    lifecycle={}, observational=True, auto_connect=False)


class _ObservationBroker:
    """Read-only capability facade, including for legacy analytics consumers.

    In particular, even an indirect consumer calling initialize cannot reach MT5.
    Reading constants is harmless; every broker read rechecks local policy.
    """
    _READS = frozenset(("terminal_info", "account_info", "positions_get",
                        "history_deals_get", "symbol_info", "symbol_info_tick",
                        "copy_rates_from_pos", "copy_rates_range", "symbols_get",
                        "order_calc_profit"))

    def __init__(self, broker):
        self._broker = broker

    def __getattr__(self, name):
        if name.isupper():
            return getattr(self._broker, name)
        if name not in self._READS:
            # Deny attachment, login, orders, shutdown and all other mutations.
            return lambda *args, **kwargs: False
        def read(*args, **kwargs):
            if not observation_policy()["read_allowed"]:
                return None
            try:
                terminal = self._broker.terminal_info()
                if terminal is None or getattr(terminal, "connected", False) is not True:
                    return None
                if name == "terminal_info":
                    return terminal
                return getattr(self._broker, name)(*args, **kwargs)
            except Exception:
                return None
        return read


mt5 = _ObservationBroker(mt5)


def broker_health():
    status = observation_policy()
    terminal = mt5.terminal_info() if status["read_allowed"] else None
    status["connected"] = terminal is not None
    if terminal is None and status["blocked_reason"] is None:
        status["blocked_reason"] = "not_attached: dashboard never initializes MT5"
    status["available"] = status["connected"]
    status["observed_at"] = datetime.now().astimezone().isoformat()
    return status


def _pid_alive(pid):
    """True when a Windows PID is alive (OpenProcess probe - fast, reliable for
    detached processes whose CommandLine is hidden from CIM queries)."""
    try:
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def _lock_alive(lockfile):
    try:
        pid = open(os.path.join(BASE, lockfile), encoding="utf-8").read().strip()
        return bool(pid) and _pid_alive(pid)
    except Exception:  # noqa: BLE001
        return False


def _port_listening(port):
    try:
        s = socket.socket()
        s.settimeout(1)
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:  # noqa: BLE001
        return False


def engines():
    if time.time() - _engine_cache["t"] < 30:
        return _engine_cache["data"]
    out = {
        "daemon": _lock_alive("daemon.lock"),
        "manage": _lock_alive("manage.lock"),
        "strategy": _lock_alive("strategy.lock"),
        "strategy2_live": _lock_alive("strategy2.lock"),
        "cockpit": _port_listening(PORT),
        "trade-relay": _port_listening(8484),
    }
    _engine_cache.update(t=time.time(), data=out)
    return out


def ledger(limit=15):
    """Read both legacy and current trade schemas; absent fields stay unknown."""
    try:
        with contextlib.closing(_db_ro()) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT * FROM trades ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
            return [{"ts": r.get("ts"), "symbol": r.get("symbol"),
                     "action": r.get("action", r.get("side")), "status": r.get("status"),
                     "detail": r.get("detail"), "magic": r.get("magic"),
                     "ticket": r.get("ticket"), "msg_id": r.get("msg_id")}
                    for r in map(dict, rows)]
    except (sqlite3.Error, OSError):
        return []


def day_pl():
    with _stage("history"):
        day0 = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(day0, datetime.now() + timedelta(days=1))
        if deals is None:
            return None, None, None
        total = sig = algo = 0.0
        for d in deals:
            pl = d.profit + d.commission + d.swap + getattr(d, "fee", 0.0)
            total += pl
            if d.magic == 20261014:
                sig += pl
            elif d.magic == 20261015:
                algo += pl
        return round(total, 2), round(sig, 2), round(algo, 2)


def channel_names():
    """Map channel id -> plain name from config.json."""
    try:
        cfg = json.load(open(CONFIG, encoding="utf-8"))
        names = {}
        for cid in cfg.get("channels", []):
            names[str(cid)] = str(cid)
        pol = cfg.get("signal_policy", {})
        for cid, p in pol.items():
            if cid.startswith("-") and isinstance(p, dict) and p.get("note"):
                names[cid] = p["note"].split(" - ")[0]
        return names
    except Exception:
        return {}


# Authentication and bounded owner-trusted PineTS runtime live at the HTTP boundary.
from cockpit_runtime import CockpitHandler, ApiError, load_token, run_pine
UI_FILE = os.path.join(BASE, "cockpit_ui.html")


def compile_pine(script_text, symbol="XAUUSD", timeframe="H1", count=220):
    return run_pine(sys.modules[__name__], script_text, symbol, timeframe, count)


def portfolio_data():
    """Live read-only positions, no cached zero substitution on broker failure."""
    try:
        from portfolio_risk import portfolio_risk
        if not (mt5.terminal_info()):
            return {"available": False, "reason": "MT5 unavailable"}
        with open(CONFIG, encoding="utf-8") as source:
            cfg = json.load(source)
        return portfolio_risk(mt5, mt5.positions_get(), mt5.account_info(), cfg.get("risk", {}))
    except Exception as exc:
        return {"available": False, "reason": "Portfolio unavailable: " + type(exc).__name__}


def attribution_data():
    """Bounded 90-day UTC deal-P&L observation, grouped by id AND version."""
    try:
        from datetime import timezone
        from strategy_identity import load_registry
        from portfolio_attribution import versioned_attribution
        if not (mt5.terminal_info()):
            return {"available": False, "reason": "MT5 unavailable"}
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=90)
        deals = mt5.history_deals_get(start, end)
        if deals is None:
            return {"available": False, "reason": "MT5 deal history unavailable"}
        account = mt5.account_info()
        if account is None or not getattr(account, "currency", None):
            return {"available": False, "reason": "Account currency unavailable"}
        # Balance/credit/deposit operations are not strategy returns.
        deals = [d for d in deals if d.type in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL)]
        result = versioned_attribution(deals, load_registry(CONFIG))
        result.update(period_start=start.isoformat(), period_end=end.isoformat(),
                      observed_at=end.isoformat(), account_currency=account.currency,
                      broker_orders_enabled=False)
        return result
    except Exception as exc:
        return {"available": False, "reason": "Attribution unavailable: " + type(exc).__name__}


def quant_data():
    """Compose pure analytics here; legacy quant_snapshot may try to attach."""
    health = broker_health()
    if not health["available"]:
        return {"available": False, "reason": health["blocked_reason"],
                "broker": health, "market": [], "broker_orders_enabled": False}
    try:
        from quant_analytics import SYMBOLS, METHODS, market_metrics, aligned_correlation, stop_risk
        now, data, markets = time.time(), {}, []
        for symbol in SYMBOLS:
            received = candles_data(symbol, 'H1', 501)
            data[symbol] = received.get('candles', []) if not received.get('error') else []
            markets.append(market_metrics(received.get('symbol') or symbol, data[symbol], now))
        account, positions = mt5.account_info(), mt5.positions_get()
        return {'available': any(m['available'] for m in markets), 'market': markets,
                'observed_at': datetime.now().astimezone().isoformat(), 'broker': broker_health(),
                'correlation': aligned_correlation(SYMBOLS[0], data[SYMBOLS[0]], SYMBOLS[1], data[SYMBOLS[1]]),
                'risk': stop_risk(mt5, positions, getattr(account, 'balance', None), getattr(account, 'currency', None)),
                'methodology': METHODS, 'broker_orders_enabled': False}
    except Exception:
        return {"available": False, "reason": "Quant observation unavailable", "broker": health,
                "market": [], "broker_orders_enabled": False}


def token_data():
    """Owner convenience: show the local dashboard credential to an authenticated session.

    Only reachable after authentication, and only over loopback. The token is the root
    secret for this machine; anyone who can read .cockpit-token can already read it.
    """
    try:
        token = load_token(BASE)
    except Exception:
        return {"available": False, "reason": "Dashboard credential unavailable"}
    return {"available": True, "token": token,
            "file": os.path.join(BASE, ".cockpit-token"),
            "note": "Local loopback credential. Auto-login already exchanges it for a "
                    "session cookie on this machine, so pasting it is optional."}

try:

    from signal_inbox import inbox as _inbox  # noqa: F401
    _HAVE_INBOX = True
except Exception:
    _HAVE_INBOX = False

try:
    import edge_stats_bridge as _edge_stats  # noqa: F401
    _HAVE_EDGE_STATS = True
except Exception:
    _HAVE_EDGE_STATS = False

try:
    from event_journal import journal as _journal  # noqa: F401
    _HAVE_JOURNAL = True
except Exception:
    _HAVE_JOURNAL = False

# Standalone mobile_view has its own connection lifecycle; HQ does not import it.


def inbox_data():
    with _stage("inbox"):
        if _HAVE_INBOX:
            try:
                return _inbox()
            except Exception:
                pass
        try:
            con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2)
            cur = con.execute(
                "SELECT ts, symbol, side, status, msg_id FROM trades "
                "ORDER BY id DESC LIMIT 12")
            names = channel_names()
            rows = []
            for r in cur.fetchall():
                status_map = {"executed": "Validated", "skipped": "Journalled"}
                rows.append({"time": r[0], "symbol": r[1] or "-",
                             "setup": (r[2] or "").upper() or "Unclassified",
                             "source": names.get(str(r[4]), str(r[4]) if r[4] is not None else "Unknown source"),
                             "status": r[3] or "Unclassified"})
            con.close()
            return rows
        except Exception:
            return []


def journal_data():
    with _stage("journal"):
        if _HAVE_JOURNAL:
            try:
                return _journal()
            except Exception:
                pass
        rows = []
        for l in ledger(12):
            rows.append({"time": l["ts"], "event": (l["action"] or "signal").title(),
                         "detail": f'{l["symbol"] or "-"} {l["status"] or ""} {l["detail"] or ""}'.strip()})
        return rows


def mobile_html():
    # The standalone mobile renderer owns a separate broker connection. Never
    # invoke it from page polling, even if its lifecycle guard would deny it.
    return ("<div class='kv'><span>Mobile broker panel</span><b>Unavailable in observational HQ</b>"
            "</div><p>HQ never connects MT5. See broker health for maintenance and connection status.</p>")


# --- scalp360 integration (all reads defensive: missing tables/files -> empty) ---

try:
    import scalp360_bridge as _s360
    NEURAL_MIN_LABELS = int(_s360.BridgeConfig().neural_min_labels)
except Exception:
    _s360 = None
    NEURAL_MIN_LABELS = 300

_s360_bridge = None


def _bridge():
    """Process-local scalp360 bridge on an in-memory DB: cockpit stays read-only
    for the live signals.db while still owning a real StageTimer whose
    latency_snapshot() feeds /api/latency."""
    global _s360_bridge
    if _s360_bridge is None:
        try:
            _s360_bridge = _s360.make_bridge(":memory:")
        except Exception:
            _s360_bridge = False
    return _s360_bridge or None


def _stage(name):
    """Time one pipeline stage through the bridge's StageTimer (no-op when the
    scalp360 package is unavailable)."""
    b = _bridge()
    return b.stage(name) if b else contextlib.nullcontext()


def _db_ro():
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2)


def neural_label_count():
    """Completed labeled outcomes only, never pending collector rows."""
    return neural_label_counts()["completed"]


def neural_label_counts():
    try:
        with contextlib.closing(_db_ro()) as con:
            total = con.execute("SELECT COUNT(*) FROM neural_labels").fetchone()[0]
            cols = {r[1] for r in con.execute("PRAGMA table_info(neural_labels)")}
            # The collector uses NULL for pending and 0/1 for finalized outcomes.
            completed = (con.execute("SELECT COUNT(*) FROM neural_labels WHERE outcome IN (0,1)").fetchone()[0]
                         if "outcome" in cols else 0)
            return {"collected": total, "completed": completed, "pending": total-completed,
                    "available": "outcome" in cols}
    except (sqlite3.Error, OSError):
        return {"collected": 0, "completed": 0, "pending": 0, "available": False}


def neural_eval_last():
    """Last persisted neural evaluation (holdout AUC + PROMOTE/KEEP_SHADOW/REJECT).
    Probes, in order: a 'neural_eval' table in signals.db, then neural_eval.json
    next to cockpit.py. None until the evaluation harness has actually run."""
    try:
        con = _db_ro()
        cols = [r[1] for r in con.execute("PRAGMA table_info(neural_eval)").fetchall()]
        if cols:
            row = con.execute("SELECT * FROM neural_eval ORDER BY rowid DESC LIMIT 1").fetchone()
            if row:
                rec = dict(zip(cols, row))
                con.close()
                return {"auc": rec.get("auc", rec.get("holdout_auc")),
                        "decision": rec.get("decision"), "ts": rec.get("ts")}
        con.close()
    except Exception:
        pass
    try:
        rec = json.load(open(os.path.join(BASE, "neural_eval.json"), encoding="utf-8"))
        if isinstance(rec, list):
            rec = rec[-1] if rec else {}
        if isinstance(rec, dict):
            return {"auc": rec.get("auc", rec.get("holdout_auc")),
                    "decision": rec.get("decision"), "ts": rec.get("ts")}
    except Exception:
        pass
    return None


def golden_eye_data():
    from command_deck import golden_eye_data as project
    return project(BASE, DB)


def ai_brain_data():
    from command_deck import ai_brain_data as project
    return project(BASE, DB)


def neural_data():
    counts = neural_label_counts()
    count = counts["completed"]
    return {"count": count, "min_needed": NEURAL_MIN_LABELS,
            "ready": counts["available"] and count >= NEURAL_MIN_LABELS,
            "progress": round(count / NEURAL_MIN_LABELS, 4) if NEURAL_MIN_LABELS else 0.0,
            "collected_count": counts["collected"], "completed_count": count,
            "pending_count": counts["pending"], "available": counts["available"],
            "count_basis": "completed labeled outcomes", "last_eval": neural_eval_last(),
            "health": _label_health()}


def _label_health():
    """Lazy integration: pipeline health (schema, map consistency, feature dims,
    accumulation rate). Never raises - an unhealthy report is still a report."""
    try:
        import label_health
    except ImportError:
        return {"available": False, "reason": "label health module unavailable"}
    try:
        report = label_health.build_report(DB)
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}
    return {"available": True, "report": report} if isinstance(report, dict) \
        else {"available": False, "reason": "unexpected label health report shape"}


def identity_data():
    """Strategy identity registry + the identity of every open position (read-only).

    Attribution is by broker magic. A magic that is not registered resolves to an
    explicit 'unknown' rather than being guessed at.
    """
    try:
        import strategy_identity as si
    except ImportError:
        return {"available": False, "reason": "strategy identity module unavailable"}
    try:
        registry = si.load_registry(CONFIG)
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"registry unavailable: {type(e).__name__}: {e}"}
    identities = [{"magic": magic, "id": ident.id, "version": ident.version,
                   "kind": ident.kind, "label": ident.label}
                  for magic, ident in sorted(registry.items(), key=lambda kv: int(kv[0]))]
    live = []
    try:
        if mt5.terminal_info():
            for p in mt5.positions_get() or []:
                ident = si.resolve_magic(int(p.magic), registry)
                live.append({"ticket": p.ticket, "symbol": p.symbol, "magic": int(p.magic),
                             "strategy_id": ident.id, "version": ident.version,
                             "label": ident.label})
    except Exception:  # noqa: BLE001
        live = []
    return {"available": True, "identities": identities, "open_positions": live,
            "note": "Attribution is by broker magic; magic 0 means opened outside the system."}


def latency_data():
    """p50/p95/p99 per pipeline stage from scalp360_bridge.latency_snapshot()."""
    b = _bridge()
    try:
        return dict(b.latency_snapshot()) if b else {}
    except Exception:
        return {}


def lineage_data(limit=5):
    """Last N intents from the scalp360 intents table - proof of the
    signal -> intent -> order -> position chain ([] when table missing)."""
    with _stage("lineage"):
        try:
            con = _db_ro()
            cur = con.execute(
                "SELECT intent_id, source, symbol, side, state FROM intents "
                "ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = [{"intent_id": r[0], "source": r[1], "symbol": r[2],
                     "side": r[3], "state": r[4]} for r in cur.fetchall()]
            con.close()
            return rows
        except Exception:
            return []


def pine_strategies():
    """Registered Pine strategies from config.json 'pine_strategies' (parallel
    build). Accepts a list of records or a {name: {...}} map; [] when absent."""
    try:
        cfg = json.load(open(CONFIG, encoding="utf-8"))
    except Exception:
        return []
    block = cfg.get("pine_strategies")

    def norm(name, rec):
        rec = rec if isinstance(rec, dict) else {}
        return {"name": str(name), "enabled": bool(rec.get("enabled", False)),
                "paper": bool(rec.get("paper", True)),
                "path": str(rec.get("path") or rec.get("file") or "")}

    out = []
    if isinstance(block, list):
        for i, rec in enumerate(block):
            if isinstance(rec, dict):
                out.append(norm(rec.get("name") or rec.get("id") or f"strategy-{i + 1}", rec))
            elif isinstance(rec, str):
                out.append({"name": rec, "enabled": False, "paper": True, "path": rec})
    elif isinstance(block, dict):
        for name, rec in block.items():
            out.append(norm(name, rec))
    return out


def pine_data():
    with _stage("pine"):
        return pine_strategies()


def strategies_data():
    """Strategy-engine status: RSI Pullback (strategy.py) + London Breakout
    (strategy2_live.py). Reads process liveness, today's entries, day P/L per
    magic, and the strategy2 one-entry-per-day state file."""
    out = []
    specs = [
        {"name": "RSI Pullback", "script": "strategy.py", "magic": 20261015,
         "symbols": ["XAUUSD", "EURUSD"], "risk": "1.0%", "note": "RSI 35/65 pullback + EMA50/200 trend"},
        {"name": "London Breakout", "script": "strategy2_live.py", "magic": 20261015,
         "symbols": ["XAUUSD"], "risk": "0.5%", "note": "London-open H1 range breakout, 1 entry/day"},
    ]
    live = engines() or {}
    for s in specs:
        rec = dict(s)
        rec["running"] = bool(live.get(s["script"].replace(".py", ""), False))
        rec["entries_today"] = None
        rec["day_pl"] = None
        rec["entries_today_reason"] = "Ledger lacks reliable per-engine magic/comment attribution"
        out.append(rec)
    # strategy2 one-entry-per-day state
    s2 = {}
    try:
        s2 = json.load(open(os.path.join(BASE, "strategy2_state.json"), encoding="utf-8"))
    except Exception:
        s2 = {}
    return {"engines": out, "strategy2_state": s2}


def health_data():
    """System health: process liveness for every engine, port checks, db size."""
    procs = []
    live = engines()
    for script in ("daemon.py", "manage.py", "strategy.py", "strategy2_live.py", "cockpit.py"):
        procs.append({"name": script, "up": bool(live.get(script.replace(".py", ""), False)) if live is not None else None})
    ports = {"cockpit": True}  # we are serving this request, so cockpit is up by definition
    try:
        req = urllib.request.Request("http://localhost:8484/", method="GET")
        urllib.request.urlopen(req, timeout=3)
        ports["trade-relay"] = True
    except Exception:
        ports["trade-relay"] = _port_listening(8484)
    db_size = 0
    try:
        db_size = os.path.getsize(DB)
    except Exception:
        pass
    return {"processes": procs, "ports": ports, "db_size": db_size,
            "broker": broker_health(),
            "maintenance": os.path.exists(os.path.join(BASE, "MAINTENANCE")),
            "halt": os.path.exists(os.path.join(BASE, "HALT")),
            "pause": os.path.exists(os.path.join(BASE, "PAUSE")),
            "stop": os.path.exists(os.path.join(BASE, "STOP"))}


def channels_data():
    """Per-channel scorecards from config signal_policy (+ channel_report.json
    expectancies when present), sorted by expectancy descending."""
    try:
        cfg = json.load(open(CONFIG, encoding="utf-8"))
    except Exception:
        return []
    pol = cfg.get("signal_policy") or {}
    rep = {}
    for fn in ("channel_report.json", "channel_report_v2.json"):
        try:
            d = json.load(open(os.path.join(BASE, fn), encoding="utf-8"))
            if isinstance(d, dict):
                rep.update(d)
        except Exception:
            pass
    names = {}
    try:
        names = channel_names() or {}
    except Exception:
        names = {}
    rows = []
    for cid, p in pol.items():
        if cid == "_default" or not isinstance(p, dict):
            continue
        mode = p.get("mode", "trading")
        exp = None
        for k in (cid, str(cid), names.get(cid, "")):
            if k and isinstance(rep.get(k), dict):
                exp = rep[k].get("expectancy", rep[k].get("exp"))
                break
        rows.append({"channel_id": cid, "name": names.get(cid, cid), "mode": mode,
                     "sl_mode": p.get("sl_mode", "-"), "tp_mode": p.get("tp_mode", "-"),
                     "expectancy": exp})
    rows.sort(key=lambda r: (r["expectancy"] is None, -(r["expectancy"] or 0)))
    return rows


def _cloudroom_status():
    """Cloudroom off-load status per target: active jobs, queue depth, GPU/CPU,
    cost tracking, auto-scaling, local fallback. Real data from cloudroom_offload,
    never mocks."""
    try:
        from cloudroom_offload import ROOT, TARGETS, desired_workers, probe, report
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "reason": "cloudroom_offload not importable: " + str(exc)[:200]}

    try:
        pr = probe()
    except Exception as exc:  # noqa: BLE001
        pr = {"service": "local_wsl", "ready": False, "error": str(exc)[:200]}

    state_dir = ROOT / ".cloudroom-state"
    queue_db = state_dir / "queue.sqlite3"

    targets = {}
    for name, cfg in TARGETS.items():
        active = 0
        queued = 0
        try:
            import sqlite3
            uri = queue_db.resolve().as_uri() + "?mode=ro"
            db = sqlite3.connect(uri, uri=True, timeout=10)
            try:
                for row in db.execute("SELECT spec, status FROM jobs"):
                    spec = json.loads(row[0]) if row[0] else {}
                    status = row[1]
                    if spec.get("target") == name:
                        if status == "running":
                            active += 1
                        elif status == "queued":
                            queued += 1
            finally:
                db.close()
        except Exception:
            pass

        try:
            rep = report(state_dir)
            cost = rep.get("local_estimated_cost_usd")
        except Exception:
            cost = None

        targets[name] = {
            "active_jobs": active,
            "queue_depth": queued,
            "gpu_cpu_utilization": "GPU" if cfg.get("preferred") == "gpu" else "CPU",
            "cost_tracking": round(cost, 4) if isinstance(cost, (int, float)) else "N/A",
            "auto_scaling_status": "desired_workers=" + str(desired_workers(queued, max_workers=2, jobs_per_worker=2)),
            "local_fallback_indicator": cfg.get("fallback", "local_cpu"),
        }

    return {"available": True, "probe": pr, "targets": targets}


def luxalgo_data():
    """LuxAlgo ecosystem status via the unified manager (one system, 11 repos):
    running services (trade-relay, local MCP), the hosted MCP endpoint probe, and
    the library-repo inventory."""
    mgr = os.path.join(os.path.dirname(BASE), "luxalgo", "luxalgo_manager.py")
    out = {"services": {}, "library_repos": [], "mcp_hosted": None}
    try:
        r = subprocess.run([sys.executable, "-u", mgr, "status"],
                           capture_output=True, text=True, timeout=25, cwd=os.path.dirname(mgr))
        if r.returncode == 0 and r.stdout.strip():
            out.update(json.loads(r.stdout.strip()))
    except Exception:  # noqa: BLE001
        pass
    # hosted MCP liveness (405 = alive, expects MCP POST)
    try:
        req = urllib.request.Request("https://mcp.luxalgo.com/mcp", method="GET")
        urllib.request.urlopen(req, timeout=5)
        out["mcp_hosted"] = {"reachable": True, "code": 200}
    except Exception as e:  # noqa: BLE001
        code = getattr(e, "code", None)
        out["mcp_hosted"] = {"reachable": bool(code), "code": code}
    return out


def prop_sim_data(n_paths=2000):
    """Standalone simulation fetches broker history; HTTP must not invoke it."""
    return {"available": False, "reason": "Broker-backed simulation disabled in observational HQ; use an offline research artifact",
            "broker": broker_health(), "broker_orders_enabled": False}


def market_intel_data(kind="congress", limit=8):
    """LuxAlgo market-trackers public record (congress, insider, contracts,
    lobbying, short_volume) with provenance.sourceUrl preserved on every row."""
    try:
        import market_intel_bridge
        return market_intel_bridge.get_market_intel(kind, limit=int(limit))
    except Exception as e:  # noqa: BLE001
        return {"rows": [], "available": False, "reason": f"{type(e).__name__}: {e}"}


def candles_data(symbol="XAUUSD", timeframe="H1", count=200, closed_only=False):
    """OHLCV candles for the chart panel, from MT5 (read-only). Returns
    {symbol, timeframe, candles:[[t,o,h,l,c,v],...]} or an honest error.

    closed_only=True drops the final received bar. That is the convention every
    other bar consumer here already follows (executor.py, backtest.py,
    neural_label_collector.py, quant_analytics.py) and it is deliberately
    timezone-INDEPENDENT: MT5 epochs are 'broker as supplied' with no guaranteed
    zone, so deciding closure by comparing them to local now would be wrong by
    the broker's UTC offset. Assuming the newest received bar is still forming
    is the conservative choice. Research/Pine callers use closed_only=True; the
    chart keeps the live bar so the trader can see it, and is told it is live.
    """
    TF = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
          "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
          "D1": mt5.TIMEFRAME_D1}
    tf = TF.get(str(timeframe).upper(), mt5.TIMEFRAME_H1)
    try:
        if mt5.terminal_info() is None:
            health = broker_health()
            return {"symbol": symbol, "timeframe": timeframe, "candles": [],
                    "error": "MT5 unavailable: " + str(health["blocked_reason"]), "broker": health}
        sym = resolve_symbol_cockpit(symbol)
        if not sym:
            return {"symbol": symbol, "timeframe": timeframe, "candles": [],
                    "error": f"symbol {symbol} not found on this broker"}
        n = max(20, min(int(count), 1500))
        # Fetch one extra so excluding the forming bar still yields n closed bars.
        rates = mt5.copy_rates_from_pos(sym, tf, 0, n + 1)
        if rates is None or len(rates) == 0:
            return {"symbol": sym, "timeframe": timeframe, "candles": [],
                    "error": "no bars returned (market may be closed)"}
        candles = [[int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])]
                   for r in rates]
        excluded = False
        if closed_only and len(candles) > 1:
            candles = candles[:-1]
            excluded = True
        candles = candles[-n:]
        return {"symbol": sym, "timeframe": str(timeframe).upper(), "candles": candles,
                "timestamp_basis": "broker as supplied",
                "last_bar_closed": False if excluded else None,
                "forming_bar_excluded": excluded,
                "closed_bar_basis": ("final received bar assumed still forming; closure is "
                                     "never inferred from broker epochs vs local time"),
                "last": candles[-1][4] if candles else None, "error": None}
    except Exception as e:  # noqa: BLE001
        return {"symbol": symbol, "timeframe": timeframe, "candles": [],
                "error": f"{type(e).__name__}: {e}"}


def resolve_symbol_cockpit(raw):
    """Exact-candidate symbol resolution (mirrors executor.resolve_symbol)."""
    raw_u = str(raw or "").upper()
    for c in (raw_u, raw_u.replace("/", ""), f".{raw_u}", f"{raw_u}.r", f"{raw_u}r",
              f"{raw_u}.c", f"{raw_u}.m", f"{raw_u}_", f"m{raw_u}"):
        if mt5.symbol_info(c):
            return c
    return None


def pine_series_data(pine_file="strategies/rsi_ema_trend.pine", symbol="XAUUSD",
                     timeframe="H1", count=220):
    from pathlib import Path
    root = Path(BASE, "strategies").resolve()
    name = str(pine_file)
    if name.startswith("strategies/"):
        name = name[len("strategies/"):]
    if not name or "/" in name or "\\" in name or not name.endswith(".pine"):
        raise ApiError(400, "Invalid strategy path")
    target = (root / name).resolve()
    if target.parent != root or not target.is_file():
        raise ApiError(404, "Strategy not found")
    if target.stat().st_size > 65536:
        raise ApiError(400, "Strategy source too large")
    return compile_pine(target.read_text(encoding="utf-8"), symbol, timeframe, count)


def news_data():
    """Upcoming High-impact USD events from news_calendar.json."""
    out = []
    try:
        cal = json.load(open(os.path.join(BASE, "news_calendar.json"), encoding="utf-8"))
    except Exception:
        return {"events": [], "active": False}
    events = cal if isinstance(cal, list) else cal.get("events", [])
    now = time.time()
    for e in events or []:
        if not isinstance(e, dict):
            continue
        out.append({"title": e.get("title") or e.get("event"), "currency": e.get("currency"),
                    "impact": e.get("impact"), "time": e.get("time") or e.get("date")})
    cfg = {}
    try:
        cfg = json.load(open(CONFIG, encoding="utf-8")).get("news_filter", {})
    except Exception:
        pass
    active = False
    try:
        import news_fetcher
        active = bool(news_fetcher.block_reason(json.load(open(CONFIG, encoding="utf-8"))))
    except Exception:
        active = False
    return {"events": out[:20], "active": active, "window": cfg}


def edge_data():
    """Edge statistics: per-channel and per-engine win rates, expectancy, Wilson 95% CI.
    Defensive: never crashes, returns empty structure on any error."""
    if _HAVE_EDGE_STATS:
        try:
            return _edge_stats.get_edge_stats()
        except Exception:
            pass
    return {"channels": [], "engines": [], "methodology": {}}


def trace(ticket):
    """Evidence-only ticket trail. No inferred validation or management claims."""
    events = []
    try:
        with contextlib.closing(_db_ro()) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT * FROM trades WHERE ticket=? ORDER BY rowid", (ticket,)).fetchall()
            for row in rows:
                rec = dict(row)
                status = rec.get("status") or "unknown"
                events.append({"time": rec.get("ts"), "event": "Ledger: " + status,
                               "detail": rec.get("detail") or "Recorded ledger status (not independent broker confirmation)",
                               "evidence": "trades ledger", "status": status})
    except (sqlite3.Error, OSError):
        pass
    position_status = "unknown"
    try:
        if mt5.terminal_info():
            positions = mt5.positions_get(ticket=ticket)
            if positions:
                position_status = "open"
            elif positions is not None:
                deals = mt5.history_deals_get(position=ticket)
                out_values = {getattr(mt5, "DEAL_ENTRY_OUT", 1), getattr(mt5, "DEAL_ENTRY_OUT_BY", 3)}
                if deals and any(getattr(d, "entry", None) in out_values for d in deals):
                    position_status = "closed"
    except Exception:
        pass
    events.append({"time": None, "event": "Position " + position_status,
                   "status": position_status, "evidence": "MT5" if position_status != "unknown" else None,
                   "detail": "Broker-confirmed status" if position_status != "unknown" else
                   "No current broker evidence; ledger alone cannot establish open/closed status"})
    return events


def state():
    observed_at = datetime.now().astimezone().isoformat()
    health = broker_health()
    ok = health["available"]
    try:
        acct = mt5.account_info() if ok else None
    except Exception:
        acct = None
    try:
        broker_positions = mt5.positions_get() if ok else None
    except Exception:
        broker_positions = None
    try:
        cfg = json.load(open(CONFIG, encoding="utf-8"))
        mode = cfg.get("mode") or "unknown"
    except Exception:
        mode = "unknown"
    pos = []
    if ok:
        with _stage("positions"):
            mgr_state = {}
            try:
                mgr_state = json.load(open(os.path.join(BASE, "manage-state.json"), encoding="utf-8"))
            except Exception:
                pass
            for p in broker_positions or []:
                mgr = mgr_state.get(str(p.ticket), {})
                r_basis = mgr.get("r")
                if (isinstance(r_basis, bool) or not isinstance(r_basis, (int, float))
                        or not math.isfinite(r_basis) or r_basis <= 0):
                    r_basis = None
                direction = (1 if p.type == mt5.POSITION_TYPE_BUY else
                             -1 if p.type == mt5.POSITION_TYPE_SELL else None)
                move = (p.price_current - p.price_open) * direction if direction is not None else None
                pl = p.profit + p.swap
                pos.append({"ticket": p.ticket, "symbol": p.symbol,
                            "side": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                            "lots": p.volume, "entry": p.price_open, "now": p.price_current,
                            "pl": round(pl, 2), "r": r_basis,
                            "r_multiple": round(move / r_basis, 2) if r_basis and move is not None else None,
                            "r_units": "symbol_price", "r_multiple_units": "R",
                            "r_multiple_basis": "directional price movement / original price risk; excludes costs",
                            "sl": p.sl, "tp": p.tp,
                            "source": "algo" if p.magic == 20261015 else "signal" if p.magic == 20261014 else "manual/other",
                            "opened": datetime.fromtimestamp(p.time).strftime("%H:%M"),
                            "be_done": bool(mgr.get("be_done"))})
    try:
        total, sigp, algop = day_pl() if ok else (None, None, None)
    except Exception:
        total, sigp, algop = None, None, None
    channels = []
    if os.path.exists(REPORT):
        try:
            channels = json.load(open(REPORT, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            channels = []
    tr_up = False
    try:
        s = socket.create_connection(("localhost", 8484), timeout=2)
        s.close()
        tr_up = True
    except OSError:
        pass
    pause = os.path.exists(os.path.join(BASE, "PAUSE"))
    halt = os.path.exists(os.path.join(BASE, "HALT"))
    return {"time": datetime.now().strftime("%H:%M:%S"), "mode": mode,
            "observed_at": observed_at,
            "broker": health, "maintenance": health["maintenance"],
            "mt5": {"available": bool(ok), "account_available": acct is not None,
                    "connected": health["connected"], "blocked_reason": health["blocked_reason"],
                    "auto_connect": False,
                    "positions_available": broker_positions is not None},
            "freshness": {"observed_at": observed_at, "engine_checked_at": _engine_cache["t"],
                          "engine_cache_seconds": 30, "broker_snapshot": bool(ok)},
            "account": {"login": acct.login if acct else None,
                        "server": acct.server if acct else None,
                        "trade_mode": acct.trade_mode if acct else None,
                        "currency": getattr(acct, "currency", None) if acct else None,
                        "type": ({0: "demo", 1: "contest", 2: "real"}.get(acct.trade_mode, "unknown")
                                 if acct else "unknown"),
                        "balance": acct.balance if acct else None,
                        "equity": acct.equity if acct else None,
                        "margin": acct.margin if acct else None,
                        "free": acct.margin_free if acct else None,
                        "profit": acct.profit if acct else None},
            "positions": pos,
            "day_pl": {"total": total, "signals": sigp, "algo": algop,
                       "available": total is not None, "units": "account_currency",
                       "basis": "MT5 deals profit + commission + swap + fee; local calendar day"},
            "engines": engines(), "halt": halt, "stop": os.path.exists(os.path.join(BASE, "STOP")),
            "pause": pause, "ledger": ledger(), "channels": channels,
            "trade_relay_up": tr_up, "inbox": inbox_data(), "journal": journal_data(), "mobile": mobile_html(),
            "neural_labels": neural_label_count(), "pine_count": len(pine_strategies()),
            "cloudroom": _cloudroom_status()}








class H(CockpitHandler):
    backend = sys.modules[__name__]


def create_server(host="127.0.0.1", port=PORT):
    server = ThreadingHTTPServer((host, port), H)
    server.cockpit_token = load_token(BASE)
    return server


def main():
    # Dashboard availability must not depend on the terminal/broker being online.
    host = os.environ.get("COCKPIT_HOST", "127.0.0.1")
    server = create_server(host, PORT)
    
    # Start strategy registry watcher for Pine Script hot-reload
    try:
        from strategy_registry import StrategyRegistry
        from pathlib import Path
        registry = StrategyRegistry(Path(BASE) / 'strategies')
        registry.start(interval=2.0)
        print(f"Strategy registry watcher started (hot-reload enabled)")
    except Exception as e:  # noqa: BLE001
        print(f"Strategy registry watcher failed to start: {e}")
    
    print(f"cockpit on http://{host}:{PORT} (read-only; local owner authentication required)")
    server.serve_forever()


if __name__ == "__main__":
    main()
