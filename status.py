"""Signal-relay health/ops status -- READ-ONLY, runs standalone.

Reports, in order:
  1. daemon.py / manage.py / strategy.py liveness: RUNNING pid=<pid> or DOWN,
     detected via PowerShell 'Get-CimInstance Win32_Process -Filter
     "Name='python.exe'"' and matching CommandLine against the script name.
     PowerShell is spawned with an explicit argv list (CreateProcess), never
     through a shell, so the WQL quoting arrives intact.
  2. MT5 attach (initialize/shutdown): account login/server/balance and open
     position counts split by magic 20261014 (signal relay) vs 20261015 (algo).
  3. Last 3 lines of daemon.log / manage.log / strategy.log when present.
  4. Kill-switch files in the relay dir: HALT, PAUSE, STOP, HALT-*, ALGO-HALT-*.
  5. Sizes of dedupe.json / manage-state.json / signals.db.

Never writes a file, never trades, never starts or stops any process.
Run:  C:/Users/voidk/miniconda3/python.exe status.py
"""
from broker_lifecycle import initialize_existing, broker_status
import glob
import json
import os
import re
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))

SCRIPTS = ("daemon.py", "manage.py", "strategy.py")
LOGS = ("daemon.log", "manage.log", "strategy.log")
STATE_FILES = ("dedupe.json", "manage-state.json", "signals.db")
RELAY_MAGIC = 20261014  # executor.py orders (signal relay)
ALGO_MAGIC = 20261015   # strategy.py orders (algo)
TAIL_LINES = 3


def _list_python_procs():
    """All python.exe processes as [(pid, commandline)] via a PowerShell CIM
    query. The query string is one argv element handed straight to
    CreateProcess -- no bash/shell in between, so "Name='python.exe'"
    keeps its quotes."""
    ps_cmd = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
              "Select-Object ProcessId,CommandLine | ConvertTo-Json")
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True, errors="replace", timeout=90,
    )
    if proc.returncode != 0:
        err = (proc.stderr or "?").strip().splitlines()
        raise RuntimeError("powershell exit %d: %s"
                           % (proc.returncode, err[0] if err else "no stderr"))
    out = (proc.stdout or "").strip()
    if not out:
        return []
    data = json.loads(out)
    if isinstance(data, dict):  # ConvertTo-Json emits a bare object for 1 hit
        data = [data]
    return [(int(d["ProcessId"]), d.get("CommandLine") or "")
            for d in data if d.get("ProcessId")]


def sec_processes():
    lines = []
    try:
        procs = _list_python_procs()
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        return (["  detection failed: %s" % exc]
                + ["  %-12s UNKNOWN" % s for s in SCRIPTS])
    for script in SCRIPTS:
        pat = re.compile(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(script))
        pids = [str(pid) for pid, cl in procs if pat.search(cl)]
        if pids:
            lines.append("  %-12s RUNNING pid=%s" % (script, ",".join(pids)))
        else:
            lines.append("  %-12s DOWN" % script)
    return lines


def sec_mt5():
    try:
        import MetaTrader5 as mt5
    except Exception as exc:  # noqa: BLE001
        return ["  attach: FAILED (cannot import MetaTrader5: %s)" % exc]
    if not initialize_existing(mt5):
        return ["  attach: BLOCKED/UNAVAILABLE (%s)" % broker_status()]
    lines = ["  attach: OK (initialized, will shutdown at end of section)"]
    try:
        ai = mt5.account_info()
        if ai is None:
            code, desc = mt5.last_error()
            lines.append("  account: unavailable (%s, %s)" % (code, desc))
        else:
            lines.append("  account: login=%s server=%s balance=%.2f %s"
                         % (ai.login, ai.server, ai.balance, ai.currency))
        positions = mt5.positions_get() or []
        n_relay = sum(1 for p in positions if p.magic == RELAY_MAGIC)
        n_algo = sum(1 for p in positions if p.magic == ALGO_MAGIC)
        n_other = len(positions) - n_relay - n_algo
        lines.append("  open positions: total=%d | relay magic %d: %d | "
                     "algo magic %d: %d | other/manual: %d"
                     % (len(positions), RELAY_MAGIC, n_relay,
                        ALGO_MAGIC, n_algo, n_other))
    finally:
        mt5.shutdown()
        lines.append("  shutdown: OK")
    return lines


def sec_logs():
    lines = []
    for name in LOGS:
        path = os.path.join(BASE, name)
        if not os.path.isfile(path):
            lines.append("  %-12s missing" % name)
            continue
        size = os.path.getsize(path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            tail = f.read().splitlines()[-TAIL_LINES:]
        lines.append("  %-12s (%d bytes), last %d line(s):"
                     % (name, size, len(tail)))
        for ln in tail:
            lines.append("    | %s" % ln)
        if not tail:
            lines.append("    | (empty)")
    return lines


def sec_switches():
    lines = []
    for name, note in (("HALT", "executor refuses NEW relay trades"),
                       ("PAUSE", "daemon console: new signal entries blocked (positions keep managing)"),
                       ("STOP", "daemon/manage/strategy loops exit")):
        path = os.path.join(BASE, name)
        lines.append("  %-10s %s" % (name, "PRESENT (%s)" % note if os.path.isfile(path) else "absent"))
    dated = sorted(os.path.basename(p)
                   for pat in ("HALT-*", "ALGO-HALT-*")
                   for p in glob.glob(os.path.join(BASE, pat)))
    if dated:
        lines.append("  dated      PRESENT: %s" % ", ".join(dated))
    else:
        lines.append("  dated      none (no HALT-* or ALGO-HALT-* files)")
    return lines


def sec_state():
    lines = []
    for name in STATE_FILES:
        path = os.path.join(BASE, name)
        if os.path.isfile(path):
            lines.append("  %-18s %d bytes" % (name, os.path.getsize(path)))
        else:
            lines.append("  %-18s missing" % name)
    return lines


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    print("signal-relay status  %s  dir=%s"
          % (time.strftime("%Y-%m-%d %H:%M:%S"), BASE))
    for title, fn in (("[1] processes (python.exe via Get-CimInstance)", sec_processes),
                      ("[2] mt5 attach", sec_mt5),
                      ("[3] log tails (last %d lines)" % TAIL_LINES, sec_logs),
                      ("[4] kill switches", sec_switches),
                      ("[5] state file sizes", sec_state)):
        print()
        print(title)
        try:
            for line in fn():
                print(line)
        except Exception as exc:  # noqa: BLE001 - one bad section must not kill the report
            print("  ERROR: %s: %s" % (type(exc).__name__, exc))


if __name__ == "__main__":
    main()
