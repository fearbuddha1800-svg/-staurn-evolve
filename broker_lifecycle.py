"""Fail-closed MT5 attach boundary. Importing this module never imports MT5.

Only initialize_existing may call the injected handle. An operator must start the
terminal manually and create BROKER_CONNECT_ALLOWED; MAINTENANCE/STOP override it.
HALT is entry policy, not an attachment hold. No retries occur inside one call.

OS file locks serialize all cooperating processes, including an entire initialize
call. Attempts are reserved durably before calling MT5, so crashes consume budget.
The OS/process-check-to-initialize race cannot be eliminated by MT5's Python API:
MT5 has no documented attach-only primitive. This boundary minimizes that window,
but cannot guarantee no launch if the terminal exits during initialize itself.
Never use this helper as permission to trade or as an account identity guarantee.
"""
from __future__ import annotations

import contextlib
import json
import math
import ntpath
import os
from pathlib import Path
import stat
import tempfile
import threading
import time

BASE = Path(__file__).resolve().parent
STATE_NAME = '.broker-lifecycle.json'
LOCK_NAME = '.broker-lifecycle.lock'
MAX_ATTEMPTS = 3
COOLDOWN_SECONDS = 60.0
_THREAD_LOCK = threading.RLock()
_DIAGNOSTIC = {'reason': 'not_checked'}


class BoundaryError(Exception):
    pass


def _remember(reason):
    with _THREAD_LOCK:
        _DIAGNOSTIC['reason'] = reason
    return False


def _regular(path):
    """Do not authorize via directories, symlinks, or unreadable metadata."""
    return stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink()


def _hold():
    try:
        for name in ('MAINTENANCE', 'STOP'):
            try:
                (BASE / name).lstat()
            except FileNotFoundError:
                continue
            return name.lower()
        if not _regular(BASE / 'BROKER_CONNECT_ALLOWED'):
            return 'authorization_missing'
    except FileNotFoundError:
        return 'authorization_missing'
    except OSError:
        return 'marker_unreadable'
    return None


def _empty():
    return dict(version=1, attempts=0, next_retry_at=0.0,
                auth_latched=False, reason='never_attempted', last_error_code=None)


def _read_state():
    path = BASE / STATE_NAME
    try:
        if not _regular(path):
            raise BoundaryError('state_invalid')
        if path.stat().st_size > 4096:
            raise BoundaryError('state_invalid')
        data = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return _empty()
    except (OSError, ValueError, UnicodeError) as exc:
        raise BoundaryError('state_invalid') from exc
    expected = set(_empty())
    if not isinstance(data, dict) or set(data) != expected:
        raise BoundaryError('state_invalid')
    if (type(data['version']) is not int or data['version'] != 1
            or type(data['attempts']) is not int
            or not 0 <= data['attempts'] <= MAX_ATTEMPTS
            or type(data['auth_latched']) is not bool
            or type(data['next_retry_at']) not in (int, float)
            or not math.isfinite(data['next_retry_at'])
            or data['next_retry_at'] < 0
            or not isinstance(data['reason'], str)
            or len(data['reason']) > 100
            or (data['last_error_code'] is not None
                and type(data['last_error_code']) is not int)):
        raise BoundaryError('state_invalid')
    if data['last_error_code'] == -6 and not data['auth_latched']:
        raise BoundaryError('state_invalid')
    return data


def _write_state(data):
    """Atomic replace, flushed before exposure; never write supplied credentials."""
    name = None
    try:
        fd, name = tempfile.mkstemp(prefix='.broker-lifecycle-', dir=BASE)
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(data, out, allow_nan=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, BASE / STATE_NAME)
    finally:
        if name is not None:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(name)


@contextlib.contextmanager
def _file_lock():
    """Nonblocking kernel lock; abandoned locks release on process death."""
    with _THREAD_LOCK:
        path = BASE / LOCK_NAME
        if path.is_symlink():
            raise BoundaryError('lock_unavailable')
        with open(path, 'a+b') as handle:
            # Windows byte-range locking permits a byte beyond EOF.
            if os.name == 'nt':
                import msvcrt
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise BoundaryError('lock_busy') from exc
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    raise BoundaryError('lock_busy') from exc
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _process_iter():
    import psutil  # optional dependency, only loaded on authorized attachment
    return psutil.process_iter()


def _path_key(value):
    if not isinstance(value, str) or not value or not ntpath.isabs(value):
        raise BoundaryError('terminal_identity_unknown')
    if ntpath.basename(value).casefold() != 'terminal64.exe':
        raise BoundaryError('terminal_identity_unknown')
    return ntpath.normcase(ntpath.normpath(value))


def _identity(proc):
    if (proc.name().casefold() != 'terminal64.exe' or not proc.is_running()
            or proc.status().casefold() in ('zombie', 'dead', 'stopped', 'suspended')):
        raise BoundaryError('terminal_identity_unknown')
    exe = proc.exe()
    key = _path_key(exe)
    born = proc.create_time()
    if (type(proc.pid) is not int or proc.pid <= 0
            or type(born) not in (int, float) or not math.isfinite(born) or born <= 0):
        raise BoundaryError('terminal_identity_unknown')
    return (proc.pid, born, key), exe


