#!/usr/bin/env python3
"""Quant HQ control CLI (hq.py) - one entry point for the signal-relay stack.

Stdlib only.  Subcommands:  start | stop | status | token | restart

How components are found (read-only probes):
  * daemon.py / manage.py / strategy.py / strategy2_live.py each own a *.lock
    file next to this script containing their PID; the lock PID decides UP/DOWN
    (alive -> UP, dead -> DOWN).  A missing lock file means "not running".
  * cockpit.py keeps no lock file, so it is detected by a TCP probe on
    port 8490 and its PID is resolved from the process listening on that port
    (netstat).  No PID is ever guessed.

How components are started:
  * Exactly the detached-spawn technique proven by
    ~/.hermes/scripts/signal-relay-watchdog.py:  python -u <script>, cwd=this
    directory, stdout+stderr appended to <script>.log, stdin=DEVNULL,
    PYTHONPATH stripped from the child env, CREATE_NO_WINDOW so no console
    window attaches, and the parent does not wait.  A breakaway-from-job flag
    is attempted first so the child also survives job-object teardown of the
    parent shell; if Windows refuses it, the plain watchdog flags are used.
  * Each source file is syntax-checked (ast.parse) before it is launched, so a
    broken edit fails loudly instead of starting a crash loop.

How components are stopped:
  * A PID is only ever terminated after its executable image is confirmed to be
    python and (when the command line is readable) to reference the expected
    script.  No tree kill (/T) is used, so unrelated processes are never hit.
  * By default the shared STOP flag is written first, which is the stack's own
    graceful shutdown path for the four engines; anything still alive after the
    grace window is then terminated by PID.  --force skips the grace window.
    A STOP flag written by this run is removed again when stop finishes.

hq never talks to MT5 and never places or modifies orders.
Exit codes: 0 = success, 1 = failure.
"""
from __future__ import annotations

import argparse
import ast
import ctypes
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

BASE = Path(__file__).resolve().parent
PORT = 8490
HOST = os.environ.get("COCKPIT_HOST") or "127.0.0.1"
DASHBOARD_URL = "http://%s:%d/" % (HOST, PORT)
TOKEN_FILE = BASE / ".cockpit-token"
PY = r"C:\Users\voidk\miniconda3\python.exe"
if not Path(PY).is_file():
    PY = sys.executable

CREATE_NO_WINDOW = 0x08000000
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
FLAGS = ("PAUSE", "HALT", "STOP", "MAINTENANCE")
ENGINE_DEPS = ("executor.py", "event_bus.py", "parser.py")


@dataclass(frozen=True)
class Component:
    name: str
    script: str
    lock: str = ""
    port: int = 0


COMPONENTS = (
    Component("cockpit", "cockpit.py", port=PORT),
    Component("daemon", "daemon.py", lock="daemon.lock"),
    Component("manage", "manage.py", lock="manage.lock"),
    Component("strategy", "strategy.py", lock="strategy.lock"),
    Component("strategy2", "strategy2_live.py", lock="strategy2.lock"),
)
ENGINES = tuple(c for c in COMPONENTS if c.lock)


