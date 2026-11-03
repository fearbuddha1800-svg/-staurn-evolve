---
slug: agent-reports.mass-verification
type: note
graph: gitnexus
---

# MASS VERIFICATION: 14 unverified watched channels x relay exit geometry (POLICY V2)

_generated 2026-10-16T19:18:36.472243+00:00 · engine: `channel_verify_mass.py` (read-only port of `channel_verify2.py` / `channel_verify_scout.py`) · full data: `mass-verification.json` · Telegram on `telethon-mass.session` (sqlite backup copy; live `telethon.session` never touched) · parser: current fixed `parser.py` (arrow-format TPs + emoji-adjacent SLs) · method per `agent-reports/exit-geometry.md`_

## Channel set (the 14)

Every channel in config.json `channels` NOT covered by any prior verification report (V1 `channel_report.json` / V2 `channel_report_v2.json` / V3 `channel_report_v3.json` / scout `scout-verification.json`): the 12 newly joined channels in `new_channels_batch.json` plus the 2 scout-shortlist incumbents that were being watched live without any simulation evidence.

| # | channel | id | link | origin |
|---:|---|---:|---|---|
| 1 | SIGNALS_XAUUSD_FOREX_GOLD | `-1003723702011` | t.me/SIGNALS_XAUUSD_FOREX_GOLD | new batch (`new_channels_batch.json`) |
| 2 | forexgdp_forex_gdp | `-1001713690419` | t.me/forexgdp_forex_gdp | new batch (`new_channels_batch.json`) |
| 3 | XAUUSD_GOLD_VIP_SIGNALS_pip | `-1003376522019` | t.me/XAUUSD_GOLD_VIP_SIGNALS_pip | new batch (`new_channels_batch.json`) |
| 4 | fx_premiere_vip_gold_btc_xauusd | `-1001912261779` | t.me/fx_premiere_vip_gold_btc_xauusd | new batch (`new_channels_batch.json`) |
| 5 | Gold_Signals_Daily_Vip | `-1003762554260` | t.me/Gold_Signals_Daily_Vip | new batch (`new_channels_batch.json`) |
| 6 | NetProfitFXFREETrading2Signals | `-1003011435611` | t.me/NetProfitFXFREETrading2Signals | new batch (`new_channels_batch.json`) |
| 7 | OANDAFX1SIGNALS | `-1003034749723` | t.me/OANDAFX1SIGNALS | new batch (`new_channels_batch.json`) |
| 8 | GoldForexSignals_VIP | `-1003196282951` | t.me/GoldForexSignals_VIP | new batch (`new_channels_batch.json`) |
| 9 | FOREXGOLDFXF | `-1003022356169` | t.me/FOREXGOLDFXF | new batch (`new_channels_batch.json`) |
| 10 | ForexTradingSignalss2 | `-1003811991226` | t.me/ForexTradingSignalss2 | new batch (`new_channels_batch.json`) |
| 11 | Xauusdgoldsignals_tips | `-1003114012204` | t.me/Xauusdgoldsignals_tips | new batch (`new_channels_batch.json`) |
| 12 | xauusd_signalsq | `-1003576321949` | t.me/xauusd_signalsq | new batch (`new_channels_batch.json`) |
| 13 | Lingrid Forex Signals | `-1001189068380` | t.me/lingridchannel | config incumbent, scout-channels-v2.md shortlist |
| 14 | Forex GDP - Free Signals (scout) | `-1001175463265` | t.me/forexgdpfree | config incumbent, scout-channels-v2.md shortlist |

## Duplicate-content clusters (mirrors)

Several of the 14 channels post the SAME signals - identical (or near-identical, within one M15 bar) side, entry-bar open and outcome for every resolved trade, posted within ~1 min of each other. They are re-branded mirrors of one source, not independent evidence. The pooled rows below therefore report BOTH raw and DEDUPED stats (every unique signal counted once); at most ONE channel per cluster may ever be promoted, or every signal would execute twice.

| cluster | mirror channels | shared resolved trades | leader (keep/promote this one) |
|---|---|---:|---|
| C1 | FX PREMIERE VIP GOLD BTC SIGNALS (`-1001912261779`) | 10 | Forex GDP - Free Signals (`-1001713690419`) |
| C2 | XAUUSD GOLD SIGNALS ®️ (`-1003114012204`), Xauusd Trading Signals (Free) (`-1003034749723`), Gold Signals (Free) (`-1003022356169`), Forex Trading Signals (Free) (`-1003811991226`, near-mirror) | 7 | Gold Xauusd Trader Signals (`-1003011435611`) |

