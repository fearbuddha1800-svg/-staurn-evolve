# Operator runbooks

## Scope, safety, and evidence
Working directory: `C:/Users/voidk/.hermes/workspace/signal-relay`. Use the configured trading environment, not whichever `python` happens to be on PATH. The watchdog pins `C:/Users/voidk/miniconda3/python.exe`; HQ resolves its own interpreter. Check identity and dependencies before a restart. Commands below are operator actions, not commands executed by this documentation task. Record UTC timestamps, component/PID, account/server identity (redacted), flags, error and result. Never record tokens, sessions, phone codes or passwords.

An entry hold does not close positions. STOP stops managers too: existing broker-side stops remain, but automated break-even/trailing management stops. Arrange authorized manual supervision before shutdown. No procedure authorizes new live trading or removes a durable daily-loss latch implicitly.

## 1. Startup and shutdown
Preflight: validate config JSON without printing secrets; check MT5 is the intended already-running terminal and account; inspect HALT, PAUSE, STOP, MAINTENANCE and SYSTEM_AUTOSTART_ALLOWED. Inspect `python hq.py status` before acting. Do not delete flags merely to make status green.

Approved startup: keep HALT/PAUSE in place during recovery, resolve STOP only after approval, run `python hq.py start --wait 20`, then `python hq.py status --strict`. HQ starts cockpit, daemon, manager, strategy and strategy2; it is not the full watchdog service list. `--force` bypasses STOP protection: not a routine recovery switch. Verify component command identities, fresh logs, `/api/broker`, `/api/identity`, `/api/health` and `/api/state`. A listening port alone is not healthy. Remove only the intended entry hold after explicit authorization and a fresh guard/account review.

Planned shutdown: establish MAINTENANCE first to suppress watchdog launches, arrange open-position supervision, then `python hq.py stop --timeout 60`. HQ writes STOP and escalates surviving identified Python processes after its grace period. Verify status and process command lines: HQ does not own every sidecar or external Node service. STOP-aware collectors should exit; separately inspect LuxAlgo orchestrator/services. Use their owning manager's documented stop procedure after checking its current CLI. Never kill all python/node processes. `hq stop --force` skips grace and is incident-only. Preserve STOP and MAINTENANCE until approved recovery. Rollback is a gated startup, not blanket flag deletion.

## 2. Control flags
|Control|Meaning|Recovery check|
|---|---|---|
|HALT|Blocks new entries in execution paths; relay can continue. Does not flatten.|Review reason and durable loss latch before removing.|
|PAUSE|Daemon pre-execute new-entry gate; existing positions continue management. Not an executor-wide universal veto.|Resume only the intended daemon flow; verify other strategy paths separately.|
|STOP|Cooperative loop termination and watchdog no-launch hold; HQ also escalates on stop timeout.|Confirm all relevant processes stopped; manual start is separate.|
|MAINTENANCE|Watchdog no-launch hold; does not stop running processes or itself block every entry.|Combine with HALT and deliberate shutdown for maintenance.|
|SYSTEM_AUTOSTART_ALLOWED|Watchdog authorization marker; absent means no launches.|Never create automatically during incident recovery.|

To create a marker intentionally: `python -c "from pathlib import Path; Path('MAINTENANCE').touch()"`. To remove one after approval: `python -c "from pathlib import Path; Path('MAINTENANCE').unlink(missing_ok=True)"`. Substitute only a reviewed literal marker. Record ownership/reason outside the flag too. A daily loss latch in `loss_halt.py` is separate durable state: deleting HALT is not a reset protocol.

## 3. Watchdog management
Source: `C:/Users/voidk/.hermes/scripts/signal-relay-watchdog.py`. Its header describes a 15-minute Hermes cron invocation; confirm the actual scheduler configuration, enabled state and next run rather than assuming it is installed. There is no invented Windows service/task name. A manual invocation can start trading components; never run it as a harmless status check.

It refuses launch on MAINTENANCE or STOP or absent SYSTEM_AUTOSTART_ALLOWED, validates config, and acquires a Windows byte lock in `.watchdog.lock`. It checks exact command paths and refuses uncertain process identities. It supervises daemon, manage, both strategies, cockpit, LuxAlgo orchestrator and `neural_label_collector.py watch`. The LuxAlgo manager owns external Node services; watchdog also refreshes news with old-calendar preservation on failure. Before maintenance create MAINTENANCE, disable the identified scheduled invocation if necessary, then verify no new launches across its next due run. Restore scheduling only after identity/guard checks; retain entry holds until approved. Stale lock-file existence alone does not imply an active OS lock. Do not remove live PID locks to force duplicate starts.