# --------------------------------------------------------------------------- #
# process / port probes (read-only)
# --------------------------------------------------------------------------- #
def _pid_alive(pid):
    """True when a Windows PID is alive (OpenProcess + STILL_ACTIVE probe)."""
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
        k32 = ctypes.windll.kernel32
        k32.OpenProcess.restype = ctypes.c_void_p
        k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        k32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        k32.CloseHandle.argtypes = [ctypes.c_void_p]
        h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            if not k32.GetExitCodeProcess(h, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            k32.CloseHandle(h)
    except Exception:  # noqa: BLE001
        return False


def _process_image(pid):
    """Full image path of `pid`, or None when it cannot be read."""
    try:
        k32 = ctypes.windll.kernel32
        k32.OpenProcess.restype = ctypes.c_void_p
        k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        k32.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                                   ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
        k32.CloseHandle.argtypes = [ctypes.c_void_p]
        h = k32.OpenProcess(0x1000, False, int(pid))
        if not h:
            return None
        try:
            buf = ctypes.create_unicode_buffer(1024)
            n = ctypes.c_ulong(1024)
            if not k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
                return None
            return buf.value or None
        finally:
            k32.CloseHandle(h)
    except Exception:  # noqa: BLE001
        return None


def _process_cmdline(pid):
    """Command line of `pid` via CIM, or None when unavailable (detached procs
    can hide it).  Best-effort only: never raises."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             '(Get-CimInstance Win32_Process -Filter "ProcessId=%d").CommandLine' % int(pid)],
            capture_output=True, text=True, timeout=30, creationflags=CREATE_NO_WINDOW)
        return (r.stdout or "").strip() or None
    except Exception:  # noqa: BLE001
        return None


def _port_open(port, host="127.0.0.1", timeout=1.0):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, int(port)))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _port_owner_pid(port):
    """PID of the process LISTENING on `port`, or None when it cannot be read."""
    try:
        r = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True,
                           text=True, errors="replace", timeout=30,
                           creationflags=CREATE_NO_WINDOW)
    except Exception:  # noqa: BLE001
        return None
    for line in (r.stdout or "").splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        if not parts[1].endswith(":%d" % int(port)) or parts[3].upper() != "LISTENING":
            continue
        try:
            return int(parts[4])
        except ValueError:
            continue
    return None


def probe(comp):
    """Read-only snapshot of one component: state UP / DOWN / unknown."""
    if comp.port:
        source = "tcp %d" % comp.port
        if not _port_open(comp.port):
            return {"up": False, "pid": None, "state": "DOWN", "source": source,
                    "detail": "no listener on %s:%d" % (HOST, comp.port)}
        pid = _port_owner_pid(comp.port)
        if pid is None:
            return {"up": True, "pid": None, "state": "UP", "source": source,
                    "detail": "listening on %s:%d; PID unknown (netstat lookup failed)"
                              % (HOST, comp.port)}
        return {"up": True, "pid": pid, "state": "UP", "source": source,
                "detail": "listening on %s:%d" % (HOST, comp.port)}
    lock_path = BASE / comp.lock
    try:
        raw = lock_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return {"up": False, "pid": None, "state": "DOWN", "source": comp.lock,
                "detail": "no %s (not running)" % comp.lock}
    except OSError as exc:
        return {"up": None, "pid": None, "state": "unknown", "source": comp.lock,
                "detail": "%s unreadable (%s)" % (comp.lock, exc.strerror or exc)}
    try:
        pid = int(raw)
    except ValueError:
        return {"up": None, "pid": None, "state": "unknown", "source": comp.lock,
                "detail": "%s holds no PID" % comp.lock}
    if not _pid_alive(pid):
        return {"up": False, "pid": pid, "state": "DOWN", "source": comp.lock,
                "detail": "stale %s (PID %d dead)" % (comp.lock, pid)}
    image = _process_image(pid)
    if image and "python" not in os.path.basename(image).lower():
        return {"up": True, "pid": pid, "state": "UP", "source": comp.lock,
                "detail": "PID %d alive but image is %s (suspicious)"
                          % (pid, os.path.basename(image))}
    return {"up": True, "pid": pid, "state": "UP", "source": comp.lock,
            "detail": "PID %d alive (%s)" % (pid, comp.lock)}


# --------------------------------------------------------------------------- #
# start
# --------------------------------------------------------------------------- #
def _valid_source(path):
    ast.parse(Path(path).read_text(encoding="utf-8-sig"), filename=str(path))


def _spawn(comp):
    """Detached spawn - the watchdog's proven technique (see module docstring)."""
    script = comp.script
    _valid_source(BASE / script)
    if comp.lock:  # the four engines import these modules at startup
        for dep in ENGINE_DEPS:
            _valid_source(BASE / dep)
    log_path = BASE / script.replace(".py", ".log")
    env = {k: v for k, v in os.environ.items() if k.upper() != "PYTHONPATH"}
    env["PYTHONIOENCODING"] = "utf-8"
    argv = [PY, "-u", script]
    with open(log_path, "a", encoding="utf-8") as log:
        try:
            return subprocess.Popen(
                argv, cwd=str(BASE), stdout=log, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, close_fds=True, env=env,
                creationflags=CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB)
        except OSError:
            # Job does not allow breakaway: fall back to the watchdog's exact flags.
            return subprocess.Popen(
                argv, cwd=str(BASE), stdout=log, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, close_fds=True, env=env,
                creationflags=CREATE_NO_WINDOW)


def _await_state(comp, want_up, timeout):
    deadline = time.time() + max(0.0, float(timeout))
    while True:
        snap = probe(comp)
        if bool(snap["up"]) is want_up:
            return snap
        if time.time() >= deadline:
            return snap
        time.sleep(0.5)


def cmd_start(args):
    if (BASE / "STOP").exists() and not args.force:
        print("hq: STOP flag is present - components would exit immediately.")
        print("hq: remove %s (or pass --force) before starting." % (BASE / "STOP"))
        return 1
    if (BASE / "MAINTENANCE").exists():
        print("hq: note: MAINTENANCE flag present - the cron watchdog is holding off; "
              "components started here are not covered by it.")

    rows, failures = [], 0
    for comp in COMPONENTS:
        snap = probe(comp)
        if snap["up"]:
            rows.append((comp.name, "already up", snap["pid"], snap["detail"]))
            continue
        try:
            proc = _spawn(comp)
        except Exception as exc:  # noqa: BLE001
            rows.append((comp.name, "FAILED", None,
                         "spawn failed: %s: %s" % (type(exc).__name__, exc)))
            failures += 1
            continue
        snap = _await_state(comp, True, args.wait)
        if snap["up"]:
            rows.append((comp.name, "STARTED", snap["pid"],
                         "pid %s, detached, log %s" % (proc.pid, comp.script.replace(".py", ".log"))))
        else:
            rows.append((comp.name, "SPAWNED not up", proc.pid,
                         "pid %s alive but not up after %gs - check %s"
                         % (proc.pid, args.wait, comp.script.replace(".py", ".log"))))
            failures += 1

    print("Quant HQ start")
    print(_table(("COMPONENT", "ACTION", "PID", "DETAIL"), rows))
    print()
    print("dashboard: %s" % DASHBOARD_URL)
    return 1 if failures else 0


# --------------------------------------------------------------------------- #
# stop
# --------------------------------------------------------------------------- #
def _kill_guard(pid, script, source):
    """(safe, why) - refuse to terminate anything that is not this component."""
    image = _process_image(pid)
    if image:
        base = os.path.basename(image)
        if "python" not in base.lower():
            return False, "refusing: PID %d runs %s, not python" % (pid, base)
    cmdline = _process_cmdline(pid)
    if cmdline:
        if script.lower() not in cmdline.lower():
            return False, ("refusing: PID %d command line does not reference %s"
                           % (pid, script))
        return True, "identity verified (%s)" % script
    return True, "cmdline unreadable; PID taken from %s" % source


def _terminate(pid):
    try:
        r = subprocess.run(["taskkill", "/PID", str(int(pid)), "/F"],
                           capture_output=True, text=True, errors="replace",
                           timeout=30, creationflags=CREATE_NO_WINDOW)
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _await_down(pid, timeout):
    deadline = time.time() + max(0.0, float(timeout))
    while _pid_alive(pid):
        if time.time() >= deadline:
            return False
        time.sleep(0.25)
    return True


def cmd_stop(args):
    graceful = not args.force
    stop_flag = BASE / "STOP"
    created_stop = False
    rows, failures = [], 0

    pending = [c for c in COMPONENTS if probe(c)["up"]]
    if not pending:
        print("Quant HQ stop")
        print("nothing to do - every component is already down")
        return 0

    try:
        if graceful:
            aware = [c for c in pending if not c.port]
            if aware and not stop_flag.exists():
                stop_flag.write_text("hq stop %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"),
                                     encoding="utf-8")
                created_stop = True
                print("hq: wrote STOP (%s) - graceful shutdown request for %s"
                      % (stop_flag, ", ".join(c.name for c in aware)))
            if aware:
                deadline = time.time() + args.timeout
                while time.time() < deadline:
                    if not any(probe(c)["up"] for c in aware):
                        break
                    time.sleep(0.5)

        for comp in pending:
            snap = probe(comp)
            if not snap["up"]:
                rows.append((comp.name, "stopped", snap["pid"], "exited on the STOP flag"))
                continue
            pid = snap["pid"]
            if not pid:
                rows.append((comp.name, "MANUAL", None,
                             "up but PID unknown (%s) - stop it manually" % snap["source"]))
                failures += 1
                continue
            safe, why = _kill_guard(pid, comp.script, snap["source"])
            if not safe:
                rows.append((comp.name, "REFUSED", pid, why))
                failures += 1
                continue
            _terminate(pid)
            gone = _await_down(pid, 10)
            rows.append((comp.name, "stopped" if gone else "FAILED", pid,
                         ("terminated; " if gone else "still alive; ") + why))
            if not gone:
                failures += 1

        print("Quant HQ stop")
        print(_table(("COMPONENT", "ACTION", "PID", "DETAIL"), rows))
        if failures == 0:
            print()
            print("note: the cron watchdog restarts these components on its next run "
                  "unless STOP or MAINTENANCE exists.")
        return 1 if failures else 0
    finally:
        if created_stop and stop_flag.exists():
            try:
                stop_flag.unlink()
                print("hq: removed the STOP flag written by this run (stack is startable again)")
            except OSError as exc:  # noqa: BLE001
                print("hq: could not remove %s: %s" % (stop_flag, exc))


