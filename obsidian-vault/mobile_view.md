---
slug: mobile_view
type: note
graph: gitnexus
---

"""mobile_view.py — compact mobile-format panel rendered from LIVE data.

Every figure in this panel is read at request time from MT5 (read-only),
signals.db, and the control-flag files. There are NO sample, demo or placeholder
values: anything that cannot be read is reported as unavailable rather than
filled in, and no control is rendered that the system does not actually offer.

Read-only by contract: never calls order_send or any TRADE_ACTION_*.
"""
from __future__ import annotations

import html
import os
import sqlite3
import time
import math
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "signals.db")

# Dark identity matching the Quant HQ dashboard.
_STYLE = (
    "font-family:Segoe UI,system-ui,sans-serif;font-size:13px;color:#edf3fa;"
    "background:#0a1018;padding:12px;box-sizing:border-box"
)
_CARD = ("background:#101b28;border:1px solid #28394a;border-radius:10px;"
         "padding:11px 13px;margin-bottom:9px")
_MUTED = "color:#a5b6c7"
_NUM = "font-variant-numeric:tabular-nums"


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def _fmt(value, digits: int = 2) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
        return f"{number:,.{digits}f}" if math.isfinite(number) else "—"
    except (TypeError, ValueError):
        return _esc(value)


def _mt5():
    """Import MetaTrader5 lazily; None when unavailable."""
    try:
        import MetaTrader5 as mt5
        return mt5
    except Exception:  # noqa: BLE001
        return None


def _account():
    """Live account snapshot, or None when it cannot be read."""
    mt5 = _mt5()
    if mt5 is None:
        return None
    try:
        if mt5.terminal_info() is None:
            return None
        acct = mt5.account_info()
    except Exception:  # noqa: BLE001
        return None
    if acct is None:
        return None
    return {"login": acct.login, "server": acct.server, "balance": acct.balance,
            "equity": acct.equity, "profit": acct.profit, "free": acct.margin_free,
            "type": {0: "demo", 1: "contest", 2: "real"}.get(acct.trade_mode, "unknown"),
            "currency": getattr(acct, "currency", None)}


def _positions(limit: int | None = None):
    """Live open positions (most recent first), or None when unreadable."""
    mt5 = _mt5()
    if mt5 is None:
        return None
    try:
        if mt5.terminal_info() is None:
            return None
        rows = mt5.positions_get()
    except Exception:  # noqa: BLE001
        return None
    if rows is None:
        return None
    out = []
    for p in rows:
        side = "BUY" if p.type == 0 else "SELL" if p.type == 1 else "?"
        out.append({"ticket": p.ticket, "symbol": p.symbol, "side": side,
                    "lots": p.volume, "entry": p.price_open, "now": p.price_current,
                    "pl": p.profit + getattr(p, "swap", 0.0),
                    "sl": p.sl, "tp": p.tp, "opened": p.time})
    out.sort(key=lambda r: r["opened"] or 0, reverse=True)
    return out if limit is None else out[:limit]


def _flags():
    return {name: os.path.exists(os.path.join(BASE, name))
            for name in ("HALT", "PAUSE", "STOP", "MAINTENANCE")}


def _recent_events(limit: int = 4):
    """Newest events from the persisted event bus, or None when unreadable."""
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2)
        try:
            rows = con.execute(
                "SELECT ts, type, source FROM events "
                "WHERE type != 'pnl_update' ORDER BY rowid DESC LIMIT ?",
                (limit,)).fetchall()
        finally:
            con.close()
        return [{"ts": r[0], "type": r[1], "source": r[2]} for r in rows]
    except (sqlite3.Error, OSError):
        return None


def _card(title: str, inner: str) -> str:
    return (f'<div style="{_CARD}"><div style="font-weight:650;font-size:12px;'
            f'letter-spacing:.03em;margin-bottom:7px">{_esc(title)}</div>{inner}</div>')


