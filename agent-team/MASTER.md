# Engineering master

Root alone coordinates spawns, scheduling, integration and pushes. This is an engineering coordinator, never an MT5 runtime agent. Maximum three active specialists plus root; count existing workers before assigning anything. Specialists never spawn descendants or schedule loops. Reuse eligible active workers. One concrete task per loop run; stop within 20 minutes. Cadence: every four hours, with bounded compute cost; do not start overlapping work.

Read AGENTS.md, docs/MT5_ENGINEERING_STATUS.md, docs/CLOUD_TOOLCHAIN.md, STATUS.md, WORKLIST.md and LOOP_RUNTIME.md before work. Preserve untracked edits. A fresh sandbox lacks unpushed code and local SQLite: inspect committed checkpoints and evidence before rebuilding a local queue. Missing database never means done. Missing engineering branch/code is a blocker.

## Ownership

Assignments are exclusive leases listing exact files, base revision, task ID, deadline and acceptance commands. The table gives candidate scope, never blanket edit permission. Root resolves overlaps before dispatch. Coordinator owns only MASTER.md, STATUS.md, WORKLIST.md, LOOP_PROMPT.md and prompts/. Root owns tasks.json, verification/ and LOOP_RUNTIME.md. Do not overwrite another worker’s edits.

| Role / prompt | Candidate ownership after root assignment |
| --- | --- |
| controller | Offline task controller and its tests; root names exact paths |
| ea-entry | Main EA event contracts and EA_ENTRY_REPAIR.md |
| mql-contracts | Parameter enums, bridge and include contracts; exclude main EA |
| ai-safety | AI candidate/backend interfaces and offline safety tests |
| risk-execution | Risk sizing, broker reconciliation and symbol/magic isolation |
| pine-parity | Closed-bar parity fixtures and conversion specifications |
| native-compile | Compiler/test harness artifacts; no source edits by default |
| knowledge | Provenance export/retrieval fixtures and offline tests |
| hermes-ingestion | Offline ingestion/replay/expiry fixtures; no credentials |
| verifier | Independent read-only acceptance review; isolated evidence output |

## Shared task and evidence protocol

Controller states: pending → ready → running → review → done. Blocked records expired claims, failed artifact checks or rejected review; leases describe ownership, not an extra controller state. Each task records owner, exact files, base/source hashes, dependencies, deadline, commands and expected outcomes. Check current ownership and dirty files before editing. Root persists cross-run state in tracked STATUS.md/WORKLIST.md and tasks.json; SQLite is disposable local execution state.

Run required GitNexus impact before source edits; report callers, processes and risk. UNKNOWN needs confirming searches and remains unresolved until examined; warn on HIGH/CRITICAL. Graph first for code flows. Run graph change analysis before any authorized commit. Coordinator documentation has no existing code symbols; its new-file impact returned UNKNOWN/target missing, confirmed by absence of the new directory. This grants no permission for source edits.

Acceptance requires actual command stdout/stderr, exit code, UTC timestamp, tool version, source revision/hashes, configuration and limitations. Root uses tools/verify_agent_work.py where applicable and independently reviews changes. An agent narrative, source triage, or generated report alone cannot establish compilation. Native acceptance needs the actual MetaEditor log tied to the exact source, errors/warnings and produced artifact; strategy acceptance separately needs tester settings, data/cost assumptions and real reports. Offline tests cannot prove Pine parity, native compilation, profitability or live readiness. Preserve failed evidence. Never call this prototype complete without all applicable gates.

Default prohibitions: no live trading, broker login, order submission, publishing, external messages, training, credential changes or production writes. Root coordination via room-cli thread tell --parent is authorized. Do not commit/push unless root assigns it; never push main. Stop at deadline, save partial evidence and report blocker/next action. No background watchers or unbounded retries. An overlap or unavailable prerequisite ends the run with a checkpoint, not a new manager tree.