# --------------------------------------------------------------------------- #
# status / token
# --------------------------------------------------------------------------- #
def cmd_status(args):
    rows, unknowns, downs = [], 0, 0
    for comp in COMPONENTS:
        snap = probe(comp)
        rows.append((comp.name, comp.script, snap["pid"] if snap["pid"] else "-",
                     snap["state"], snap["detail"]))
        if snap["state"] == "unknown":
            unknowns += 1
        elif snap["state"] == "DOWN":
            downs += 1

    print("Quant HQ status  (%s)" % time.strftime("%Y-%m-%d %H:%M:%S"))
    print(_table(("COMPONENT", "SCRIPT", "PID", "STATE", "DETAIL"), rows))
    print()
    print("dashboard : %s%s" % (DASHBOARD_URL, "" if _port_open(PORT) else "  (not listening)"))
    print("flags     : " + " | ".join(
        "%s %s" % (f, "ACTIVE" if (BASE / f).exists() else "absent") for f in FLAGS))
    print("token file: %s%s" % (TOKEN_FILE, "" if TOKEN_FILE.exists() else "  (missing)"))
    print("logs      : %s" % BASE)
    print("summary   : %d up, %d down, %d unknown" % (len(COMPONENTS) - downs - unknowns, downs, unknowns))

    if unknowns:
        return 1  # a check could not be performed
    if args.strict and downs:
        return 1
    return 0


