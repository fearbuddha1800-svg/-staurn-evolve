---
slug: agent-reports.full-sweep
type: note
graph: gitnexus
---

# FULL CHANNEL SWEEP - ranked report + policy recommendations (V3)

_generated 2026-11-03T06:10:16.323972+00:00 · engine: `channel_verify3.py` (read-only) · scan: `scan-inventory.json` + `agent-reports/scan-inventory.md` · full data: `channel_report_v3.json` · prior runs: `channel_report.json` (V1, their exits) and `channel_report_v2.json` (V2, incumbents only)_

## Question

Inventory and triage EVERY dialog the account can see (main folder + archive), then deep-verify every source with enough signal flow (>= 8 complete signals in a 200-msg window) under the PROVEN V2 exit-geometry method (`agent-reports/exit-geometry.md`): keep their direction + entry timing, throw away their exits, manage with the relay's own trailing engine.

## Method (identical to exit-geometry.md unless noted)

- Deep-verify fetch: 300 messages per candidate (per exit-geometry.md), same recap skip ('tp hit'/'pips'), same keep-filter, same stale screen (>1% from price at signal time).
- Market entry at the open of the first M15 bar at/after signal time; server-time offset from the freshest tick across 6 liquid symbols (this run: 7200s).
- Variant A = channel's stated SL; variant B = 2 x Wilder ATR(14) M15 (closed bars only); ALL channel TPs ignored; BE at +1R (+10pt buffer), 0.5R trail from +1.5R, ratchet-only; 48h walk; conservative same-bar rule; 0.07R round-trip costs.
- Verdict bands: exp after costs >= +0.05R POSITIVE EDGE, <= -0.05R NEGATIVE, else FLAT; n < 10 resolved trades = INSUFFICIENT DATA (tentative).
- Scan stage used NO MT5. Verify stage MT5 access strictly read-only (initialize/shutdown + copy_rates/symbol_info/symbol_info_tick/symbol_select; order_send never called). Telegram ran on `telethon-scan.session`, a sqlite-backup copy of the live `telethon.session` (never connected, never written). No existing file modified; config.json read-only; no channel joined.

## Sweep summary

- Dialogs inventoried: **134** (main folder + archived), excluded **15** (bots / own chats / relay feed), triaged **119**.
- Deep-verify gate (complete >= 8): **19** chats; **19** verified.

## Ranked verified chats (best variant first)

