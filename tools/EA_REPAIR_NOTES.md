# EA configuration and bridge repair — 2026-11-04

Scope: only `HybridMicrostructure/ParamUX.mqh`, `AIBridge.mqh`,
`AIBridgeUX.mqh`, and this new note. No commit or native MT5 compilation.

## Impact evidence

Read AGENTS.md, docs/MT5_ENGINEERING_STATUS.md, and the local
`.claude/skills/gitnexus-impact-analysis/SKILL.md` workflow.
Ran `rtk proxy gitnexus impact <target> --direction upstream --repo /code/Personal`
for all three existing owned files and `OnTick`. Repository/worktree:
`signal-relay` at `/code/Personal`. Index reports one commit behind HEAD.
All file results: UNKNOWN, zero resolved callers/processes/modules.
OnTick: target absent, UNKNOWN. These results do not establish low risk.

Precise text reference searches across `*.mq*` confirmed the main EA includes
all three headers; AISignalsEngine includes them again. Guards now prevent
repeated declarations. Main EA calls Init in OnInit, Deinit in OnDeinit,
TickMaintenance in OnTick, and Confirm from BUY/SELL branches in
ProcessSweepLogic. Both Confirm calls have 13 arguments. The two g_coreParams
members are read in OnTick. CheckSnapbackCondition and CheckMTFConfirmation
already exist in the main EA and were not redefined. Graph-level transitive
callers and execution processes remain unresolved; text evidence identifies
these concrete consumers only. No existing function body was edited.

## Repairs

- Restored 40 missing input declarations and four configuration enum types
  corresponding to explicit branches in the EA: money management, capital
  base, SL/TP mode, and session selection.
- Missing numeric/session values use explicit zero/empty unconfigured defaults.
  These are not recovered historical defaults or trading recommendations. MA
  periods, lot/risk, sessions, ratios, and ATR multipliers need owner configuration
  and validation before use. Existing defaults were preserved.
- Added g_coreParams with the exact two consumed fields, copied from inputs in
  AIBridge_Init. Init returns false and logs unavailable backend. The current
  main EA ignores that return; this repair does not claim initialization fails.
- Added the exact 13-argument AIBridge_Confirm signature. It always returns false,
  including when InpAIBridgeEnabled is false. No backend availability or neural
  inference is fabricated; no entry is authorized through this final gate.
- Added empty UX lifecycle hooks with explicit comments that panel rendering,
  outcome tracking, and tuning are unimplemented. No chart objects are created.
- Added include guards and corrected standard color identifiers to clrDarkGray
  and clrWhite.

Zero lot/risk alone is NOT a safety gate: existing NormalizeLot clamps upward.
The unconditional bridge rejection is the entry gate supplied by this repair.
Existing position-management code is unchanged and not audited by this work.

## Verification and remaining blockers

`rtk proxy python tools/ea_readiness.py` exits 1, as expected:
- Main EA: zero undeclared inputs (40 before); AISignalsEngine invalid
  decorative preprocessor header remains.
- ResearchFramework: unsupported delegate_task and invalid header remain.

Source signature assertions pass: 71 unique input declarations across owned
headers; include guards; files under 300 lines; exactly one definition of each
bridge API; both BUY/SELL calls match 13 parameters including const MqlTick&;
Confirm unconditionally rejects; owned includes define no event handlers.
`git diff --check` passes but these source files are untracked, so it cannot
validate their contents. No MQL linter/compiler is available; assertions and
readiness are limited source checks, not typechecking or compilation.

Known untouched blockers: main EA missing semicolon after the H1 handle error
Print; ProcessSweepLogic called with seven arguments but defined with six;
CheckMTFConfirmation uses seven-argument MQL4-style iMA calls. AI engine has
its own OnInit/OnTick/OnDeinit handlers, invalid headers, CopyRates destination
snapshot.Time, and unvalidated/fixed prediction logic. Main snapback/MTF failures
modify fields rather than reject entries. None is repaired by these headers.
Readiness does not detect every one of these defects or prove trading safety.

Native MetaEditor/MT5 remains inaccessible. No compile, strategy test, inference,
live trading, external messages, dependency installation, children, or commit.
Only the authorized parent-thread report is sent via room-cli.
