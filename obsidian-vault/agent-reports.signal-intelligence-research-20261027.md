---
slug: agent-reports.signal-intelligence-research-20261027
type: note
graph: gitnexus
---

# EVOLVE — Better Signal Sources and Evidence Gates

Research date: 2026-10-27 UTC. This is a research/design recommendation, not a claim of profitable providers or a deployment. No subscriptions purchased, Telegram sessions opened, broker orders sent, risk settings changed, or accounts switched.

## Actual local evidence

A read-only snapshot of `signals.db` at 2026-10-27T17:40:11Z contained:

- 1,017 `signal_received` rows; 1,013 unique source/message identities; 20 sources.
- 74 parsed candidates, 175 needs-review messages, 764 non-signals.
- Only 42 candidates have comparable entry/stop/ordered-target geometry. Two cross-source exact-geometry echo candidates were observed. Neither proves copying or original authorship.
- Newest stored receipt: 2026-10-21T01:43:20.156112Z. All sources have stale receipts under this report's 24-hour observation threshold. This is not proof that providers stopped posting; the ingest service or capture path may have stopped.
- Three global numeric neural outcomes, without demonstrated source-level cost-adjusted realized-R attribution. No provider ranking by profitability is defensible.

See `source-intelligence-20261027.json` and `.md` for per-source counts, OCR/extraction evidence, timestamps and limitations. These are receipt logs, not complete channel histories.

## Where to find stronger candidates

### 1. Structured, versioned TradingView/Pine strategy alerts — first priority

Use strategies whose actual source can be reviewed, not attractive indicator screenshots. Require confirmed-bar alert behavior, explicit symbol/side/timeframe, signal identity, strategy version, bar-close timestamp, publication timestamp and provenance. A TradingView alert is a transport mechanism, not proof of predictive edge.

Official webhook documentation says alerts are HTTP POSTs, only ports 80 and 443 are accepted, a request exceeding three seconds is cancelled, and two-factor authentication is required. Therefore a future receiver should durably record and acknowledge quickly, then validate asynchronously. Do not put broker passwords in payloads. Validate sender/authentication and enforce deduplication, bounded payload size, strict schema, replay/age checks and symbol allowlists before any execution path.

Confirmed-bar conditions such as `barstate.isconfirmed` can avoid a class of realtime crossover repainting. They do not by themselves eliminate higher-timeframe lookahead, future leakage, revisions or dishonest backtests. Audit those separately. Persist the original Pine text verbatim and hash the strategy version.

Sources:
- https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/
- https://tradingview.com/pine-script-docs/concepts/repainting/

### 2. Existing Telegram sources — repair measurement before adding volume

The immediate dataset contains a large review queue and no recent receipts. Restore authenticated capture separately from broker execution. Do not start a second client against a writable Telethon session already owned by another process. Capture source/message IDs, original publication date, receipt date, edit/reply/forward metadata and original text/media hashes. Preserve later edits as versions, never silently replace the original decision evidence.

Classify entry, recap, management, advertisement, ambiguous and parser error separately. OCR/LLM extraction must return abstention instead of inventing symbol, side or prices. The parser is not an autonomous trading authority. Correlated or copied alerts count as one evidence cluster, not independent votes.

The next useful shortlist is the current sources with enough independently logged forward observations, low missing-data rates, timely original alerts and source-linked outcomes. No channel is recommended as profitable from the current records.

### 3. MQL5 Signals — candidate discovery with inspectable execution history

Inspect age, equity drawdown (not just balance growth), open exposure, leverage, deposit/withdrawal effects, holding duration, broker/server, demo versus real mode and observed copying slippage. Reject hidden tail risk, escalating losing positions and performance dependent on another broker's fills. Do not subscribe or auto-copy as part of this audit.

MetaTrader's official monitoring guide exposes demo/real mode and expected slippage, and explicitly notes that demo providers can take risks they would not take with real money. Broker-recorded history is stronger evidence than chat screenshots; it still does not establish future returns.