def _build_body() -> str:
    parts = []

    acct = _account()
    if acct is None:
        parts.append(_card("Account", f'<div style="{_MUTED}">Unavailable — MT5 is not '
                                      'attached or the broker snapshot could not be read.</div>'))
    else:
        currency = _esc(acct.get("currency") or "currency unavailable")
        profit = acct["profit"]
        colour = "#79d6af" if (profit or 0) > 0 else "#ff9b9b" if (profit or 0) < 0 else "#edf3fa"
        parts.append(_card(
            f"Account · {currency}",
            f'<div style="{_MUTED};font-size:11px">Login {_esc(acct["login"])} · '
            f'{_esc(acct["type"])} · {_esc(acct["server"])}</div>'
            f'<div style="display:flex;justify-content:space-between;margin-top:8px;{_NUM}">'
            f'<span><div style="{_MUTED};font-size:11px">Balance</div>'
            f'<b>{_fmt(acct["balance"])}</b></span>'
            f'<span><div style="{_MUTED};font-size:11px">Equity</div>'
            f'<b>{_fmt(acct["equity"])}</b></span>'
            f'<span><div style="{_MUTED};font-size:11px">Floating</div>'
            f'<b style="color:{colour}">{_fmt(profit)}</b></span></div>'))

    pos = _positions()
    if pos is None:
        parts.append(_card("Open positions", f'<div style="{_MUTED}">Unavailable — broker '
                                             'position data could not be read.</div>'))
    elif not pos:
        parts.append(_card("Open positions", f'<div style="{_MUTED}">No open positions.</div>'))
    else:
        rows = []
        for p in pos:
            colour = "#79d6af" if (p["pl"] or 0) > 0 else "#ff9b9b" if (p["pl"] or 0) < 0 else "#edf3fa"
            protected = "SL set" if p["sl"] else "NO STOP"
            sl_colour = "#79d6af" if p["sl"] else "#ff9b9b"
            rows.append(
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;'
                f'padding:6px 0;border-top:1px solid #1d2b3a;{_NUM}">'
                f'<span><b>{_esc(p["symbol"])}</b> <span style="{_MUTED};font-size:11px">'
                f'{_esc(p["side"])} {_fmt(p["lots"], 2)}</span><br>'
                f'<span style="{_MUTED};font-size:10px">#{_esc(p["ticket"])} · '
                f'<span style="color:{sl_colour}">{protected}</span></span></span>'
                f'<b style="color:{colour}">{_fmt(p["pl"])}</b></div>')
        parts.append(_card(f"Open positions · {len(pos)}", "".join(rows)))

    flags = _flags()
    active = [k for k, v in flags.items() if v]
    if active:
        flag_html = " ".join(
            f'<span style="background:#3a2a1a;border:1px solid #6d5736;color:#f0d4a5;'
            f'border-radius:6px;padding:2px 7px;font-size:11px">{_esc(k)}</span>'
            for k in active)
    else:
        flag_html = (f'<span style="{_MUTED};font-size:11px">'
                     'All clear — no HALT / PAUSE / STOP / MAINTENANCE flag is set.</span>')
    parts.append(_card("Protection flags", flag_html))

    events = _recent_events()
    if events is None:
        parts.append(_card("Recent activity", f'<div style="{_MUTED}">Unavailable — the event '
                                              'store could not be read.</div>'))
    elif not events:
        parts.append(_card("Recent activity", f'<div style="{_MUTED}">No recorded events yet.</div>'))
    else:
        rows = "".join(
            f'<div style="padding:5px 0;border-top:1px solid #1d2b3a">'
            f'<div style="font-size:11px"><b>{_esc(e["type"].replace("_", " "))}</b> '
            f'<span style="{_MUTED}">· {_esc(e["source"])}</span></div>'
            f'<div style="{_MUTED};font-size:10px">{_esc(str(e["ts"])[:19])}</div></div>'
            for e in events)
        parts.append(_card("Recent activity", rows))

    return "".join(parts)


def get_mobile_html() -> str:
    """Compact mobile-format panel built from live data.

    Returns the panel HTML, or an explicit unavailable notice — never sample
    data, and never an exception.
    """
    try:
        body = _build_body()
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception as e:  # noqa: BLE001
        return (f'<div style="{_STYLE}"><div style="{_CARD}">'
                f'<div style="{_MUTED}">Mobile panel unavailable: '
                f'{_esc(type(e).__name__)}</div></div></div>')
    return (
        f'<div style="{_STYLE}">'
        f'<div style="max-width:420px;margin:0 auto">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:4px 2px 10px">'
        f'<b style="letter-spacing:.04em">QUANT <span style="color:#69dcec">HQ</span></b>'
        f'<span style="{_MUTED};font-size:11px;{_NUM}">snapshot · {_esc(stamp)}</span></div>'
        f'{body}'
        f'<div style="{_MUTED};font-size:10px;padding:4px 2px">'
        f'Read-only MT5 / signals.db snapshot fetched at the time above. Quote freshness is unverified; latest broker prices can remain unchanged while the market is closed. Refresh to read again.'
        f'</div></div></div>'
    )

## Links from
- [[test_real_data_views]]
