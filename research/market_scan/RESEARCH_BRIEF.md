# Research brief: an evidence-led MT5 product studio

Research date: 2026-11-04. This is a bounded first pass, not a crawl of the entire
web, a profitability leaderboard, or proof of a defensible market gap.

## Decision

Build a professional strategy engineering workstation around the existing stack:
closed-bar Pine conversion, deterministic risk, source-linked signal ingestion,
clear operational states, and retained verification evidence. Sell specific,
measurable capabilities only after their acceptance gates pass. Validate customer
demand before committing to a commercial product range.

The proposed first product is a strategy/replay and risk workspace with a native
MT5 execution core. The browser companion is a proposed research/observability
surface, not a required dependency for Market products or an order authority.
This is an architecture proposal; no new runtime integration was deployed.

## What was researched

- Twelve official MT5 Market listings across trade managers, scanners, copying
  utilities, conventional EAs and gold/AI products. [Catalog](mql5_catalog.json)
  and [listing findings](MQL5_FINDINGS.md) retain exact URLs and evidence labels.
- Six engineering references: LEAN, NautilusTrader, Freqtrade/FreqAI, TradingView
  Pine, MetaQuotes MT5 and Hermes Agent. [Engineering findings](ENGINEERING_FINDINGS.md)
  link primary docs and define proposed acceptance criteria.
- Three interface references below. These are transferable patterns, not copied
  screenshots, branded layouts or permission to redistribute proprietary libraries.
- One real collector invocation across six approved URLs: four page/hash records,
  one transport/encoding/size failure and one robots-unavailable/denied outcome.
  See [raw metadata](crawl_metadata.jsonl). Failure categories are grouped; the
  collector does not establish the exact underlying cause. No blocked page was
  bypassed. The manual listing study is separate from that six-URL invocation.

No sampled product was installed, bought, traded, reverse-engineered or benchmarked.
Every functional listing claim remains a seller claim. Current sales, prices and
ratings are omitted: they are volatile and do not establish trading merit.

## Findings and product implications

