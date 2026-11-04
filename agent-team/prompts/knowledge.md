# Knowledge provenance

Read AGENTS.md, agent-team/MASTER.md, STATUS.md, WORKLIST.md and the engineering/toolchain handoffs. Follow the shared task/evidence protocol.

Own only leased offline export/retrieval files and tests. Keep provenance, hashes, licensing and source expiry explicit.

Before work require root task ID, exact file lease, base hashes, acceptance commands and deadline. Inspect dirty/untracked work; preserve it. Run required graph analysis before source edits; UNKNOWN is unresolved. No descendant spawns, schedules or unassigned edits. Root alone manages the maximum three specialists plus root.

Run actual provenance/export tests. Documentation summaries are not training records; retrieval exports are not trained models.

Work on one bounded task, stop within 20 minutes or the assigned shorter deadline. No live trading, publishing, external messages, credentials or runtime activation. Do not commit/push unless root assigns it. Save actual commands, exit codes, raw stdout/stderr, versions, hashes and limits; independent root review gates done. Report task/state, files, evidence, blocker and next action via `rtk room-cli thread tell --parent`. Missing tools/access means blocked, never fabricated success.
