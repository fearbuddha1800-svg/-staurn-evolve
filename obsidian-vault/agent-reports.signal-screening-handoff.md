---
slug: agent-reports.signal-screening-handoff
type: note
graph: gitnexus
---

# Signal screening upgrade — verified handoff

## Delivered and verified
- `signal_source_audit.py`: read-only SQLite audit of stored `signal_received` events. Tracks replayed receipt events, exact numeric geometry matches inside a configurable window, same-source repetitions and cross-source echoes. Preserves decimal precision; refuses to infer side or market entry. No broker or network imports and no policy mutations.
- Executed against `signals.db`: 85 unique receipt messages, 14 sources, zero malformed events, zero exact echoes. Only FOUR messages have complete comparable entry/SL/TP geometry. This is insufficient coverage to judge the user's repeated-post complaint. Do not claim the channels are independent or repeat-free.
- `signal_provenance.py` plus additive `daemon.py` payload patch: records source chat/message, reply parent, posting/edit timestamps, forwarding flag and forwarded post number, grouped-message ID. Cross-peer replies do not get a guessed parent trace. No entry, exit, policy, config or service-lifecycle changes.
- 17 offline tests PASS; exact output in `signal-screening-tests.txt`. `daemon.py` compiles. The running daemon was NOT restarted; provenance changes are on disk, not verified live.

## Corrections to prior assistant claims
- Do not assert eight channels should be live or six policies are missing. Historical memories conflict and live configuration was not verified in this pass. Existing shadow settings remain untouched.
- Do not assert a full repair of reply routing. This patch only adds provenance; it does not change follow-up classification/execution.
- Do not treat backtest-positive small samples as validated forward profitability.
- No new provider has been independently validated or enrolled. No claimed new profitable channel.

## Source research: verified official pages
Fetched with urllib, HTTP 200:
1. TradingView webhook documentation: https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/
   Explains POST alerts and JSON messages. Best candidate for structured calls from individually evaluated Pine strategies, not proof that public strategies are profitable. Requires an alert-capable account; do not imply zero-cost entitlement.
2. CFTC COT: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm
   Official positioning data: generally Tuesday observations released Friday. Useful as slow regime context, NOT fresh intraday trade calls.
3. FX Blue Live: https://www.fxblue.com/live/
   Free trading-history analysis/publication service. Use as a place to inspect candidate providers' histories, NOT a signal feed or proof of skill by itself. Examine losses, drawdown, leverage, duration, account identity/type and hidden history.
4. Myfxbook API: https://www.myfxbook.com/api returned HTTP 403. Do not claim API contents or accessibility verified.
Search/extract tools were unreliable: configured ddgs missing; direct extract unsupported. Used direct official-page retrieval instead. No defensible Telegram/Discord provider shortlist established.

## Screening architecture still needed
1. Persist immutable source snapshots and edit history with receipt and source timestamps; associate forwarded/replied messages with explicit provenance. Never infer original authorship solely from first receipt.
2. Classify new entry / update / recap / promotion / ambiguous before trade eligibility. Reply context augments a signal; never invent missing symbol/side from a TP ladder alone.
3. Cluster near-duplicates in SHADOW first: same instrument/direction, instrument-aware entry zones and SL/TP geometry, bounded time, optional text similarity. Identical calls are one idea with multiple observations, not several independent votes. Current audit only covers exact complete geometry.
4. Forward source scoring after spread/slippage/commission, using the system's actual stop/trail rules. Track unique ideas, sample size, uncertainty, latency, drawdown and coverage. Do not rank by advertised win rate or deleted/edited winner recaps.
5. UI source table should expose original observation vs uncertain authorship, duplicates, parse/review failures, policy mode and exact rejection reason. No website redesign required.
6. Validate raw-history coverage and import historical messages read-only before drawing channel-wide conclusions. Existing 85 stored events are not a full channel sweep.
7. Source admission: timestamped pre-move calls, full losing history, no hidden martingale/grid risk, executable latency, out-of-sample forward shadow performance. No automatic promotions based on marketing claims.

## Next safe engineering unit
Build a typed, offline-tested entry/update classifier and replay fixture set using actual raw messages and their reply parents; retain current executor policy. Then evaluate near-match clustering against replay fixtures and measure false merges before any production screening change. No service restart authorized/performed in this work.