| # | chat | id | arch | sig/day | A: n / exp | B: n / exp | best | verdict (best variant) |
|---:|---|---:|---|---:|---|---|---|---|
| 1 | 𝙱𝚎𝚜𝚝 𝚂𝚒𝚐𝚗𝚊𝚕 𝙵𝚘𝚛𝚎𝚡 | -1002369502254 | - | 0.79 | 31 / +0.924 | 31 / +0.580 | A | POSITIVE EDGE |
| 2 | XAUHQ 🏛️ | -1001207746934 | - | 0.43 | 37 / +0.579 | 37 / +0.461 | A | POSITIVE EDGE |
| 3 | 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1002639725270 | A | 0.86 | 34 / +0.262 | 34 / +0.270 | B | POSITIVE EDGE |
| 4 | 𝑋𝐴𝑈𝑈𝑆𝐷 𝑇𝑅𝐴𝐷𝐼𝑁𝐺 𝑀𝐴𝑆𝑇𝐸𝑅 | -1002010239852 | - | 0.72 | 40 / +0.230 | 40 / +0.089 | A | POSITIVE EDGE |
| 5 | Gold Signals Daily 🔔🏆 | -1003762554260 | - | 0.88 | 16 / +0.206 | 16 / -0.196 | A | POSITIVE EDGE |
| 6 | 𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 𝐓𝐄𝐀𝐌 | -1003924380674 | - | 2.45 | 23 / -0.097 | 24 / +0.152 | B | POSITIVE EDGE |
| 7 | UnitedSignals (Best Forex Signals) | -1001215049720 | - | 1.51 | 46 / +0.101 | 46 / -0.050 | A | POSITIVE EDGE |
| 8 | 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1002520344727 | - | 2.47 | 19 / -0.184 | 20 / +0.096 | B | POSITIVE EDGE |
| 9 | 𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1002620653001 | - | 1.92 | 33 / +0.069 | 33 / +0.086 | B | POSITIVE EDGE |
| 10 | XAUUSD GOLD SIGNALS | -1003376522019 | - | 0.23 | 15 / -0.230 | 15 / +0.080 | B | POSITIVE EDGE |
| 11 | 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐕𝐕𝐈𝐏 𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 | -1002647890905 | A | 0.67 | 25 / +0.031 | 25 / +0.067 | B | POSITIVE EDGE |
| 12 | GOLD FOREX SIGNALS VIP | -1003196282951 | - | 3.40 | 54 / -0.061 | 57 / +0.003 | B | FLAT |
| 13 | Asterra Gold | -1003751867978 | - | 0.79 | 36 / -0.029 | 37 / -0.182 | A | FLAT |
| 14 | 𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1001601213792 | - | 1.17 | 29 / -0.169 | 29 / -0.034 | B | FLAT |
| 15 | 𝐗𝐀𝐔𝐔𝐒𝐃 𝐏𝐑𝐎 𝐒𝐈𝐆𝐍𝐀𝐋 | -1002692333123 | - | 0.90 | 27 / -0.222 | 27 / -0.085 | B | NEGATIVE |
| 16 | SureShot GOLD | -1001588519179 | - | 0.95 | 26 / -0.161 | 26 / -0.487 | A | NEGATIVE |
| 17 | Gold Signals VIP (XAUUSD FOREX) | -1001868019139 | - | 1.75 | 22 / -0.289 | 22 / -0.230 | B | NEGATIVE |
| 18 | Christopher Alan Harrison💪 | -1001932578394 | - | 0.10 | 6 / -0.638 | 6 / +0.069 | B | INSUFFICIENT DATA (n=6 < 10) - tentatively POSITIVE EDGE |
| 19 | Gold Scalping - EdgeTrade 👑 | -1001988895125 | - | 1.17 | 0 / - | 0 / - | - | INSUFFICIENT DATA: 0 resolved trades |

Pooled across all verified chats: variant A 519 trades, exp after costs +0.078R; variant B 525 trades, exp after costs +0.050R.

## Channel x variant detail