def _existing(requested):
    target = _path_key(requested) if requested is not None else None
    candidates = []
    try:
        for proc in _process_iter():
            # Even an unreadable name makes the inventory uncertain, not permission.
            if proc.name().casefold() != 'terminal64.exe':
                continue
            identity, exe = _identity(proc)
            if target is None or identity[2] == target:
                candidates.append((proc, identity, exe))
    except BoundaryError:
        raise
    except Exception as exc:
        raise BoundaryError('terminal_identity_unknown') from exc
    if not candidates:
        raise BoundaryError('terminal_not_running')
    if len(candidates) != 1:
        raise BoundaryError('terminal_identity_ambiguous')
    return candidates[0]


def _blocked_state(data, now):
    if data['auth_latched']:
        return 'auth_latched'
    if data['reason'] == 'attempt_reserved':
        return 'attempt_outcome_unknown'
    if data['attempts'] >= MAX_ATTEMPTS:
        return 'retry_budget_exhausted'
    if now < data['next_retry_at']:
        return 'cooldown'
    return None


def initialize_existing(mt5, *args, **kwargs) -> bool:
    """Accept mt5.initialize arguments; return False without MT5 calls on denial.

    Explicit path must match exactly one verified running terminal. With no path,
    exactly one terminal must exist and its verified executable path is supplied
    positionally, preventing MT5's default terminal-discovery selection. Other
    arguments are forwarded unchanged; never persisted or exposed in diagnostics.
    Failure budget is global to this repository, not per account/process. Three
    failed/crashed attempts require manual reset; cooldown is 60 seconds.
    """
    hold = _hold()
    if hold:
        return _remember(hold)
    try:
        with _file_lock():
            hold = _hold()
            if hold:
                return _remember(hold)
            data = _read_state()
            now = time.time()
            if not math.isfinite(now) or now < 0:
                raise BoundaryError('clock_invalid')
            reason = _blocked_state(data, now)
            if reason:
                return _remember(reason)
            if args and 'path' in kwargs:
                raise BoundaryError('initialize_arguments_invalid')
            requested = args[0] if args else kwargs.get('path')
            if (args or 'path' in kwargs) and requested is None:
                raise BoundaryError('initialize_arguments_invalid')
            proc, identity, exe = _existing(requested)
            data.update(attempts=data['attempts'] + 1,
                        next_retry_at=now + COOLDOWN_SECONDS,
                        reason='attempt_reserved', last_error_code=None)
            _write_state(data)  # No broker call unless durable reservation succeeds.
            hold = _hold()
            if hold:
                return _remember(hold)
            if _identity(proc)[0] != identity:
                raise BoundaryError('terminal_identity_changed')
            call_args = args if (args or 'path' in kwargs) else (exe,)
            try:
                ok = mt5.initialize(*call_args, **kwargs)
            except Exception:
                data['reason'] = 'initialize_exception'
                _write_state(data)
                return _remember(data['reason'])
            if ok is True:
                data = _empty()
                data['reason'] = 'connected'
            else:
                code = None
                try:
                    error = mt5.last_error()
                    if isinstance(error, (tuple, list)) and error and type(error[0]) is int:
                        code = error[0]
                except Exception:
                    pass
                data.update(reason='auth_latched' if code == -6 else 'initialize_failed',
                            auth_latched=code == -6, last_error_code=code)
            _write_state(data)
            _remember(data['reason'])
            return ok is True
    except BoundaryError as exc:
        return _remember(str(exc))
    except Exception:
        return _remember('boundary_unavailable')


def broker_status() -> dict:
    """Pure local read: no locks/files created, process probes, or MT5 calls.

    connected is historical, never a live-connection assertion. eligible is only
    local policy, never terminal/account verification. Reason supersedes stale
    injected mt5.last_error() when initialize_existing returned False.
    """
    hold = _hold()
    try:
        data = _read_state()
        reason = hold or _blocked_state(data, time.time())
        with _THREAD_LOCK:
            last_reason = _DIAGNOSTIC['reason']
        reason = reason or (last_reason if last_reason != 'not_checked' else data['reason'])
        return dict(eligible=not hold and not _blocked_state(data, time.time()),
                    reason=reason, last_check_reason=last_reason,
                    last_attempt_reason=data['reason'],
                    attempts=data['attempts'], max_attempts=MAX_ATTEMPTS,
                    next_retry_at=data['next_retry_at'], auth_latched=data['auth_latched'],
                    last_error_code=data['last_error_code'], live_verified=False)
    except Exception:
        return dict(eligible=False, reason=hold or 'state_invalid',
                    auth_latched=None, live_verified=False)


def reset_broker_latch(*, confirmation: str) -> bool:
    """Offline operator API only. No HTTP endpoint must expose this function.

    Requires confirmation='RESET_BROKER_LATCH' AND MAINTENANCE or STOP present.
    Does not create authorization, remove holds, call MT5 or start processes.
    Can deliberately repair malformed persisted state under the same kernel lock.
    """
    if confirmation != 'RESET_BROKER_LATCH' or _hold() not in ('maintenance', 'stop'):
        return _remember('manual_reset_denied')
    try:
        with _file_lock():
            if _hold() not in ('maintenance', 'stop'):
                return _remember('manual_reset_denied')
            data = _empty()
            data['reason'] = 'manual_reset'
            _write_state(data)
            _remember('manual_reset')
            return True
    except Exception:
        return _remember('manual_reset_failed')
