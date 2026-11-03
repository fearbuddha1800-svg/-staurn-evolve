---
slug: agent-reports.exit-geometry
type: note
graph: gitnexus
---

# EXIT-GEOMETRY research: channel DIRECTION x relay trailing exit (POLICY V2)

_generated 2026-10-15T23:22:17.419670+00:00 · engine: `channel_verify2.py` (read-only) · full data: `channel_report_v2.json` · baseline: `channel_report.json` (V1, the channels' own exits)_

## Question

V1 forensics showed every watched channel is a **TP-farm**: 81-91% win rates but avg R ~ 0 after costs, because their TP1 sits far closer than their SL (they harvest cosmetic win%, give back -1R on the losers). This research isolates the variable: **keep the channels' direction and entry timing, throw away their entire exit geometry, and manage every trade with the relay's own `manage.py` engine** (break-even at +1R, then a 0.5R trailing stop from +1.5R - no take-profit anywhere).

## Method

- Same 300-message fetch per channel, same deterministic parser and same keep-filter as V1: parse_ok, non-manage, has SL, >=1 TP, numeric entry, not stale (>1% from price at signal time). Trade set is identical to V1; only the exit policy changes.
- Market entry at the open of the first M15 bar at/after signal time (MT5 server-time offset from the freshest tick across XAUUSD/EURUSD/GBPUSD/US30/XAGUSD/AUDUSD; this run: 10799s).
- **Variant A**: initial SL = the channel's stated SL (R = |entry - SL|). **Variant B**: initial SL = 2 x ATR(14) (Wilder, M15, strictly closed bars before entry; the stated SL is ignored).
- ALL channel TPs ignored. Exit management identical to `manage.py` (config.json `manage`): SL -> entry +/- 10 points at +1R favorable; from +1.5R favorable the SL trails 0.5R behind the best favorable price. Ratchet-only, never widens.
- Walk up to 48h from entry. Conservative same-bar rule: the stop as it stood at bar open is checked FIRST; that bar's favorable extreme may then advance the stop, effective next bar. (BE/trail levels are always levels the market actually traded through, so their fills are real; initial-SL fills are at the SL level, same no-slippage convention as V1.)
- Costs: 0.07R round-trip haircut per trade. win% = resolved trades with R > 0 (break-even exits with the 10-point buffer count as tiny wins, which they are). max DD = worst peak-to-trough of the cumulative after-cost R curve, trades ordered by entry time.
- Verdict bands on expectancy after costs: >= +0.05R POSITIVE EDGE, <= -0.05R NEGATIVE, else FLAT; n < 10 resolved trades = INSUFFICIENT DATA (verdict is tentative).
- Trades whose 48h window extends beyond available data are `pending` and excluded from stats (the 48h horizon vs V1's 24h means the freshest ~2 days of signals are still open - counts are reported honestly per channel).
- Telegram ran on a sqlite-backup COPY of the live session (`telethon-research.session`); `telethon.session` was never opened for connect and never written. MT5 access was strictly read-only: initialize/shutdown + copy_rates/symbol_info/symbol_info_tick only; no order_send anywhere.

## Results: channel x variant

| channel | variant | trades | win% | avg R | exp after costs (R) | max DD (R) | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| Best Signal Forex | A | 32 | 59.4 | +0.084 | +0.014 | 8.69 | FLAT |
| Best Signal Forex | B | 32 | 65.6 | +0.337 | +0.267 | 8.69 | POSITIVE EDGE |
| XAUUSD PRO SIGNAL | A | 29 | 51.7 | +0.166 | +0.096 | 5.43 | POSITIVE EDGE |
| XAUUSD PRO SIGNAL | B | 29 | 44.8 | +0.007 | -0.063 | 6.10 | NEGATIVE |
| Grow Trading | A | 3 | 0.0 | -1.000 | -1.070 | 3.21 | INSUFFICIENT DATA (n=3 < 10) - tentatively NEGATIVE |
| Grow Trading | B | 3 | 33.3 | -0.664 | -0.734 | 2.20 | INSUFFICIENT DATA (n=3 < 10) - tentatively NEGATIVE |
| XAUUSD FREE SIGNALS | A | 11 | 81.8 | +0.625 | +0.555 | 1.26 | POSITIVE EDGE |
| XAUUSD FREE SIGNALS | B | 11 | 90.9 | +1.033 | +0.963 | 1.07 | POSITIVE EDGE |
| Easy Forex OFFICIAL | A | 0 | - | - | - | - | INSUFFICIENT DATA: 0 resolved trades |
| Easy Forex OFFICIAL | B | 0 | - | - | - | - | INSUFFICIENT DATA: 0 resolved trades |
| **ALL CHANNELS (pooled)** | **A** | 75 | 57.3 | +0.152 | +0.082 | 8.75 | POSITIVE EDGE |
| **ALL CHANNELS (pooled)** | **B** | 75 | 60.0 | +0.271 | +0.201 | 8.61 | POSITIVE EDGE |

Exit-mix per variant (pooled): initial-SL full losses 62 (A 32 / B 30), break-even exits 32 (A 16 / B 16), trailing-stop exits 56 (A 27 / B 29), 48h timeouts 0 (A 0 / B 0).

## V1 (their exits) vs V2 (our exits), expectancy after costs

| channel | V1 trades | V1 win% | V1 avg R | V1 exp | V2-A exp | V2-B exp | delta (best V2 - V1) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Best Signal Forex | 32 | 81.2 | -0.008 | -0.078 | +0.014 | +0.267 | +0.345 |
| XAUUSD PRO SIGNAL | 29 | 82.8 | +0.030 | -0.040 | +0.096 | -0.063 | +0.136 |
| Grow Trading | 3 | 33.3 | -0.637 | -0.707 | -1.070 | -0.734 | -0.027 |
| XAUUSD FREE SIGNALS | 11 | 90.9 | +0.046 | -0.024 | +0.555 | +0.963 | +0.987 |
| Easy Forex OFFICIAL | 0 | - | - | - | - | - | - |

## Per-channel detail

### Best Signal Forex (`-1002369502254`)

- messages 300 (media-only 19, recaps 145, unparseable 6, stale 0, pending-no-bar 0)
- **variant A**: 32 resolved (initial-SL 13, BE 9, trail 10, timeout 0; pending 0, no-ATR 0), win% 59.4, avg +0.084R, exp after costs +0.014R, net +2.69R, maxDD 8.69R -> **FLAT**
- **variant B**: 32 resolved (initial-SL 11, BE 9, trail 12, timeout 0; pending 0, no-ATR 0), win% 65.6, avg +0.337R, exp after costs +0.267R, net +10.80R, maxDD 8.69R -> **POSITIVE EDGE**

### XAUUSD PRO SIGNAL (`-1002692333123`)

- messages 300 (media-only 75, recaps 86, unparseable 2, stale 0, pending-no-bar 0)
- **variant A**: 29 resolved (initial-SL 14, BE 4, trail 11, timeout 0; pending 0, no-ATR 0), win% 51.7, avg +0.166R, exp after costs +0.096R, net +4.82R, maxDD 5.43R -> **POSITIVE EDGE**
- **variant B**: 29 resolved (initial-SL 16, BE 3, trail 10, timeout 0; pending 0, no-ATR 0), win% 44.8, avg +0.007R, exp after costs -0.063R, net +0.19R, maxDD 6.10R -> **NEGATIVE**

### Grow Trading (`-1001920020352`)

- messages 300 (media-only 57, recaps 4, unparseable 12, stale 0, pending-no-bar 0)
- **variant A**: 3 resolved (initial-SL 3, BE 0, trail 0, timeout 0; pending 0, no-ATR 0), win% 0.0, avg -1.000R, exp after costs -1.070R, net -3.00R, maxDD 3.21R -> **INSUFFICIENT DATA (n=3 < 10) - tentatively NEGATIVE**
- **variant B**: 3 resolved (initial-SL 2, BE 1, trail 0, timeout 0; pending 0, no-ATR 0), win% 33.3, avg -0.664R, exp after costs -0.734R, net -1.99R, maxDD 2.20R -> **INSUFFICIENT DATA (n=3 < 10) - tentatively NEGATIVE**

### XAUUSD FREE SIGNALS (`-1002165799093`)

- messages 300 (media-only 0, recaps 190, unparseable 49, stale 1, pending-no-bar 0)
- **variant A**: 11 resolved (initial-SL 2, BE 3, trail 6, timeout 0; pending 0, no-ATR 0), win% 81.8, avg +0.625R, exp after costs +0.555R, net +6.88R, maxDD 1.26R -> **POSITIVE EDGE**
- **variant B**: 11 resolved (initial-SL 1, BE 3, trail 7, timeout 0; pending 0, no-ATR 0), win% 90.9, avg +1.033R, exp after costs +0.963R, net +11.36R, maxDD 1.07R -> **POSITIVE EDGE**

### Easy Forex OFFICIAL (`-1001284268486`)

- messages 300 (media-only 63, recaps 143, unparseable 21, stale 0, pending-no-bar 0)
- **variant A**: 0 resolved (initial-SL 0, BE 0, trail 0, timeout 0; pending 0, no-ATR 0), win% -, avg -R, exp after costs -R, net -R, maxDD -R -> **INSUFFICIENT DATA: 0 resolved trades**
- **variant B**: 0 resolved (initial-SL 0, BE 0, trail 0, timeout 0; pending 0, no-ATR 0), win% -, avg -R, exp after costs -R, net -R, maxDD -R -> **INSUFFICIENT DATA: 0 resolved trades**

## Verdict

- **Best combo: XAUUSD FREE SIGNALS x variant B** - 11 trades, win% 90.9, avg +1.033R, **expectancy after costs +0.963R**, maxDD 1.07R (POSITIVE EDGE).
- **Research answer: POSITIVE EDGE - direction carries real edge once exit geometry is ours** (pooled expectancy after costs: A +0.082R over 75 trades, B +0.201R over 75 trades).
- 4 of 6 adequately-sampled combos are positive after costs; replacing the channels' TP-farm exits with the trailing engine flips the best channel from ~0R (V1) to +0.963R per trade.

## Caveats

- M15 granularity: no intra-bar path, so the conservative same-bar rule systematically takes the WORST fill ordering; real trailing would have done at least this well (manage.py runs on 10s ticks).
- Samples are small: Grow Trading has ~3 checkable signals, Easy Forex OFFICIAL posts zero verifiable signals (143 of ~300 messages are self-reported recaps). Only the XAUUSD channels and Best Signal Forex reach double digits.
- The 48h horizon (vs V1's 24h) leaves the freshest ~2 days of signals open (`pending`); they are excluded from stats, so V2 samples skew slightly older than V1's.
- No slippage modeling (fills at the stop level); the 0.07R haircut covers spread/commission in R terms, same assumption as the relay's own backtest.
- Read-only guarantees: `telethon.session` untouched (research ran on a backup copy), MT5 never sent an order, no existing file was modified. Created: `channel_verify2.py`, `channel_report_v2.json`, `agent-reports/exit-geometry.md`, `telethon-research.session`.