## Question

Does the raw DIRECTION of these 14 channels carry an edge when every trade is managed by the relay's own trailing exit (`manage.py`), all channel TPs ignored - i.e. should any of them be promoted from the default `shadow` signal_policy to a trading policy, and should any be removed from the watch list outright?

## Method (identical to exit-geometry.md unless noted)

- Last ~300 messages per channel, relay's own deterministic parser, same keep-filter as V1/V2: parse_ok, non-manage, has SL, >=1 TP, numeric entry, not stale (>1% from price at signal time).
- Market entry at the open of the first M15 bar at/after signal time (MT5 server-time offset from the freshest tick across XAUUSD/EURUSD/GBPUSD/US30/XAGUSD/AUDUSD; this run: 10800s).
- **Variant A**: initial SL = the channel's stated SL (R = |entry - SL|). **Variant B**: initial SL = 2 x ATR(14) (Wilder, M15, strictly closed bars before entry; stated SL ignored).
- ALL channel TPs ignored. Exit management identical to `manage.py` (config.json `manage`): SL -> entry +/- 10 points at +1R favorable; from +1.5R favorable the SL trails 0.5R behind the best favorable price. Ratchet-only.
- Walk up to 48h from entry. Conservative same-bar rule: the stop as it stood at bar open is checked FIRST; that bar's favorable extreme may then advance the stop, effective next bar.
- Costs: 0.07R round-trip haircut per trade. win% = resolved trades with R > 0. max DD = worst peak-to-trough of the cumulative after-cost R curve, trades ordered by entry time.
- Verdict bands on expectancy after costs: >= +0.05R POSITIVE EDGE, <= -0.05R NEGATIVE, else FLAT; n < 10 resolved trades = INSUFFICIENT DATA (verdict is tentative).
- Calls: **PROMOTE** needs best adequate variant exp >= +0.05R and n >= 10; **DEMOTE** (remove from config.json `channels`) when the best adequate variant is <= -0.05R; **DUPLICATE** for mirror feeds (identical trade set as another watched channel - keep/promote at most ONE per cluster); everything else stays in the default `shadow` policy. All 14 channels are currently watched with `signal_policy._default = {"mode": "shadow"}` - nothing is auto-traded from them today.
- Trades whose 48h window extends beyond available data are `pending` and excluded from stats. MT5 strictly read-only (copy_rates/symbol_info/symbol_info_tick/symbol_select only; no order_send).

## Results: channel x variant (14 channels)

