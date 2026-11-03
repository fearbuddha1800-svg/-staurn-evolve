---
slug: agent-reports.portfolio-risk-delivery
type: note
graph: gitnexus
---

# Portfolio / strategy attribution delivery

## Delivered
- New `portfolio_risk.py`: reuses `quant_analytics.stop_risk` exactly; unknown totals remain null, unprotected/unpriced tickets surfaced, largest-risk concentration, native-unit directional symbol/FX currency exposures, optional explicit portfolio money / % balance caps and existing position cap. No trade operations.
- New `portfolio_attribution.py`: partitions history by (strategy id, version) before using `strategy_identity.attribution_report` (legacy helper groups by id only). Fees/commissions/swaps included. Unknown magics preserved. Current-registry attribution limitation documented.
- `cockpit.py`: defensive `/api/portfolio` live snapshot and `/api/attribution` 90-day UTC BUY/SELL history adapter. `cockpit_runtime.py`: both routes wired to authenticated simple GET dispatch.
- Updated BOTH test route lists, as explicitly required.
- New `test_portfolio_risk.py` (11 tests) and `verify_portfolio_live.py` (real curl bootstrap verification, cookie stays in scratch temporary directory).

## Real test output
Command:
`PYTHONPATH= C:/Users/voidk/miniconda3/python.exe -m pytest test_portfolio_risk.py test_cockpit_api.py test_cockpit_contracts.py test_cockpit_new_features.py -q`

```text
...................................                                      [100%]
35 passed in 1.76s
```

Exact separately requested regression command:
`PYTHONPATH= C:/Users/voidk/miniconda3/python.exe -m pytest test_cockpit_api.py test_cockpit_contracts.py test_cockpit_new_features.py -q`

```text
........................                                                 [100%]
24 passed in 1.69s
```

## Real live verification
Old listener PID 369396 terminated. New cockpit launched through terminal tracked background process `proc_f296cce8b4c5` (launcher PID 360876). Keep it running; parent may re-home it under its persistent supervision on completion if needed.

`PYTHONPATH= C:/Users/voidk/miniconda3/python.exe verify_portfolio_live.py` completed with exit 0. Used real curl.exe GET `/`, extracted single-use nonce, POST `/api/bootstrap` with correct Origin, and curl cookie-authenticated GETs of BOTH endpoints. Complete unmodified JSON responses are in `agent-reports/portfolio-live-responses.json`.

Observed at 2026-10-17T17:32:01Z:
- Portfolio: USD 48.160000000000004 mark-to-stop risk; 4 positions / 4 protected, 0 unprotected; concentration 0.5284468438538206; positions cap 5, observed 4, not breached.
- No monetary portfolio risk cap exists in current config: both monetary and % cap checks explicitly unconfigured/null. Config was NOT edited and sizing/daily caps were NOT misrepresented as portfolio caps.
- Currency decomposition intentionally incomplete: XAUUSD is not an FX contract under broker contract metadata. `by_currency: null`, `exposure_complete: false`, reason and known FX subtotal returned. Risk valuation itself is complete. Root `available: false` truthfully reflects partial currency exposure coverage.
- Attribution: available true, 8 BUY/SELL deals, USD -0.08 total; manual v0.0.0: 3 deals / 0.00; signal-relay v1.0.0: 5 deals / -0.08. Window starts 2026-07-19T17:32:01.368959Z and ends 2026-10-17T17:32:01.368959Z.

## Limitations
Stop risk is NOT a guaranteed maximum loss: excludes fees, gaps, slippage, execution uncertainty. Native exposure units are not account-currency notionals and never summed across unlike currencies. Unsupported non-FX currency decomposition returns unknown, not invented exposure. Historical strategy versions/engines sharing magic cannot be recovered from the registry. No order was placed, modified or closed; no HALT/PAUSE/STOP/MAINTENANCE flags touched.

## Files
Modified cockpit.py, cockpit_runtime.py, test_cockpit_api.py, test_cockpit_new_features.py (route-list-only edits in existing tests).
Created portfolio_risk.py, portfolio_attribution.py, test_portfolio_risk.py, verify_portfolio_live.py, agent-reports/portfolio-live-responses.json, agent-reports/portfolio-risk-delivery.md.