| Observed pattern | Evidence | Our proposed response |
| --- | --- | --- |
| Trade managers advertise risk previews, chart-level planning, partial exits and presets | [CM Trade Manager](https://www.mql5.com/en/market/product/202369), [Trade Assistant](https://www.mql5.com/en/market/product/23415) | Specify account-currency risk, commissions/cost assumptions, broker volume constraints and failure handling before order intent |
| Multi-timeframe scanning reduces repeated chart switching | [RSI Kernel Scanner](https://www.mql5.com/en/market/product/124946), full catalog for other examples | State bar age, confirmation, source and unavailable/stale state per cell; deduplicate alerts |
| AI-labeled products describe different mechanisms | [Unlocked AI](https://www.mql5.com/en/market/product/175271), [Sentinel X](https://www.mql5.com/en/market/product/167360) | Identify actual model/provider/version, feature schema, calibration evidence, expiry, API budget and outage policy; do not equate a label with trained inference |
| A modular engine makes responsibilities inspectable | [LEAN framework](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview) | Separate signal, portfolio/risk, order intent and broker reconciliation; preserve a shared event identity |
| Data absence and query failure need different states | [Grafana state/health](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rule-evaluation/alert-rule-state-and-health/) | Preserve unknown exposure; show last observation time and failure reason; disable conflicting actions |

These are design hypotheses inferred from the sample, not evidence that competing
products lack the proposed safeguards. Public listings often omit implementation
details. A gap in documentation is not proof of a gap in functionality.

## How it should look

Use a restrained, high-information workspace: clear typography, aligned numbers,
a persistent environment label, visible gate state and one decision inspector.
Reserve strong color for actionable state. Avoid decorative motion in the trading
surface; support keyboard navigation, reduced motion and mobile reflow.

1. **Command desk:** price/replay context, source age, model availability and release
   gates. Display unknown account/exposure as unknown, not zero. The decision
   inspector explains HOLD/rejection with source IDs and deterministic reasons.
2. **Research:** a filterable product/source catalog with claim/fact/unknown labels,
   retrieval dates, rights status and direct citations. No composite win-rate score.
3. **Evidence lab:** source/config hashes, compiler output, Pine parity differences,
   model evaluation and broker reconciliation reports. Gate promotion by evidence.
4. **Strategy builder (future):** a versioned spec, supported Pine constructs,
   explicit unsupported behavior and closed-bar replay before terminal export.

Interface references:
- [OpenBB widget anatomy](https://docs.openbb.co/workspace/analysts/widgets/overview)
  describes data sources, metadata, presentation and linked parameters. Proposed
  adaptation: symbol/timeframe context shared across source-attributed panels.
- [TradingView trading primitives](https://www.tradingview.com/charting-library-docs/latest/trading_terminal/Trading-Primitives/)
  distinguishes chart drawings from broker integration; current availability is
  product/version dependent. Proposed adaptation: separate a visual order plan
  from a confirmed broker state. The prototype uses original SVG, no TradingView SDK.
- [Grafana no-data/error handling](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rule-evaluation/nodata-and-error-states/)
  supports explicit degraded states. Proposed adaptation: distinguish missing,
  stale, query failure and disconnected conditions, with timestamp and reason.

[Open the interactive design](design/index.html). It contains three working views,
a deterministic synthetic chart, replay slider and local data-state scenarios.
Every price path is illustrative; it has no live feed, broker, account metrics,
trained model or order endpoint. Evidence labels describe the project checkpoint,
not a dynamically polled backend. Browser checks cover navigation, stale-state
chart removal/control disabling and mobile horizontal fit. These do not establish
full accessibility, production compatibility or backend integration.

## How it should work

source receipt → validated event → closed-bar features → strategy/model decision
→ deterministic risk verdict → immutable order intent → broker reconciliation.

Each record needs a correlation ID, event/receipt/availability times, source and
configuration identities, explicit rejection reason and versioned schema. Keep
Hermes/LLM-generated text outside order authority. AI may provide research or
candidate signals; risk and execution rules remain deterministic and testable.

Pine conversion must preserve warmup, timeframe availability, sessions/timezones,
state and execution timing; it cannot be treated as syntax replacement. Use an
oracle and identical inputs, then distinguish signal parity from broker fills.
[Official Pine repainting](https://www.tradingview.com/pine-script-docs/concepts/repainting/).

External requests cannot execute in MT5 Strategy Tester. A WebRequest cloud-AI
path needs separately disclosed fixture/replay and runtime tests; ordinary tester
results do not alone validate that path.
[Official WebRequest contract](https://www.mql5.com/en/docs/network/webrequest).

Market packaging is a distinct release surface. Verify current rules for DLLs,
compiled artifacts, claims, licensing and permitted dependencies. Formal Market
checks do not certify future profitability. Do not require a separate paid bridge
or external license system without an applicable-rule review.
[Official Market rules](https://www.mql5.com/en/market/rules).

## Evaluation rubric (proposed, not product scores)

Score observable evidence, not adjectives: reliability/recovery 25%, reproducible
validation 25%, risk correctness 20%, workflow/accessibility 15%, operation/support
10%, portability/packaging 5%. Mark unknown dimensions unknown; do not award points
because a listing fails to mention a failure mode. These weights are our proposed
engineering priorities, not a validated predictor of profitability or demand.

## Development handoff

[Development backlog](DEVELOPMENT_BACKLOG.md) converts findings into scoped work.
Reuse existing project components before adding frameworks. Native compilation,
Pine parity and trained-model validation remain separate unachieved gates. No
production dashboard, terminal, Telegram gateway or training runtime was changed.

Collector validation: 26 offline tests and Ruff passed. Prototype validation:
JavaScript syntax check plus four real-browser checks passed. Full legacy trading
tests were not run for this isolated research/collector/proposal change.