| channel | variant | trades | win% | avg R | exp after costs (R) | max DD (R) | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| SIGNALS_XAUUSD_FOREX_GOLD | A | 15 | 46.7 | +0.196 | +0.126 | 3.41 | POSITIVE EDGE |
| SIGNALS_XAUUSD_FOREX_GOLD | B | 15 | 40.0 | -0.034 | -0.104 | 5.50 | NEGATIVE |
| forexgdp_forex_gdp | A | 10 | 50.0 | -0.046 | -0.116 | 2.14 | NEGATIVE |
| forexgdp_forex_gdp | B | 10 | 60.0 | +0.351 | +0.281 | 2.14 | POSITIVE EDGE |
| XAUUSD_GOLD_VIP_SIGNALS_pip | A | 12 | 41.7 | -0.001 | -0.071 | 3.59 | NEGATIVE |
| XAUUSD_GOLD_VIP_SIGNALS_pip | B | 12 | 41.7 | -0.048 | -0.118 | 4.28 | NEGATIVE |
| fx_premiere_vip_gold_btc_xauusd | A | 10 | 50.0 | -0.046 | -0.116 | 2.14 | NEGATIVE |
| fx_premiere_vip_gold_btc_xauusd | B | 10 | 60.0 | +0.351 | +0.281 | 2.14 | POSITIVE EDGE |
| Gold_Signals_Daily_Vip | A | 10 | 50.0 | -0.226 | -0.296 | 3.52 | NEGATIVE |
| Gold_Signals_Daily_Vip | B | 11 | 63.6 | +0.217 | +0.147 | 3.27 | POSITIVE EDGE |
| NetProfitFXFREETrading2Signals | A | 8 | 37.5 | -0.388 | -0.458 | 3.66 | INSUFFICIENT DATA (n=8 < 10) - tentatively NEGATIVE |
| NetProfitFXFREETrading2Signals | B | 8 | 37.5 | +0.077 | +0.007 | 3.21 | INSUFFICIENT DATA (n=8 < 10) - tentatively FLAT |
| OANDAFX1SIGNALS | A | 8 | 37.5 | -0.388 | -0.458 | 3.66 | INSUFFICIENT DATA (n=8 < 10) - tentatively NEGATIVE |
| OANDAFX1SIGNALS | B | 8 | 37.5 | +0.077 | +0.007 | 3.21 | INSUFFICIENT DATA (n=8 < 10) - tentatively FLAT |
| GoldForexSignals_VIP | A | 45 | 48.9 | +0.057 | -0.013 | 6.49 | FLAT |
| GoldForexSignals_VIP | B | 47 | 57.4 | +0.231 | +0.161 | 5.43 | POSITIVE EDGE |
| FOREXGOLDFXF | A | 8 | 37.5 | -0.388 | -0.458 | 3.66 | INSUFFICIENT DATA (n=8 < 10) - tentatively NEGATIVE |
| FOREXGOLDFXF | B | 8 | 37.5 | +0.077 | +0.007 | 3.21 | INSUFFICIENT DATA (n=8 < 10) - tentatively FLAT |
| ForexTradingSignalss2 | A | 8 | 37.5 | -0.388 | -0.458 | 3.66 | INSUFFICIENT DATA (n=8 < 10) - tentatively NEGATIVE |
| ForexTradingSignalss2 | B | 8 | 37.5 | +0.077 | +0.007 | 3.21 | INSUFFICIENT DATA (n=8 < 10) - tentatively FLAT |
| Xauusdgoldsignals_tips | A | 8 | 37.5 | -0.388 | -0.458 | 3.66 | INSUFFICIENT DATA (n=8 < 10) - tentatively NEGATIVE |
| Xauusdgoldsignals_tips | B | 8 | 37.5 | +0.077 | +0.007 | 3.21 | INSUFFICIENT DATA (n=8 < 10) - tentatively FLAT |
| xauusd_signalsq | A | 14 | 57.1 | -0.013 | -0.083 | 2.37 | NEGATIVE |
| xauusd_signalsq | B | 14 | 71.4 | +0.373 | +0.303 | 2.14 | POSITIVE EDGE |
| Lingrid Forex Signals | A | 0 | - | - | - | - | INSUFFICIENT DATA: 0 resolved trades |
| Lingrid Forex Signals | B | 0 | - | - | - | - | INSUFFICIENT DATA: 0 resolved trades |
| Forex GDP - Free Signals (scout) | A | 0 | - | - | - | - | INSUFFICIENT DATA: 0 resolved trades |
| Forex GDP - Free Signals (scout) | B | 0 | - | - | - | - | INSUFFICIENT DATA: 0 resolved trades |
| **ALL 14 CHANNELS (pooled, raw)** | **A** | 156 | 46.2 | -0.086 | -0.156 | 29.24 | NEGATIVE |
| **ALL 14 CHANNELS (pooled, raw)** | **B** | 159 | 51.6 | +0.173 | +0.103 | 16.24 | POSITIVE EDGE |
| **ALL CHANNELS (pooled, DEDUPED - mirrors counted once)** | **A** | 102 | 49.0 | -0.005 | -0.075 | 11.61 | NEGATIVE |
| **ALL CHANNELS (pooled, DEDUPED - mirrors counted once)** | **B** | 105 | 56.2 | +0.210 | +0.140 | 5.54 | POSITIVE EDGE |

## Ranked (best variant per channel, expectancy after costs)