| channel | variant | trades | win% | avg R | exp after costs (R) | max DD (R) | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| 𝙱𝚎𝚜𝚝 𝚂𝚒𝚐𝚗𝚊𝚕 𝙵𝚘𝚛𝚎𝚡 | A | 31 | 80.6 | +0.994 | +0.924 | 2.26 | POSITIVE EDGE |
| 𝙱𝚎𝚜𝚝 𝚂𝚒𝚐𝚗𝚊𝚕 𝙵𝚘𝚛𝚎𝚡 | B | 31 | 83.9 | +0.650 | +0.580 | 2.26 | POSITIVE EDGE |
| XAUHQ 🏛️ | A | 37 | 81.1 | +0.649 | +0.579 | 2.14 | POSITIVE EDGE |
| XAUHQ 🏛️ | B | 37 | 83.8 | +0.531 | +0.461 | 3.27 | POSITIVE EDGE |
| 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | A | 34 | 61.8 | +0.332 | +0.262 | 3.27 | POSITIVE EDGE |
| 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | B | 34 | 55.9 | +0.340 | +0.270 | 5.18 | POSITIVE EDGE |
| 𝑋𝐴𝑈𝑈𝑆𝐷 𝑇𝑅𝐴𝐷𝐼𝑁𝐺 𝑀𝐴𝑆𝑇𝐸𝑅 | A | 40 | 62.5 | +0.300 | +0.230 | 5.55 | POSITIVE EDGE |
| 𝑋𝐴𝑈𝑈𝑆𝐷 𝑇𝑅𝐴𝐷𝐼𝑁𝐺 𝑀𝐴𝑆𝑇𝐸𝑅 | B | 40 | 52.5 | +0.159 | +0.089 | 7.67 | POSITIVE EDGE |
| Gold Signals Daily 🔔🏆 | A | 16 | 68.8 | +0.276 | +0.206 | 5.41 | POSITIVE EDGE |
| Gold Signals Daily 🔔🏆 | B | 16 | 50.0 | -0.126 | -0.196 | 6.13 | NEGATIVE |
| 𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 𝐓𝐄𝐀𝐌 | A | 23 | 47.8 | -0.027 | -0.097 | 5.14 | NEGATIVE |
| 𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 𝐓𝐄𝐀𝐌 | B | 24 | 58.3 | +0.222 | +0.152 | 3.27 | POSITIVE EDGE |
| UnitedSignals (Best Forex Signals) | A | 46 | 52.2 | +0.171 | +0.101 | 7.33 | POSITIVE EDGE |
| UnitedSignals (Best Forex Signals) | B | 46 | 50.0 | +0.020 | -0.050 | 6.46 | NEGATIVE |
| 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | A | 19 | 42.1 | -0.114 | -0.184 | 5.14 | NEGATIVE |
| 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | B | 20 | 55.0 | +0.166 | +0.096 | 3.27 | POSITIVE EDGE |
| 𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | A | 33 | 54.5 | +0.139 | +0.069 | 5.15 | POSITIVE EDGE |
| 𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | B | 33 | 57.6 | +0.156 | +0.086 | 4.56 | POSITIVE EDGE |
| XAUUSD GOLD SIGNALS | A | 15 | 33.3 | -0.160 | -0.230 | 7.37 | NEGATIVE |
| XAUUSD GOLD SIGNALS | B | 15 | 53.3 | +0.150 | +0.080 | 2.20 | POSITIVE EDGE |
| 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐕𝐕𝐈𝐏 𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 | A | 25 | 56.0 | +0.101 | +0.031 | 7.21 | FLAT |
| 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐕𝐕𝐈𝐏 𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 | B | 25 | 52.0 | +0.137 | +0.067 | 10.18 | POSITIVE EDGE |
| GOLD FOREX SIGNALS VIP | A | 54 | 48.1 | +0.009 | -0.061 | 9.27 | NEGATIVE |
| GOLD FOREX SIGNALS VIP | B | 57 | 52.6 | +0.073 | +0.003 | 9.06 | FLAT |
| Asterra Gold | A | 36 | 44.4 | +0.041 | -0.029 | 8.63 | FLAT |
| Asterra Gold | B | 37 | 37.8 | -0.112 | -0.182 | 7.08 | NEGATIVE |
| 𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | A | 29 | 48.3 | -0.099 | -0.169 | 8.78 | NEGATIVE |
| 𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | B | 29 | 44.8 | +0.036 | -0.034 | 6.84 | FLAT |
| 𝐗𝐀𝐔𝐔𝐒𝐃 𝐏𝐑𝐎 𝐒𝐈𝐆𝐍𝐀𝐋 | A | 27 | 51.9 | -0.152 | -0.222 | 8.42 | NEGATIVE |
| 𝐗𝐀𝐔𝐔𝐒𝐃 𝐏𝐑𝐎 𝐒𝐈𝐆𝐍𝐀𝐋 | B | 27 | 48.1 | -0.015 | -0.085 | 5.61 | NEGATIVE |
| SureShot GOLD | A | 26 | 53.8 | -0.091 | -0.161 | 5.79 | NEGATIVE |
| SureShot GOLD | B | 26 | 34.6 | -0.417 | -0.487 | 12.77 | NEGATIVE |
| Gold Signals VIP (XAUUSD FOREX) | A | 22 | 40.9 | -0.219 | -0.289 | 7.49 | NEGATIVE |
| Gold Signals VIP (XAUUSD FOREX) | B | 22 | 45.5 | -0.160 | -0.230 | 6.45 | NEGATIVE |
| Christopher Alan Harrison💪 | A | 6 | 16.7 | -0.568 | -0.638 | 3.83 | INSUFFICIENT DATA (n=6 < 10) - tentatively NEGATIVE |
| Christopher Alan Harrison💪 | B | 6 | 66.7 | +0.139 | +0.069 | 1.07 | INSUFFICIENT DATA (n=6 < 10) - tentatively POSITIVE EDGE |
| Gold Scalping - EdgeTrade 👑 | A | 0 | - | - | - | - | INSUFFICIENT DATA: 0 resolved trades |
| Gold Scalping - EdgeTrade 👑 | B | 0 | - | - | - | - | INSUFFICIENT DATA: 0 resolved trades |

