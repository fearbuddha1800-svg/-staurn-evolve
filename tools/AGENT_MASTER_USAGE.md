# Agent master

Stdlib-only, local SQLite bookkeeping. No agent runtime or command execution.
The coordinator maintains role docs in `agent-team/`. SQLite is local to one
checkout: fresh runs do not share it. Canonical tracked checkpoints belong in
`agent-team/STATUS.md`; the trusted coordinator updates those separately.

Spec is a nonempty JSON array. All fields shown are required; unknown fields
(including commands and pass flags) are rejected.

```json
[{"id":"check-controller","role":"verifier","owned_paths":["reports/controller.json"],"deps":[],"acceptance":[{"id":"report","path":"reports/controller.json","sha256":null}]}]
```

`sha256` is either a lowercase 64-character expected digest or null. Null permits
future artifacts: submit pins the actual nonempty readable file hash, and review
requires the same hash. Known expected digests must match at both stages. Paths
are normalized relative POSIX paths. Dependencies must exist and be acyclic.

```sh
python tools/agent_master.py --db /tmp/agent-state.db --root "$PWD" initialize --spec tasks.json --workers 3
python tools/agent_master.py --db /tmp/agent-state.db --root "$PWD" status
python tools/agent_master.py --db /tmp/agent-state.db --root "$PWD" claim check-controller --owner worker-1 --ttl 900
python tools/agent_master.py --db /tmp/agent-state.db --root "$PWD" submit check-controller --owner worker-1
python tools/agent_master.py --db /tmp/agent-state.db --root "$PWD" review check-controller --reviewer coordinator --decision approve
```

Run actual verification separately, for example the root-owned
`python tools/verify_agent_work.py controller`; use its report path as an acceptance
artifact. The reviewer must inspect that report and confirm checks actually passed.
Hashes prove artifact integrity only: a worker can fabricate report bytes. This is
not authenticated test execution or cryptographic attestation. Reviewer/owner
strings are not authentication; this tool assumes trusted local operators and a
trusted filesystem/database. It never runs a task-supplied command.

API: `Controller(db, root).initialize(tasks, workers=3)`, `status()`,
`claim(id, owner, ttl=900)`, `submit(id, owner)`,
`review(id, reviewer, approve: bool, reason="")`. CLI reports sorted JSON and exits
2 on invalid operations, 0 on accepted operations; inspect task state for failed
verification. SQLite `evidence` rows contain task, phase, serialized measured
checks, and recording time. Reports sort tasks by ID; expiry timestamps reflect
real claim time.

Transitions: pending becomes ready when all deps are done; ready/blocked can be
claimed with completed deps. Running claims expire to blocked. Submission becomes
review on successful measurement or blocked on failure. A different reviewer ID
approves review to done after remeasurement, or rejects to blocked (reason required).
Reclaim clears earlier evidence. Defaults: three running workers; TTL 900 seconds
(maximum 86400). Running tasks reject matching roles (case insensitive) and equal
or ancestor/descendant owned paths (case insensitive). Ownership is a scheduling
declaration, not an OS write sandbox; symlink aliases and concurrent external
filesystem edits require operator discipline. Review tasks do not reserve workers.
No automatic checkpoint sync, scheduling, trading, messaging, or commits.
