---
slug: channel_report_v2
type: note
graph: gitnexus
---

{
  "generated_utc": "2026-10-15T23:22:17.419670+00:00",
  "research": "EXIT-GEOMETRY: channel direction + relay trailing exit (POLICY V2)",
  "method": {
    "messages_per_channel": 300,
    "parser": "relay's own parser.parse_signal (deterministic, no AI fallback)",
    "keep_filter": "parse_ok, non-manage, has SL, >=1 TP, numeric entry, not stale >1% (identical to V1)",
    "timeframe": "M15",
    "horizon": "48h from simulated entry",
    "entry": "open of first M15 bar at/after signal time (market entry)",
    "initial_sl": "variant A = channel's stated SL; variant B = 2 x Wilder ATR(14) M15 of strictly closed bars before the entry bar",
    "channel_tps": "IGNORED entirely",
    "exit_management": "manage.py rules from config.json: SL -> entry +/- 10pt buffer at +1R; from +1.5R trails 0.5R behind best favorable price; ratchet-only",
    "same_bar_rule": "stop as of bar open checked FIRST; this bar's favorable extreme may then advance the stop, effective next bar (conservative)",
    "timeout": "exit at close of last bar inside 48h, partial +/-R",
    "stale": "stated entry >1% away from price at signal time",
    "recap": "messages containing 'tp hit' or 'pips' counted, never simulated",
    "win_pct": "resolved trades with R > 0 (BE+buffer exits are tiny wins)",
    "costs": "0.07R round-trip haircut per trade (same as V1/backtest.py)",
    "max_dd": "worst peak-to-trough of cumulative after-cost R curve, trades ordered by entry time",
    "verdict_bands": "expectancy after costs >= +0.05R POSITIVE EDGE, <= -0.05R NEGATIVE, else FLAT; n < 10 = INSUFFICIENT DATA (tentative)",
    "server_offset_s": 10799,
    "server_offset_method": "freshest tick across XAUUSD/EURUSD/GBPUSD/US30/XAGUSD/AUDUSD",
    "tick_times_at_run": {
      "XAUUSD": 1792117332,
      "EURUSD": 1792117332,
      "GBPUSD": 1792117332,
      "US30": 1792117331,
      "XAGUSD": 1792117332,
      "AUDUSD": 1792117332
    },
    "symbols_selected_for_data": [],
    "session": "telethon-research.session (sqlite backup copy of telethon.session; live session never connected/written)",
    "mt5_access": "read-only: initialize/shutdown + copy_rates/symbol_info/symbol_info_tick/symbol_select; order_send never called"
  },
  "channels": [
    {
      "id": -1002369502254,
      "name": "\ud835\ude71\ud835\ude8e\ud835\ude9c\ud835\ude9d \ud835\ude82\ud835\ude92\ud835\ude90\ud835\ude97\ud835\ude8a\ud835\ude95 \ud835\ude75\ud835\ude98\ud835\ude9b\ud835\ude8e\ud835\udea1",
      "plain_name": "Best Signal Forex",
      "messages": 300,
      "media_only": 19,
      "not_signal": 98,
      "unparseable": 6,
      "unverifiable": 0,
      "recap_posts": 145,
      "no_data": 0,
      "pending": 0,
      "degenerate": 0,
      "stale": 0,
      "error": null,
      "signals": [
        {
          "msg_id": 7716,
          "date_utc": "2026-10-15T12:11:02+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4150.0,
          "sl": 4163.0,
          "tps": [
            4125.0,
            4130.0,
            4135.0,
            4140.0,
            4145.0
          ],
          "price_at_signal": 4144.92,
          "entry_gap_pct": 0.123,
          "sim_entry": 4148.51,
          "variants": {
            "A": {
              "init_sl": 4163.0,
              "r_init": 14.49,
              "outcome": "be",
              "r": 0.007,
              "exit": 4148.41,
              "exit_time_server": "2026-10-15T15:45:00+srv"
            },
            "B": {
              "init_sl": 4160.31624,
              "r_init": 11.80624,
              "outcome": "trail",
              "r": 1.047,
              "exit": 4136.14312,
              "exit_time_server": "2026-10-15T15:45:00+srv"
            }
          },
          "atr14_m15": 5.90312
        },
        {
          "msg_id": 7702,
          "date_utc": "2026-10-14T13:55:22+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4098.0,
          "sl": 4110.0,
          "tps": [
            4075.0,
            4080.0,
            4084.0,
            4088.0,
            4093.0
          ],
          "price_at_signal": 4103.96,
          "entry_gap_pct": 0.145,
          "sim_entry": 4088.16,
          "variants": {
            "A": {
              "init_sl": 4110.0,
              "r_init": 21.84,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4110.0,
              "exit_time_server": "2026-10-15T01:30:00+srv"
            },
            "B": {
              "init_sl": 4112.86283,
              "r_init": 24.70283,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4112.86283,
              "exit_time_server": "2026-10-15T03:00:00+srv"
            }
          },
          "atr14_m15": 12.35141
        },
        {
          "msg_id": 7690,
          "date_utc": "2026-10-14T12:08:12+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4145.0,
          "sl": 4130.0,
          "tps": [
            4150.0,
            4155.0,
            4160.0,
            4165.0,
            4175.0
          ],
          "price_at_signal": 4139.27,
          "entry_gap_pct": 0.138,
          "sim_entry": 4149.48,
          "variants": {
            "A": {
              "init_sl": 4130.0,
              "r_init": 19.48,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4130.0,
              "exit_time_server": "2026-10-14T15:30:00+srv"
            },
            "B": {
              "init_sl": 4137.72146,
              "r_init": 11.75854,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4137.72146,
              "exit_time_server": "2026-10-14T15:30:00+srv"
            }
          },
          "atr14_m15": 5.87927
        },
        {
          "msg_id": 7686,
          "date_utc": "2026-10-14T07:22:38+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4145.0,
          "sl": 4155.0,
          "tps": [
            4120.0,
            4125.0,
            4130.0,
            4135.0,
            4140.0
          ],
          "price_at_signal": 4148.94,
          "entry_gap_pct": 0.095,
          "sim_entry": 4146.22,
          "variants": {
            "A": {
              "init_sl": 4155.0,
              "r_init": 8.78,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4155.0,
              "exit_time_server": "2026-10-14T11:15:00+srv"
            },
            "B": {
              "init_sl": 4160.72477,
              "r_init": 14.50477,
              "outcome": "trail",
              "r": 3.72,
              "exit": 4092.26238,
              "exit_time_server": "2026-10-14T15:45:00+srv"
            }
          },
          "atr14_m15": 7.25238
        },
        {
          "msg_id": 7667,
          "date_utc": "2026-10-13T12:26:37+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4187.0,
          "sl": 4200.0,
          "tps": [
            4162.0,
            4167.0,
            4172.0,
            4177.0,
            4182.0
          ],
          "price_at_signal": 4186.42,
          "entry_gap_pct": 0.014,
          "sim_entry": 4186.75,
          "variants": {
            "A": {
              "init_sl": 4200.0,
              "r_init": 13.25,
              "outcome": "be",
              "r": 0.008,
              "exit": 4186.65,
              "exit_time_server": "2026-10-13T16:15:00+srv"
            },
            "B": {
              "init_sl": 4197.02079,
              "r_init": 10.27079,
              "outcome": "be",
              "r": 0.01,
              "exit": 4186.65,
              "exit_time_server": "2026-10-13T16:15:00+srv"
            }
          },
          "atr14_m15": 5.1354
        },
        {
          "msg_id": 7647,
          "date_utc": "2026-10-12T06:02:44+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4192.0,
          "sl": 4205.0,
          "tps": [
            4170.0,
            4175.0,
            4180.0,
            4183.0,
            4187.0
          ],
          "price_at_signal": 4191.0,
          "entry_gap_pct": 0.024,
          "sim_entry": 4185.62,
          "variants": {
            "A": {
              "init_sl": 4205.0,
              "r_init": 19.38,
              "outcome": "trail",
              "r": 1.105,
              "exit": 4164.21,
              "exit_time_server": "2026-10-12T15:45:00+srv"
            },
            "B": {
              "init_sl": 4198.95644,
              "r_init": 13.33644,
              "outcome": "trail",
              "r": 1.832,
              "exit": 4161.18822,
              "exit_time_server": "2026-10-12T15:45:00+srv"
            }
          },
          "atr14_m15": 6.66822
        },
        {
          "msg_id": 7628,
          "date_utc": "2026-10-09T08:43:51+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4192.0,
          "sl": 4205.0,
          "tps": [
            4170.0,
            4175.0,
            4180.0,
            4183.0,
            4187.0
          ],
          "price_at_signal": 4198.33,
          "entry_gap_pct": 0.151,
          "sim_entry": 4191.19,
          "variants": {
            "A": {
              "init_sl": 4205.0,
              "r_init": 13.81,
              "outcome": "be",
              "r": 0.007,
              "exit": 4191.09,
              "exit_time_server": "2026-10-09T15:30:00+srv"
            },
            "B": {
              "init_sl": 4203.90477,
              "r_init": 12.71477,
              "outcome": "be",
              "r": 0.008,
              "exit": 4191.09,
              "exit_time_server": "2026-10-09T15:30:00+srv"
            }
          },
          "atr14_m15": 6.35738
        },
        {
          "msg_id": 7611,
          "date_utc": "2026-10-08T12:56:38+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4115.0,
          "sl": 4103.0,
          "tps": [
            4120.0,
            4125.0,
            4130.0,
            4135.0,
            4140.0
          ],
          "price_at_signal": 4119.13,
          "entry_gap_pct": 0.1,
          "sim_entry": 4118.63,
          "variants": {
            "A": {
              "init_sl": 4103.0,
              "r_init": 15.63,
              "outcome": "be",
              "r": 0.006,
              "exit": 4118.73,
              "exit_time_server": "2026-10-08T18:00:00+srv"
            },
            "B": {
              "init_sl": 4103.51012,
              "r_init": 15.11988,
              "outcome": "be",
              "r": 0.007,
              "exit": 4118.73,
              "exit_time_server": "2026-10-08T18:00:00+srv"
            }
          },
          "atr14_m15": 7.55994
        },
        {
          "msg_id": 7590,
          "date_utc": "2026-10-07T11:05:58+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4120.0,
          "sl": 4132.0,
          "tps": [
            4095.0,
            4100.0,
            4105.0,
            4110.0,
            4115.0
          ],
          "price_at_signal": 4116.79,
          "entry_gap_pct": 0.078,
          "sim_entry": 4120.99,
          "variants": {
            "A": {
              "init_sl": 4132.0,
              "r_init": 11.01,
              "outcome": "trail",
              "r": 3.238,
              "exit": 4085.345,
              "exit_time_server": "2026-10-07T15:30:00+srv"
            },
            "B": {
              "init_sl": 4132.36248,
              "r_init": 11.37248,
              "outcome": "trail",
              "r": 3.118,
              "exit": 4085.52624,
              "exit_time_server": "2026-10-07T15:30:00+srv"
            }
          },
          "atr14_m15": 5.68624
        },
        {
          "msg_id": 7585,
          "date_utc": "2026-10-06T12:15:33+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4175.0,
          "sl": 4162.0,
          "tps": [
            4180.0,
            4185.0,
            4195.0,
            4200.0
          ],
          "price_at_signal": 4178.39,
          "entry_gap_pct": 0.081,
          "sim_entry": 4175.8,
          "variants": {
            "A": {
              "init_sl": 4162.0,
              "r_init": 13.8,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4162.0,
              "exit_time_server": "2026-10-06T16:15:00+srv"
            },
            "B": {
              "init_sl": 4163.63713,
              "r_init": 12.16287,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4163.63713,
              "exit_time_server": "2026-10-06T16:15:00+srv"
            }
          },
          "atr14_m15": 6.08144
        },
        {
          "msg_id": 7564,
          "date_utc": "2026-10-05T03:40:20+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4146.0,
          "sl": 4157.0,
          "tps": [
            4126.0,
            4130.0,
            4133.0,
            4137.0,
            4141.0
          ],
          "price_at_signal": 4143.16,
          "entry_gap_pct": 0.069,
          "sim_entry": 4143.25,
          "variants": {
            "A": {
              "init_sl": 4157.0,
              "r_init": 13.75,
              "outcome": "be",
              "r": 0.007,
              "exit": 4143.15,
              "exit_time_server": "2026-10-05T09:00:00+srv"
            },
            "B": {
              "init_sl": 4158.98376,
              "r_init": 15.73376,
              "outcome": "be",
              "r": 0.006,
              "exit": 4143.15,
              "exit_time_server": "2026-10-05T09:00:00+srv"
            }
          },
          "atr14_m15": 7.86688
        },
        {
          "msg_id": 7540,
          "date_utc": "2026-10-02T09:37:10+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4187.0,
          "sl": 4200.0,
          "tps": [
            4165.0,
            4170.0,
            4174.0,
            4178.0,
            4182.0
          ],
          "price_at_signal": 4186.45,
          "entry_gap_pct": 0.013,
          "sim_entry": 4184.22,
          "variants": {
            "A": {
              "init_sl": 4200.0,
              "r_init": 15.78,
              "outcome": "be",
              "r": 0.006,
              "exit": 4184.12,
              "exit_time_server": "2026-10-02T14:00:00+srv"
            },
            "B": {
              "init_sl": 4199.24564,
              "r_init": 15.02564,
              "outcome": "be",
              "r": 0.007,
              "exit": 4184.12,
              "exit_time_server": "2026-10-02T14:00:00+srv"
            }
          },
          "atr14_m15": 7.51282
        },
        {
          "msg_id": 7529,
          "date_utc": "2026-10-01T11:25:06+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4165.0,
          "sl": 4152.0,
          "tps": [
            4170.0,
            4175.0,
            4180.0,
            4185.0,
            4190.0
          ],
          "price_at_signal": 4169.38,
          "entry_gap_pct": 0.105,
          "sim_entry": 4171.72,
          "variants": {
            "A": {
              "init_sl": 4152.0,
              "r_init": 19.72,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4152.0,
              "exit_time_server": "2026-10-01T17:00:00+srv"
            },
            "B": {
              "init_sl": 4156.66823,
              "r_init": 15.05177,
              "outcome": "be",
              "r": 0.007,
              "exit": 4171.82,
              "exit_time_server": "2026-10-01T16:15:00+srv"
            }
          },
          "atr14_m15": 7.52588
        },
        {
          "msg_id": 7514,
          "date_utc": "2026-09-30T06:05:58+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4177.0,
          "sl": 4165.0,
          "tps": [
            4182.0,
            4187.0,
            4192.0,
            4197.0,
            4202.0
          ],
          "price_at_signal": 4178.0,
          "entry_gap_pct": 0.024,
          "sim_entry": 4183.12,
          "variants": {
            "A": {
              "init_sl": 4165.0,
              "r_init": 18.12,
              "outcome": "be",
              "r": 0.006,
              "exit": 4183.22,
              "exit_time_server": "2026-09-30T12:15:00+srv"
            },
            "B": {
              "init_sl": 4169.26201,
              "r_init": 13.85799,
              "outcome": "be",
              "r": 0.007,
              "exit": 4183.22,
              "exit_time_server": "2026-09-30T12:15:00+srv"
            }
          },
          "atr14_m15": 6.92899
        },
        {
          "msg_id": 7502,
          "date_utc": "2026-09-29T09:52:22+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4142.0,
          "sl": 4130.0,
          "tps": [
            4147.0,
            4152.0,
            4157.0,
            4162.0,
            4167.0
          ],
          "price_at_signal": 4145.52,
          "entry_gap_pct": 0.085,
          "sim_entry": 4145.7,
          "variants": {
            "A": {
              "init_sl": 4130.0,
              "r_init": 15.7,
              "outcome": "trail",
              "r": 1.371,
              "exit": 4167.23,
              "exit_time_server": "2026-09-29T17:30:00+srv"
            },
            "B": {
              "init_sl": 4132.82609,
              "r_init": 12.87391,
              "outcome": "trail",
              "r": 1.782,
              "exit": 4168.64305,
              "exit_time_server": "2026-09-29T17:30:00+srv"
            }
          },
          "atr14_m15": 6.43695
        },
        {
          "msg_id": 7489,
          "date_utc": "2026-09-28T12:45:49+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4148.0,
          "sl": 4162.0,
          "tps": [
            4125.0,
            4130.0,
            4135.0,
            4140.0,
            4143.0
          ],
          "price_at_signal": 4145.12,
          "entry_gap_pct": 0.069,
          "sim_entry": 4154.27,
          "variants": {
            "A": {
              "init_sl": 4162.0,
              "r_init": 7.73,
              "outcome": "trail",
              "r": 1.151,
              "exit": 4145.375,
              "exit_time_server": "2026-09-28T16:30:00+srv"
            },
            "B": {
              "init_sl": 4173.79462,
              "r_init": 19.52462,
              "outcome": "trail",
              "r": 1.729,
              "exit": 4120.51231,
              "exit_time_server": "2026-09-28T18:00:00+srv"
            }
          },
          "atr14_m15": 9.76231
        },
        {
          "msg_id": 7475,
          "date_utc": "2026-09-28T04:42:25+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4200.0,
          "sl": 4212.0,
          "tps": [
            4175.0,
            4180.0,
            4185.0,
            4190.0,
            4195.0
          ],
          "price_at_signal": 4199.45,
          "entry_gap_pct": 0.013,
          "sim_entry": 4198.09,
          "variants": {
            "A": {
              "init_sl": 4212.0,
              "r_init": 13.91,
              "outcome": "trail",
              "r": 1.578,
              "exit": 4176.145,
              "exit_time_server": "2026-09-28T09:30:00+srv"
            },
            "B": {
              "init_sl": 4214.77282,
              "r_init": 16.68282,
              "outcome": "trail",
              "r": 1.232,
              "exit": 4177.53141,
              "exit_time_server": "2026-09-28T09:30:00+srv"
            }
          },
          "atr14_m15": 8.34141
        },
        {
          "msg_id": 7449,
          "date_utc": "2026-09-25T08:21:54+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4278.0,
          "sl": 4268.0,
          "tps": [
            4283.0,
            4288.0,
            4293.0,
            4298.0,
            4305.0
          ],
          "price_at_signal": 4281.67,
          "entry_gap_pct": 0.086,
          "sim_entry": 4284.11,
          "variants": {
            "A": {
              "init_sl": 4268.0,
              "r_init": 16.11,
              "outcome": "trail",
              "r": 1.458,
              "exit": 4307.605,
              "exit_time_server": "2026-09-25T14:15:00+srv"
            },
            "B": {
              "init_sl": 4270.35976,
              "r_init": 13.75024,
              "outcome": "trail",
              "r": 1.344,
              "exit": 4302.58488,
              "exit_time_server": "2026-09-25T13:30:00+srv"
            }
          },
          "atr14_m15": 6.87512
        },
        {
          "msg_id": 7435,
          "date_utc": "2026-09-24T06:52:53+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4278.0,
          "sl": 4290.0,
          "tps": [
            4255.0,
            4260.0,
            4265.0,
            4270.0,
            4273.0
          ],
          "price_at_signal": 4277.72,
          "entry_gap_pct": 0.007,
          "sim_entry": 4276.2,
          "variants": {
            "A": {
              "init_sl": 4290.0,
              "r_init": 13.8,
              "outcome": "trail",
              "r": 1.349,
              "exit": 4257.58,
              "exit_time_server": "2026-09-24T13:00:00+srv"
            },
            "B": {
              "init_sl": 4289.93317,
              "r_init": 13.73317,
              "outcome": "trail",
              "r": 1.358,
              "exit": 4257.54659,
              "exit_time_server": "2026-09-24T13:00:00+srv"
            }
          },
          "atr14_m15": 6.86659
        },
        {
          "msg_id": 7431,
          "date_utc": "2026-09-23T12:08:41+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4312.0,
          "sl": 4300.0,
          "tps": [
            4317.0,
            4322.0,
            4327.0,
            4332.0,
            4337.0
          ],
          "price_at_signal": 4309.51,
          "entry_gap_pct": 0.058,
          "sim_entry": 4318.81,
          "variants": {
            "A": {
              "init_sl": 4300.0,
              "r_init": 18.81,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4300.0,
              "exit_time_server": "2026-09-23T16:00:00+srv"
            },
            "B": {
              "init_sl": 4305.84718,
              "r_init": 12.96282,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4305.84718,
              "exit_time_server": "2026-09-23T15:30:00+srv"
            }
          },
          "atr14_m15": 6.48141
        },
        {
          "msg_id": 7428,
          "date_utc": "2026-09-23T11:39:16+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4303.0,
          "sl": 4315.0,
          "tps": [
            4278.0,
            4283.0,
            4288.0,
            4293.0,
            4298.0
          ],
          "price_at_signal": 4306.2,
          "entry_gap_pct": 0.074,
          "sim_entry": 4304.78,
          "variants": {
            "A": {
              "init_sl": 4315.0,
              "r_init": 10.22,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4315.0,
              "exit_time_server": "2026-09-23T15:00:00+srv"
            },
            "B": {
              "init_sl": 4317.31238,
              "r_init": 12.53238,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4317.31238,
              "exit_time_server": "2026-09-23T15:00:00+srv"
            }
          },
          "atr14_m15": 6.26619
        },
        {
          "msg_id": 7403,
          "date_utc": "2026-09-22T07:28:27+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4322.0,
          "sl": 4335.0,
          "tps": [
            4300.0,
            4305.0,
            4310.0,
            4313.0,
            4317.0
          ],
          "price_at_signal": 4320.21,
          "entry_gap_pct": 0.041,
          "sim_entry": 4315.28,
          "variants": {
            "A": {
              "init_sl": 4335.0,
              "r_init": 19.72,
              "outcome": "be",
              "r": 0.005,
              "exit": 4315.18,
              "exit_time_server": "2026-09-22T11:45:00+srv"
            },
            "B": {
              "init_sl": 4332.5202,
              "r_init": 17.2402,
              "outcome": "be",
              "r": 0.006,
              "exit": 4315.18,
              "exit_time_server": "2026-09-22T11:45:00+srv"
            }
          },
          "atr14_m15": 8.6201
        },
        {
          "msg_id": 7390,
          "date_utc": "2026-09-21T04:56:32+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4359.0,
          "sl": 4371.0,
          "tps": [
            4335.0,
            4341.0,
            4345.0,
            4350.0,
            4354.0
          ],
          "price_at_signal": 4361.63,
          "entry_gap_pct": 0.06,
          "sim_entry": 4355.79,
          "variants": {
            "A": {
              "init_sl": 4371.0,
              "r_init": 15.21,
              "outcome": "be",
              "r": 0.007,
              "exit": 4355.69,
              "exit_time_server": "2026-09-21T13:15:00+srv"
            },
            "B": {
              "init_sl": 4371.15459,
              "r_init": 15.36459,
              "outcome": "be",
              "r": 0.007,
              "exit": 4355.69,
              "exit_time_server": "2026-09-21T13:15:00+srv"
            }
          },
          "atr14_m15": 7.6823
        },
        {
          "msg_id": 7379,
          "date_utc": "2026-09-18T12:24:02+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4365.0,
          "sl": 4377.0,
          "tps": [
            4340.0,
            4345.0,
            4350.0,
            4355.0,
            4360.0
          ],
          "price_at_signal": 4373.83,
          "entry_gap_pct": 0.202,
          "sim_entry": 4358.16,
          "variants": {
            "A": {
              "init_sl": 4377.0,
              "r_init": 18.84,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4377.0,
              "exit_time_server": "2026-09-18T19:15:00+srv"
            },
            "B": {
              "init_sl": 4376.35986,
              "r_init": 18.19986,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4376.35986,
              "exit_time_server": "2026-09-18T19:15:00+srv"
            }
          },
          "atr14_m15": 9.09993
        },
        {
          "msg_id": 7372,
          "date_utc": "2026-09-18T06:01:48+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4380.0,
          "sl": 4370.0,
          "tps": [
            4385.0,
            4390.0,
            4395.0,
            4400.0,
            4405.0
          ],
          "price_at_signal": 4377.28,
          "entry_gap_pct": 0.062,
          "sim_entry": 4388.85,
          "variants": {
            "A": {
              "init_sl": 4370.0,
              "r_init": 18.85,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4370.0,
              "exit_time_server": "2026-09-18T15:15:00+srv"
            },
            "B": {
              "init_sl": 4371.49159,
              "r_init": 17.35841,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4371.49159,
              "exit_time_server": "2026-09-18T15:00:00+srv"
            }
          },
          "atr14_m15": 8.6792
        },
        {
          "msg_id": 7365,
          "date_utc": "2026-09-17T12:23:03+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4365.0,
          "sl": 4355.0,
          "tps": [
            4370.0,
            4375.0,
            4380.0,
            4385.0,
            4390.0
          ],
          "price_at_signal": 4354.49,
          "entry_gap_pct": 0.241,
          "sim_entry": 4380.93,
          "variants": {
            "A": {
              "init_sl": 4355.0,
              "r_init": 25.93,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4355.0,
              "exit_time_server": "2026-09-17T17:45:00+srv"
            },
            "B": {
              "init_sl": 4357.76459,
              "r_init": 23.16541,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4357.76459,
              "exit_time_server": "2026-09-17T16:30:00+srv"
            }
          },
          "atr14_m15": 11.5827
        },
        {
          "msg_id": 7363,
          "date_utc": "2026-09-17T05:27:32+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4290.0,
          "sl": 4302.0,
          "tps": [
            4268.0,
            4272.0,
            4276.0,
            4280.0,
            4285.0
          ],
          "price_at_signal": 4294.03,
          "entry_gap_pct": 0.094,
          "sim_entry": 4286.46,
          "variants": {
            "A": {
              "init_sl": 4302.0,
              "r_init": 15.54,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4302.0,
              "exit_time_server": "2026-09-17T08:45:00+srv"
            },
            "B": {
              "init_sl": 4306.80301,
              "r_init": 20.34301,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4306.80301,
              "exit_time_server": "2026-09-17T09:00:00+srv"
            }
          },
          "atr14_m15": 10.1715
        },
        {
          "msg_id": 7337,
          "date_utc": "2026-09-16T13:41:39+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4348.0,
          "sl": 4360.0,
          "tps": [
            4330.0,
            4335.0,
            4340.0,
            4343.0
          ],
          "price_at_signal": 4351.92,
          "entry_gap_pct": 0.09,
          "sim_entry": 4340.43,
          "variants": {
            "A": {
              "init_sl": 4360.0,
              "r_init": 19.57,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4360.0,
              "exit_time_server": "2026-09-16T18:45:00+srv"
            },
            "B": {
              "init_sl": 4357.34498,
              "r_init": 16.91498,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4357.34498,
              "exit_time_server": "2026-09-16T18:00:00+srv"
            }
          },
          "atr14_m15": 8.45749
        },
        {
          "msg_id": 7331,
          "date_utc": "2026-09-16T11:07:04+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4347.0,
          "sl": 4335.0,
          "tps": [
            4352.0,
            4356.0,
            4361.0,
            4366.0,
            4371.0
          ],
          "price_at_signal": 4350.05,
          "entry_gap_pct": 0.07,
          "sim_entry": 4347.05,
          "variants": {
            "A": {
              "init_sl": 4335.0,
              "r_init": 12.05,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4335.0,
              "exit_time_server": "2026-09-16T15:30:00+srv"
            },
            "B": {
              "init_sl": 4332.90309,
              "r_init": 14.14691,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4332.90309,
              "exit_time_server": "2026-09-16T17:00:00+srv"
            }
          },
          "atr14_m15": 7.07345
        },
        {
          "msg_id": 7308,
          "date_utc": "2026-09-15T09:33:27+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4264.0,
          "sl": 4251.0,
          "tps": [
            4268.0,
            4272.0,
            4276.0,
            4280.0,
            4284.0
          ],
          "price_at_signal": 4266.86,
          "entry_gap_pct": 0.067,
          "sim_entry": 4269.48,
          "variants": {
            "A": {
              "init_sl": 4251.0,
              "r_init": 18.48,
              "outcome": "trail",
              "r": 1.176,
              "exit": 4291.22,
              "exit_time_server": "2026-09-15T17:15:00+srv"
            },
            "B": {
              "init_sl": 4253.34558,
              "r_init": 16.13442,
              "outcome": "trail",
              "r": 1.133,
              "exit": 4287.75279,
              "exit_time_server": "2026-09-15T16:00:00+srv"
            }
          },
          "atr14_m15": 8.06721
        },
        {
          "msg_id": 7285,
          "date_utc": "2026-09-14T11:52:01+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4294.0,
          "sl": 4306.0,
          "tps": [
            4278.0,
            4282.0,
            4286.0,
            4290.0,
            4374.0
          ],
          "price_at_signal": 4292.26,
          "entry_gap_pct": 0.041,
          "sim_entry": 4286.99,
          "variants": {
            "A": {
              "init_sl": 4306.0,
              "r_init": 19.01,
              "outcome": "trail",
              "r": 1.263,
              "exit": 4262.985,
              "exit_time_server": "2026-09-14T16:15:00+srv"
            },
            "B": {
              "init_sl": 4303.8636,
              "r_init": 16.8736,
              "outcome": "trail",
              "r": 1.486,
              "exit": 4261.9168,
              "exit_time_server": "2026-09-14T16:15:00+srv"
            }
          },
          "atr14_m15": 8.4368
        },
        {
          "msg_id": 7276,
          "date_utc": "2026-09-14T04:36:25+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4330.0,
          "sl": 4341.0,
          "tps": [
            4312.0,
            4316.0,
            4320.0,
            4323.0,
            4326.0
          ],
          "price_at_signal": 4331.46,
          "entry_gap_pct": 0.034,
          "sim_entry": 4323.38,
          "variants": {
            "A": {
              "init_sl": 4341.0,
              "r_init": 17.62,
              "outcome": "trail",
              "r": 1.939,
              "exit": 4289.22,
              "exit_time_server": "2026-09-14T12:30:00+srv"
            },
            "B": {
              "init_sl": 4340.88962,
              "r_init": 17.50962,
              "outcome": "trail",
              "r": 1.954,
              "exit": 4289.16481,
              "exit_time_server": "2026-09-14T12:30:00+srv"
            }
          },
          "atr14_m15": 8.75481
        }
      ],
      "variants": {
        "A": {
          "trades": 32,
          "wins": 19,
          "losses": 13,
          "win_pct": 59.4,
          "net_r": 2.69,
          "avg_r": 0.084,
          "expectancy_after_costs_r": 0.014,
          "max_dd_r": 8.69,
          "verdict": "FLAT",
          "pending": 0,
          "no_atr": 0,
          "classes": {
            "sl": 13,
            "be": 9,
            "trail": 10,
            "timeout": 0
          }
        },
        "B": {
          "trades": 32,
          "wins": 21,
          "losses": 11,
          "win_pct": 65.6,
          "net_r": 10.8,
          "avg_r": 0.337,
          "expectancy_after_costs_r": 0.267,
          "max_dd_r": 8.69,
          "verdict": "POSITIVE EDGE",
          "pending": 0,
          "no_atr": 0,
          "classes": {
            "sl": 11,
            "be": 9,
            "trail": 12,
            "timeout": 0
          }
        }
      },
      "v1_channel_exit": {
        "simulated": 32,
        "win_pct": 81.25,
        "avg_r": -0.008,
        "expectancy_after_costs_r": -0.078
      }
    },
    {
      "id": -1002692333123,
      "name": "\ud835\udc17\ud835\udc00\ud835\udc14\ud835\udc14\ud835\udc12\ud835\udc03 \ud835\udc0f\ud835\udc11\ud835\udc0e \ud835\udc12\ud835\udc08\ud835\udc06\ud835\udc0d\ud835\udc00\ud835\udc0b",
      "plain_name": "XAUUSD PRO SIGNAL",
      "messages": 300,
      "media_only": 75,
      "not_signal": 108,
      "unparseable": 2,
      "unverifiable": 0,
      "recap_posts": 86,
      "no_data": 0,
      "pending": 0,
      "degenerate": 0,
      "stale": 0,
      "error": null,
      "signals": [
        {
          "msg_id": 1290,
          "date_utc": "2026-10-15T04:43:14+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4147.0,
          "sl": 4165.0,
          "tps": [
            4130.0,
            4137.0,
            4140.0,
            4143.0
          ],
          "price_at_signal": 4146.31,
          "entry_gap_pct": 0.017,
          "sim_entry": 4145.06,
          "variants": {
            "A": {
              "init_sl": 4165.0,
              "r_init": 19.94,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4165.0,
              "exit_time_server": "2026-10-15T16:15:00+srv"
            },
            "B": {
              "init_sl": 4161.45771,
              "r_init": 16.39771,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4161.45771,
              "exit_time_server": "2026-10-15T16:15:00+srv"
            }
          },
          "atr14_m15": 8.19885
        },
        {
          "msg_id": 1274,
          "date_utc": "2026-10-14T01:11:11+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4154.0,
          "sl": 4173.0,
          "tps": [
            4130.0,
            4140.0,
            4145.0,
            4150.0
          ],
          "price_at_signal": 4154.75,
          "entry_gap_pct": 0.018,
          "sim_entry": 4151.58,
          "variants": {
            "A": {
              "init_sl": 4173.0,
              "r_init": 21.42,
              "outcome": "trail",
              "r": 2.608,
              "exit": 4095.72,
              "exit_time_server": "2026-10-14T15:45:00+srv"
            },
            "B": {
              "init_sl": 4162.60893,
              "r_init": 11.02893,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4162.60893,
              "exit_time_server": "2026-10-14T04:15:00+srv"
            }
          },
          "atr14_m15": 5.51447
        },
        {
          "msg_id": 1267,
          "date_utc": "2026-10-13T07:03:21+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4194.0,
          "sl": 4206.0,
          "tps": [
            4178.0,
            4182.0,
            4186.0,
            4190.0
          ],
          "price_at_signal": 4191.75,
          "entry_gap_pct": 0.054,
          "sim_entry": 4189.73,
          "variants": {
            "A": {
              "init_sl": 4206.0,
              "r_init": 16.27,
              "outcome": "trail",
              "r": 1.168,
              "exit": 4170.725,
              "exit_time_server": "2026-10-13T17:45:00+srv"
            },
            "B": {
              "init_sl": 4201.5993,
              "r_init": 11.8693,
              "outcome": "trail",
              "r": 1.787,
              "exit": 4168.52465,
              "exit_time_server": "2026-10-13T17:30:00+srv"
            }
          },
          "atr14_m15": 5.93465
        },
        {
          "msg_id": 1264,
          "date_utc": "2026-10-13T03:12:21+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4180.0,
          "sl": 4194.0,
          "tps": [
            4164.0,
            4168.0,
            4172.0,
            4176.0
          ],
          "price_at_signal": 4179.69,
          "entry_gap_pct": 0.007,
          "sim_entry": 4179.78,
          "variants": {
            "A": {
              "init_sl": 4194.0,
              "r_init": 14.22,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4194.0,
              "exit_time_server": "2026-10-13T07:30:00+srv"
            },
            "B": {
              "init_sl": 4194.60208,
              "r_init": 14.82208,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4194.60208,
              "exit_time_server": "2026-10-13T07:30:00+srv"
            }
          },
          "atr14_m15": 7.41104
        },
        {
          "msg_id": 1260,
          "date_utc": "2026-10-13T01:45:35+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4158.0,
          "sl": 4172.0,
          "tps": [
            4142.0,
            4146.0,
            4150.0,
            4154.0
          ],
          "price_at_signal": 4156.68,
          "entry_gap_pct": 0.032,
          "sim_entry": 4164.75,
          "variants": {
            "A": {
              "init_sl": 4172.0,
              "r_init": 7.25,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4172.0,
              "exit_time_server": "2026-10-13T05:15:00+srv"
            },
            "B": {
              "init_sl": 4179.50943,
              "r_init": 14.75943,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4179.50943,
              "exit_time_server": "2026-10-13T05:45:00+srv"
            }
          },
          "atr14_m15": 7.37971
        },
        {
          "msg_id": 1258,
          "date_utc": "2026-10-13T00:30:45+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4162.0,
          "sl": 4148.0,
          "tps": [
            4166.0,
            4170.0,
            4174.0,
            4178.0
          ],
          "price_at_signal": 4164.23,
          "entry_gap_pct": 0.054,
          "sim_entry": 4160.69,
          "variants": {
            "A": {
              "init_sl": 4148.0,
              "r_init": 12.69,
              "outcome": "trail",
              "r": 2.626,
              "exit": 4194.015,
              "exit_time_server": "2026-10-13T08:30:00+srv"
            },
            "B": {
              "init_sl": 4150.27388,
              "r_init": 10.41612,
              "outcome": "trail",
              "r": 1.431,
              "exit": 4175.59194,
              "exit_time_server": "2026-10-13T06:15:00+srv"
            }
          },
          "atr14_m15": 5.20806
        },
        {
          "msg_id": 1243,
          "date_utc": "2026-10-12T00:34:19+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4205.0,
          "sl": 4191.0,
          "tps": [
            4208.0,
            4212.0,
            4216.0,
            4220.0
          ],
          "price_at_signal": 4205.36,
          "entry_gap_pct": 0.009,
          "sim_entry": 4208.21,
          "variants": {
            "A": {
              "init_sl": 4191.0,
              "r_init": 17.21,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4191.0,
              "exit_time_server": "2026-10-12T08:00:00+srv"
            },
            "B": {
              "init_sl": 4194.67427,
              "r_init": 13.53573,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4194.67427,
              "exit_time_server": "2026-10-12T07:45:00+srv"
            }
          },
          "atr14_m15": 6.76786
        },
        {
          "msg_id": 1229,
          "date_utc": "2026-10-09T09:53:36+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4186.0,
          "sl": 4172.0,
          "tps": [
            4190.0,
            4194.0,
            4198.0,
            4202.0
          ],
          "price_at_signal": 4184.78,
          "entry_gap_pct": 0.029,
          "sim_entry": 4185.84,
          "variants": {
            "A": {
              "init_sl": 4172.0,
              "r_init": 13.84,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4172.0,
              "exit_time_server": "2026-10-09T15:45:00+srv"
            },
            "B": {
              "init_sl": 4174.36804,
              "r_init": 11.47196,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4174.36804,
              "exit_time_server": "2026-10-09T15:45:00+srv"
            }
          },
          "atr14_m15": 5.73598
        },
        {
          "msg_id": 1215,
          "date_utc": "2026-10-09T04:28:27+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4182.0,
          "sl": 4166.0,
          "tps": [
            4186.0,
            4190.0,
            4194.0,
            4198.0
          ],
          "price_at_signal": 4179.28,
          "entry_gap_pct": 0.065,
          "sim_entry": 4182.16,
          "variants": {
            "A": {
              "init_sl": 4166.0,
              "r_init": 16.16,
              "outcome": "trail",
              "r": 1.058,
              "exit": 4199.25,
              "exit_time_server": "2026-10-09T08:45:00+srv"
            },
            "B": {
              "init_sl": 4170.15183,
              "r_init": 12.00817,
              "outcome": "trail",
              "r": 1.596,
              "exit": 4201.32592,
              "exit_time_server": "2026-10-09T08:45:00+srv"
            }
          },
          "atr14_m15": 6.00408
        },
        {
          "msg_id": 1209,
          "date_utc": "2026-10-09T01:55:44+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4172.0,
          "sl": 4190.0,
          "tps": [
            4148.0,
            4152.0,
            4156.0,
            4160.0,
            4164.0,
            4169.0
          ],
          "price_at_signal": 4169.14,
          "entry_gap_pct": 0.069,
          "sim_entry": 4175.19,
          "variants": {
            "A": {
              "init_sl": 4190.0,
              "r_init": 14.81,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4190.0,
              "exit_time_server": "2026-10-09T08:15:00+srv"
            },
            "B": {
              "init_sl": 4189.97498,
              "r_init": 14.78498,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4189.97498,
              "exit_time_server": "2026-10-09T08:15:00+srv"
            }
          },
          "atr14_m15": 7.39249
        },
        {
          "msg_id": 1193,
          "date_utc": "2026-10-08T06:46:59+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4126.0,
          "sl": 4140.0,
          "tps": [
            4105.0,
            4110.0,
            4115.0,
            4120.0
          ],
          "price_at_signal": 4125.19,
          "entry_gap_pct": 0.02,
          "sim_entry": 4121.72,
          "variants": {
            "A": {
              "init_sl": 4140.0,
              "r_init": 18.28,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4140.0,
              "exit_time_server": "2026-10-08T17:30:00+srv"
            },
            "B": {
              "init_sl": 4135.77818,
              "r_init": 14.05818,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4135.77818,
              "exit_time_server": "2026-10-08T17:15:00+srv"
            }
          },
          "atr14_m15": 7.02909
        },
        {
          "msg_id": 1192,
          "date_utc": "2026-10-08T03:54:20+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4137.0,
          "sl": 4123.0,
          "tps": [
            4141.0,
            4145.0,
            4149.0,
            4153.0
          ],
          "price_at_signal": 4136.89,
          "entry_gap_pct": 0.003,
          "sim_entry": 4136.27,
          "variants": {
            "A": {
              "init_sl": 4123.0,
              "r_init": 13.27,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4123.0,
              "exit_time_server": "2026-10-08T08:45:00+srv"
            },
            "B": {
              "init_sl": 4121.29121,
              "r_init": 14.97879,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4121.2912

... (truncated, 90541 total bytes) ...