## Recommendations

### Add to config.json `channels` + go-live `signal_policy` (validated parameters)

```json
{
  "channels_add": [
    "-1002369502254",
    "-1001207746934",
    "-1002639725270",
    "-1002010239852",
    "-1003762554260",
    "-1003924380674",
    "-1001215049720",
    "-1002520344727",
    "-1002620653001",
    "-1003376522019",
    "-1002647890905"
  ],
  "signal_policy_add": {
    "-1002369502254": {
      "sl_mode": "channel",
      "tp_mode": "none"
    },
    "-1001207746934": {
      "sl_mode": "channel",
      "tp_mode": "none"
    },
    "-1002639725270": {
      "sl_mode": "atr",
      "atr_mult": 2.0,
      "tp_mode": "none"
    },
    "-1002010239852": {
      "sl_mode": "channel",
      "tp_mode": "none"
    },
    "-1003762554260": {
      "sl_mode": "channel",
      "tp_mode": "none"
    },
    "-1003924380674": {
      "sl_mode": "atr",
      "atr_mult": 2.0,
      "tp_mode": "none"
    },
    "-1001215049720": {
      "sl_mode": "channel",
      "tp_mode": "none"
    },
    "-1002520344727": {
      "sl_mode": "atr",
      "atr_mult": 2.0,
      "tp_mode": "none"
    },
    "-1002620653001": {
      "sl_mode": "atr",
      "atr_mult": 2.0,
      "tp_mode": "none"
    },
    "-1003376522019": {
      "sl_mode": "atr",
      "atr_mult": 2.0,
      "tp_mode": "none"
    },
    "-1002647890905": {
      "sl_mode": "atr",
      "atr_mult": 2.0,
      "tp_mode": "none"
    }
  }
}
```
- **𝙱𝚎𝚜𝚝 𝚂𝚒𝚐𝚗𝚊𝚕 𝙵𝚘𝚛𝚎𝚡** (`-1002369502254`) (already in channels - keep/adjust policy): variant A: 31 trades, exp after costs +0.924R (win% 80.6, maxDD 2.26R). Policy: `{"sl_mode": "channel", "tp_mode": "none"}`.
- **XAUHQ 🏛️** (`-1001207746934`) (already in channels - keep/adjust policy): variant A: 37 trades, exp after costs +0.579R (win% 81.1, maxDD 2.14R). Policy: `{"sl_mode": "channel", "tp_mode": "none"}`.
- **𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑** (`-1002639725270`) (already in channels - keep/adjust policy): variant B: 34 trades, exp after costs +0.270R (win% 55.9, maxDD 5.18R). Policy: `{"sl_mode": "atr", "atr_mult": 2.0, "tp_mode": "none"}`.
- **𝑋𝐴𝑈𝑈𝑆𝐷 𝑇𝑅𝐴𝐷𝐼𝑁𝐺 𝑀𝐴𝑆𝑇𝐸𝑅** (`-1002010239852`) (already in channels - keep/adjust policy): variant A: 40 trades, exp after costs +0.230R (win% 62.5, maxDD 5.55R). Policy: `{"sl_mode": "channel", "tp_mode": "none"}`.
- **Gold Signals Daily 🔔🏆** (`-1003762554260`) (already in channels - keep/adjust policy): variant A: 16 trades, exp after costs +0.206R (win% 68.8, maxDD 5.41R). Policy: `{"sl_mode": "channel", "tp_mode": "none"}`.
- **𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 𝐓𝐄𝐀𝐌** (`-1003924380674`) (already in channels - keep/adjust policy): variant B: 24 trades, exp after costs +0.152R (win% 58.3, maxDD 3.27R). Policy: `{"sl_mode": "atr", "atr_mult": 2.0, "tp_mode": "none"}`.
- **UnitedSignals (Best Forex Signals)** (`-1001215049720`): variant A: 46 trades, exp after costs +0.101R (win% 52.2, maxDD 7.33R). Policy: `{"sl_mode": "channel", "tp_mode": "none"}`.
- **𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑** (`-1002520344727`) (already in channels - keep/adjust policy): variant B: 20 trades, exp after costs +0.096R (win% 55.0, maxDD 3.27R). Policy: `{"sl_mode": "atr", "atr_mult": 2.0, "tp_mode": "none"}`.
- **𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑** (`-1002620653001`) (already in channels - keep/adjust policy): variant B: 33 trades, exp after costs +0.086R (win% 57.6, maxDD 4.56R). Policy: `{"sl_mode": "atr", "atr_mult": 2.0, "tp_mode": "none"}`.
- **XAUUSD GOLD SIGNALS** (`-1003376522019`) (already in channels - keep/adjust policy): variant B: 15 trades, exp after costs +0.080R (win% 53.3, maxDD 2.2R). Policy: `{"sl_mode": "atr", "atr_mult": 2.0, "tp_mode": "none"}`.
- **𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐕𝐕𝐈𝐏 𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋** (`-1002647890905`): variant B: 25 trades, exp after costs +0.067R (win% 52.0, maxDD 10.18R). Policy: `{"sl_mode": "atr", "atr_mult": 2.0, "tp_mode": "none"}`.

