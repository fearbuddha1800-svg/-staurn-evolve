---
slug: channel_report_v3
type: note
graph: gitnexus
---

{
  "generated_utc": "2026-11-03T06:10:16.323972+00:00",
  "research": "FULL CHANNEL SWEEP v3: every dialog inventoried + triaged; deep verification via the V2 exit-geometry engine (channel direction x relay trailing exit)",
  "method": {
    "scan": "see scan-inventory.json (inventory + 200-msg triage per chat)",
    "verify_gate": "chats with >= 8 complete signals in the triage window",
    "verify_engine": "channel_verify2.analyze_channel verbatim (300-msg fetch, recap skip, keep-filter, stale 1% screen, market entry at first M15 bar at/after signal)",
    "variants": "A = channel's stated SL; B = 2 x Wilder ATR(14) M15 (strictly closed bars); ALL channel TPs ignored",
    "exit_management": "manage.py rules: BE at +1R (+10pt buffer), 0.5R trail from +1.5R, ratchet-only; 48h walk; conservative same-bar rule",
    "costs": "0.07R round-trip haircut per trade",
    "verdict_bands": "exp after costs >= +0.05R POSITIVE EDGE, <= -0.05R NEGATIVE, else FLAT; n < 10 = INSUFFICIENT DATA (tentative)",
    "server_offset_s": 7200,
    "server_offset_method": "freshest tick across XAUUSD/EURUSD/GBPUSD/US30/XAGUSD/AUDUSD",
    "tick_times_at_run": {
      "XAUUSD": 1793693396,
      "EURUSD": 1793693396,
      "GBPUSD": 1793693396,
      "US30": 1793693394,
      "XAGUSD": 1793693397,
      "AUDUSD": 1793693396
    },
    "session": "telethon-scan.session (copy; live session never connected/written)",
    "mt5_access": "read-only: initialize/shutdown + copy_rates/symbol_info/symbol_info_tick/symbol_select; order_send never called"
  },
  "scan_candidates": [
    {
      "id": -1001868019139,
      "title": "Gold Signals VIP (XAUUSD FOREX)",
      "complete": 59,
      "signals_per_day": 1.75,
      "archived": false
    },
    {
      "id": -1001215049720,
      "title": "UnitedSignals (Best Forex Signals)",
      "complete": 42,
      "signals_per_day": 1.51,
      "archived": false
    },
    {
      "id": -1003196282951,
      "title": "GOLD FOREX SIGNALS VIP",
      "complete": 39,
      "signals_per_day": 3.4,
      "archived": false
    },
    {
      "id": -1003751867978,
      "title": "Asterra Gold",
      "complete": 34,
      "signals_per_day": 0.79,
      "archived": false
    },
    {
      "id": -1001207746934,
      "title": "XAUHQ \ud83c\udfdb\ufe0f",
      "complete": 33,
      "signals_per_day": 0.43,
      "archived": false
    },
    {
      "id": -1002010239852,
      "title": "\ud835\udc4b\ud835\udc34\ud835\udc48\ud835\udc48\ud835\udc46\ud835\udc37 \ud835\udc47\ud835\udc45\ud835\udc34\ud835\udc37\ud835\udc3c\ud835\udc41\ud835\udc3a \ud835\udc40\ud835\udc34\ud835\udc46\ud835\udc47\ud835\udc38\ud835\udc45",
      "complete": 30,
      "signals_per_day": 0.72,
      "archived": false
    },
    {
      "id": -1002620653001,
      "title": "\ud835\udc17\ud835\udc00\ud835\udc14\ud835\udc14\ud835\udc12\ud835\udc03 \ud835\udc06\ud835\udc0e\ud835\udc0b\ud835\udc03 \ud835\udc0f\ud835\udc11\ud835\udc0e \ud835\udc13\ud835\udc11\ud835\udc00\ud835\udc03\ud835\udc04\ud835\udc11",
      "complete": 25,
      "signals_per_day": 1.92,
      "archived": false
    },
    {
      "id": -1002639725270,
      "title": "\ud835\udc0f\ud835\udc11\ud835\udc0e \ud835\udc13\ud835\udc11\ud835\udc00\ud835\udc03\ud835\udc04\ud835\udc11",
      "complete": 21,
      "signals_per_day": 0.86,
      "archived": true
    },
    {
      "id": -1001601213792,
      "title": "\ud835\udc17\ud835\udc00\ud835\udc14\ud835\udc14\ud835\udc12\ud835\udc03 \ud835\udc06\ud835\udc0e\ud835\udc0b\ud835\udc03 \ud835\udc0f\ud835\udc11\ud835\udc0e \ud835\udc13\ud835\udc11\ud835\udc00\ud835\udc03\ud835\udc04\ud835\udc11",
      "complete": 21,
      "signals_per_day": 1.17,
      "archived": false
    },
    {
      "id": -1002369502254,
      "title": "\ud835\ude71\ud835\ude8e\ud835\ude9c\ud835\ude9d \ud835\ude82\ud835\ude92\ud835\ude90\ud835\ude97\ud835\ude8a\ud835\ude95 \ud835\ude75\ud835\ude98\ud835\ude9b\ud835\ude8e\ud835\udea1",
      "complete": 21,
      "signals_per_day": 0.79,
      "archived": false
    },
    {
      "id": -1002647890905,
      "title": "\ud835\udc0f\ud835\udc11\ud835\udc04\ud835\udc0c\ud835\udc08\ud835\udc14\ud835\udc0c \ud835\udc15\ud835\udc15\ud835\udc08\ud835\udc0f \ud835\udc05\ud835\udc17 \ud835\udc12\ud835\udc08\ud835\udc06\ud835\udc0d\ud835\udc00\ud835\udc0b",
      "complete": 18,
      "signals_per_day": 0.67,
      "archived": true
    },
    {
      "id": -1003924380674,
      "title": "\ud835\udc05\ud835\udc17 \ud835\udc12\ud835\udc08\ud835\udc06\ud835\udc0d\ud835\udc00\ud835\udc0b \ud835\udc13\ud835\udc04\ud835\udc00\ud835\udc0c",
      "complete": 17,
      "signals_per_day": 2.45,
      "archived": false
    },
    {
      "id": -1001588519179,
      "title": "SureShot GOLD",
      "complete": 17,
      "signals_per_day": 0.95,
      "archived": false
    },
    {
      "id": -1002692333123,
      "title": "\ud835\udc17\ud835\udc00\ud835\udc14\ud835\udc14\ud835\udc12\ud835\udc03 \ud835\udc0f\ud835\udc11\ud835\udc0e \ud835\udc12\ud835\udc08\ud835\udc06\ud835\udc0d\ud835\udc00\ud835\udc0b",
      "complete": 16,
      "signals_per_day": 0.9,
      "archived": false
    },
    {
      "id": -1002520344727,
      "title": "\ud835\udc06\ud835\udc0e\ud835\udc0b\ud835\udc03 \ud835\udc0f\ud835\udc11\ud835\udc0e \ud835\udc13\ud835\udc11\ud835\udc00\ud835\udc03\ud835\udc04\ud835\udc11",
      "complete": 15,
      "signals_per_day": 2.47,
      "archived": false
    },
    {
      "id": -1003762554260,
      "title": "Gold Signals Daily \ud83d\udd14\ud83c\udfc6",
      "complete": 11,
      "signals_per_day": 0.88,
      "archived": false
    },
    {
      "id": -1003376522019,
      "title": "XAUUSD GOLD SIGNALS",
      "complete": 9,
      "signals_per_day": 0.23,
      "archived": false
    },
    {
      "id": -1001932578394,
      "title": "Christopher Alan Harrison\ud83d\udcaa",
      "complete": 8,
      "signals_per_day": 0.1,
      "archived": false
    },
    {
      "id": -1001988895125,
      "title": "Gold Scalping - EdgeTrade \ud83d\udc51",
      "complete": 8,
      "signals_per_day": 1.17,
      "archived": false
    }
  ],
  "verified_count": 19,
  "channels": [
    {
      "id": -1001868019139,
      "name": "Gold Signals VIP (XAUUSD FOREX)",
      "plain_name": "Gold Signals VIP (XAUUSD FOREX)",
      "messages": 300,
      "media_only": 52,
      "not_signal": 34,
      "unparseable": 115,
      "unverifiable": 0,
      "recap_posts": 8,
      "no_data": 21,
      "pending": 0,
      "degenerate": 0,
      "stale": 48,
      "error": null,
      "signals": [
        {
          "msg_id": 4488,
          "date_utc": "2026-11-02T16:49:53+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 50.98231,
          "sl": 50.37451,
          "tps": [
            51.90414
          ],
          "price_at_signal": 50.995,
          "entry_gap_pct": 0.025,
          "sim_entry": 50.927,
          "variants": {
            "A": {
              "init_sl": 50.37451,
              "r_init": 0.55249,
              "outcome": "sl",
              "r": -1.0,
              "exit": 50.37451,
              "exit_time_server": "2026-11-03T03:00:00+srv"
            },
            "B": {
              "init_sl": 50.51257,
              "r_init": 0.41443,
              "outcome": "sl",
              "r": -1.0,
              "exit": 50.51257,
              "exit_time_server": "2026-11-02T21:15:00+srv"
            }
          },
          "atr14_m15": 0.20721
        },
        {
          "msg_id": 4487,
          "date_utc": "2026-11-02T14:37:13+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 3.955,
          "sl": 3.925,
          "tps": [
            4.008
          ],
          "price_at_signal": 3947.86,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4482,
          "date_utc": "2026-11-01T14:10:17+00:00",
          "raw_symbol": "BTCUSD",
          "resolved": null,
          "side": "buy",
          "entry": 77.848,
          "sl": 77.649,
          "tps": [
            78.142
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4477,
          "date_utc": "2026-10-31T14:10:11+00:00",
          "raw_symbol": "XTIUSD",
          "resolved": null,
          "side": "buy",
          "entry": 102.94,
          "sl": 102.24,
          "tps": [
            103.97
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4471,
          "date_utc": "2026-10-30T10:11:01+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 3.988,
          "sl": 3.974,
          "tps": [
            4.009
          ],
          "price_at_signal": 3991.64,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4469,
          "date_utc": "2026-10-30T09:41:19+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 50.81283,
          "sl": 50.19646,
          "tps": [
            51.73739
          ],
          "price_at_signal": 50.79,
          "entry_gap_pct": 0.045,
          "sim_entry": 50.768,
          "variants": {
            "A": {
              "init_sl": 50.19646,
              "r_init": 0.57154,
              "outcome": "sl",
              "r": -1.0,
              "exit": 50.19646,
              "exit_time_server": "2026-10-30T13:45:00+srv"
            },
            "B": {
              "init_sl": 50.35949,
              "r_init": 0.40851,
              "outcome": "sl",
              "r": -1.0,
              "exit": 50.35949,
              "exit_time_server": "2026-10-30T13:30:00+srv"
            }
          },
          "atr14_m15": 0.20425
        },
        {
          "msg_id": 4465,
          "date_utc": "2026-10-29T13:30:01+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 102.268,
          "sl": 102.184,
          "tps": [
            102.395
          ],
          "price_at_signal": 4025.35,
          "entry_gap_pct": 97.459,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4464,
          "date_utc": "2026-10-29T13:15:43+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 1.11303,
          "sl": 1.11215,
          "tps": [
            1.11441
          ],
          "price_at_signal": 4025.42,
          "entry_gap_pct": 99.972,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4460,
          "date_utc": "2026-10-28T09:37:02+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 54.02443,
          "sl": 53.8458,
          "tps": [
            54.30099
          ],
          "price_at_signal": 53.913,
          "entry_gap_pct": 0.207,
          "sim_entry": 53.919,
          "variants": {
            "A": {
              "init_sl": 53.8458,
              "r_init": 0.0732,
              "outcome": "sl",
              "r": -1.0,
              "exit": 53.8458,
              "exit_time_server": "2026-10-28T11:45:00+srv"
            },
            "B": {
              "init_sl": 53.67169,
              "r_init": 0.24731,
              "outcome": "sl",
              "r": -1.0,
              "exit": 53.67169,
              "exit_time_server": "2026-10-28T12:00:00+srv"
            }
          },
          "atr14_m15": 0.12365
        },
        {
          "msg_id": 4457,
          "date_utc": "2026-10-28T09:00:33+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.055,
          "sl": 4.044,
          "tps": [
            4.071
          ],
          "price_at_signal": 4052.87,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4454,
          "date_utc": "2026-10-27T15:53:07+00:00",
          "raw_symbol": "EURUSD",
          "resolved": "EURUSD",
          "side": "buy",
          "entry": 1.11445,
          "sl": 1.11357,
          "tps": [
            1.116
          ],
          "price_at_signal": 1.11441,
          "entry_gap_pct": 0.004,
          "sim_entry": 1.11428,
          "variants": {
            "A": {
              "init_sl": 1.11357,
              "r_init": 0.00071,
              "outcome": "sl",
              "r": -1.0,
              "exit": 1.11357,
              "exit_time_server": "2026-10-27T18:15:00+srv"
            },
            "B": {
              "init_sl": 1.11311,
              "r_init": 0.00117,
              "outcome": "sl",
              "r": -1.0,
              "exit": 1.11311,
              "exit_time_server": "2026-10-27T22:00:00+srv"
            }
          },
          "atr14_m15": 0.00059
        },
        {
          "msg_id": 4453,
          "date_utc": "2026-10-27T15:35:02+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 102.233,
          "sl": 102.13,
          "tps": [
            102.393
          ],
          "price_at_signal": 4058.81,
          "entry_gap_pct": 97.481,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4446,
          "date_utc": "2026-10-26T10:55:17+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 53.97947,
          "sl": 53.84204,
          "tps": [
            54.18594
          ],
          "price_at_signal": 53.911,
          "entry_gap_pct": 0.127,
          "sim_entry": 53.947,
          "variants": {
            "A": {
              "init_sl": 53.84204,
              "r_init": 0.10496,
              "outcome": "sl",
              "r": -1.0,
              "exit": 53.84204,
              "exit_time_server": "2026-10-26T13:15:00+srv"
            },
            "B": {
              "init_sl": 53.67771,
              "r_init": 0.26929,
              "outcome": "be",
              "r": 0.037,
              "exit": 53.957,
              "exit_time_server": "2026-10-26T14:45:00+srv"
            }
          },
          "atr14_m15": 0.13465
        },
        {
          "msg_id": 4444,
          "date_utc": "2026-10-26T10:25:05+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.017,
          "sl": 4.005,
          "tps": [
            4.034
          ],
          "price_at_signal": 4016.8,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4442,
          "date_utc": "2026-10-25T16:00:01+00:00",
          "raw_symbol": "BTCUSD",
          "resolved": null,
          "side": "buy",
          "entry": 80.581,
          "sl": 80.384,
          "tps": [
            80.882
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4437,
          "date_utc": "2026-10-24T15:20:17+00:00",
          "raw_symbol": "ETHUSD",
          "resolved": null,
          "side": "buy",
          "entry": 2.339,
          "sl": 2.321,
          "tps": [
            2.369
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4431,
          "date_utc": "2026-10-23T15:25:13+00:00",
          "raw_symbol": "MARKET",
          "resolved": null,
          "side": "buy",
          "entry": 101.716,
          "sl": 101.617,
          "tps": [
            101.862
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4430,
          "date_utc": "2026-10-23T15:10:11+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.002,
          "sl": 3.988,
          "tps": [
            4.025
          ],
          "price_at_signal": 4022.78,
          "entry_gap_pct": 99.901,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4422,
          "date_utc": "2026-10-22T11:25:01+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 1.12064,
          "sl": 1.1192,
          "tps": [
            1.12283
          ],
          "price_at_signal": 4087.05,
          "entry_gap_pct": 99.973,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4421,
          "date_utc": "2026-10-22T11:10:46+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 55.85326,
          "sl": 55.15122,
          "tps": [
            56.92407
          ],
          "price_at_signal": 55.953,
          "entry_gap_pct": 0.178,
          "sim_entry": 55.928,
          "variants": {
            "A": {
              "init_sl": 55.15122,
              "r_init": 0.77678,
              "outcome": "sl",
              "r": -1.0,
              "exit": 55.15122,
              "exit_time_server": "2026-10-22T16:30:00+srv"
            },
            "B": {
              "init_sl": 55.55464,
              "r_init": 0.37336,
              "outcome": "sl",
              "r": -1.0,
              "exit": 55.55464,
              "exit_time_server": "2026-10-22T16:30:00+srv"
            }
          },
          "atr14_m15": 0.18668
        },
        {
          "msg_id": 4418,
          "date_utc": "2026-10-21T10:15:13+00:00",
          "raw_symbol": "SIGNAL",
          "resolved": null,
          "side": "buy",
          "entry": 101.756,
          "sl": 101.726,
          "tps": [
            101.802
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4416,
          "date_utc": "2026-10-21T09:45:17+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.123,
          "sl": 4.113,
          "tps": [
            4.139
          ],
          "price_at_signal": 4121.86,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4412,
          "date_utc": "2026-10-20T15:34:42+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 58.06496,
          "sl": 57.44998,
          "tps": [
            58.98006
          ],
          "price_at_signal": 58.441,
          "entry_gap_pct": 0.643,
          "sim_entry": 58.45,
          "variants": {
            "A": {
              "init_sl": 57.44998,
              "r_init": 1.00002,
              "outcome": "sl",
              "r": -1.0,
              "exit": 57.44998,
              "exit_time_server": "2026-10-21T04:00:00+srv"
            },
            "B": {
              "init_sl": 57.91938,
              "r_init": 0.53062,
              "outcome": "sl",
              "r": -1.0,
              "exit": 57.91938,
              "exit_time_server": "2026-10-20T18:00:00+srv"
            }
          },
          "atr14_m15": 0.26531
        },
        {
          "msg_id": 4409,
          "date_utc": "2026-10-20T14:42:44+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 1.12523,
          "sl": 1.12369,
          "tps": [
            1.12758
          ],
          "price_at_signal": 4122.49,
          "entry_gap_pct": 99.973,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4405,
          "date_utc": "2026-10-19T09:40:13+00:00",
          "raw_symbol": "GROWTH",
          "resolved": null,
          "side": "buy",
          "entry": 101.917,
          "sl": 101.789,
          "tps": [
            102.111
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4402,
          "date_utc": "2026-10-19T08:52:23+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.172,
          "sl": 4.162,
          "tps": [
            4.187
          ],
          "price_at_signal": 4182.46,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4399,
          "date_utc": "2026-10-18T10:55:11+00:00",
          "raw_symbol": "BTCUSD",
          "resolved": null,
          "side": "buy",
          "entry": 82.071,
          "sl": 81.641,
          "tps": [
            82.711
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4394,
          "date_utc": "2026-10-17T15:35:56+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 56.97839,
          "sl": 56.6573,
          "tps": [
            57.47328
          ],
          "price_at_signal": 57.043,
          "entry_gap_pct": 0.113,
          "sim_entry": 56.918,
          "variants": {
            "A": {
              "init_sl": 56.6573,
              "r_init": 0.2607,
              "outcome": "trail",
              "r": 1.345,
              "exit": 57.26865,
              "exit_time_server": "2026-10-19T02:00:00+srv"
            },
            "B": {
              "init_sl": 56.5905,
              "r_init": 0.3275,
              "outcome": "trail",
              "r": 1.109,
              "exit": 57.28125,
              "exit_time_server": "2026-10-19T02:30:00+srv"
            }
          },
          "atr14_m15": 0.16375
        },
        {
          "msg_id": 4393,
          "date_utc": "2026-10-17T15:22:22+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 1.12387,
          "sl": 1.12249,
          "tps": [
            1.12596
          ],
          "price_at_signal": 4168.77,
          "entry_gap_pct": 99.973,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4388,
          "date_utc": "2026-10-16T15:40:14+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.176,
          "sl": 4.164,
          "tps": [
            4.193
          ],
          "price_at_signal": 4196.79,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4387,
          "date_utc": "2026-10-16T15:27:09+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 101.634,
          "sl": 101.458,
          "tps": [
            101.893
          ],
          "price_at_signal": 4189.11,
          "entry_gap_pct": 97.574,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4382,
          "date_utc": "2026-10-15T15:02:17+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 1.12068,
          "sl": 1.11852,
          "tps": [
            1.1239
          ],
          "price_at_signal": 4154.71,
          "entry_gap_pct": 99.973,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4381,
          "date_utc": "2026-10-15T14:48:17+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 57.14173,
          "sl": 56.46083,
          "tps": [
            58.17472
          ],
          "price_at_signal": 56.762,
          "entry_gap_pct": 0.669,
          "sim_entry": 56.552,
          "variants": {
            "A": {
              "init_sl": 56.46083,
              "r_init": 0.09117,
              "outcome": "trail",
              "r": 1.068,
              "exit": 56.64942,
              "exit_time_server": "2026-10-15T17:15:00+srv"
            },
            "B": {
              "init_sl": 56.12445,
              "r_init": 0.42755,
              "outcome": "trail",
              "r": 1.081,
              "exit": 57.01423,
              "exit_time_server": "2026-10-15T18:30:00+srv"
            }
          },
          "atr14_m15": 0.21377
        },
        {
          "msg_id": 4375,
          "date_utc": "2026-10-14T08:46:01+00:00",
          "raw_symbol": "SIGNAL",
          "resolved": null,
          "side": "buy",
          "entry": 102.168,
          "sl": 102.109,
          "tps": [
            102.257
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4371,
          "date_utc": "2026-10-14T07:55:15+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.147,
          "sl": 4.134,
          "tps": [
            4.166
          ],
          "price_at_signal": 4152.2,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4369,
          "date_utc": "2026-10-13T17:33:43+00:00",
          "raw_symbol": "EURUSD",
          "resolved": "EURUSD",
          "side": "buy",
          "entry": 1.11896,
          "sl": 1.11757,
          "tps": [
            1.12105
          ],
          "price_at_signal": 1.11921,
          "entry_gap_pct": 0.022,
          "sim_entry": 1.11911,
          "variants": {
            "A": {
              "init_sl": 1.11757,
              "r_init": 0.00154,
              "outcome": "be",
              "r": 0.065,
              "exit": 1.11921,
              "exit_time_server": "2026-10-14T12:15:00+srv"
            },
            "B": {
              "init_sl": 1.1179,
              "r_init": 0.00121,
              "outcome": "trail",
              "r": 1.166,
              "exit": 1.12052,
              "exit_time_server": "2026-10-14T08:45:00+srv"
            }
          },
          "atr14_m15": 0.0006
        },
        {
          "msg_id": 4366,
          "date_utc": "2026-10-13T16:47:38+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 59.27396,
          "sl": 58.83812,
          "tps": [
            59.93931
          ],
          "price_at_signal": 59.305,
          "entry_gap_pct": 0.052,
          "sim_entry": 59.3,
          "variants": {
            "A": {
              "init_sl": 58.83812,
              "r_init": 0.46188,
              "outcome": "sl",
              "r": -1.0,
              "exit": 58.83812,
              "exit_time_server": "2026-10-14T04:15:00+srv"
            },
            "B": {
              "init_sl": 58.94555,
              "r_init": 0.35445,
              "outcome": "sl",
              "r": -1.0,
              "exit": 58.94555,
              "exit_time_server": "2026-10-13T20:45:00+srv"
            }
          },
          "atr14_m15": 0.17722
        },
        {
          "msg_id": 4363,
          "date_utc": "2026-10-12T15:24:03+00:00",
          "raw_symbol": "GROWTH",
          "resolved": null,
          "side": "buy",
          "entry": 102.48,
          "sl": 102.289,
          "tps": [
            102.769
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4361,
          "date_utc": "2026-10-12T14:48:02+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.168,
          "sl": 4.15,
          "tps": [
            4.195
          ],
          "price_at_signal": 4172.96,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4357,
          "date_utc": "2026-10-11T16:09:37+00:00",
          "raw_symbol": "ETHUSD",
          "resolved": null,
          "side": "buy",
          "entry": 2.531,
          "sl": 2.515,
          "tps": [
            2.554
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4351,
          "date_utc": "2026-10-10T11:45:14+00:00",
          "raw_symbol": "XTIUSD",
          "resolved": null,
          "side": "buy",
          "entry": 91.67,
          "sl": 91.1,
          "tps": [
            92.54
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4348,
          "date_utc": "2026-10-09T16:13:26+00:00",
          "raw_symbol": "EURUSD",
          "resolved": "EURUSD",
          "side": "buy",
          "entry": 1.11931,
          "sl": 1.11787,
          "tps": [
            1.12142
          ],
          "price_at_signal": 1.11959,
          "entry_gap_pct": 0.025,
          "sim_entry": 1.11966,
          "variants": {
            "A": {
              "init_sl": 1.11787,
              "r_init": 0.00179,
              "outcome": "timeout",
              "r": 0.302,
              "exit": 1.1202,
              "exit_time_server": "2026-10-10T00:00:00+srv"
            },
            "B": {
              "init_sl": 1.11847,
              "r_init": 0.00119,
              "outcome": "timeout",
              "r": 0.452,
              "exit": 1.1202,
              "exit_time_server": "2026-10-10T00:00:00+srv"
            }
          },
          "atr14_m15": 0.0006
        },
        {
          "msg_id": 4346,
          "date_utc": "2026-10-09T15:45:02+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.19,
          "sl": 4.161,
          "tps": [
            4.233
          ],
          "price_at_signal": 4184.36,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4341,
          "date_utc": "2026-10-08T15:45:11+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 58.902,
          "sl": 58.4193,
          "tps": [
            59.64319
          ],
          "price_at_signal": 59.043,
          "entry_gap_pct": 0.239,
          "sim_entry": 58.976,
          "variants": {
            "A": {
              "init_sl": 58.4193,
              "r_init": 0.5567,
              "outcome": "trail",
              "r": 2.423,
              "exit": 60.32465,
              "exit_time_server": "2026-10-09T08:45:00+srv"
            },
            "B": {
              "init_sl": 58.50624,
              "r_init": 0.46976,
              "outcome": "trail",
              "r": 2.964,
              "exit": 60.36812,
              "exit_time_server": "2026-10-09T08:45:00+srv"
            }
          },
          "atr14_m15": 0.23488
        },
        {
          "msg_id": 4340,
          "date_utc": "2026-10-08T15:30:02+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 102.194,
          "sl": 102.101,
          "tps": [
            102.331
          ],
          "price_at_signal": 4136.9,
          "entry_gap_pct": 97.53,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4333,
          "date_utc": "2026-10-07T15:36:01+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 1.11863,
          "sl": 1.11621,
          "tps": [
            1.12236
          ],
          "price_at_signal": 4099.48,
          "entry_gap_pct": 99.973,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4332,
          "date_utc": "2026-10-07T15:21:41+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.101,
          "sl": 4.077,
          "tps": [
            4.136
          ],
          "price_at_signal": 4097.68,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4327,
          "date_utc": "2026-10-06T14:05:19+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 101.928,
          "sl": 101.802,
          "tps": [
            102.118
          ],
          "price_at_signal": 4169.97,
          "entry_gap_pct": 97.556,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4326,
          "date_utc": "2026-10-06T13:49:35+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 61.27783,
          "sl": 60.88056,
          "tps": [
            61.88559
          ],
          "price_at_signal": 61.324,
          "entry_gap_pct": 0.075,
          "sim_entry": 61.332,
          "variants": {
            "A": {
              "init_sl": 60.88056,
              "r_init": 0.45144,
              "outcome": "sl",
              "r": -1.0,
              "exit": 60.88056,
              "exit_time_server": "2026-10-06T17:15:00+srv"
            },
            "B": {
              "init_sl": 60.99021,
              "r_init": 0.34179,
              "outcome": "sl",
              "r": -1.0,
              "exit": 60.99021,
              "exit_time_server": "2026-10-06T16:45:00+srv"
            }
          },
          "atr14_m15": 0.17089
        },
        {
          "msg_id": 4319,
          "date_utc": "2026-10-05T08:45:11+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.165,
          "sl": 4.142,
          "tps": [
            4.201
          ],
          "price_at_signal": 4159.15,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4318,
          "date_utc": "2026-10-05T08:30:05+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 1.12022,
          "sl": 1.11718,
          "tps": [
            1.12476
          ],
          "price_at_signal": 4152.91,
          "entry_gap_pct": 99.973,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4315,
          "date_utc": "2026-10-04T11:40:13+00:00",
          "raw_symbol": "ETHUSD",
          "resolved": null,
          "side": "buy",
          "entry": 2.702,
          "sl": 2.693,
          "tps": [
            2.715
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4311,
          "date_utc": "2026-10-03T13:59:59+00:00",
          "raw_symbol": "XTIUSD",
          "resolved": null,
          "side": "buy",
          "entry": 91.342,
          "sl": 90.16,
          "tps": [
            93.16
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4306,
          "date_utc": "2026-10-02T15:09:58+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.168,
          "sl": 4.149,
          "tps": [
            14.195
          ],
          "price_at_signal": 4191.13,
          "entry_gap_pct": 99.901,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4304,
          "date_utc": "2026-10-02T14:40:47+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 61.13326,
          "sl": 60.78079,
          "tps": [
            61.65268
          ],
          "price_at_signal": 61.428,
          "entry_gap_pct": 0.48,
          "sim_entry": 61.344,
          "variants": {
            "A": {
              "init_sl": 60.78079,
              "r_init": 0.56321,
              "outcome": "sl",
              "r": -1.0,
              "exit": 60.78079,
              "exit_time_server": "2026-10-02T17:45:00+srv"
            },
            "B": {
              "init_sl": 60.74503,
              "r_init": 0.59897,
              "outcome": "sl",
              "r": -1.0,
              "exit": 60.74503,
              "exit_time_server": "2026-10-02T17:45:00+srv"
            }
          },
          "atr14_m15": 0.29949
        },
        {
          "msg_id": 4300,
          "date_utc": "2026-10-01T11:29:58+00:00",
          "raw_symbol": "GROWTH",
          "resolved": null,
          "side": "buy",
          "entry": 101.776,
          "sl": 101.519,
          "tps": [
            102.168
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4298,
          "date_utc": "2026-10-01T10:59:58+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 1.12918,
          "sl": 1.1269,
          "tps": [
            1.13257
          ],
          "price_at_signal": 4161.47,
          "entry_gap_pct": 99.973,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4292,
          "date_utc": "2026-09-30T11:29:58+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.18,
          "sl": 4.164,
          "tps": [
            4.204
          ],
          "price_at_signal": 4187.17,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4290,
          "date_utc": "2026-09-30T10:59:44+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 60.76258,
          "sl": 60.51055,
          "tps": [
            61.14642
          ],
          "price_at_signal": 60.885,
          "entry_gap_pct": 0.201,
          "sim_entry": 60.844,
          "variants": {
            "A": {
              "init_sl": 60.51055,
              "r_init": 0.33345,
              "outcome": "trail",
              "r": 1.668,
              "exit": 61.40028,
              "exit_time_server": "2026-09-30T15:45:00+srv"
            },
            "B": {
              "init_sl": 60.50022,
              "r_init": 0.34378,
              "outcome": "trail",
              "r": 1.603,
              "exit": 61.39511,
              "exit_time_server": "2026-09-30T15:45:00+srv"
            }
          },
          "atr14_m15": 0.17189
        },
        {
          "msg_id": 4284,
          "date_utc": "2026-09-29T07:44:58+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 1.13448,
          "sl": 1.13325,
          "tps": [
            1.13634
          ],
          "price_at_signal": 4143.26,
          "entry_gap_pct": 99.973,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4283,
          "date_utc": "2026-09-29T07:30:05+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 101.287,
          "sl": 101.184,
          "tps": [
            101.439
          ],
          "price_at_signal": 4143.26,
          "entry_gap_pct": 97.555,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4281,
          "date_utc": "2026-09-28T16:22:59+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 61.05156,
          "sl": 59.91772,
          "tps": [
            62.72123
          ],
          "price_at_signal": 61.012,
          "entry_gap_pct": 0.065,
          "sim_entry": 61.125,
          "variants": {
            "A": {
              "init_sl": 59.91772,
              "r_init": 1.20728,
              "outcome": "timeout",
              "r": -0.718,
              "exit": 60.258,
              "exit_time_server": "2026-09-30T18:30:00+srv"
            },
            "B": {
              "init_sl": 60.60974,
              "r_init": 0.51526,
              "outcome": "be",
              "r": 0.019,
              "exit": 61.135,
              "exit_time_server": "2026-09-28T19:45:00+srv"
            }
          },
          "atr14_m15": 0.25763
        },
        {
          "msg_id": 4279,
          "date_utc": "2026-09-28T15:53:02+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.117,
          "sl": 4.071,
          "tps": [
            4.188
          ],
          "price_at_signal": 4123.19,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4273,
          "date_utc": "2026-09-27T15:28:04+00:00",
          "raw_symbol": "BTCUSD",
          "resolved": null,
          "side": "buy",
          "entry": 84.558,
          "sl": 84.29,
          "tps": [
            84.967
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4268,
          "date_utc": "2026-09-26T15:03:56+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 2.668,
          "sl": 2.684,
          "tps": [
            2.695
          ],
          "price_at_signal": 4291.11,
          "entry_gap_pct": 99.938,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4261,
          "date_utc": "2026-09-25T08:55:07+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 64.42695,
          "sl": 64.01853,
          "tps": [
            64.02942
          ],
          "price_at_signal": 63.765,
          "entry_gap_pct": 1.038,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4260,
          "date_utc": "2026-09-25T08:37:40+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 1.13895,
          "sl": 1.13782,
          "tps": [
            1.14063
          ],
          "price_at_signal": 4273.72,
          "entry_gap_pct": 99.973,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4257,
          "date_utc": "2026-09-24T14:50:14+00:00",
          "raw_symbol": "STRONG",
          "resolved": null,
          "side": "buy",
          "entry": 101.278,
          "sl": 101.188,
          "tps": [
            101.411
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4256,
          "date_utc": "2026-09-24T14:35:13+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.264,
          "sl": 4.251,
          "tps": [
            4.285
          ],
          "price_at_signal": 4276.38,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4250,
          "date_utc": "2026-09-23T09:31:57+00:00",
          "raw_symbol": "EURUSD",
          "resolved": "EURUSD",
          "side": "buy",
          "entry": 1.14142,
          "sl": 1.14016,
          "tps": [
            1.14327
          ],
          "price_at_signal": 1.14191,
          "entry_gap_pct": 0.043,
          "sim_entry": 1.14181,
          "variants": {
            "A": {
              "init_sl": 1.14016,
              "r_init": 0.00165,
              "outcome": "sl",
              "r": -1.0,
              "exit": 1.14016,
              "exit_time_server": "2026-09-23T15:30:00+srv"
            },
            "B": {
              "init_sl": 1.14088,
              "r_init": 0.00093,
              "outcome": "sl",
              "r": -1.0,
              "exit": 1.14088,
              "exit_time_server": "2026-09-23T12:45:00+srv"
            }
          },
          "atr14_m15": 0.00047
        },
        {
          "msg_id": 4249,
          "date_utc": "2026-09-23T09:07:16+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 65.45094,
          "sl": 64.8312,
          "tps": [
            66.3757
          ],
          "price_at_signal": 65.387,
          "entry_gap_pct": 0.098,
          "sim_entry": 65.363,
          "variants": {
            "A": {
              "init_sl": 64.8312,
              "r_init": 0.5318,
              "outcome": "sl",
              "r": -1.0,
              "exit": 64.8312,
              "exit_time_server": "2026-09-23T14:30:00+srv"
            },
            "B": {
              "init_sl": 64.97414,
              "r_init": 0.38886,
              "outcome": "sl",
              "r": -1.0,
              "exit": 64.97414,
              "exit_time_server": "2026-09-23T14:15:00+srv"
            }
          },
          "atr14_m15": 0.19443
        },
        {
          "msg_id": 4245,
          "date_utc": "2026-09-22T15:29:59+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.336,
          "sl": 4.319,
          "tps": [
            4.362
          ],
          "price_at_signal": 4333.63,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4243,
          "date_utc": "2026-09-22T14:59:57+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 100.515,
          "sl": 100.429,
          "tps": [
            100.644
          ],
          "price_at_signal": 4341.11,
          "entry_gap_pct": 97.685,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4237,
          "date_utc": "2026-09-21T15:29:57+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.348,
          "sl": 4.334,
          "tps": [
            4.371
          ],
          "price_at_signal": 4340.02,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4236,
          "date_utc": "2026-09-21T15:14:57+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 1.14727,
          "sl": 1.14671,
          "tps": [
            1.14811
          ],
          "price_at_signal": 4346.03,
          "entry_gap_pct": 99.974,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4231,
          "date_utc": "2026-09-20T12:28:50+00:00",
          "raw_symbol": "BTCUSD",
          "resolved": null,
          "side": "buy",
          "entry": 80.395,
          "sl": 80.047,
          "tps": [
            80.931
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4226,
          "date_utc": "2026-09-19T15:24:57+00:00",
          "raw_symbol": "XTIUSD",
          "resolved": null,
          "side": "buy",
          "entry": 99.405,
          "sl": 98.047,
          "tps": [
            101.475
          ],
          "outcome": "no_symbol_on_broker"
        },
        {
          "msg_id": 4222,
          "date_utc": "2026-09-18T16:05:17+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 66.33065,
          "sl": 65.83695,
          "tps": [
            67.08586
          ],
          "price_at_signal": 66.328,
          "entry_gap_pct": 0.004,
          "sim_entry": 66.343,
          "variants": {
            "A": {
              "init_sl": 65.83695,
              "r_init": 0.50605,
              "outcome": "be",
              "r": 0.02,
              "exit": 66.353,
              "exit_time_server": "2026-09-18T22:45:00+srv"
            },
            "B": {
              "init_sl": 65.86049,
              "r_init": 0.48251,
              "outcome": "be",
              "r": 0.021,
              "exit": 66.353,
              "exit_time_server": "2026-09-18T22:45:00+srv"
            }
          },
          "atr14_m15": 0.24126
        },
        {
          "msg_id": 4219,
          "date_utc": "2026-09-18T15:19:58+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 100.476,
          "sl": 100.395,
          "tps": [
            100.601
          ],
          "price_at_signal": 4351.5,
          "entry_gap_pct": 97.691,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4216,
          "date_utc": "2026-09-17T13:54:58+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4.368,
          "sl": 4.322,
          "tps": [
            4.437
          ],
          "price_at_signal": 4360.5,
          "entry_gap_pct": 99.9,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4213,
          "date_utc": "2026-09-17T13:10:14+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 1.14909,
          "sl": 1.14701,
          "tps": [
            1.15231
          ],
          "price_at_signal": 4349.51,
          "entry_gap_pct": 99.974,
          "outcome": "stale_repost"
        },
        {
          "msg_id": 4208,
          "date_utc": "2026-09-16T15:20:58+00:00",
          "raw_symbol": "XAGUSD",
          "resolved": "XAGUSD",
          "side": "buy",
          "entry": 64.76613,
          "sl": 64.38014,
          "tps": [
            65.34373
          ],
          "price_at_signal": 64.373,
          "entry_gap_pct": 0.611,
          "sim_entry": 64.302,
          "variants": {
            "A": {
              "init_sl": 64.38014,
              "r_init": 0.07814,
              "outcome": "sl",
              "r": 1.0,
              "exit": 64.38014,
              "exit_time_server": "2026-09-16T17:30:00+srv"
            },
            "B": {
              "init_sl": 63.88398,
              "r_init": 0.41802,
              "outcome": "be",
              "r": 0.024,
              "exit": 64.312,
              "exit_time_server": "2026-09-16T20:00:00+srv"
            }
          },
          "atr14_m15": 0.20901
        },
        {
          "msg_id": 4206,
          "date_utc": "2026-09-16T14:51:57+00:00",
         

... (truncated, 641805 total bytes) ...