| # | channel | id | A: n / exp | B: n / exp | best | best exp (R) | verdict | call |
|---:|---|---:|---|---|---|---:|---|---|
| 1 | xauusd_signalsq | `-1003576321949` | 14 / -0.083 | 14 / +0.303 | B | +0.303 | POSITIVE EDGE | PROMOTE |
| 2 | forexgdp_forex_gdp | `-1001713690419` | 10 / -0.116 | 10 / +0.281 | B | +0.281 | POSITIVE EDGE | PROMOTE |
| 3 | fx_premiere_vip_gold_btc_xauusd | `-1001912261779` | 10 / -0.116 | 10 / +0.281 | B | +0.281 | POSITIVE EDGE | DUPLICATE (mirror feed) |
| 4 | GoldForexSignals_VIP | `-1003196282951` | 45 / -0.013 | 47 / +0.161 | B | +0.161 | POSITIVE EDGE | PROMOTE |
| 5 | Gold_Signals_Daily_Vip | `-1003762554260` | 10 / -0.296 | 11 / +0.147 | B | +0.147 | POSITIVE EDGE | PROMOTE |
| 6 | SIGNALS_XAUUSD_FOREX_GOLD | `-1003723702011` | 15 / +0.126 | 15 / -0.104 | A | +0.126 | POSITIVE EDGE | PROMOTE |
| 7 | XAUUSD_GOLD_VIP_SIGNALS_pip | `-1003376522019` | 12 / -0.071 | 12 / -0.118 | A | -0.071 | NEGATIVE | DEMOTE (remove from config.json channels) |
| 8 | NetProfitFXFREETrading2Signals | `-1003011435611` | 8 / -0.458 | 8 / +0.007 | - | - | INSUFFICIENT DATA: 8 resolved trades max | STAY SHADOW |
| 9 | OANDAFX1SIGNALS | `-1003034749723` | 8 / -0.458 | 8 / +0.007 | - | - | INSUFFICIENT DATA: 8 resolved trades max | DUPLICATE (mirror feed) |
| 10 | FOREXGOLDFXF | `-1003022356169` | 8 / -0.458 | 8 / +0.007 | - | - | INSUFFICIENT DATA: 8 resolved trades max | DUPLICATE (mirror feed) |
| 11 | ForexTradingSignalss2 | `-1003811991226` | 8 / -0.458 | 8 / +0.007 | - | - | INSUFFICIENT DATA: 8 resolved trades max | DUPLICATE (mirror feed) |
| 12 | Xauusdgoldsignals_tips | `-1003114012204` | 8 / -0.458 | 8 / +0.007 | - | - | INSUFFICIENT DATA: 8 resolved trades max | DUPLICATE (mirror feed) |
| 13 | Lingrid Forex Signals | `-1001189068380` | 0 / - | 0 / - | - | - | INSUFFICIENT DATA: 0 resolved trades max | STAY SHADOW |
| 14 | Forex GDP - Free Signals (scout) | `-1001175463265` | 0 / - | 0 / - | - | - | INSUFFICIENT DATA: 0 resolved trades max | STAY SHADOW |

## Recommendations (promote / shadow / demote)

### FOREX GOLD SIGNALS XAUUSD (`-1003723702011`)

- **CALL: PROMOTE to trading policy - variant A** (variant A clears the bar: +0.126R expectancy after costs over 15 resolved trades (win% 46.7, maxDD 3.41R)).
- Policy params: `{"sl_mode": "channel", "tp_mode": "none"}` (sl_mode/atr_mult/tp_mode per config.json signal_policy schema); exits via manage.py: BE at +1R (10pt buffer), trail 0.5R from +1.5R, 48h horizon, 0.07R costs assumed.
- Prior evidence: no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set).

### Forex GDP - Free Signals (`-1001713690419`)

- **CALL: PROMOTE to trading policy - variant B** (variant B clears the bar: +0.281R expectancy after costs over 10 resolved trades (win% 60.0, maxDD 2.14R) NOTE: content is mirrored by 1 other watched channel(s) (FX PREMIERE VIP GOLD BTC SIGNALS (`-1001912261779`)); promote at most ONE channel of this cluster.).
- Policy params: `{"sl_mode": "atr", "atr_mult": 2.0, "tp_mode": "none"}` (sl_mode/atr_mult/tp_mode per config.json signal_policy schema); exits via manage.py: BE at +1R (10pt buffer), trail 0.5R from +1.5R, 48h horizon, 0.07R costs assumed.
- Prior evidence: no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set).

### XAUUSD GOLD SIGNALS (`-1003376522019`)

- **CALL: DEMOTE - remove from config.json `channels`** (best variant A is -0.071R after costs over 12 trades - at or below -0.05R: verified NEGATIVE, do not relay (other variant n=12 exp -0.118)).
- Prior evidence: no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set).

### FX PREMIERE VIP GOLD BTC SIGNALS (`-1001912261779`)

- **CALL: DUPLICATE - mirror of Forex GDP - Free Signals (`-1001713690419`)** - identical trade set (same 10 resolved signals, same side/entry/outcome) with Forex GDP - Free Signals (`-1001713690419`) - the same content re-branded; NOT independent evidence. Keep at most ONE channel of this cluster in config.json; if the leader is promoted, do NOT also add this mirror (every signal would execute twice).
- Action: keep at most one channel of the cluster in config.json `channels`; if the leader is promoted, remove this mirror (or keep it shadow) - never promote both.
- Prior evidence: no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set).