### Add in SHADOW mode (recorded, never traded)

```json
{
  "channels_add": [
    "-1003196282951",
    "-1003751867978",
    "-1001601213792",
    "-1001932578394"
  ],
  "signal_policy_add": {
    "-1003196282951": {
      "mode": "shadow"
    },
    "-1003751867978": {
      "mode": "shadow"
    },
    "-1001601213792": {
      "mode": "shadow"
    },
    "-1001932578394": {
      "mode": "shadow"
    }
  }
}
```
- **GOLD FOREX SIGNALS VIP** (`-1003196282951`): flat/thin: best variant B exp after costs +0.003R over 57 trades - record only.
- **Asterra Gold** (`-1003751867978`): flat/thin: best variant A exp after costs -0.029R over 36 trades - record only.
- **𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑** (`-1001601213792`): flat/thin: best variant B exp after costs -0.034R over 29 trades - record only.
- **Christopher Alan Harrison💪** (`-1001932578394`): variant B exp after costs +0.069R but only 6 trades (<10) - shadow until the sample grows.

### Do NOT add

- **𝐗𝐀𝐔𝐔𝐒𝐃 𝐏𝐑𝐎 𝐒𝐈𝐆𝐍𝐀𝐋** (`-1002692333123`): verified NEGATIVE: best variant B exp after costs -0.085R over 27 trades.
- **SureShot GOLD** (`-1001588519179`): verified NEGATIVE: best variant A exp after costs -0.161R over 26 trades.
- **Gold Signals VIP (XAUUSD FOREX)** (`-1001868019139`): verified NEGATIVE: best variant B exp after costs -0.230R over 22 trades.
- **Gold Scalping - EdgeTrade 👑** (`-1001988895125`): zero resolved trades in either variant - nothing to trade.

### Incumbents (already in config.json) - keep/adjust

