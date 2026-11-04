# Cross-run worklist

1. Root reconcile tasks.json, STATUS.md, committed verification evidence and active leases before selecting work.
2. Native compile remains blocked until actual MetaEditor/compiler access and logs exist. Do not replace this gate with static triage.
3. Pine synthetic fixture task completed in run b44fffbf (base 83d1e1f): seven hand-calculated cases, 15 fixture checks and 5 verifier tests passed with independent review. Actual Pine/MQL export comparison remains blocked; obtain matching runtime/compiler evidence before full parity acceptance. Evidence: verification/pine-parity/; exact file lease and hashes: tasks.json and execution.json. Do not repeat this synthetic scope.
4. Subsequent work requires explicit root task/file leases: backend validation, risk/execution, offline Hermes ingestion and measured strategy testing. No runtime activation.

For each run append a concise task ID, revision/hashes, state, evidence paths, blocker and next action to the canonical checkpoint through root integration. Do not silently reset statuses from a missing local database. Root owns the machine-readable task spec and evidence directories.