### Gold Signals Daily 🔔🏆 (`-1003762554260`)

- **CALL: PROMOTE to trading policy - variant B** (variant B clears the bar: +0.147R expectancy after costs over 11 resolved trades (win% 63.6, maxDD 3.27R)).
- Policy params: `{"sl_mode": "atr", "atr_mult": 2.0, "tp_mode": "none"}` (sl_mode/atr_mult/tp_mode per config.json signal_policy schema); exits via manage.py: BE at +1R (10pt buffer), trail 0.5R from +1.5R, 48h horizon, 0.07R costs assumed.
- Prior evidence: no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set).

### Gold Xauusd Trader Signals (`-1003011435611`)

- **CALL: STAY SHADOW** - fewer than 10 resolved trades in both variants (A n=8, B n=8) - sample too small for a promote/demote call NOTE: content is mirrored by 4 other watched channel(s) (Forex Trading Signals (Free) (`-1003811991226`), XAUUSD GOLD SIGNALS ®️ (`-1003114012204`), Xauusd Trading Signals (Free) (`-1003034749723`), Gold Signals (Free) (`-1003022356169`)); promote at most ONE channel of this cluster..
- Prior evidence: no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set).

### Xauusd Trading Signals (Free) (`-1003034749723`)

- **CALL: DUPLICATE - mirror of Gold Xauusd Trader Signals (`-1003011435611`)** - identical trade set (same 7 resolved signals, same side/entry/outcome) with Gold Xauusd Trader Signals (`-1003011435611`) - the same content re-branded; NOT independent evidence. Keep at most ONE channel of this cluster in config.json; if the leader is promoted, do NOT also add this mirror (every signal would execute twice).
- Action: keep at most one channel of the cluster in config.json `channels`; if the leader is promoted, remove this mirror (or keep it shadow) - never promote both.
- Prior evidence: no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set).

### GOLD FOREX SIGNALS VIP (`-1003196282951`)

- **CALL: PROMOTE to trading policy - variant B** (variant B clears the bar: +0.161R expectancy after costs over 47 resolved trades (win% 57.4, maxDD 5.43R)).
- Policy params: `{"sl_mode": "atr", "atr_mult": 2.0, "tp_mode": "none"}` (sl_mode/atr_mult/tp_mode per config.json signal_policy schema); exits via manage.py: BE at +1R (10pt buffer), trail 0.5R from +1.5R, 48h horizon, 0.07R costs assumed.
- Prior evidence: no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set).

### Gold Signals (Free) (`-1003022356169`)

- **CALL: DUPLICATE - mirror of Gold Xauusd Trader Signals (`-1003011435611`)** - identical trade set (same 7 resolved signals, same side/entry/outcome) with Gold Xauusd Trader Signals (`-1003011435611`) - the same content re-branded; NOT independent evidence. Keep at most ONE channel of this cluster in config.json; if the leader is promoted, do NOT also add this mirror (every signal would execute twice).
- Action: keep at most one channel of the cluster in config.json `channels`; if the leader is promoted, remove this mirror (or keep it shadow) - never promote both.
- Prior evidence: no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set).

### Forex Trading Signals (Free) (`-1003811991226`)

- **CALL: DUPLICATE - mirror of Gold Xauusd Trader Signals (`-1003011435611`)** - near-identical trade set (6 of 7 resolved signals shared) with Gold Xauusd Trader Signals (`-1003011435611`) - the same content re-branded; NOT independent evidence. Keep at most ONE channel of this cluster in config.json; if the leader is promoted, do NOT also add this mirror (every signal would execute twice).
- Action: keep at most one channel of the cluster in config.json `channels`; if the leader is promoted, remove this mirror (or keep it shadow) - never promote both.
- Prior evidence: no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set).

### XAUUSD GOLD SIGNALS ®️ (`-1003114012204`)

- **CALL: DUPLICATE - mirror of Gold Xauusd Trader Signals (`-1003011435611`)** - identical trade set (same 7 resolved signals, same side/entry/outcome) with Gold Xauusd Trader Signals (`-1003011435611`) - the same content re-branded; NOT independent evidence. Keep at most ONE channel of this cluster in config.json; if the leader is promoted, do NOT also add this mirror (every signal would execute twice).
- Action: keep at most one channel of the cluster in config.json `channels`; if the leader is promoted, remove this mirror (or keep it shadow) - never promote both.
- Prior evidence: no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set).

