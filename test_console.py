"""Console unit tests: command parser, DM auth gate, unknown-command reply,
pause/resume file semantics, and the _console_branch wiring (with notify and
MT5 stubbed - pure python, no Telegram, no trades, machine state untouched).

Same pattern as test_suite.py: print PASS/FAIL per case, exit 0 = all pass.
Run:  PYTHONPATH=. C:/Users/voidk/miniconda3/python.exe test_console.py
"""
import asyncio
import os
import sys
import tempfile

import daemon

fails = 0


def check(name, got, want):
    global fails
    if got != want:
        fails += 1
        print(f"FAIL {name}: got {got!r} want {want!r}")
    else:
        print(f"PASS {name}")


def check_true(name, cond):
    check(name, bool(cond), True)


# ---- parse_command: every command, case-insensitive, leading '/' ----------
PARSE_CASES = [
    ("status", ("status", None)),
    ("/status", ("status", None)),
    ("STATUS", ("status", None)),
    ("  /StAtUs  ", ("status", None)),
    ("/close 123456", ("close", "123456")),
    ("Close 123456", ("close", "123456")),
    ("closeall", ("closeall", None)),
    ("/CloseAll", ("closeall", None)),
    ("pause", ("pause", None)),
    ("/PAUSE", ("pause", None)),
    ("resume", ("resume", None)),
    ("Resume", ("resume", None)),
    ("help", ("help", None)),
    ("/help", ("help", None)),
    ("", (None, None)),
    ("   ", (None, None)),
    ("/", (None, None)),
    ("buy XAUUSD now", ("buy", "XAUUSD")),  # junk word -> unknown at dispatch
]
for raw, want in PARSE_CASES:
    check(f"parse {raw!r}", daemon.parse_command(raw), want)

# ---- classify_dm: the auth gate --------------------------------------------
# watched channels (negative Telethon ids) are NEVER console events, even
# when the message comes from the owner himself
check("classify watched channel from owner",
      daemon.classify_dm(-1002165799093, 8877588890), "channel")
check("classify watched channel from stranger",
      daemon.classify_dm(-1002369502254, 111222333), "channel")
check("classify basic group from owner",
      daemon.classify_dm(-987654321, 8877588890), "channel")
# owner in the daemon's own DM chat -> the only path that yields a command
check("classify owner DM", daemon.classify_dm(8877588890, 8877588890), "owner")
# non-user sender in a DM -> rejected (silently ignored by the branch)
check("classify stranger in daemon DM", daemon.classify_dm(8877588890, 987654321), "foreign")
check("classify bot DM", daemon.classify_dm(609517172, 609517172), "foreign")
# owner typing in some OTHER chat (friend/bot DM) -> not a command
check("classify owner in foreign chat", daemon.classify_dm(555000111, 8877588890), "foreign")
# belt-and-braces channels arg: a listed chat is never treated as a DM
check("classify listed chat", daemon.classify_dm(8877588890, 8877588890, [8877588890]), "channel")

# ---- dispatch: unknown command reply ---------------------------------------
r = daemon._dispatch_command("frobnicate", None, "frobnicate")
check_true("unknown command reply says 'unknown command'", "unknown command" in r)
name, arg = daemon.parse_command("hello")
check_true("plain word DM -> unknown command reply",
           "unknown command" in daemon._dispatch_command(name, arg, "hello"))

# ---- dispatch: help lists every shipped command -----------------------------
r = daemon._dispatch_command("help", None, "help")
for word in ("status", "close <ticket>", "closeall", "pause", "resume", "help"):
    check_true(f"help lists {word!r}", word in r)

# ---- dispatch: close arg validation (pure path - no MT5 touched) ------------
check_true("close without ticket -> usage",
           "usage" in daemon._dispatch_command("close", None, "close"))
check_true("close non-numeric -> usage",
           "usage" in daemon._dispatch_command("close", "abc", "close abc"))
check_true("close negative -> usage",
           "usage" in daemon._dispatch_command("close", "-5", "close -5"))

# ---- pause/resume: real functions, scratch PAUSE file (machine untouched) ---
tmp = tempfile.mkdtemp(prefix="console-test-")
saved_pause = daemon.PAUSE_FILE
try:
    daemon.PAUSE_FILE = os.path.join(tmp, "PAUSE")
    check("no PAUSE initially", daemon.paused(), False)
    check_true("pause reply mentions PAUSE", "PAUSE" in daemon._cmd_pause())
    check("PAUSE exists after pause", daemon.paused(), True)
    check_true("pause is idempotent", "already" in daemon._cmd_pause())
    check_true("resume reply confirms removal", "removed" in daemon._cmd_resume())
    check("PAUSE gone after resume", daemon.paused(), False)
    check_true("resume when absent says not active", "not active" in daemon._cmd_resume())
finally:
    daemon.PAUSE_FILE = saved_pause


# ---- wiring: _console_branch consumes DMs, passes channels through ----------
class _Msg:
    def __init__(self, sender_id, text):
        self.sender_id = sender_id
        self.text = text
        self.message = text


class _Ev:
    def __init__(self, chat_id, sender_id, text):
        self.chat_id = chat_id
        self.message = _Msg(sender_id, text)


_sent = []
_notify_backup = daemon.notify._send_sync
daemon.notify._send_sync = lambda text, chat_id=None: _sent.append(text) or True
try:
    # owner DM command -> consumed + reply sent via notify._send_sync
    consumed = asyncio.run(daemon._console_branch(_Ev(8877588890, 8877588890, "help")))
    check("owner DM consumed", consumed, True)
    check_true("help reply went through notify._send_sync", _sent and "closeall" in _sent[-1])
    # non-user sender -> silently ignored: consumed, NO reply
    _sent.clear()
    consumed = asyncio.run(daemon._console_branch(_Ev(8877588890, 12345, "status")))
    check("stranger DM consumed (ignored)", consumed, True)
    check("stranger DM got no reply", _sent, [])
    # channel message -> NOT consumed: falls through to the signal path
    consumed = asyncio.run(daemon._console_branch(
        _Ev(-1002165799093, 8877588890, "BUY XAUUSD SL 2640 TP 2660")))
    check("channel message not consumed", consumed, False)
finally:
    daemon.notify._send_sync = _notify_backup

print()
print("ALL PASS" if fails == 0 else f"{fails} FAILURE(S)")
sys.exit(0 if fails == 0 else 1)
