---
slug: agent-reports.scout-verification
type: note
graph: gitnexus
---

# SCOUT VERIFICATION: 3 scout-verified channels x relay exit geometry (POLICY V2)

_generated 2026-10-16T17:37:50.345847+00:00 · engine: `channel_verify_scout.py` (read-only port of `channel_verify2.py`) · full data: `scout-verification.json` · Telegram on `telethon-scout-verify.session` (sqlite backup copy; live `telethon.session` never touched) · parser: current fixed `parser.py` (arrow-format TPs + emoji-adjacent SLs)_

## Channels

| channel | id | link |
|---|---|---|
| XAUHQ | `-1001207746934` | t.me/Goldsignals |
| SureShotFX free gold | `-1001588519179` | t.me/ssfgold |
| Gold Signals VIP | `-1001868019139` | t.me/gold_forex_signals_vip |

## Question

Expedited re-verification of the 3 scout-verified gold channels with the JUST-FIXED parser (arrow-format TPs, emoji-adjacent SLs): does the channels' raw DIRECTION carry an edge when every trade is managed by the relay's own trailing exit (`manage.py`), all channel TPs ignored?

## Method

- Last ~300 messages per channel, relay's own deterministic parser, same keep-filter as V1/V2: parse_ok, non-manage, has SL, >=1 TP, numeric entry, not stale (>1% from price at signal time).
- Market entry at the open of the first M15 bar at/after signal time (MT5 server-time offset from the freshest tick across XAUUSD/EURUSD/GBPUSD/US30/XAGUSD/AUDUSD; this run: 10801s).
- **Variant A**: initial SL = the channel's stated SL (R = |entry - SL|). **Variant B**: initial SL = 2 x ATR(14) (Wilder, M15, strictly closed bars before entry; stated SL ignored).
- ALL channel TPs ignored. Exit management identical to `manage.py` (config.json `manage`): SL -> entry +/- 10 points at +1R favorable; from +1.5R favorable the SL trails 0.5R behind the best favorable price. Ratchet-only.
- Walk up to 48h from entry. Conservative same-bar rule: the stop as it stood at bar open is checked FIRST; that bar's favorable extreme may then advance the stop, effective next bar.
- Costs: 0.07R round-trip haircut per trade. win% = resolved trades with R > 0. max DD = worst peak-to-trough of the cumulative after-cost R curve, trades ordered by entry time.
- Verdict bands on expectancy after costs: >= +0.05R POSITIVE EDGE, <= -0.05R NEGATIVE, else FLAT; n < 8 resolved trades = INSUFFICIENT (verdict tentative). Task gate: >= 8 complete signals required for a promote call.
- Trades whose 48h window extends beyond available data are `pending` and excluded from stats. MT5 strictly read-only (copy_rates/symbol_info/symbol_info_tick only; no order_send).

## Results: channel x variant

| channel | variant | trades | win% | avg R | exp after costs (R) | max DD (R) | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| XAUHQ | A | 32 | 65.6 | +0.060 | -0.010 | 4.94 | FLAT |
| XAUHQ | B | 32 | 62.5 | +0.072 | +0.002 | 4.99 | FLAT |
| SureShotFX free gold | A | 26 | 53.8 | -0.110 | -0.180 | 6.71 | NEGATIVE |
| SureShotFX free gold | B | 26 | 46.2 | -0.042 | -0.112 | 9.06 | NEGATIVE |
| Gold Signals VIP | A | 24 | 62.5 | +0.110 | +0.040 | 2.95 | FLAT |
| Gold Signals VIP | B | 24 | 58.3 | +0.244 | +0.174 | 4.54 | POSITIVE EDGE |
| **ALL 3 CHANNELS (pooled)** | **A** | 82 | 61.0 | +0.021 | -0.049 | 8.76 | FLAT |
| **ALL 3 CHANNELS (pooled)** | **B** | 82 | 56.1 | +0.086 | +0.016 | 12.98 | FLAT |

## Recommendations (promote / shadow)

### XAUHQ (`-1001207746934`)

- **CALL: STAY SHADOW** - best variant B is +0.002R after costs over 32 trades - does not clear +0.05R (other variant A n=32 exp -0.01).
- Prior evidence: full-sweep (old parser, 200 msgs): 0 complete signals - not verified.

