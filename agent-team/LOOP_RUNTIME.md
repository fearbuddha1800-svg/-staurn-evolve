# Scheduled engineering lead

Each fresh scheduled run acts as the root coordinator for that run. It may spawn
at most three specialist children through Cloudroom; those children never spawn.
Root owns integration and checkpoints. No descendant manager trees or new loops.

Engineering branch: origin/room/agent-master-435af152. Never push main.
Schedule: every four hours, UTC. One ready task and a requested 20-minute budget
per run. The budget is a prompt constraint, not a process timeout. Runs use Cloud
Credits. No external service secrets are requested (--secrets none).

Fresh runs get Git code, not this sandbox's unpushed edits, tool installations or
local SQLite state. In their own clean run checkout, fetch the engineering branch
and merge its tip with git merge --ff-only FETCH_HEAD. Stop on dirt or divergence.
Never reset another user's branch or overwrite files. Read committed team files.

Before pushing, review the diff, run checks and mandatory GitNexus change analysis,
commit only assigned files, then git pull --rebase origin room/agent-master-435af152.
Recheck conflict resolutions. Push only with
 git push origin HEAD:refs/heads/room/agent-master-435af152
Never force-push. Unknown conflicts require human review. No main merges,
deployment, publishing, trading activation, external messages or model training.

STATUS.md, WORKLIST.md, tasks.json and committed evidence are the cross-run
handoff. Rebuild local SQLite only after inspecting these and verifying current
source hashes. Hash records establish integrity, not authenticated execution.
Check tools and bootstrap as needed from docs/CLOUD_TOOLCHAIN.md. Missing native
MetaEditor is a blocker, not a passed compile check. Avoid repeating unchanged
blockers; choose independent ready work.

Record outcome through room-cli loop report. Archive only the fresh run when no
user action remains. Leave it open for access/conflicts/decisions. Never archive
the original interactive thread. Cloudroom's actual CLI --help wins over stale
examples. This is engineering automation, not an autonomous trading runtime.
