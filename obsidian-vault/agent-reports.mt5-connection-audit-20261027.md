---
slug: agent-reports.mt5-connection-audit-20261027
type: note
graph: gitnexus
---

# MT5 connection audit — 2026-10-27

## Verdict

**There are concrete application defects, but they do not explain an independent MetaTrader5-only initialization failure.** The supplied observation is that a bare probe explicitly targeting `C:/Program Files/MetaTrader 5/terminal64.exe` returns `-6 Authorization failed`, with no account information, after a graceful restart. That observation was supplied to this audit; it was **not reproduced here**. It locates the immediate blocker outside the relay's ordinary signal/guard call paths: terminal/account authorization or the MT5 binding/terminal environment. It does not, by itself, prove a broker outage, an expired demo, incorrect credentials, or a specific wrong server.

Separately, the **current on-disk `executor.py` is an offline stub, not the executor its callers require**. Fixing terminal authorization alone will not repair this source integration. A newly created demo also will not satisfy the manager's existing hard-coded account pin until an explicitly authorized migration changes the expected identity.

## Scope and method

- Text and Python AST inspection only: `daemon.py`, `executor.py`, `manage.py`, `strategy.py`, `strategy2_live.py`, `strategy2_backtest.py`, `strategy_identity.py`, and safe helpers `manager_connection.py`, `mt5_comm.py`, `stop_legality.py`.
- Read applicable `C:/Users/voidk/AGENTS.md`; no additional `AGENTS.md`/`AGENTS.local.md` exists along the project/report ancestry checked. Read `ARCHITECTURE.md` for intended component contracts, not runtime proof.
- All ten Python sources above parsed successfully with `ast.parse`. Enumerated connection calls and executor definitions/imports without executing project code.
- No live project imports, MT5 calls, account changes, trades, stop changes, restarts, credential reads, `.env` reads, or configuration-file reads. No git staging/commits. Only this report is written.
- Findings describe inspected disk content. They do not establish what an already-running process imported, when a file changed, or who changed it. In particular, do not infer an executor overwrite history from its present contents.

## Concrete findings, ranked

### 1. Critical integration blocker: executor contract is absent

**Evidence:** `executor.py:1-10` explicitly describes an offline-only stub. Its public operations are `place_order` (`24-25`) and `run_once` (`107`), not `execute` or `execute_algo`. AST inspection of the complete module finds no definitions/import bindings for `execute`, `halted`, `load_config`, `execute_algo`, `mt5`, `DB`, or `resolve_symbol`.

Callers still require that missing interface:

- `daemon.py:38`: `from executor import execute, halted, load_config`.
- `daemon.py:691`: `execute(parsed, msg_id=msg_id, channel_id=event.chat_id)`.
- `daemon.py:308-310`, `776-784`: accesses `executor.mt5` and `executor.resolve_symbol`.
- `strategy.py:285-290`: the default authority branch calls `executor.execute_algo(...)`.
- `strategy2_live.py:412-416`: likewise calls `executor.execute_algo(...)`.
- Intended architecture still describes both executor entry points at `ARCHITECTURE.md:18-23,62,70-73`.

**Consequence:** Under ordinary local module resolution, daemon startup cannot satisfy its executor import. The strategies' authority branches cannot resolve `execute_algo`. These are source-level failures independent of broker authorization; no live import was attempted to demonstrate them. `strategy2_live.py:403-408` persists a `sending` day reservation *before* the missing call, and `356-358` blocks another same-day attempt. Thus reaching this broken branch can also leave a reserved day without an actual submission; this is a control-flow implication, not an observed state-file condition.

**Fix:** Establish the intended, reviewed executor implementation and its explicit API contract before enabling a new deployment. Preserve the offline stub under an unambiguous offline module/interface if needed. Add offline AST/import-contract tests that do not initialize a database or MT5. Do not simply bypass the shared authority via the legacy direct-send switch. Note `executor.py:257-258` calls `_init_db()` on import; importing it is not a read-only audit technique.

### 2. High migration blocker: manager is pinned to the old demo

**Evidence:** `manage.py:31-33` hard-codes `EXPECTED_DEMO_LOGIN`. The main loop supplies that constant at `328`, not a config-selected identity. `manager_connection.py:19-23` rejects a different login or non-demo trade mode; `38-40` returns without reconnecting over an observed mismatch. `manage.py:329-336` skips management while blocked.

**Consequence:** A new demo correctly fails closed as `account_mismatch`. This check does not call `login`, rewrite terminal account credentials, or cause a bare MT5 authorization error. It runs only after a snapshot can supply account information.

**Fix:** Preserve fail-closed behavior. For a separately approved migration, use one validated non-secret deployment identity containing expected login, exact server, demo mode, and approved terminal path; require explicit approval when changing it. Never auto-adopt the terminal's current account or remove the demo requirement.

### 3. High safety/configuration gap: connection selection is implicit and identity checks are uneven

**Evidence:** Every inspected MT5/broker `initialize()` call has **zero positional arguments and no keyword arguments**:

- `daemon.py:310,777`;
- `manage.py:321,348`;
- `manager_connection.py:45`;
- `strategy.py:343,380`;
- `strategy2_live.py:458,491`.

