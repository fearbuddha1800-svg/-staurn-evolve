---
slug: agent-reports.redevelop-broker-lifecycle
type: note
graph: gitnexus
---

# Broker lifecycle boundary

## Delivered / ownership

Created only `broker_lifecycle.py`, `test_broker_lifecycle.py`, and this report. All three owned paths were absent before work; no pre-existing owned file required a snapshot under `backups/redevelop-20261027T174250Z`. Did not modify integration modules, credentials, configuration, operational markers, suspended workers, or deployments.

## Exact integration contract

```python
from broker_lifecycle import initialize_existing, broker_status

ok = initialize_existing(mt5, *args, **kwargs)  # bool; injected MT5-compatible handle
status = broker_status()                      # JSON-safe local diagnostics
```

- Import is inert: no MetaTrader5 import, process enumeration, broker call, or filesystem mutation. `psutil` is imported lazily only when an authorized attachment reaches process verification.
- `initialize_existing` accepts the MT5 initialization arguments, forwards an explicit path and other parameters unchanged, and returns `False` on denial/unknown/error. Without a path, it requires exactly one verified running terminal and supplies its executable path explicitly. Duplicate positional/keyword path, null path, relative paths and mismatched executables fail closed.
- Module directory is the policy/state root, independent of caller working directory.
- Existing `MAINTENANCE` or `STOP` overrides authorization. An explicit regular-file `BROKER_CONNECT_ALLOWED` is required. `HALT` does not prohibit attachment for protective management. This is attachment policy only, not order authorization.
- Verify process name, executable path, running/status, PID and creation time using psutil; reject inaccessible/ambiguous identity and recheck immediately before initialization. No failures/unknowns authorize default terminal discovery.
- One attempt per invocation, 60-second cooldown after failure, three failed attempts maximum until explicit manual reset. Successful initialization clears failure budget. No sleeps or hidden retry loops.
- `-6` returned by `last_error()` after failed initialization sets a persistent auth latch. Do not consult the handle's potentially stale `last_error()` after a blocked call; use `broker_status()` instead.
- Repository-wide state `.broker-lifecycle.json` is atomically replaced after fsync. Windows `msvcrt` byte-range locks / POSIX `fcntl` locks plus a process-local RLock serialize cooperating processes through the entire attempt. Contended cross-process locks deny immediately. Thread callers serialize then reevaluate policy.
- Reserve the attempt durably before any MT5 call. If the process crashes or result persistence fails, `attempt_reserved` becomes `attempt_outcome_unknown`, blocking all further attempts until manual reset. This also protects an auth result that could not be saved. Malformed/unreadable state denies rather than silently resetting.
- No credentials, server names, account arguments, exception text, or broker error messages are persisted; only integer error codes and static reasons.

### `broker_status()` fields

Normal local snapshot: `eligible`, `reason`, `last_check_reason`, `last_attempt_reason`, `attempts`, `max_attempts`, `next_retry_at`, `auth_latched`, `last_error_code`, `live_verified`.

`eligible` means local marker/state policy only, not verified terminal/account connectivity. `reason` prioritizes active holds/persistent blocks; `last_check_reason` preserves the calling process's most recent exact denial; `last_attempt_reason` is shared persisted history. `connected` is historical, never live telemetry; `live_verified` is always false. Invalid/unreadable state gives a smaller fail-closed dictionary with `eligible=False`, reason, `auth_latched=None`, `live_verified=False`. Status never creates locks/state, probes processes, imports MT5, or calls the handle.

### Manual reset: deliberately not an HTTP route

```python
from broker_lifecycle import reset_broker_latch
reset_broker_latch(confirmation='RESET_BROKER_LATCH')
```

Requires an existing `MAINTENANCE` or `STOP` hold and exact confirmation. May repair malformed state. Does not remove holds, create authorization, initialize MT5, start processes, or alter broker/account state. Do not expose this function through an HTTP endpoint or automated recovery routine.

## Verification

Executed on the Windows host, offline:

```text
PYTHONPATH= PYTHONDONTWRITEBYTECODE=1 python -B -m unittest test_broker_lifecycle -v
----------------------------------------------------------------------
Ran 35 tests in 0.360s

OK
```

Tests inject fake MT5 handles/process enumerators and use disposable directories under Hermes scratch. The one child interpreter imports only this helper and holds a test-directory kernel lock; it does not launch a terminal or worker. Coverage includes default denial/no side effects, both holds, HALT protection access, missing/ambiguous terminal, inaccessible process identity, mismatch/invalid paths, last-moment identity change/exit, forwarded arguments and credential redaction, auth latch across fresh imports, failed persistence after auth response, cooldown/budget, crashes, malformed state variants, manual reset, pure status reads, real cross-process lock contention/release, and thread serialization.

An initial run exposed two diagnostic expectations: a reserved attempt is intentionally dominated by `attempt_outcome_unknown` after identity changes. Added `last_check_reason` to preserve the specific identity diagnostic while retaining the durable fail-closed reason; rerun passed all 35 tests.

Read-only actual-root status verification returned:

```json
{"attempts":0,"auth_latched":false,"eligible":false,"last_attempt_reason":"never_attempted","last_check_reason":"not_checked","last_error_code":null,"live_verified":false,"max_attempts":3,"next_retry_at":0.0,"reason":"maintenance"}
```

Observed markers: HALT=true, MAINTENANCE=true, STOP=false, BROKER_CONNECT_ALLOWED=false. Neither lifecycle runtime state nor lock file exists in the actual repository. No real MT5 import/initialization/account/broker/order call was performed. Suspended production processes were not resumed, terminated, restarted, or otherwise touched.

## Important limit / remaining integration responsibility

MT5's Python `initialize` API is not a documented attach-only primitive. A running terminal can exit between the final process check and internal initialization, and MT5 could then launch it. No preflight-only wrapper can honestly eliminate that race. This implementation never calls initialize for a terminal already known missing/uncertain and forces an identified path; **absolute no-autolaunch during terminal-exit races still requires an external OS execution restriction or an actually attach-only broker API**. Do not remove maintenance/authorize deployment while treating this wrapper as an absolute guarantee.

The helper verifies executable process identity, not authenticated broker account identity. Integrators must retain their existing account/order safety checks. Cross-process serialization assumes cooperating workers using the same local policy root/filesystem; same-user malicious modification and noncooperating direct calls are outside this boundary.

Reusable verification procedure: patch the module root and process enumerator before every attach test; never import real MT5; exercise a second interpreter only for local kernel-lock tests; run tests with bytecode disabled; inspect actual-root status only through the pure read API afterward. Integration changes and deployment are outside this worker's ownership.

