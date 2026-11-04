# Offline parity contract fixtures

These synthetic price-bar fixtures define a candidate contract, not an existing
strategy or proof of Pine/MQL parity. No Pine runtime, MetaEditor, ticks, order
book, costs or profitability are measured here. Actual exports from both runtimes
must be compared against this oracle before claiming cross-runtime parity.

All times are integer UTC seconds. A bar becomes visible at open + duration,
including equality. Decisions use only bars closed at `asof`, in ascending order.
SMA(2) requires two contiguous, non-null closes in the same explicit session.
A missing close, a timestamp gap or a session change resets warmup and crossover
history. Missing bars are never forward-filled. Sessions are fixture labels;
exchange timezone/DST calendar generation remains outside this contract.

BUY requires previous close <= previous SMA and current close > current SMA;
SELL reverses those comparisons. Other results are HOLD, including warmup.
Higher-timeframe close is the latest supplied HTF bar with close time <= the
decision time. An incomplete HTF bar cannot leak its close; no HTF bar means null.
These are close-time visibility rules, not a claim that a particular Pine
request.security configuration implements them.

`cases.json` contains hand-calculated expected records. `contract.py` is a small
offline reference evaluator. Tests compare full records and mutate unavailable
future data to check that it cannot affect earlier decisions. The input is
trusted test data, not an ingestion API.

Run `python tools/verify_agent_work.py pine-fixtures` to retain real stdout,
stderr, timestamps and source hashes. Full parity remains blocked on actual
Pine and native MQL execution outputs tied to matching source and settings.