### Xauusd Trading Signals (`-1003576321949`)

- **CALL: PROMOTE to trading policy - variant B** (variant B clears the bar: +0.303R expectancy after costs over 14 resolved trades (win% 71.4, maxDD 2.14R)).
- Policy params: `{"sl_mode": "atr", "atr_mult": 2.0, "tp_mode": "none"}` (sl_mode/atr_mult/tp_mode per config.json signal_policy schema); exits via manage.py: BE at +1R (10pt buffer), trail 0.5R from +1.5R, 48h horizon, 0.07R costs assumed.
- Prior evidence: no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set).

### Lingrid Forex Signals (`-1001189068380`)

- **CALL: STAY SHADOW** - fewer than 10 resolved trades in both variants (A n=0, B n=0) - sample too small for a promote/demote call.
- Prior evidence: scout-channels-v2.md shortlist #5 (Lingrid) - external survey evidence only, never simulated before this run.

### Forex GDP - Free Signals (`-1001175463265`)

- **CALL: STAY SHADOW** - fewer than 10 resolved trades in both variants (A n=0, B n=0) - sample too small for a promote/demote call.
- Prior evidence: scout-channels-v2.md shortlist #7 (Forex GDP free feed) - external survey evidence only, never simulated before this run.

## Per-channel detail

### FOREX GOLD SIGNALS XAUUSD (`-1003723702011`)

- messages 300 (media-only 131, recaps 67, unparseable 22, stale 0, no-data 0, pending-no-bar 0)
- **variant A**: 15 resolved (initial-SL 8, BE 1, trail 3, timeout 3; pending 0, no-ATR 0), win% 46.7, avg +0.196R, exp after costs +0.126R, net +2.93R, maxDD 3.41R -> **POSITIVE EDGE**
- **variant B**: 15 resolved (initial-SL 9, BE 0, trail 5, timeout 1; pending 0, no-ATR 0), win% 40.0, avg -0.034R, exp after costs -0.104R, net -0.52R, maxDD 5.50R -> **NEGATIVE**

### Forex GDP - Free Signals (`-1001713690419`)

- messages 300 (media-only 77, recaps 7, unparseable 4, stale 0, no-data 0, pending-no-bar 0)
- **variant A**: 10 resolved (initial-SL 6, BE 1, trail 3, timeout 0; pending 0, no-ATR 0), win% 50.0, avg -0.046R, exp after costs -0.116R, net -0.46R, maxDD 2.14R -> **NEGATIVE**
- **variant B**: 10 resolved (initial-SL 4, BE 0, trail 6, timeout 0; pending 0, no-ATR 0), win% 60.0, avg +0.351R, exp after costs +0.281R, net +3.51R, maxDD 2.14R -> **POSITIVE EDGE**

### XAUUSD GOLD SIGNALS (`-1003376522019`)

- messages 300 (media-only 131, recaps 70, unparseable 25, stale 0, no-data 0, pending-no-bar 0)
- **variant A**: 12 resolved (initial-SL 6, BE 1, trail 2, timeout 3; pending 0, no-ATR 0), win% 41.7, avg -0.001R, exp after costs -0.071R, net -0.02R, maxDD 3.59R -> **NEGATIVE**
- **variant B**: 12 resolved (initial-SL 7, BE 0, trail 4, timeout 1; pending 0, no-ATR 0), win% 41.7, avg -0.048R, exp after costs -0.118R, net -0.58R, maxDD 4.28R -> **NEGATIVE**

### FX PREMIERE VIP GOLD BTC SIGNALS (`-1001912261779`)

- messages 300 (media-only 77, recaps 7, unparseable 4, stale 0, no-data 0, pending-no-bar 0)
- **variant A**: 10 resolved (initial-SL 6, BE 1, trail 3, timeout 0; pending 0, no-ATR 0), win% 50.0, avg -0.046R, exp after costs -0.116R, net -0.46R, maxDD 2.14R -> **NEGATIVE**
- **variant B**: 10 resolved (initial-SL 4, BE 0, trail 6, timeout 0; pending 0, no-ATR 0), win% 60.0, avg +0.351R, exp after costs +0.281R, net +3.51R, maxDD 2.14R -> **POSITIVE EDGE**