### SureShotFX free gold (`-1001588519179`)

- **CALL: STAY SHADOW** - best variant B is -0.112R after costs over 26 trades - does not clear +0.05R (other variant A n=26 exp -0.18).
- Prior evidence: full-sweep (old parser, 200 msgs): NEGATIVE - best variant B -0.112R over 26 trades.

### Gold Signals VIP (`-1001868019139`)

- **CALL: PROMOTE to trading policy - variant B** (variant B clears the bar: +0.174R expectancy after costs over 24 resolved trades (win% 58.3, maxDD 4.54R)).
- Policy params: `{"sl_mode": "atr", "atr_mult": 2.0, "tp_mode": "none"}` (sl_mode/atr_mult/tp_mode per config.json signal_policy schema); exits via manage.py: BE at +1R (10pt buffer), trail 0.5R from +1.5R, 48h horizon, 0.07R costs assumed.
- Prior evidence: full-sweep (old parser, 200 msgs): POSITIVE EDGE - variant B +0.124R over 25 trades.

## Per-channel detail

### XAUHQ (`-1001207746934`)

- messages 300 (media-only 37, recaps 87, unparseable 19, stale 0, no-data 0, pending-no-bar 0)
- **variant A**: 32 resolved (initial-SL 12, BE 11, trail 7, timeout 2; pending 0, no-ATR 0), win% 65.6, avg +0.060R, exp after costs -0.010R, net +1.93R, maxDD 4.94R -> **FLAT**
- **variant B**: 32 resolved (initial-SL 12, BE 7, trail 11, timeout 2; pending 0, no-ATR 0), win% 62.5, avg +0.072R, exp after costs +0.002R, net +2.32R, maxDD 4.99R -> **FLAT**

### SureShotFX free gold (`-1001588519179`)

- messages 300 (media-only 31, recaps 155, unparseable 5, stale 0, no-data 0, pending-no-bar 0)
- **variant A**: 26 resolved (initial-SL 13, BE 6, trail 7, timeout 0; pending 0, no-ATR 0), win% 53.8, avg -0.110R, exp after costs -0.180R, net -2.85R, maxDD 6.71R -> **NEGATIVE**
- **variant B**: 26 resolved (initial-SL 14, BE 3, trail 9, timeout 0; pending 0, no-ATR 0), win% 46.2, avg -0.042R, exp after costs -0.112R, net -1.09R, maxDD 9.06R -> **NEGATIVE**

### Gold Signals VIP (`-1001868019139`)

- messages 300 (media-only 51, recaps 7, unparseable 118, stale 49, no-data 18, pending-no-bar 0)
- **variant A**: 24 resolved (initial-SL 8, BE 8, trail 5, timeout 3; pending 0, no-ATR 0), win% 62.5, avg +0.110R, exp after costs +0.040R, net +2.64R, maxDD 2.95R -> **FLAT**
- **variant B**: 24 resolved (initial-SL 9, BE 5, trail 8, timeout 2; pending 0, no-ATR 0), win% 58.3, avg +0.244R, exp after costs +0.174R, net +5.85R, maxDD 4.54R -> **POSITIVE EDGE**

## Caveats

- M15 granularity with the conservative same-bar rule takes the WORST fill ordering; real manage.py trailing (10s ticks) would do at least this well.
- Samples are one ~300-message window per channel; n between 8 and ~20 should be treated as a small sample - consider reduced risk_pct on promotion and re-verify after another 2 weeks of live shadow data.
- The parser still cannot read ASCII `->` arrows or TPs/SLs glued to decorative emoji with no separator (unicode arrows read fine); any such messages land in `unparseable` and are honestly counted, never simulated.
- The 48h horizon leaves the freshest ~2 days of signals `pending`, excluded from stats.
- No slippage modeling; fills at stop levels, 0.07R haircut covers spread/commission in R terms (same assumption as V1/V2/backtest.py).
- Read-only guarantees: `telethon.session` never opened for connect and never written (research ran on `telethon-scout-verify.session`); MT5 never sent an order; no existing file modified. Created: `channel_verify_scout.py`, `telethon-scout-verify.session` (+journal), `scout-verification.json`, `agent-reports/scout-verification.md`.

