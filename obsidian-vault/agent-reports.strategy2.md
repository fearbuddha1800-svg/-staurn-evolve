---
slug: agent-reports.strategy2
type: note
graph: gitnexus
---

# Strategy 2 — London-Open Breakout (H1, XAUUSD + EURUSD)

## Verdict: FAIL

XAUUSD passes every acceptance criterion; EURUSD does not reach PF 1.10 in any
of the 32 parameter cells tested (best 1.068, and that cell breaks XAUUSD).
Best honest result (selected parameters below): **XAUUSD PF 1.113 / +64.0R /
1052 trades / maxDD 28.3R — EURUSD PF 1.045 / +26.1R / 1109 trades / maxDD 31.8R.**

## Selected parameters (identical for both symbols, spec-faithful)

- Range: H1 bars opening 00:00–06:59 UTC, day valid only with all 7 bars
- Signal window: bars opening 07:00–14:59 UTC (round-2 finding: first close
  beyond the range after 15:00 UTC — post-London drift — is collectively
  negative on BOTH symbols; cutoff added for robustness)
- Entry: first H1 close beyond range ± 0.10×ATR14 (spec buffer); one entry/day;
  fill at the contiguous next H1 open (no weekend fills)
- SL: opposite range edge, distance capped at 1.50×ATR14 (spec cap)
- No fixed TP. Exits mirror manage.py (as simulated in backtest.py): SL→BE
  (+0.01×ATR buffer) at +1R; from +1.5R trail 0.5R behind the bar extreme
- Costs: 0.07R round-trip per trade; conservative same-bar rule = SL checked
  before any BE/trail arming (a bar touching both counts as the loss)
- skip_hours_utc [22,23]: tested in round 1 — made both symbols slightly
  worse — kept OFF per the "only if it improves PF" rule

## Per-symbol results (selected params, 2021-09/12 → 2026-10-16 UTC, all costs included)

| Symbol | Trades | Win% | Net R | PF | maxDD (R) | Avg R/trade | Exits SL/BE/Trail |
|--------|--------|------|-------|-----|-----------|-------------|-------------------|
| XAUUSD | 1052 | 34.9 | +64.0 | 1.113 | 28.3 | +0.061 | 518 / 167 / 367 |
| EURUSD | 1109 | 34.2 | +26.1 | 1.045 | 31.8 | +0.024 | 533 / 197 / 379 |

Acceptance: XAUUSD ✓ PF ✓ trades ✓ DD | EURUSD ✗ PF (1.045 < 1.10) ✗ DD
(31.8R > 30R) ✓ trades (≥100).

## Method / harness conventions (identical rigor to backtest.py)

- Data: cached H1 CSVs (`strategy2_data_XAUUSD.csv` 29,999 bars from 2021-09,
  `strategy2_data_EURUSD.csv` 29,999 bars from 2021-12). Bar timestamps are
  MT5 **server time** (EET = UTC+2 winter / EEST = UTC+3 during EU DST),
  converted per the EU DST calendar (last Sunday of March / October);
  week-opens verified to land Sun 21:00–23:00 UTC. 1311/1585 (XAUUSD) and
  1246/1507 (EURUSD) UTC days have a valid 00:00–07:00 range. Wilder ATR(14)
  identical to strategy.Indicators.
- One position per symbol; signals on a closed bar fill at the next bar open;
  SL checked first within a bar; BE/trail stops moved this bar are effective
  only from the next bar (conservative same-bar rule); no entry on the bar a
  position exited; entry skipped if next bar is not the contiguous hour.

## Parameter rounds (max 3, same params for both symbols)

- **Round 1 — spec exactly as given** (no cutoff): XAUUSD PF 1.099, +59.5R,
  1132 trades, maxDD 29.2R; EURUSD PF 1.028, +16.9R, 1161 trades, maxDD 44.8R.
  skip_hours [22,23] variant: both symbols slightly worse → OFF.
- **Round 2 — 18-cell grid** (cutoff {15,16} × buffer {0.10,0.15,0.20} × cap
  {1.00,1.50,2.00}): cap 1.5 is the only viable stop (1.0 → XAU maxDD 42–46R;
  2.0 → EUR net negative). Cutoff 15 dominates 16. Best joint cell =
  buffer 0.10 / cap 1.5 / cutoff 15 (XAU all-pass; EUR PF 1.045, DD 31.8R).
  Best EUR cell (buffer 0.15): PF 1.068, DD 22.4R — but XAU drops to PF 1.089,
  DD 36.2R (fails).
- **Round 3 — 9-cell refinement**: range-width floor (0.75/1.0×ATR) barely
  binds and does not help; 8-bar range reading (00:00–07:59, signals from
  08:00) improves XAU slightly but collapses EUR to PF 1.006; buffer 0.12,
  caps 1.25/1.75 all worse (1.75 → EUR PF 0.964). Confirms the selected cell
  is the local optimum and that EURUSD's shortfall is structural, not a
  tuning artifact.

## Robustness notes

- Year-by-year (selected): XAUUSD +13.3 / +8.8 / +9.4 / +22.4 / −1.4 / +11.5
  (2021 partial from Sep, 2026 to Oct 16); EURUSD −5.7 / +7.6 / +9.7 / +20.6 /
  −9.0 / +2.9 (2021 = 8 trades, Dec only). 2025 was negative on both symbols —
  the edge is regime-sensitive.
- Direction split: XAUUSD P&L is carried by shorts (+57.7R; longs +6.3R) —
  long breakouts got faded through the 2021–2026 gold bull run. EURUSD
  balanced (longs +18.4R, shorts +7.7R). No direction filter applied.
- Exits at SL price even when a bar gaps through it (backtest.py convention);
  a position still open at data end is dropped (1 case, EURUSD).

## Bottom line

The London-open breakout complements the RSI-pullback engine on XAUUSD but
fails acceptance on EURUSD: after 3 rounds / 32 cells, EURUSD's ceiling is
PF 1.068 and at the selected cell it is PF 1.045 with maxDD 31.8R. Report this
as a FAIL for the pair; XAUUSD alone is deployable-grade (PF 1.113, 1052
trades, +64.0R, DD 28.3R with all costs included).

## Files

- `strategy2_backtest.py` — self-contained read-only backtester (stdlib only,
  no MT5, no orders): `--round N` runs a round, `--select NAME` records the
  final pick. Reruns are deterministic.
- `strategy2_results.json` — all 29 variant runs (rounds 1–3), the selected
  variant, per-symbol stats/diagnostics, and the acceptance evaluation.
- `agent-reports/strategy2.md` — this report.

