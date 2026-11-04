# MT5 engineering handoff — 2026-11-04

Update after tool installation: GitNexus now runs under a dedicated Node 22
runtime and this checkout has been indexed. The bootstrap failure in the original
repair-order notes below is historical. MQL5 `OnTick` is still unresolved by the
graph; Python impact queries work. See `CLOUD_TOOLCHAIN.md` for the verified setup.

The requested product is not complete. Prior conversation claims of compilation,
trained neural networks, working Pine strategy conversion, and ten-agent research
execution are not supported by the copied source. Do not deploy these drafts.

## Verified deliverables

- `tools/ea_readiness.py`: offline include/input/invalid orchestration triage.
  It reports 40 undeclared EA inputs and invalid source directives. It does not
  implement an MQL parser, compiler, strategy tester, or full safety audit.
- `mql5-training/offline_pipeline.py`: provenance/hash checks and reproducible
  retrieval export. Four authored documentation summaries; zero training records.
  See `mql5-training/README.md` for commands and the legacy artifact audit.
- `HybridMicrostructure/AISignalsEngineFailClosed.mqh`: separate replacement
  candidate refusing initialization and emitting only HOLD. It is not integrated
  or MetaEditor-compiled and does not change current EA behavior.
- Two Cloudroom reviews covered EA defects and training artifacts in parallel.
  `ResearchFramework.mq5` remains an invalid draft, not an agent runner.

Validation: 12 new unittest cases passed; Ruff passed on new Python files;
Python syntax compilation passed. The source triage fails as expected on the
existing drafts. No full legacy project suite, terminal compile, backtest,
model training, UI render, Telegram integration test, or trading occurred.

## Repair order

1. Restore GitNexus for this checkout (`/code/Personal`, advertised repository
   `signal-relay`). No local `.gitnexus/run.cjs` or index exists. npm bootstrap
   failed; Bun bootstrap failed building tree-sitter against Node 24. Impact
   callers/processes and risk remain UNKNOWN. Both impact and detect-changes
   were attempted. Do not treat this as a clean graph result or commit gate.
2. Restore explicit parameter enums/inputs, bridge implementations and
   `g_coreParams`. Remove event handlers from includes, repair headers/braces,
   replace MQL4 value-return indicator calls with MQL5 handles/CopyBuffer,
   and correct CopyRates destination types. Compile with MetaEditor and retain
   its actual log. Existing functions were preserved pending required impact.
3. Replace fixed neural predictions and shared Pine heuristics with validated
   implementations. Unknown model availability must reject initialization;
   calibration, expected value, and win probability require measured evidence.
4. Enforce snapback/MTF rejection and direction agreement before order submission.
   Reject invalid risk sizing and unaffordable minimum lots. Repair order-book
   allocation. Preserve symbol/magic isolation and reconcile broker outcomes.
5. Establish closed-bar Pine/MQL5 parity fixtures covering warmup, missing data,
   session boundaries and higher-timeframe confirmation. Distinguish price-bar
   approximations from actual order-book or tick evidence.
6. Run real-tick strategy tests with broker settings and costs recorded, then
   held-out walk-forward and demo forward tests. Keep genuine reports separate
   from hypothetical strategy descriptions. No profitability result exists here.
7. Connect the knowledge export to the actual Hermes application's retrieval
   interface. Identify the runtime/model and licenses before selecting training.
   Locate the local Telegram service/config without exposing credentials, then
   exercise ingestion, replay prevention, provenance and expiry offline.
8. Build and render UI changes against verified runtime states. No UI overhaul,
   marketplace store, commercial product validation, or scheduled agent loop has
   been completed by this handoff.

## Access needed

Cloudroom reports computer access is turned off. The open local MT5 terminal and
local Hermes process cannot be reached from this environment. Turn on computer
access in Cloudroom to enable inspection and MetaEditor/tester work. Credentials
must remain in local environment/secret storage, never chat or Git.

## Official engineering references checked

- [MQL5 OrderSend](https://www.mql5.com/en/docs/trading/ordersend): boolean success
  alone does not establish trade execution; inspect result fields and broker events.
- [MQL5 ONNX](https://www.mql5.com/en/docs/onnx): actual model loading/inference and
  Strategy Tester support are available; class names alone do not supply them.
- [Strategy testing](https://www.mql5.com/en/docs/runtime/testing): document test
  mode, real-tick availability, spread assumptions, and platform limitations.
- [Pine repainting](https://www.tradingview.com/pine-script-docs/concepts/repainting/):
  higher-timeframe confirmation and historical/realtime behavior need explicit
  handling when reproducing strategy signals.