### Gold Signals Daily 🔔🏆 (`-1003762554260`)

- messages 300 (media-only 114, recaps 47, unparseable 1, stale 1, no-data 0, pending-no-bar 0)
- **variant A**: 10 resolved (initial-SL 5, BE 3, trail 2, timeout 0; pending 1, no-ATR 0), win% 50.0, avg -0.226R, exp after costs -0.296R, net -2.26R, maxDD 3.52R -> **NEGATIVE**
- **variant B**: 11 resolved (initial-SL 4, BE 3, trail 4, timeout 0; pending 0, no-ATR 0), win% 63.6, avg +0.217R, exp after costs +0.147R, net +2.39R, maxDD 3.27R -> **POSITIVE EDGE**

### Gold Xauusd Trader Signals (`-1003011435611`)

- messages 300 (media-only 226, recaps 25, unparseable 0, stale 0, no-data 0, pending-no-bar 0)
- **variant A**: 8 resolved (initial-SL 5, BE 2, trail 1, timeout 0; pending 0, no-ATR 0), win% 37.5, avg -0.388R, exp after costs -0.458R, net -3.10R, maxDD 3.66R -> **INSUFFICIENT DATA (n=8 < 10) - tentatively NEGATIVE**
- **variant B**: 8 resolved (initial-SL 5, BE 1, trail 2, timeout 0; pending 0, no-ATR 0), win% 37.5, avg +0.077R, exp after costs +0.007R, net +0.62R, maxDD 3.21R -> **INSUFFICIENT DATA (n=8 < 10) - tentatively FLAT**

### Xauusd Trading Signals (Free) (`-1003034749723`)

- messages 300 (media-only 226, recaps 25, unparseable 0, stale 0, no-data 0, pending-no-bar 0)
- **variant A**: 8 resolved (initial-SL 5, BE 2, trail 1, timeout 0; pending 0, no-ATR 0), win% 37.5, avg -0.388R, exp after costs -0.458R, net -3.10R, maxDD 3.66R -> **INSUFFICIENT DATA (n=8 < 10) - tentatively NEGATIVE**
- **variant B**: 8 resolved (initial-SL 5, BE 1, trail 2, timeout 0; pending 0, no-ATR 0), win% 37.5, avg +0.077R, exp after costs +0.007R, net +0.62R, maxDD 3.21R -> **INSUFFICIENT DATA (n=8 < 10) - tentatively FLAT**

### GOLD FOREX SIGNALS VIP (`-1003196282951`)

- messages 300 (media-only 46, recaps 103, unparseable 11, stale 1, no-data 3, pending-no-bar 0)
- **variant A**: 45 resolved (initial-SL 17, BE 4, trail 14, timeout 10; pending 2, no-ATR 0), win% 48.9, avg +0.057R, exp after costs -0.013R, net +2.56R, maxDD 6.49R -> **FLAT**
- **variant B**: 47 resolved (initial-SL 20, BE 9, trail 18, timeout 0; pending 0, no-ATR 0), win% 57.4, avg +0.231R, exp after costs +0.161R, net +10.87R, maxDD 5.43R -> **POSITIVE EDGE**

### Gold Signals (Free) (`-1003022356169`)

- messages 300 (media-only 226, recaps 25, unparseable 0, stale 0, no-data 0, pending-no-bar 0)
- **variant A**: 8 resolved (initial-SL 5, BE 2, trail 1, timeout 0; pending 0, no-ATR 0), win% 37.5, avg -0.388R, exp after costs -0.458R, net -3.10R, maxDD 3.66R -> **INSUFFICIENT DATA (n=8 < 10) - tentatively NEGATIVE**
- **variant B**: 8 resolved (initial-SL 5, BE 1, trail 2, timeout 0; pending 0, no-ATR 0), win% 37.5, avg +0.077R, exp after costs +0.007R, net +0.62R, maxDD 3.21R -> **INSUFFICIENT DATA (n=8 < 10) - tentatively FLAT**

### Forex Trading Signals (Free) (`-1003811991226`)

- messages 300 (media-only 226, recaps 25, unparseable 0, stale 0, no-data 0, pending-no-bar 0)
- **variant A**: 8 resolved (initial-SL 5, BE 2, trail 1, timeout 0; pending 0, no-ATR 0), win% 37.5, avg -0.388R, exp after costs -0.458R, net -3.10R, maxDD 3.66R -> **INSUFFICIENT DATA (n=8 < 10) - tentatively NEGATIVE**
- **variant B**: 8 resolved (initial-SL 5, BE 1, trail 2, timeout 0; pending 0, no-ATR 0), win% 37.5, avg +0.077R, exp after costs +0.007R, net +0.62R, maxDD 3.21R -> **INSUFFICIENT DATA (n=8 < 10) - tentatively FLAT**

