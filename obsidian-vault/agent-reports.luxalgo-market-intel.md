---
slug: agent-reports.luxalgo-market-intel
type: note
graph: gitnexus
---

# LuxAlgo Market Intelligence Integration Report

## What Shipped
- `market_intel_bridge.py`: A bridge module that provides defensive access to LuxAlgo Market Trackers data (congress, insider, contracts, lobbying, short_volume) with caching, symbol filtering, and limit.
- `test_market_intel_bridge.py`: Unit tests covering unknown kind, missing data, provenance preservation, symbol filtering, limit, and cache behaviour.
- A small synthetic fixture used for testing (created and torn down in tests).

## Where the Data Actually Lives
The market-trackers data is stored in:
```
C:/Users/voidk/.hermes/workspace/luxalgo/market-trackers-data/
```
With subdirectories for each dataset:
- congress/trades/latest.json
- insider/transactions/latest.json
- contracts/awards/latest.json
- lobbying/filings/latest.json
- short-volume/daily/latest.json

## Test Verdict
All tests pass (7/7). The bridge correctly handles unknown kinds, missing data, preserves provenance.sourceUrl, filters by symbol, enforces limits, and caches reads to avoid redundant file I/O.

## How to Call It
```python
from market_intel_bridge import get_market_intel
# Get up to 20 congress trades for symbol NVDA
result = get_market_intel('congress', symbol='NVDA', limit=20)
if result['available']:
    rows = result['rows']  # Each row includes provenance.sourceUrl
else:
    print(f"Data not available: {result['reason']}")
```