Source: https://www.metatrader5.com/en/terminal/help/signals/signal_monitoring

### 4. Myfxbook — verification evidence, not a free signal feed

Check both Track Record and Trading Privileges verification. The former means displayed history matches broker history; the latter verifies ownership/trading access. Neither certifies a profitable strategy or grants us access to private data. Prefer transparent equity, open positions, deposits and sufficiently long histories. Do not infer an order-feed API from a public performance page.

Source: https://www.myfxbook.com/help/knowledge-base/verification/

### 5. CFTC COT — slow regime context only

Use positioning as timestamped context, not an immediate scalp entry. Reports generally reflect Tuesday positions and are released Friday at 15:30 Eastern; holiday schedules can differ. A backtest must use availability/release time, not the earlier observation date, or it leaks future information.

Sources:
- https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm
- https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm

## Intelligence architecture worth building

1. **Capture ledger:** immutable originals plus edit versions, identity, provenance, receipt/publication times, parser version and content hash. Account connection health must remain separate from signal ingestion health.
2. **Extraction:** deterministic parser first; OCR/LLM for ambiguous material with explicit abstention, structured validation, deadlines and provider diagnostics. OAuth provider configuration is not automatically an API-key-compatible `/chat/completions` endpoint.
3. **Evidence layer:** receipt freshness, comparable geometry, duplicate clusters, parse failures, missing/censored outcomes and source-to-decision lineage. This delivery adds a read-only report, not a production execution gate.
4. **Shadow evaluator:** evaluate every eligible candidate independently of whether it was traded. Store source entry evidence, contemporaneous bid/ask, closed-bar features, spread, latency, slippage assumptions and the system's own stop/trailing policy. Record unavailable data rather than fabricate fills.
5. **Outcome attribution:** reconcile broker fills, partial closes, commissions, swaps and final realized R to original source and strategy version. Do not mix paper and broker outcomes. The user's stop-only 2xATR/trailing policy is evaluated separately from the channel's advertised TP/SL results.
6. **Chronological testing:** time-ordered holdout/walk-forward, purging of overlapping outcomes, leakage checks, cost stress, regime and symbol slices, confidence intervals and multiple-testing accounting. Small best-backtest samples are not promotion evidence.
7. **Learning:** train a challenger only on validated labels with costs and feature provenance. Compare out-of-sample against the unchanged baseline. Count gates alone do not prove usable data. Promotion is separately reviewed, versioned and reversible; no automatic increase in risk.
8. **Execution:** reuse the existing protected entry authority only after demo identity, real broker connectivity, fresh quotes, legal 2xATR stops, spread/margin/daily/open-risk and duplicate checks pass. Unknown account or unknown send outcome means no entry. No fixed TP or naked orders.

## Connection finding and new demo account

A standalone `MetaTrader5.initialize()` against the explicit terminal executable failed with `-6 Authorization failed` even without importing the signal-relay modules. Therefore those modules are not necessary to reproduce the current authorization failure. It does not prove every application connection path is correct; that source audit is separate.

The supplied terminal report said `connecting`, `last_authorized_at: null`, zero equity/free margin and cached balance. Community/MQL5.com login is not broker authorization. A selected cached account is not a verified broker session.

When a new demo is created, its exact identity must be explicitly approved and pinned across the relevant guards. Do not simply replace one login string or silently attach to whichever terminal account happens to be active. First perform read-only verification of account login, server, demo trade mode, terminal connectivity, permissions and fresh market data. Credentials must be entered through the terminal or secure credential path, not chat.

## Delivered now / not delivered

Delivered: `source_intelligence.py`, regression tests, real read-only dataset report, sourced candidate-discovery criteria. Additive files only; existing trade code and settings are unchanged by this implementation. Rollback consists of removing these additive artifacts after preserving reports if desired.

Not delivered by this report: restored Telegram ingestion, new demo authorization, repaired AI endpoint, new provider subscription, validated profitable source, model training, automated source promotion or a live deployment. Separate read-only audits are running for connection and extraction defects.