def cmd_token(args):
    env_token = os.environ.get("COCKPIT_TOKEN")
    token = None
    try:
        token = (TOKEN_FILE.read_text(encoding="utf-8")).strip() or None
    except OSError:
        token = None
    if not token and env_token:
        print("token file : %s (missing - using COCKPIT_TOKEN from the environment)" % TOKEN_FILE)
        print("token      : %s" % env_token)
        print("dashboard  : %s" % DASHBOARD_URL)
        return 0
    if not token:
        print("hq: no dashboard token: %s is missing or empty." % TOKEN_FILE)
        print("hq: start cockpit.py once to mint one (load_token creates it).")
        return 1
    print("token file : %s" % TOKEN_FILE)
    print("token      : %s" % token)
    print("dashboard  : %s%s" % (DASHBOARD_URL, "" if _port_open(PORT) else "  (not listening)"))
    print("note       : loopback dashboard; opening the URL auto-exchanges this token for a "
          "session cookie, so pasting it is optional.")
    return 0


# --------------------------------------------------------------------------- #
# restart / plumbing
# --------------------------------------------------------------------------- #
def cmd_restart(args):
    rc_stop = cmd_stop(args)
    if rc_stop != 0:
        print("hq: restart aborted - stop did not complete cleanly")
        return 1
    print()
    return cmd_start(args)


