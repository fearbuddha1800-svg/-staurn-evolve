# Engineering findings: MT5, Pine and Hermes

Research date: 2026-11-04. Six relevant systems, selected for engineering fit;
no profitability ranking. Sources below are official documentation or maintainer
repositories, read on this date. Documentation URLs are mutable, not version pins.
**Fact** denotes a source-described capability; **Inference** denotes an authored
recommendation, not a verified implementation or measured result in this repo.
No source code was copied. Reuse of ideas does not establish permission to copy
code, redistribute models, or use datasets; review each artifact's terms separately.

## Repository baseline and limits

Read [MT5 engineering status](../../docs/MT5_ENGINEERING_STATUS.md) and
[team checkpoint](../../agent-team/STATUS.md). Their current summaries report
main-EA static triage and fail-closed initialization, but native compilation is
blocked and Pine parity only ready. The engineering handoff retains older findings
that contradict later repair summaries: reconcile by artifact hash and actual logs,
not by choosing the most favorable paragraph. These are document-reported states;
this research did not independently rerun the checkers or inspect native artifacts.

The knowledge pipeline reports four authored summaries and zero training records.
Neither a trained model nor working Telegram/Hermes integration is established.
No terminal, account, trading, training, installation or source change was performed.
GitNexus impact on this new document returned target-not-found and UNKNOWN;
callers/processes are unresolved. A confirming text search found no reference to
ENGINEERING_FINDINGS in docs, agent-team or research. This is a new research-only
artifact, not a graph-based assurance about trading code.

## Six systems: useful patterns and boundaries

### 1. QuantConnect LEAN — explicit simulation assumptions

**Fact:** LEAN separates fill, fee, slippage, brokerage and buying-power models.
Defaults assume liquid instruments; the documentation recommends customization
for illiquid assets or large orders.
[Official reality modeling](https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/key-concepts).

**Inference:** Reuse that separation in MT5 test specifications: record each cost,
volume and margin assumption rather than treating an equity curve as sufficient
evidence. Persist a run manifest and rejected-order counts. A configurable model
is useful architecture, but does not establish realistic calibration or AI skill.

### 2. NautilusTrader — replay through shared engine components