## 4. MT5 reconnection
Hold entries; capture last error, connection freshness and expected account identity from existing observational endpoints. Check the intended terminal UI manually: connection, account/server, demo restriction and symbol subscription. `broker_lifecycle.py` and `manager_connection.py` enforce guarded attachment to an existing terminal, account match and demo checks. Do not call unguarded initialize/shutdown from ad hoc probes or start a different terminal to silence errors. If a terminal relaunch is necessary, it is a separately approved operator action, not an automatic retry.

After terminal recovery, use guarded component recovery, verify account/server and broker evidence, reconcile open positions and ledger before replaying any message. Unknown send outcomes require broker reconciliation, not blind order retries. Keep holds if identity or reconciliation is uncertain. No dashboard action can enable trading.

## 5. Telegram re-authentication
Hold entries and suppress supervisor restart; stop the daemon and verify no other process owns `telethon.session`. Back up the session securely while quiesced. `login.py` requires the phone number as argv[1]; calling it without an argument exits. In a private local terminal with history/transcripts disabled, the operator may run the approved interpreter as `python login.py <phone-with-country-code>` using their own number; the phone is briefly visible in the process arguments. Review that privacy trade-off first, or implement and review a private-input wrapper before use. The operator enters login codes and 2FA directly into the interactive prompt, never in chat, logs, command arguments or documentation. Do not reuse a live session from a scout process or delete it to fix a lock. If authorization is revoked, preserve the old session as sensitive evidence and replace only by explicit operator action. Restart one daemon under holds, confirm it receives a known permitted channel event without executing a trade, then approve release. Respect Telegram wait intervals; repeated login loops worsen rate limits.

## 6. Log rotation
Sources are append-opened logs (watchdog inherits child stdout handles); do not rename/truncate an actively held Windows file and assume rotation worked. Set MAINTENANCE, arrange position supervision and stop the owning processes. Identify exact logs, copy to an access-controlled timestamped archive, verify size/hash, then rotate only those closed files and restart under entry hold. Include external service logs under their own manager. Do not purge signals.db, sessions, token files, current incident evidence or SQLite sidecars as 'logs'. Retention and disk thresholds require local policy; none are promised by runtime. Success: new log receives fresh timestamps, archive readable, disk available, no secret exposure. Rollback: stop owner and restore its previous file; preserve both copies if unsure.

## 7. Backup and restore signals.db
Use SQLite online backup, NOT a raw copy of a live database/WAL combination. Store backups on an access-controlled volume, not a public repo. Example from the repository (choose an unused destination):
```bash
python -c "import sqlite3; s=sqlite3.connect('file:signals.db?mode=ro',uri=True); d=sqlite3.connect('signals.backup.db'); s.backup(d); print(d.execute('PRAGMA integrity_check').fetchone()[0]); d.close(); s.close()"
```
Success requires `ok`, an independent read of the resulting backup and recorded SHA-256/size/time. Snapshot relevant config/version and schema inventory separately; protect credentials separately. A backup file existing is not proof of restoreability.

Restore: create MAINTENANCE and entry hold; arrange supervision; stop ALL writers/readers including collectors, strategies and external integrations; confirm process identities and closed DB handles. Preserve a fresh pre-restore SQLite backup and any WAL/SHM as a complete rollback set. Validate the candidate with read-only `PRAGMA integrity_check`, compare sqlite_master/schema and required tables to the current application, and assess event/label provenance. While quiesced, move the original database and matching sidecars together into an incident archive, then stage the validated backup as signals.db on the same volume. Never leave an old -wal beside a replacement DB, and never delete a live WAL. Test the replacement read-only before starting writers.

Restart under HALT/PAUSE, verify schema, row counts, latest events, broker positions and dedupe keys against pre-restore evidence. Old snapshots may forget executed trades: reconcile with broker history before permitting any reprocessing. Keep provenance/loss-halt state consistent; a DB restore is not permission to reset risk state. If verification fails, stop all owners and restore the archived DB plus its matching sidecars together. Rehearse on an isolated copy; this documentation task does not restore production.