def _table(headers, rows):
    cells = [[str(c) for c in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in cells:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))
    out = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)).rstrip()]
    out.append("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in cells:
        out.append("  ".join((row[i] if i < len(row) else "").ljust(widths[i])
                             for i in range(len(headers))).rstrip())
    return "\n".join(out)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="hq",
        description="Quant HQ control CLI - start/stop/status/token/restart for the "
                    "signal-relay stack (cockpit, daemon, manage, strategy, strategy2_live).",
        epilog="exit codes: 0 = success, 1 = failure.  "
               "hq never places, modifies or closes orders.")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_start = sub.add_parser("start", help="start every component that is not already up",
                             description="Start cockpit.py, daemon.py, manage.py, strategy.py and "
                                         "strategy2_live.py detached. Components already running "
                                         "(lock PID alive / port 8490 listening) are skipped.")
    p_start.add_argument("--wait", type=float, default=20.0, metavar="SECONDS",
                         help="how long to wait for each started component to come up (default 20)")
    p_start.add_argument("--force", action="store_true",
                         help="start even when the STOP flag is present")
    p_start.set_defaults(func=cmd_start)

    p_stop = sub.add_parser("stop", help="stop each component by its lock-file PID",
                            description="Stop every running component. Writes the shared STOP flag "
                                        "first (graceful), then terminates anything still alive by "
                                        "the PID from its lock file / port listener. Refuses to "
                                        "kill a PID that is not a python process.")
    p_stop.add_argument("--timeout", type=float, default=60.0, metavar="SECONDS",
                        help="grace window for the STOP flag before terminating (default 60)")
    p_stop.add_argument("--force", action="store_true",
                        help="skip the graceful STOP window and terminate immediately")
    p_stop.set_defaults(func=cmd_stop)

    p_status = sub.add_parser("status", help="component / PID / UP-DOWN table plus flags and URL",
                              description="Read-only: component, PID and UP/DOWN state from each "
                                          "lock file (cockpit: port 8490), the dashboard URL, the "
                                          "control flags and the token file path.")
    p_status.add_argument("--strict", action="store_true",
                          help="exit 1 when any component is DOWN (default: only unknown checks fail)")
    p_status.set_defaults(func=cmd_status)

    p_token = sub.add_parser("token", help="print the dashboard token and URL",
                             description="Print the dashboard token from .cockpit-token and the "
                                         "URL to open it at.")
    p_token.set_defaults(func=cmd_token)

    p_restart = sub.add_parser("restart", help="stop, then start",
                               description="Stop every component (same semantics as 'stop'), then "
                                           "start every component that is not up.")
    p_restart.add_argument("--timeout", type=float, default=60.0, metavar="SECONDS",
                           help="stop grace window for the STOP flag (default 60)")
    p_restart.add_argument("--wait", type=float, default=20.0, metavar="SECONDS",
                           help="how long to wait for each started component to come up (default 20)")
    p_restart.add_argument("--force", action="store_true",
                           help="skip the graceful STOP window and ignore the STOP flag")
    p_restart.set_defaults(func=cmd_restart)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        print("\nhq: a subcommand is required (start | stop | status | token | restart)")
        return 1
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        print("hq: interrupted", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print("hq: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