### XAUUSD GOLD SIGNALS ®️ (`-1003114012204`)

- messages 300 (media-only 226, recaps 25, unparseable 0, stale 0, no-data 0, pending-no-bar 0)
- **variant A**: 8 resolved (initial-SL 5, BE 2, trail 1, timeout 0; pending 0, no-ATR 0), win% 37.5, avg -0.388R, exp after costs -0.458R, net -3.10R, maxDD 3.66R -> **INSUFFICIENT DATA (n=8 < 10) - tentatively NEGATIVE**
- **variant B**: 8 resolved (initial-SL 5, BE 1, trail 2, timeout 0; pending 0, no-ATR 0), win% 37.5, avg +0.077R, exp after costs +0.007R, net +0.62R, maxDD 3.21R -> **INSUFFICIENT DATA (n=8 < 10) - tentatively FLAT**

### Xauusd Trading Signals (`-1003576321949`)

- messages 300 (media-only 91, recaps 99, unparseable 12, stale 0, no-data 0, pending-no-bar 0)
- **variant A**: 14 resolved (initial-SL 6, BE 3, trail 4, timeout 1; pending 0, no-ATR 0), win% 57.1, avg -0.013R, exp after costs -0.083R, net -0.18R, maxDD 2.37R -> **NEGATIVE**
- **variant B**: 14 resolved (initial-SL 4, BE 3, trail 7, timeout 0; pending 0, no-ATR 0), win% 71.4, avg +0.373R, exp after costs +0.303R, net +5.23R, maxDD 2.14R -> **POSITIVE EDGE**

### Lingrid Forex Signals (`-1001189068380`)

- messages 300 (media-only 80, recaps 83, unparseable 81, stale 0, no-data 0, pending-no-bar 0)
- **variant A**: 0 resolved (initial-SL 0, BE 0, trail 0, timeout 0; pending 0, no-ATR 0), win% -, avg -R, exp after costs -R, net -R, maxDD -R -> **INSUFFICIENT DATA: 0 resolved trades**
- **variant B**: 0 resolved (initial-SL 0, BE 0, trail 0, timeout 0; pending 0, no-ATR 0), win% -, avg -R, exp after costs -R, net -R, maxDD -R -> **INSUFFICIENT DATA: 0 resolved trades**

### Forex GDP - Free Signals (`-1001175463265`)

- messages 300 (media-only 6, recaps 2, unparseable 112, stale 0, no-data 2, pending-no-bar 0)
- **variant A**: 0 resolved (initial-SL 0, BE 0, trail 0, timeout 0; pending 0, no-ATR 0), win% -, avg -R, exp after costs -R, net -R, maxDD -R -> **INSUFFICIENT DATA: 0 resolved trades**
- **variant B**: 0 resolved (initial-SL 0, BE 0, trail 0, timeout 0; pending 0, no-ATR 0), win% -, avg -R, exp after costs -R, net -R, maxDD -R -> **INSUFFICIENT DATA: 0 resolved trades**

## Caveats

- M15 granularity with the conservative same-bar rule takes the WORST fill ordering; real manage.py trailing (10s ticks) would do at least this well.
- Samples are one ~300-message window per channel; n between 10 and ~20 should be treated as a small sample - consider reduced risk_pct on promotion and re-verify after another 2 weeks of live shadow data.
- The parser still cannot read ASCII `->` arrows or TPs/SLs glued to decorative emoji with no separator (unicode arrows read fine); any such messages land in `unparseable` and are honestly counted, never simulated.
- The 48h horizon leaves the freshest ~2 days of signals `pending`, excluded from stats.
- No slippage modeling; fills at stop levels, 0.07R haircut covers spread/commission in R terms (same assumption as V1/V2/backtest.py).
- Read-only guarantees: `telethon.session` never opened for connect and never written (research ran on `telethon-mass.session`); MT5 never sent an order; no existing file modified; config.json read-only; no process started or stopped. Created: `channel_verify_mass.py`, `telethon-mass.session` (+journal), `mass-verification.json`, `agent-reports/mass-verification.md`.

