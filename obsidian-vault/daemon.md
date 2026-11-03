---
slug: daemon
type: note
graph: gitnexus
---

"""Signal-relay daemon: watches selected Telegram chats with YOUR account (Telethon
userbot), parses trading signals, executes them on MT5 (via executor.py), and
reports everything into the Hermes chat (via notify.py).

First-time setup (one-off, needs interaction):
    python daemon.py --login          # prompts for api_id/api_hash if not in .env, phone, then code

Then:
    python daemon.py --list-dialogs  # print your chats with IDs -> put them in config.json
    python daemon.py                  # run the relay

Kill switches:
    HALT file next to this script  -> stop placing NEW trades (relay/notify keeps running)
    PAUSE file (console 'pause')   -> daemon-side pre-execute gate: blocks NEW signal
                                      entries only; open positions keep managing and
                                      executor.py / manage.py never read this file
    STOP file                      -> clean exit of the serve loop
    ask the Hermes agent           -> it can create/delete the HALT file for you

Telegram console (DM commands):
    The owner (Telegram user id 8877588890) commands this daemon from the DM chat
    with the relay account: status | close <ticket> | closeall | pause | resume |
    help (case-insensitive, leading '/' tolerated). Replies go through
    notify._send_sync like every relay report. DMs are NEVER parsed as signals;
    DMs from anyone else are ignored silently (one log line, no reply).
"""
import asyncio
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone

import notify
import parser as sigparser
from executor import execute, halted, load_config
from broker_lifecycle import initialize_existing
from event_bus import bus

BASE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.join(BASE, "telethon.session")
HERMES_ENV = os.path.join(os.path.expanduser("~"), ".hermes", ".env")
CREDS_FILE = os.path.join(BASE, "telegram_creds.json")
STOP_FILE = os.path.join(BASE, "STOP")
MAGIC = 20261014  # magic number executor.execute() stamps on relay trades
LOCK_FILE = os.path.join(BASE, "daemon.lock")
OWNER_ID = 8877588890  # the only Telegram user whose DMs are console commands
PAUSE_FILE = os.path.join(BASE, "PAUSE")  # console 'pause': daemon-side NEW-entry gate (executor/manage never read it)
_ENGINE_STARTED = None  # serve-loop start time; console 'status' reports uptime from it


# ---- scalp360 bridge (ADDITIVE integration) ----------------------------------
# Wires the verified scalp360 package into the live relay. make_bridge()
# runs the bridge's idempotent _ensure_schema() pass over signals.db
# (adds lineage tables: intents, positions, event_claims, neural_labels)
# and exposes the zone-aware gold parser. Failure is logged and NEVER
# blocks the daemon: _bridge stays None and every use site no-ops.
try:
    import scalp360_bridge
    _bridge = scalp360_bridge.make_bridge()
except Exception as _e:  # noqa: BLE001
    _bridge = None
    print(f"scalp360 bridge unavailable (relay continues without it): {type(_e).__name__}: {_e}")