No `login(...)` call was found in these ten sources. No inspected initialization supplies `login`, `password`, `server`, `path`, or a terminal executable. `manager_connection.py:16-28` validates login/demo/connectivity/position availability but does not validate server or executable/data path. `strategy_identity.py` concerns strategy/magic identity, not broker-account pinning.

The daemon helper accepts a non-None `terminal_info()` without checking `.connected` (`daemon.py:309-312`); its channel-update attach check repeats that pattern (`776-779`). The strategies obtain account data (`strategy.py:257`; `strategy2_live.py:363-365`) without a local login/server/demo comparison. The current executor stub cannot supply a downstream account guard; a hypothetical restored executor must be assessed separately.

**Consequence:** Application attaches can depend on MT5's default terminal selection and saved terminal state. This is a real selection risk, **not evidence that the wrong terminal was selected**. An explicit-path bare probe removes the application's omitted-path ambiguity for that invocation, but does not prove that executable's account/server or user/data-directory state is correct. An executable path is not an account identity.

**Fix:** Centralize explicit approved-path attachment plus exact login/server/demo readback in every process and revalidate before broker mutations. Check transport connectivity and account/position-query availability separately. Keep credentials out of logs. Configuration edits alone currently cannot affect argument-free connection calls.

### 4. Medium operability defect: retry loops hide the actual failure and ignore STOP while attaching

**Evidence:** Initial attach loops at `manage.py:321-323`, `strategy.py:343-345`, and `strategy2_live.py:458-460` retry indefinitely with generic messages, without logging `last_error()` or checking `STOP`. The STOP checks occur only afterward (`manage.py:325`; `strategy.py:355`; `strategy2_live.py:463`). Broad per-pass exception handlers invoke bare initialize again (`manage.py:346-349`; `strategy.py:378-381`; `strategy2_live.py:489-492`), including after non-connection programming/config errors.

`manager_connection.py:44-48` shuts down its binding and retries initialization once; failure becomes `reconnect_failed`, without preserving the binding's native error. Once manager passes start, this can recur on subsequent passes.

**Consequence:** Persistent authorization failure can look like a terminal-not-running condition; STOP cannot end those initial retry loops. Programming errors can trigger unnecessary attach attempts. Reattachment is not a demonstrated remedy for rejected authorization.

**Fix:** Capture sanitized native error immediately, classify authorization versus IPC/transient failures, bound/back off retries, honor STOP during initial attachment, and avoid reconnecting merely because an arbitrary pass raised an exception. Preserve the helper's refusal to reconnect over a known identity mismatch.

### 5. Medium disconnect defect: strategy.py dereferences unavailable account data

**Evidence:** `strategy.py:257-260` dereferences `acct.balance` without a None check. `strategy2_live.py:363-365` does have that check. `strategy.py:244-245,254` also converts `positions_get() is None` into an empty-position list using `or []`.

**Consequence:** Missing account data can raise an application exception and enter the generic reconnect handler. Position-query failure can be mistaken for no positions. Neither behavior explains why an isolated bare initialize returned authorization failure.

**Fix:** Fail closed on absent account data or unavailable position queries; distinguish unavailable from confirmed empty. Carry that requirement into the restored shared executor contract.

## Prior signature suspicions checked against current source

| Suspicion | Current-source conclusion |
|---|---|
| Daemon passes unsupported `trace_id` to `execute` | **Not present at the current execution call.** `daemon.py:690-691` explicitly uses only `msg_id` and `channel_id` keywords. There is no current `execute` implementation to bind against, so end-to-end compatibility is not verified. The concrete blocker is the missing executor interface, not a proven `trace_id` TypeError. |
| `plan_position_stop` rejects `broker_utc_offset_s` | **Not supported by current source.** Caller passes it at `manage.py:179-183`; callee accepts `**options` at `stop_legality.py:151`, forwards them at `168-169`, and `assess_stop_change` explicitly accepts `broker_utc_offset_s=0` at `77-79`. The value is validated at `100-104`. This path is source-compatible; no live stop plan was executed. |

## Authorization boundary and next verification gates

The supplied bare probe does not import the relay, call its missing executor interface, pass its signal keywords, or reach its stop guard. Therefore those application defects cannot directly generate that probe's result. Inspected code contains no explicit MT5 credential login/overwrite operation. It does not prove no other program, terminal UI action, uninspected code, or saved state ever changed an account.

Rank next work by dependency, without performing it in this audit:

1. **Resolve terminal/account authorization independently.** The owner can provision the new demo and confirm its exact broker server/account in the approved terminal. A separately authorized, read-only bare probe must then report successful explicit-path initialization plus matching account/server/demo identity and connected terminal state. Do not equate initializing with an authorized verified account. Do not transmit credentials through chat or log output.
2. **Repair the executor contract offline.** Verify required definitions, caller keywords, guard coverage, and no-live-side-effect contract tests before any runtime activation. Account replacement does not solve missing Python exports.
3. **Approve and configure the new identity atomically across components.** Keep hard failure on old/mismatched/live accounts and pin the approved terminal/server, not just the login number.
4. **Add offline fault tests.** Cover wrong login/server/live mode; None account/terminal/positions; disconnected terminal; `-6` initialization failure; STOP during attach retries; broad non-transport exceptions; and unchanged stop-guard keyword compatibility. Do not send orders as a connectivity test.

No broker state, terminal selection, terminal login history, process import provenance, or active configuration value was independently established by this source-only audit. No product modules were modified.