- **𝙱𝚎𝚜𝚝 𝚂𝚒𝚐𝚗𝚊𝚕 𝙵𝚘𝚛𝚎𝚡** (`-1002369502254`): go-live - variant A: 31 trades, exp after costs +0.924R (win% 80.6, maxDD 2.26R).
- **XAUHQ 🏛️** (`-1001207746934`): go-live - variant A: 37 trades, exp after costs +0.579R (win% 81.1, maxDD 2.14R).
- **𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑** (`-1002639725270`): go-live - variant B: 34 trades, exp after costs +0.270R (win% 55.9, maxDD 5.18R).
- **𝑋𝐴𝑈𝑈𝑆𝐷 𝑇𝑅𝐴𝐷𝐼𝑁𝐺 𝑀𝐴𝑆𝑇𝐸𝑅** (`-1002010239852`): go-live - variant A: 40 trades, exp after costs +0.230R (win% 62.5, maxDD 5.55R).
- **Gold Signals Daily 🔔🏆** (`-1003762554260`): go-live - variant A: 16 trades, exp after costs +0.206R (win% 68.8, maxDD 5.41R).
- **𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 𝐓𝐄𝐀𝐌** (`-1003924380674`): go-live - variant B: 24 trades, exp after costs +0.152R (win% 58.3, maxDD 3.27R).
- **𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑** (`-1002520344727`): go-live - variant B: 20 trades, exp after costs +0.096R (win% 55.0, maxDD 3.27R).
- **𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑** (`-1002620653001`): go-live - variant B: 33 trades, exp after costs +0.086R (win% 57.6, maxDD 4.56R).
- **XAUUSD GOLD SIGNALS** (`-1003376522019`): go-live - variant B: 15 trades, exp after costs +0.080R (win% 53.3, maxDD 2.2R).
- **GOLD FOREX SIGNALS VIP** (`-1003196282951`): shadow - flat/thin: best variant B exp after costs +0.003R over 57 trades - record only.
- **Asterra Gold** (`-1003751867978`): shadow - flat/thin: best variant A exp after costs -0.029R over 36 trades - record only.
- **𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑** (`-1001601213792`): shadow - flat/thin: best variant B exp after costs -0.034R over 29 trades - record only.
- **𝐗𝐀𝐔𝐔𝐒𝐃 𝐏𝐑𝐎 𝐒𝐈𝐆𝐍𝐀𝐋** (`-1002692333123`): do-not-add - verified NEGATIVE: best variant B exp after costs -0.085R over 27 trades.
- **SureShot GOLD** (`-1001588519179`): do-not-add - verified NEGATIVE: best variant A exp after costs -0.161R over 26 trades.
- **Gold Signals VIP (XAUUSD FOREX)** (`-1001868019139`): do-not-add - verified NEGATIVE: best variant B exp after costs -0.230R over 22 trades.
- **Christopher Alan Harrison💪** (`-1001932578394`): shadow-promising - variant B exp after costs +0.069R but only 6 trades (<10) - shadow until the sample grows.
- **Certified Picks** (`-1003884507657`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Forex Trading Signals (Free)** (`-1003811991226`): NOT re-verified - only 2 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **FOREX GOLD SIGNALS XAUUSD** (`-1003723702011`): NOT re-verified - only 7 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Signal8** (`-1003629327586`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Xauusd Trading Signals** (`-1003576321949`): NOT re-verified - only 4 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **XAUUSD GOLD SIGNALS ®️** (`-1003114012204`): NOT re-verified - only 2 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Xauusd Trading Signals (Free)** (`-1003034749723`): NOT re-verified - only 2 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Gold Signals (Free)** (`-1003022356169`): NOT re-verified - only 2 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Gold Xauusd Trader Signals** (`-1003011435611`): NOT re-verified - only 2 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **𝐗𝐀𝐔𝐔𝐒𝐃 𝐓𝐑𝐀𝐃𝐈𝐍𝐆 𝐌𝐀𝐒𝐓𝐄𝐑𝐒** (`-1002698908514`): NOT re-verified - only 4 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **PLATINUM .PICKS.** (`-1002477522071`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **TYL - TRADING 📊🚀** (`-1002281357812`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **𝑿𝑨𝑼𝑼𝑺𝑫 𝑭𝑹𝑬𝑬 𝑺𝑰𝑮𝑵𝑨𝑳𝑺** (`-1002165799093`): NOT re-verified - only 3 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: POSITIVE EDGE, B exp +0.963R. Keep current config placement.
- **Simple Forex Tools** (`-1002073061621`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Grow Trading** (`-1001920020352`): NOT re-verified - only 4 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: INSUFFICIENT DATA (n=3 < 10) - tentatively NEGATIVE, B exp -0.734R. Keep current config placement.
- **MQL5 Algo Trading** (`-1001904158438`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Pockets of Rizdom 🧠** (`-1001715953952`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Forex GDP - Free Signals** (`-1001713690419`): NOT re-verified - only 5 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Intelligent Trading Signals** (`-1001346757271`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **GOLD Copy Trading** (`-1001335852535`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Easy Forex 👑 OFFICIAL CHANNEL** (`-1001284268486`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: INSUFFICIENT DATA: 0 resolved trades. Keep current config placement.
- **HIRN SIGNALS v7.8** (`-1001248393106`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Lingrid Forex Signals** (`-1001189068380`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Forex GDP - Free Signals** (`-1001175463265`): NOT re-verified - only 2 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **Whale Sniper** (`-1001127580919`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.
- **GOLD Trader Dan** (`-1001095525244`): NOT re-verified - only 0 complete signals in the 200-msg triage window (gate 8). Prior V2 evidence: n/a. Keep current config placement.

## V1 / V2 / V3 comparison (incumbents)

| chat | id | V1 exp (their exits) | V2-A exp | V2-B exp | V3-A exp | V3-B exp |
|---|---:|---:|---:|---:|---:|---:|
| 𝙱𝚎𝚜𝚝 𝚂𝚒𝚐𝚗𝚊𝚕 𝙵𝚘𝚛𝚎𝚡 | -1002369502254 | -0.078 | +0.014 | +0.267 | +0.924 | +0.580 |
| XAUHQ 🏛️ | -1001207746934 | - | - | - | +0.579 | +0.461 |
| 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1002639725270 | - | - | - | +0.262 | +0.270 |
| 𝑋𝐴𝑈𝑈𝑆𝐷 𝑇𝑅𝐴𝐷𝐼𝑁𝐺 𝑀𝐴𝑆𝑇𝐸𝑅 | -1002010239852 | - | - | - | +0.230 | +0.089 |
| Gold Signals Daily 🔔🏆 | -1003762554260 | - | - | - | +0.206 | -0.196 |
| 𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 𝐓𝐄𝐀𝐌 | -1003924380674 | - | - | - | -0.097 | +0.152 |
| UnitedSignals (Best Forex Signals) | -1001215049720 | - | - | - | +0.101 | -0.050 |
| 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1002520344727 | - | - | - | -0.184 | +0.096 |
| 𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1002620653001 | - | - | - | +0.069 | +0.086 |
| XAUUSD GOLD SIGNALS | -1003376522019 | - | - | - | -0.230 | +0.080 |
| 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐕𝐕𝐈𝐏 𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 | -1002647890905 | - | - | - | +0.031 | +0.067 |
| GOLD FOREX SIGNALS VIP | -1003196282951 | - | - | - | -0.061 | +0.003 |
| Asterra Gold | -1003751867978 | - | - | - | -0.029 | -0.182 |
| 𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1001601213792 | - | - | - | -0.169 | -0.034 |
| 𝐗𝐀𝐔𝐔𝐒𝐃 𝐏𝐑𝐎 𝐒𝐈𝐆𝐍𝐀𝐋 | -1002692333123 | -0.040 | +0.096 | -0.063 | -0.222 | -0.085 |
| SureShot GOLD | -1001588519179 | - | - | - | -0.161 | -0.487 |
| Gold Signals VIP (XAUUSD FOREX) | -1001868019139 | - | - | - | -0.289 | -0.230 |
| Christopher Alan Harrison💪 | -1001932578394 | - | - | - | -0.638 | +0.069 |
| Gold Scalping - EdgeTrade 👑 | -1001988895125 | - | - | - | - | - |

## Caveats

- Same as exit-geometry.md: M15 granularity + conservative same-bar rule takes the WORST fill ordering (live manage.py trails on 10s ticks); no slippage modeling (0.07R haircut covers costs); the 48h horizon leaves the freshest ~2 days of signals `pending`, excluded from stats.
- Triage complete counts are from a 200-message window; the verify stage re-derives its trade set from a 300-message fetch per exit-geometry.md, so per-chat message stats differ between the two files by design.
- Media-only posts are counted, never OCR-parsed; user-chat samples can be tiny (a DM with a handful of signals) - treat 'INSUFFICIENT DATA' verdicts as exactly that.
- Read-only guarantees: `telethon.session` never connected (scan ran on a sqlite backup copy), MT5 never sent an order, no existing file modified, config.json untouched, no channel joined, no process started/stopped. Created: `channel_verify3.py`, `scan-inventory.json`, `agent-reports/scan-inventory.md`, `channel_report_v3.json`, `agent-reports/full-sweep.md`, `telethon-scan.session`.