**Fact:** Backtests use the same core engines, cache, message bus and portfolio
components as live trading. Historical streams produce results and metrics;
its backtesting guide distinguishes data/venue configuration, matching, trade
queues and bar execution.
[Official backtesting guide](https://nautilustrader.io/docs/latest/concepts/backtesting/).

**Inference:** Adopt an event contract shared by offline replay and execution
adapters. Log event ordering, strategy decision and broker reconciliation under one
correlation ID. Match claims to data granularity: OHLC replay cannot substantiate
queue position or actual order-book liquidity. Shared components reduce divergence;
they do not prove identical fills or validate predictive models.

### 3. Freqtrade / FreqAI — chronological training lifecycle

**Fact:** FreqAI supports feature/label pipelines, periodic historical retraining,
persisted models and background live retraining.
[Official FreqAI overview](https://www.freqtrade.io/en/stable/freqai/).
Freqtrade's lookahead tool compares baseline and sliced runs to identify biased
signals; its documentation describes caveats, so a passing check is not proof of
absence of every leak.
[Official lookahead analysis](https://www.freqtrade.io/en/stable/lookahead-analysis/).

**Inference:** Borrow rolling fit/predict boundaries and immutable model identities,
not the assumption that retraining creates an edge. Retain training intervals,
preprocessing state, labels and prediction traces. Separate risk limits from model
scores and compare against a non-AI baseline. No installation is proposed.

### 4. TradingView Pine v6 — signal timing is part of the strategy

**Fact:** Realtime and historical calculations can differ. For confirmed
higher-timeframe requests, the documented offset and lookahead settings must be
used together; lookahead without the offset can introduce future information.
[Official repainting guide](https://www.tradingview.com/pine-script-docs/concepts/repainting/).
By default, strategies calculate at bar close and emulator market fills occur on
the next available tick, generally the following bar's open. Execution settings
can change this behavior.
[Official strategy execution](https://www.tradingview.com/pine-script-docs/concepts/strategies/).

**Inference:** Conversion must preserve state, availability timestamps, warmup,
order intent and execution settings, not merely indicator formulas. Save a
bar-by-bar oracle. Distinguish signal parity from broker fill parity. Pine's
emulator is not evidence of real liquidity, external feed provenance or AI quality.

### 5. MetaQuotes MT5 / MQL5 — native inference and broker lifecycle

**Fact:** MQL5 provides ONNX loading, shape configuration and inference, including
historical validation in the tester.
[Official ONNX reference](https://www.mql5.com/en/docs/onnx).
External-interaction functions including WebRequest do not execute in the tester;
optimization also suppresses most Print output.
[Official tester limitations](https://www.mql5.com/en/docs/runtime/testing).
OrderSend success alone is not execution: inspect response codes and reconcile
multiple transaction events.
[Official OrderSend contract](https://www.mql5.com/en/docs/trading/ordersend).

**Inference:** Package deterministic offline input fixtures for Telegram/Hermes
signals and use retained reports rather than Print-only observability. Native ONNX
support does not validate labels, calibration or training provenance.

**Fact:** Market products require compiled EX5/EX4, prohibit DLL calls and profit
promises, and must not present backtests as real trading. Automated validation
checks known programming errors; passing does not guarantee future results.
[Official Market rules](https://www.mql5.com/en/market/rules).
**Inference:** Treat marketplace packaging as a separate release gate after native
engineering evidence; review bridge and model packaging against current rules.

### 6. Nous Research Hermes Agent — orchestration, not a trading engine

**Fact:** The maintainer repository describes a messaging gateway including
Telegram, provider/model configuration, persistent memory and skill creation.
[Official Hermes Agent repository](https://github.com/NousResearch/hermes-agent).
**Inference:** These capabilities fit research retrieval and structured ingestion,
but do not establish a market-data feed, simulator, risk engine or trading model.
The local application's identity/version is unconfirmed; do not assume it is this
project or that an existing retrieval adapter is compatible. Generated skills and
conversation memory are not evidence of neural-network weight training.

## Cross-system design recommendation (inference)

Use the patterns within the existing stack; these are not dependency selections.

| Concern | Best-fit pattern from scan | Concrete repository improvement |
| --- | --- | --- |
| Architecture | LEAN model separation; Nautilus shared events | Separate signal, risk decision, order intent and broker outcome contracts |
| Simulation | Pine timing; Nautilus granularity; MT5 native tests | Freeze timing/cost profiles; compare decisions before comparing fills |
| Data/provenance | FreqAI training lifecycle | Hash raw fixtures, transformations, model and report; retain availability times |
| Risk | LEAN buying-power model; MQL5 broker lifecycle | Deterministic preflight limits and fail-closed unknown states |
| Observability | Nautilus event stream; tester limitations | Replayable audit events and explicit run artifacts, including rejection reasons |
| AI evidence | FreqAI rolling evaluation; ONNX inference | Leakage-controlled held-out predictions plus exported-model parity |
| Hermes boundary | Gateway and retrieval | Untrusted text becomes validated data; no direct authority to submit orders |

Proposed record chain: source receipt → parsed signal → feature snapshot →
model/strategy decision → risk verdict → order intent → broker event. Every stage
should carry source/config/version hashes, UTC event and receipt times, a stable
ID and reason code. Redact tokens and personal content in retained diagnostics.

## Prioritized measurable acceptance gates (proposals, not achieved)

### P0 — establish native and Pine evidence before strategy claims

1. **Native compilation:** close `native-compile` only with actual MetaEditor
   version, source/include hashes, command/config, complete log and EX5 hash.
   Require zero errors and zero unexplained warnings. Static triage cannot pass
   this gate. Keep `ResearchFramework` identified as a preserved invalid draft.
2. **Conversion contract:** for each Pine script, pin its source hash, Pine version,
   inputs, chart type, session/timezone, symbol mapping, tick size, warmup and
   execution flags. Record an explicit unsupported-feature list. Reject any script
   using unsupported intrabar state rather than silently substituting heuristics.
3. **Pine parity:** compare at least 1,000 post-warmup bars per fixture on identical
   OHLC inputs. Cover gaps, missing bars, session/DST boundaries, HTF transitions,
   flat values and insufficient history. Require 100% agreement on signal direction,
   rejection and order-intent timestamps; predeclare numeric tolerance per series
   (initial proposal: absolute 1e-8 + relative 1e-6). No unexplained mismatch passes.
4. **No future dependence:** perturb future bars; require zero changes to earlier
   closed-bar decisions. Replay HTF arrivals incrementally; require zero use before
   confirmation. Record both signal time and earliest eligible fill time.

These gates implement repair-order items 2, 3 and 5 and the team's `pine-parity`
state. Each gate must link machine-readable results and the input hashes.

### P0 — deterministic ingestion and execution safety

5. **Telegram offline ingestion:** use at least 30 fixed messages spanning valid,
   duplicate, expired, edited, reordered, malformed, unauthorized and injection-like
   content. Retain chat/message identity, edit version, receipt/event time, payload
   hash and parser version. Require 100% expected acceptance/rejection and zero
   duplicate order intents across replay plus restart. Treat edits as explicit
   revisions; never as automatic authority to replace a previously executed order.
6. **Expiry and provenance:** define TTL and clock-skew limits in versioned config;
   test exactly at and either side of each boundary. Missing identity, unsupported
   symbol, stale signal or ambiguous price/side must produce zero executable intents.
   Hermes output must cite retained source IDs; injected instructions cannot change
   the allowlist, risk config or execution permissions. Test with network disabled.
7. **Risk and reconciliation:** exercise at least 20 deterministic cases covering
   invalid stop distances, volume steps, unaffordable minimum lots, margin failure,
   stale quotes, spread/exposure/daily-loss limits, rejection, timeout, partial fill,
   restart and duplicate events. Require zero limit breaches and zero blind retry
   orders on unknown outcomes. Reconcile by request/order/deal IDs and symbol/magic;
   replaying duplicate transactions must leave exposure unchanged.
8. **Audit completeness:** 100% of accepted/rejected signals must have a correlation
   ID and reason; every submitted intent must end in a reconciled outcome or explicit
   unresolved alarm that blocks further conflicting orders. No secrets in fixtures
   or logs. Proposed offline ingest-to-verdict p95 budget: 1 second on a recorded
   machine; exclude network/broker latency and report those separately later.

These gates implement handoff items 4 and 7. They propose offline fixtures only;
no Telegram connection, external message or trading authorization is implied.

### P1 — validated models and realistic tests

9. **Model manifest:** require model SHA-256, runtime/opset, feature order/dtypes,
   shapes, training-data hashes, availability timestamps, label horizon,
   preprocessing fit interval, seed and dependency versions. Missing, corrupt,
   incompatible, stale or non-finite artifacts must fail closed in every fixture.
10. **Chronological evaluation:** freeze at least three rolling train/validation/test
    folds; purge overlapping label horizons across boundaries and fit preprocessing
    only on training data. Freeze thresholds before the final held-out evaluation.
    Retain every prediction and compare with a declared non-AI baseline using Brier
    score/calibration for probabilities, plus coverage and cost-adjusted outcomes.
    Report confidence intervals and negative results. Predeclare required sample
    size from target uncertainty; insufficient samples mean inconclusive, not pass.
11. **Export parity:** compare source-runtime and MQL5 ONNX outputs on at least
    1,000 frozen feature vectors, including boundary/missing-value policy cases.
    Proposed tolerance: absolute 1e-5 + relative 1e-4, frozen before running;
    require 100% direction/threshold-decision agreement. Measure latency/memory on
    the target terminal; no inferred performance from another runtime.
12. **Tester realism:** retain real-tick test configuration, broker/server and
    symbol specifications, data coverage/gaps, spread, fees, swap, leverage and
    execution-delay assumptions. Run base and doubled-cost stress profiles.
    Require reproducible decision traces and zero risk-invariant violations;
    generated ticks must be labeled separately from real-tick coverage. Costs and
    missing data may invalidate the experiment even when the EA runs successfully.

These gates implement handoff items 3 and 6. Neither a valid model file nor an
improved backtest metric establishes live readiness or a profitability claim.
Any subsequent demo forward test requires a separate authorized test plan.

### P2 — controlled research delivery

13. Identify the actual Hermes runtime/repository/version before wiring retrieval.
    For 20 fixed research queries require a source-linked answer or explicit
    abstention; require zero fabricated source IDs and zero order submissions.
    Keep retrieved summaries separate from training records and model artifacts.
14. Reconcile team status from retained reports/hashes, not absent local queue state.
    A fresh sandbox missing evidence must show blocked. Never promote checker
    completion into native compile, parity, model validation or release completion.
15. Before a Market release, document each applicable current rule, packaging
    dependency and validation result. Require evidence links for every product
    claim; no backtest described as live results. No release work was performed here.