def _s360_log(msg):
    """Best-effort append to daemon.log (scalp360 bridge diagnostics); never raises."""
    try:
        with open(os.path.join(BASE, "daemon.log"), "a", encoding="utf-8") as f:
            f.write(f"[scalp360 {time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:  # noqa: BLE001
        pass


# ---- single-instance lock ---------------------------------------------------
def _pid_is_live_python(pid, script_marker=None):
    """True when `pid` names a running process whose executable is python(.exe)
    and (when given) whose command line contains script_marker. The marker guards
    against Windows pid-reuse false positives that would block restarts."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.OpenProcess.restype = ctypes.c_void_p
        k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        k32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        k32.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                                   ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint32)]
        k32.CloseHandle.argtypes = [ctypes.c_void_p]
        h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            if not k32.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:
                return False  # 259 = STILL_ACTIVE
            buf = ctypes.create_unicode_buffer(1024)
            n = ctypes.c_ulong(1024)
            if not k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
                return True  # alive; image name unavailable
            if "python" not in os.path.basename(buf.value).lower():
                return False
            if script_marker:
                import subprocess as _sp
                try:
                    cl = _sp.run(["powershell", "-NoProfile", "-Command",
                                  f"(Get-CimInstance Win32_Process -Filter \"ProcessId={int(pid)}\").CommandLine"],
                                 capture_output=True, text=True, timeout=30).stdout.strip()
                    return bool(cl) and script_marker in cl
                except Exception:  # noqa: BLE001
                    return True
            return True
        finally:
            k32.CloseHandle(h)
    except Exception:  # noqa: BLE001
        return False


def _acquire_single_instance():
    """Refuse to run alongside another live python holding LOCK_FILE: print a
    note and sys.exit(0). A stale lock (dead/non-python PID) is overwritten."""
    old = ""
    try:
        with open(LOCK_FILE, "r", encoding="utf-8") as f:
            old = (f.read() or "").strip()
    except OSError:
        pass
    if old and _pid_is_live_python(old, os.path.basename(__file__)):
        print(f"daemon.py: another instance is already running (pid {old}) - exiting")
        sys.exit(0)
    try:
        with open(LOCK_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except OSError as e:  # noqa: BLE001
        print("daemon.py: could not write lock file:", e)


def _release_lock():
    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass


def _file_creds():
    """api_id/api_hash from telegram_creds.json next to this script (preferred,
    avoids touching the protected ~/.hermes/.env)."""
    try:
        with open(CREDS_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        api_id = int(d.get("api_id") or 0)
        api_hash = (d.get("api_hash") or "").strip()
        return (api_id or None), (api_hash or None)
    except Exception:  # noqa: BLE001
        return None, None


def _env_creds():
    api_id = api_hash = None
    f_id, f_hash = _file_creds()
    if f_id and f_hash:
        return f_id, f_hash
    if os.path.exists(HERMES_ENV):
        with open(HERMES_ENV, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.match(r"\s*TELEGRAM_API_ID\s*=\s*(\d+)", line)
                if m:
                    api_id = int(m.group(1))
                m = re.match(r"\s*TELEGRAM_API_HASH\s*=\s*(\S+)", line)
                if m:
                    api_hash = m.group(1).strip().strip('"').strip("'")
    return api_id, api_hash


def _get_client():
    from telethon import TelegramClient
    api_id, api_hash = _env_creds()
    if not (os.path.exists(SESSION) or (api_id and api_hash)):
        print("No session and no TELEGRAM_API_ID/TELEGRAM_API_HASH in ~/.hermes/.env.")
        print("Get them at https://my.telegram.org -> API development tools, then run: python daemon.py --login")
        sys.exit(1)
    return TelegramClient(SESSION, api_id or 0, api_hash or "")


async def login_flow():
    from telethon import TelegramClient
    api_id, api_hash = _env_creds()
    if not (api_id and api_hash):
        api_id = int(input("api_id from my.telegram.org: ").strip())
        api_hash = input("api_hash: ").strip()
    client = TelegramClient(SESSION, api_id, api_hash)
    await client.start()  # prompts for phone + code on first run
    me = await client.get_me()
    print(f"Logged in as {me.first_name} (@{me.username}). Session saved: {SESSION}")
    await client.disconnect()


async def list_dialogs():
    client = _get_client()
    await client.connect()
    if not await client.is_user_authorized():
        print("Session not authorized - run --login first")
        return
    print(f"{'chat_id':<16} {'type':<8} title")
    async for d in client.iter_dialogs(limit=200):
        cid = str(d.id)
        if cid.startswith("-100"):
            cid = str(d.id)  # keep full -100... id
        print(f"{cid:<16} {d.entity.__class__.__name__[:4]:<8} {d.name}")
    await client.disconnect()


def _fmt_signal(p):
    tps = p.get("tps") or []
    tp_s = ", ".join(str(t) for t in tps) or "-"
    return (f"{p.get('action','?').upper()} {p.get('symbol')} "
            f"{'@ ' + str(p['entry']) if isinstance(p.get('entry'), float) else '(market)'} | "
            f"SL {p.get('sl') or '-'} | TP {tp_s}")


# ---------------------------------------------------------------------------
# Telegram console: DM commands from the owner.
#
# Auth model: this Telethon session is a DEDICATED relay account (not the
# owner's own account). The owner (Telegram user id 8877588890, @v01dkrawl7er)
# commands it from the 1:1 DM chat with that account, so a command is a
# private message where BOTH the peer chat id and the sender id equal
# OWNER_ID. Every other DM - a stranger, a bot, or the owner typing in some
# other chat (friends, the Hermes bot) - is ignored silently with one log
# line and can NEVER reach the signal path: a DM is never parsed as a signal,
# whoever sent it. Channel/group messages (negative Telethon chat ids) never
# enter the console branch at all; the watched-signal flow is unchanged.
#
# MT5 access mirrors executor.execute()'s own attach pattern (initialize only
# when the in-process connection is down, NEVER shutdown): using
# executor.mt5_session() here would shutdown the executor's live connection
# mid-trade. There is deliberately no second terminal login.
# ---------------------------------------------------------------------------

def paused():
    """Console PAUSE switch, read only by THIS daemon's pre-execute gate (the
    same spot that checks HALT): blocks NEW signal entries. executor.py and
    manage.py never read this file, so open positions keep being managed and
    may still be closed while paused."""
    return os.path.exists(PAUSE_FILE)


def _clog(msg):
    print(f"[console {time.strftime('%H:%M:%S')}] {msg}")


def parse_command(text):
    """'  /Close 123456 ' -> ('close', '123456'). Case-insensitive, tolerates a
    leading '/' and extra whitespace. Returns (None, None) for empty input.
    Unknown words are returned as-is; dispatch replies 'unknown command'."""
    t = (text or "").strip()
    if t.startswith("/"):
        t = t[1:].strip()
    if not t:
        return None, None
    parts = t.split()
    return parts[0].lower(), (parts[1] if len(parts) > 1 else None)


def classify_dm(chat_id, sender_id, channels=None):
    """Classify one message for the console branch (pure, unit-tested):
    'channel' - not a private chat (Telethon marks groups/channels negative):
               the watched-signal path owns it, unchanged.
    'owner'   - DM in the daemon's own chat FROM the owner (both == OWNER_ID).
    'foreign' - any other DM: ignored silently (one log line), never a signal."""
    if not isinstance(chat_id, int) or chat_id < 0:
        return "channel"
    if channels and chat_id in channels:  # belt-and-braces: watched chats are never DMs
        return "channel"
    if chat_id == OWNER_ID and sender_id == OWNER_ID:
        return "owner"
    return "foreign"


_HELP_TEXT = (
    "Console commands (DM only; case-insensitive, leading '/' ok):\n"
    "  status         account balance/equity, open positions, uptime, last ledger rows\n"
    "  close <ticket> close that exact open position\n"
    "  closeall       close every open position\n"
    "  pause          block NEW signal entries (open positions keep managing)\n"
    "  resume         re-enable new signal entries\n"
    "  help           this list"
)


def _mt5_or_none():
    """Attach to MT5 exactly like executor.execute(): initialize only when the
    in-process connection is down, never shutdown (shutdown would tear down the
    executor's live connection mid-trade). Returns the executor's MetaTrader5
    module, or None when MT5 cannot be attached."""
    import executor
    mt5 = executor.mt5
    if mt5 is None:
        return None
    if mt5.terminal_info() is None and not initialize_existing(mt5):
        return None
    return mt5


def _fmt_money(v):
    try:
        return f"{float(v):+.2f}"
    except (TypeError, ValueError):
        return str(v)


def _last_ledger_rows(n=3):
    """Last n rows of signals.db 'trades' (the relay ledger), read-only."""
    import executor
    try:
        con = sqlite3.connect(executor.DB)
        try:
            rows = con.execute(
                "SELECT ts, symbol, side, lot, status, detail, ticket FROM trades"
                " ORDER BY id DESC LIMIT ?", (int(n),)).fetchall()
        finally:
            con.close()
    except Exception as e:  # noqa: BLE001
        return [f"  ledger unreadable: {type(e).__name__}: {e}"]
    if not rows:
        return ["  (ledger empty)"]
    out = []
    for ts, symbol, side, lot, status, detail, ticket in rows:
        d = " ".join(str(detail or "").split())
        if len(d) > 60:
            d = d[:57] + "..."
        line = f"  {ts} | {symbol or '-'} {side or '-'} lot {lot if lot is not None else '-'} -> {status}"
        if ticket:
            line += f" #{ticket}"
        if d:
            line += f" ({d})"
        out.append(line)
    return out


def _cmd_status():
    lines = [f"CONSOLE STATUS {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    mt5 = _mt5_or_none()
    if mt5 is None:
        lines.append("MT5: not attached - cannot read account/positions (is the terminal running?)")
    else:
        ai = mt5.account_info()
        if ai is None:
            code, desc = mt5.last_error()
            lines.append(f"MT5: attached but account_info unavailable ({code}, {desc})")
        else:
            lines.append(f"Account {ai.login} @ {ai.server}")
            lines.append(f"  balance {ai.balance:.2f} {ai.currency} | equity {ai.equity:.2f} | free margin {ai.margin_free:.2f}")
        positions = mt5.positions_get()
        if positions is None:
            lines.append("Open positions: API error (positions_get returned None)")
        elif not positions:
            lines.append("Open positions: none")
        else:
            total_pl = sum(p.profit for p in positions)
            lines.append(f"Open positions ({len(positions)}) - total P/L {_fmt_money(total_pl)}:")
            for p in positions:
                d = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
                sl = f"{p.sl:g}" if p.sl else "-"
                lines.append(f"  #{p.ticket} {p.symbol} {d} {p.volume:g} lots | SL {sl} | P/L {_fmt_money(p.profit)}")
    cfg = load_config()
    if _ENGINE_STARTED is None:
        lines.append("Engine uptime: not serving yet (starting up)")
    else:
        up = max(0, int(time.time() - _ENGINE_STARTED))
        since = time.strftime("%H:%M:%S", time.localtime(_ENGINE_STARTED))
        lines.append(f"Engine uptime: {up // 3600}h {(up % 3600) // 60}m (serving since {since}, pid {os.getpid()})")
    lines.append(f"Mode: {cfg.get('mode')} | HALT: {'ACTIVE' if halted() else 'absent'} | "
                 f"PAUSE: {'ACTIVE (new entries blocked)' if paused() else 'absent'}")
    lines.append("Last ledger rows:")
    lines.extend(_last_ledger_rows(3))
    return "\n".join(lines)


def _fill_type(mt5, sym):
    """Prefer executor's filling-mode helper; fall back to the same bit logic
    if a parallel executor.py edit renames it."""
    try:
        import executor
        return executor._fill_type(sym)
    except Exception:  # noqa: BLE001
        fm = getattr(mt5.symbol_info(sym), "filling_mode", 1)
        if fm & 2:
            return mt5.ORDER_FILLING_IOC
        if fm & 1:
            return mt5.ORDER_FILLING_FOK
        return mt5.ORDER_FILLING_RETURN


def _close_position(mt5, p):
    """Close one open position: same request shape as executor.close_all_positions,
    targeted at this exact ticket. Returns (ok, detail)."""
    tick = mt5.symbol_info_tick(p.symbol)
    if tick is None:
        return False, f"no market data for {p.symbol}"
    side = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    req = {"action": mt5.TRADE_ACTION_DEAL, "position": p.ticket, "symbol": p.symbol,
           "volume": p.volume, "type": side,
           "price": tick.ask if p.type == mt5.POSITION_TYPE_BUY else tick.bid,
           "deviation": 50, "magic": MAGIC, "comment": "sigrelay console close",
           "type_time": mt5.ORDER_TIME_GTC, "type_filling": _fill_type(mt5, p.symbol)}
    res = mt5.order_send(req)
    if res is None:
        return False, f"order_send returned None ({mt5.last_error()})"
    if res.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"retcode {res.retcode} {res.comment}"
    return True, f"filled @ {res.price:g}"


def _cmd_close(arg):
    """close <ticket>: close that EXACT open position (no symbol/magic filter -
    the owner names the position)."""
    ticket_txt = (arg or "").strip()
    if not re.fullmatch(r"\d+", ticket_txt):
        return "usage: close <ticket>  (MT5 position number - see 'status')"
    ticket = int(ticket_txt)
    mt5 = _mt5_or_none()
    if mt5 is None:
        return "close failed: MT5 not attached (is the terminal running?)"
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        return f"close failed: no open position #{ticket}"
    p = positions[0]
    ok, detail = _close_position(mt5, p)
    if not ok:
        return f"close failed for #{ticket}: {detail}"
    d = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
    return f"closed #{p.ticket} {p.symbol} {d} {p.volume:g} lots ({detail}) | P/L at close {_fmt_money(p.profit)}"


def _cmd_closeall():
    import executor
    mt5 = _mt5_or_none()
    if mt5 is None:
        return "closeall failed: MT5 not attached (is the terminal running?)"
    positions = mt5.positions_get()
    if positions is None:
        return "closeall failed: positions_get API error"
    if not positions:
        return "closeall: no open positions"
    pl = sum(p.profit for p in positions)
    close_all = getattr(executor, "close_all_positions", None)
    if callable(close_all):
        n = close_all()  # existing executor helper: closes every open position
    else:  # executor.py reworked: close each exact ticket ourselves
        n = 0
        for p in positions:
            ok, _detail = _close_position(mt5, p)
            n += 1 if ok else 0
    return f"closeall: closed {n}/{len(positions)} position(s) | P/L at close {_fmt_money(pl)}"


def _cmd_pause():
    if paused():
        return "PAUSE already active - new signal entries blocked."
    try:
        with open(PAUSE_FILE, "w", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} console pause (owner DM)\n")
    except OSError as e:
        return f"pause failed: could not write PAUSE file: {e}"
    return ("PAUSE ACTIVE: new signal entries blocked. Open positions keep managing "
            "(manage.py unaffected). DM 'resume' to re-enable entries.")


def _cmd_resume():
    if os.path.exists(PAUSE_FILE):
        try:
            os.remove(PAUSE_FILE)
        except OSError as e:
            return f"resume failed: could not delete PAUSE file: {e}"
        return "PAUSE removed - new signal entries re-enabled."
    return "PAUSE was not active."


def _dispatch_command(name, arg, raw):
    """Route a parsed command to its handler. ALWAYS returns reply text (the
    owner gets feedback even on errors). help/unknown/usage paths are pure."""
    try:
        if name == "help":
            return _HELP_TEXT
        if name == "status":
            return _cmd_status()
        if name == "close":
            return _cmd_close(arg)
        if name == "closeall":
            return _cmd_closeall()
        if name == "pause":
            return _cmd_pause()
        if name == "resume":
            return _cmd_resume()
        return f"unknown command: {raw.strip()!r} - DM 'help' for the list"
    except Exception as e:  # noqa: BLE001
        return f"console command error ({name}): {type(e).__name__}: {e}"


async def _console_reply(text):
    """Send the console reply through notify._send_sync (the same channel as
    every relay report: notify_chat_id from config.json). Runs in a worker
    thread so a slow Telegram API call can never stall signal ingestion."""
    try:
        if hasattr(asyncio, "to_thread"):
            sent = await asyncio.to_thread(notify._send_sync, text)
        else:  # pragma: no cover - old-Python fallback
            sent = await asyncio.get_event_loop().run_in_executor(None, notify._send_sync, text)
        if not sent:
            _clog("reply send returned False (notify._send_sync)")
        return sent
    except Exception as e:  # noqa: BLE001
        _clog(f"reply failed: {type(e).__name__}: {e}")
        return False


async def _console_branch(event):
    """The DM gate for on_message. Returns True when the event is a private
    chat message consumed by the console (command handled, or foreign/empty DM
    silently ignored) - such events NEVER reach the signal path. Returns False
    for channel/group messages so the watched-signal flow below runs exactly
    as before (cost: one int comparison)."""
    try:
        cid = getattr(event, "chat_id", None)
        if not isinstance(cid, int) or cid < 0:
            return False  # channel/group message: the signal path owns it
        msg = getattr(event, "message", None)
        sender_id = getattr(msg, "sender_id", None)
        if classify_dm(cid, sender_id) != "owner":
            _clog(f"DM ignored: sender {sender_id} chat {cid}")  # one line, silent
            return True
        raw = (getattr(msg, "text", None) or getattr(msg, "message", "") or "").strip()
        if not raw:
            _clog("owner DM without text ignored")  # sticker/photo/empty: consumed
            return True
        name, arg = parse_command(raw)
        if name is None:
            return True
        t0 = time.time()
        reply = _dispatch_command(name, arg, raw)
        _clog(f"command {raw!r} handled in {time.time() - t0:.2f}s")
        await _console_reply(reply)
        return True
    except Exception as e:  # noqa: BLE001
        _clog(f"console branch error: {type(e).__name__}: {e}")
        return True  # a DM must never fall through to the signal path


async def on_message(event, client):
    try:
        # -- Telegram console branch ------------------------------------------
        # A DM (positive Telethon chat id) is a console event, never a signal:
        # handled and consumed here, before any OCR/AI/parse work. Channel and
        # group messages fail the cheap id check and flow on unchanged.
        if await _console_branch(event):
            return
        import ai_filter
        cfg = load_config()
        msg = event.message
        t0 = time.time()
        raw = (msg.text or msg.message or "").strip()
        via_ocr = False
        if not raw and getattr(msg, "photo", None):
            raw = await ai_filter.ocr_message(msg)
            via_ocr = bool(raw)
        if not raw:
            return
        chat_title = ""
        try:
            chat = await event.get_chat()
            chat_title = getattr(chat, "title", None) or getattr(chat, "username", "") or str(event.chat_id)
        except Exception:  # noqa: BLE001
            chat_title = str(event.chat_id)
        tag = f"[{chat_title}]"
        msg_id = f"{event.chat_id}:{msg.id}"
        t_ocr = time.time() - t0

        # scalp360 zone-aware parse (ADDITIVE parallel check ONLY: the
        # existing parser below remains the sole input to execution). The
        # bridge's gold parser preserves entry/TP zones instead of
        # collapsing them to a single price; a NEW_ENTRY confirmation is
        # logged to daemon.log for audit. Any bridge failure is swallowed.
        if _bridge is not None:
            try:
                _ev = _bridge.parse_signal(raw, str(event.chat_id), msg.id)
                if _ev.kind.name == "NEW_ENTRY":
                    _s360_log(f"zone-aware parse OK {tag} {msg_id}")
                    bus.publish({
                        "type": "zone_parsed",
                        "source": "scalp360-bridge",
                        "payload": {"msg_id": msg_id, "kind": _ev.kind.name,
                                    "digest": _ev.digest},
                        "trace_id": msg_id,
                    })
            except Exception as _e:  # noqa: BLE001
                _s360_log(f"zone-aware parse error {msg_id}: {type(_e).__name__}: {_e}")

        parsed = sigparser.parse_signal(raw)
        used_ai = False
        ai_info = ""
        ai_cfg = cfg.get("ai") or {}
        needs_ai = (via_ocr and not parsed.get("parse_ok")) or \
                   (parsed.get("is_signal") and not parsed.get("parse_ok"))
        if needs_ai and ai_cfg.get("enabled", True):
            ai, ai_info = ai_filter.llm_extract(raw)
            cand = ai_filter.to_parsed(ai)
            if cand and cand.get("confidence", 0) >= float(ai_cfg.get("min_confidence", 0.65)):
                parsed = cand
                used_ai = True
        t_parse = time.time() - t0

        # end-to-end trace_id: msg_id '<chat_id>:<message id>' follows the signal
        # from receipt through execution (executor) to position close (manage);
        # queryable at GET /api/events?trace_id=<msg_id>
        from signal_provenance import telegram_provenance
        bus.publish({
            "type": "signal_received",
            "source": f"tg:{event.chat_id}",
            "payload": {"msg_id": msg_id, "chat": chat_title, "via_ocr": via_ocr,
                        "used_ai": used_ai, "parsed": parsed,
                        "provenance": telegram_provenance(event.chat_id, msg)},
            "trace_id": msg_id,
        })

        if not parsed.get("is_signal"):
            return  # not signal-like: ignore (no relay noise)
        if not parsed.get("parse_ok"):
            await notify.send(f"{tag} SIGNAL (needs manual review)\n{raw[:600]}\nreason: {parsed.get('reason')}")
            return

        # results/recap screen: a win post ('TP1 hit +180 pips', 'profit
        # booked', win screenshots) carries side+symbol+numbers too, so the
        # regex fast-path parses it as a FRESH trade - the bug this kills.
        # If the text reads like results, the AI validator must confirm a
        # live signal (is_signal + ai.min_confidence) before it may execute;
        # otherwise the post is routed to handle_channel_update (position
        # aware) and never executed as a new trade.
        if not used_ai and ai_filter.looks_like_results(raw):
            screen_ai, screen_info = ai_filter.llm_extract(raw)
            cand = ai_filter.to_parsed(screen_ai)
            if cand and cand.get("confidence", 0) >= float(ai_cfg.get("min_confidence", 0.65)):
                parsed["confidence"] = cand.get("confidence")
                used_ai = True
                ai_info = f"results-screen cleared ({screen_info})"
            else:
                await handle_channel_update(tag, parsed, raw, chat_id=event.chat_id)
                return

        summary = f"{tag} {_fmt_signal(parsed)}" + (f" | AI conf {parsed.get('confidence')}" if used_ai else "")

        if halted():
            await notify.send(summary + "\nHALT active - not executed.")
            return
        if paused():
            # console PAUSE: daemon-side gate, checked exactly like HALT. Blocks
            # NEW entries only - open positions keep managing below/elsewhere.
            await notify.send(summary + "\nPAUSE active - new entries blocked "
                              "(open positions keep managing; DM 'resume').")
            return
        if cfg.get("mode") == "confirm":
            await notify.send(summary + f"\nConfirm mode: reply in the Hermes chat to approve (ref {msg_id}).")
            return

        # analysis layer: cross-channel dedupe + stale-entry check
        dup, note = ai_filter.dedupe_check_and_add(parsed, msg_id)
        if dup:
            await notify.send(f"{tag} {note} - not re-entered")
            return
        # price sanity: market entries must sit within 0.15% of the live
        # price, limit/stop entries within 1.0% - anything else is stale.
        if isinstance(parsed.get("entry"), float):
            tol = 2.0 if parsed.get("order_type", "market") == "market" else 1.0
            sane_err = ai_filter.price_sane(parsed.get("symbol"), parsed.get("entry"), tol_pct=tol)
            if sane_err:
                await notify.send(f"{tag} skipped: stale/invalid entry ({sane_err})")
                return

        # EXECUTE FIRST, report after - cuts notify latency out of the entry path
        # Executor derives trace_id from msg_id; keep its public contract.
        res = execute(parsed, msg_id=msg_id, channel_id=event.chat_id)
        t_exec = time.time() - t0
        status = res.get("status")
        line = {"executed": "EXECUTED", "dry_run_ok": "DRY-RUN OK", "broker_rejected": "BROKER REJECTED",
                "skipped": "SKIPPED"}.get(status, status.upper() if status else "?")
        speed = (f"\u23f1 {t_exec:.1f}s to entry (parse {t_parse - t_ocr:.2f}s"
                 + (f", ocr {t_ocr:.1f}s" if via_ocr else "")
                 + (f", ai {ai_info}" if used_ai else "") + ")")
        await notify.send(f"{summary}\n=> {line}: {res.get('detail') or res.get('fill_price') or ''}"
                          + (f" ticket {res['ticket']}" if res.get("ticket") else "")
                          + (f"\n{speed}"))
    except Exception as e:  # noqa: BLE001
        try:
            await notify.send(f"signal-relay error: {type(e).__name__}: {e}")
        except Exception:  # noqa: BLE001
            print("relay error:", e)


_TP_HIT_RE = re.compile(
    r"\b(?:tp|t\.p|take\s*profit|targets?|tgt)(?:\s*\d)?"
    r"(?:\s*(?:is|was|has\s*been|just|already|partially|fully|safely))?\s+hit\b"
    r"|\bhit\s+(?:our\s+|the\s+|my\s+)?(?:tp|t\.p|take\s*profit|targets?)\b"
    r"|\b(?:tp|t\.p)\s*\d?\s*\u2705",
    re.IGNORECASE)


def _mentions_tp_hit(text):
    return bool(text) and bool(_TP_HIT_RE.search(text))


def _ledger_tickets_for_chat(chat_id, db=None):
    """Ledger lineage: executed relay trades whose signal came FROM THIS channel.

    Every executed trade is recorded with msg_id '<chat_id>:<message id>' (see
    on_message), so a channel update from chat C may only touch tickets whose
    msg_id starts with '<C>:'. Positions opened from another channel, manual
    trades and algo positions (absent from the ledger, or recorded without a
    chat-prefixed msg_id) are structurally excluded. Reads the 50 most recent
    executed rows; an unreadable/missing ledger fails CLOSED (empty map ->
    nothing is eligible, nothing gets touched)."""
    out = {}
    if chat_id is None:
        return out
    if db is None:
        import executor
        db = executor.DB
    prefix = f"{chat_id}:"
    try:
        con = sqlite3.connect(db)
        try:
            rows = con.execute(
                "SELECT ticket, msg_id, side, symbol FROM trades"
                " WHERE status='executed' AND ticket IS NOT NULL AND ticket!=0"
                " ORDER BY id DESC LIMIT 50").fetchall()
        finally:
            con.close()
    except Exception as e:  # noqa: BLE001
        print("lineage ledger read failed:", type(e).__name__, e)
        return out
    for ticket, msg_id, side, symbol in rows:
        try:
            t = int(ticket)
        except (TypeError, ValueError):
            continue
        if t and str(msg_id or "").startswith(prefix):
            out[t] = {"ticket": t, "msg_id": str(msg_id), "side": side, "symbol": symbol}
    return out


async def handle_channel_update(tag, parsed, raw, chat_id=None):
    """A results/recap post that survived the regex fast-path. It is bound to
    lineage: the only position it may ever touch is one the relay actually
    holds, that was opened by a signal FROM THE SAME CHANNEL (ledger msg_id
    prefix '<chat_id>:'), and that is still open right now (re-verified in
    mt5.positions_get) - a reported TP hit then protects it by moving SL to
    breakeven via executor.sl_to_breakeven. Everything else - another
    channel's position, a manual/algo trade, a stale recap after we closed -
    is reported and skipped: never executed as a new trade, never modified."""
    try:
        import executor
        excerpt = " ".join((raw or "").split())[:140]
        # lineage gate FIRST: tickets not executed from this exact channel
        # (other channels, manual trades, algo magic 20261015) are ineligible
        # before we even look at MT5.
        eligible = _ledger_tickets_for_chat(chat_id)
        mt5 = _mt5_or_none()
        if mt5 is None:
            await notify.send(f"{tag} channel update: MT5 not connected - nothing touched. {excerpt}")
            return
        if not eligible:
            await notify.send(f"{tag} skipped results/recap post "
                              f"(no executed trade from this channel in the ledger): {excerpt}")
            return
        sym = executor.resolve_symbol(parsed.get("symbol") or "")
        want = mt5.POSITION_TYPE_BUY if parsed.get("action") == "buy" else mt5.POSITION_TYPE_SELL
        positions = mt5.positions_get(symbol=sym) if sym else []
        if positions is None:
            # API error is NOT 'no positions open' - touch nothing.
            await notify.send(f"{tag} channel update: positions_get() returned None "
                              f"(API error) - nothing touched. {excerpt}")
            return
        pos = None
        for p in positions:
            if p.magic == MAGIC and p.type == want and p.ticket in eligible:
                pos = p
                break
        if pos is not None:
            lineage = eligible[pos.ticket]["msg_id"]
            await notify.send(f"{tag} channel update for our position #{pos.ticket} "
                              f"P/L {pos.profit:+.2f} (lineage {lineage})")
            if _mentions_tp_hit(raw):
                status = executor.sl_to_breakeven(pos)
                await notify.send(f"{tag} #{pos.ticket}: TP reported -> {status}")
            return
        await notify.send(f"{tag} skipped results/recap post "
                          f"(no open {parsed.get('symbol')} position from this channel): {excerpt}")
    except Exception as e:  # noqa: BLE001
        try:
            await notify.send(f"{tag} channel-update handler error: {type(e).__name__}: {e}")
        except Exception:  # noqa: BLE001
            print("handle_channel_update error:", e)


class _SyntheticEvent:
    """Minimal event adapter so catch-up messages reuse the live on_message path."""

    def __init__(self, msg, chat_id, client):
        self.message = msg
        self.chat_id = chat_id
        self._client = client

    async def get_chat(self):
        try:
            return await self._client.get_entity(self.chat_id)
        except Exception:  # noqa: BLE001

            class _T:  # fallback title
                title = str(self.chat_id)
            return _T()


async def run():
    global _ENGINE_STARTED
    from telethon import events
    cfg = load_config()
    channels = cfg.get("channels") or []
    if not channels:
        print("No channels configured in config.json - nothing to watch. Run --list-dialogs first.")
        return
    _acquire_single_instance()
    attempt = 0
    try:
        while True:  # never die: 'database is locked'/network errors retry
            attempt += 1
            client = None
            print(f"telethon connect+serve attempt {attempt} ({time.strftime('%H:%M:%S')})")
            try:
                client = _get_client()
                await client.connect()
                if not await client.is_user_authorized():
                    print("Session not authorized - run --login first")
                    raise RuntimeError("session not authorized")
                async def handler(event):
                    await on_message(event, client)

                client.add_event_handler(handler, events.NewMessage(chats=channels))

                async def dm_handler(event):
                    # Telegram console sweep: forward ONLY private chats
                    # (positive Telethon peer ids) into on_message's console
                    # branch. Channel/group events bail out after one
                    # comparison, so the signal path is untouched and a DM
                    # can never be parsed as a signal.
                    cid = getattr(event, "chat_id", None)
                    if isinstance(cid, int) and cid > 0:
                        await on_message(event, client)

                client.add_event_handler(dm_handler, events.NewMessage())
                _ENGINE_STARTED = _ENGINE_STARTED or time.time()
                await notify.send(f"signal-relay ONLINE - watching {len(channels)} chat(s). "
                                  f"mode={cfg.get('mode')} | console: DM 'help' for commands")
                print("watching:", channels, "- mode:", cfg.get("mode"))
                # catch-up: process any signals that arrived while we were down
                try:
                    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
                    for ch in channels:
                        try:
                            async for m in client.iter_messages(ch, limit=20):
                                if m.date and m.date > cutoff:
                                    await on_message(_SyntheticEvent(m, ch, client), client)
                        except Exception as e:  # noqa: BLE001
                            print(f"catchup {ch} failed: {type(e).__name__}")
                    print("catch-up pass complete")
                except Exception as e:  # noqa: BLE001
                    print("catch-up pass failed:", type(e).__name__, str(e)[:80])
                while not os.path.exists(STOP_FILE):
                    await asyncio.sleep(5)
                await notify.send("signal-relay STOPPED (STOP file).")
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                print(f"serve attempt {attempt} failed: {type(e).__name__}: {e} - retrying in 60s")
                if client is not None:
                    try:
                        await client.disconnect()
                    except Exception:  # noqa: BLE001
                        pass
                for _ in range(12):  # 60s backoff, but honor the STOP file
                    if os.path.exists(STOP_FILE):
                        await notify.send("signal-relay STOPPED (STOP file).")
                        return
                    await asyncio.sleep(5)
    finally:
        _release_lock()


def main():
    if "--login" in sys.argv:
        asyncio.run(login_flow())
    elif "--list-dialogs" in sys.argv:
        asyncio.run(list_dialogs())
    else:
        asyncio.run(run())


if __name__ == "__main__":
    main()

## Links from
- [[analyze_channels]]
- [[channel_verify]]
- [[channel_verify2]]
- [[channel_verify3]]
- [[channel_verify_mass]]
- [[channel_verify_scout]]
- [[create_feed_channel]]
- [[integration_status]]
- [[login]]
- [[login2]]
- [[relay_main]]
- [[test_console]]
