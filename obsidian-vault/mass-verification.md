---
slug: mass-verification
type: note
graph: gitnexus
---

{
  "generated_utc": "2026-10-16T19:18:36.472243+00:00",
  "research": "MASS VERIFICATION: 14 unverified watched channels x relay trailing exit (POLICY V2, fixed parser)",
  "channel_set": "the 14 config.json-watched channels with no prior verification evidence: 12 from new_channels_batch.json + 2 scout-shortlist incumbents (Lingrid, Forex GDP free)",
  "method": {
    "messages_per_channel": 300,
    "parser": "relay's own parser.parse_signal (current fixed version: arrow-format TPs + emoji-adjacent SLs)",
    "keep_filter": "parse_ok, non-manage, has SL, >=1 TP, numeric entry, not stale >1% (identical to V1/V2)",
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
    "costs": "0.07R round-trip haircut per trade (same as V1/V2/backtest.py)",
    "max_dd": "worst peak-to-trough of cumulative after-cost R curve, trades ordered by entry time",
    "verdict_bands": "expectancy after costs >= +0.05R POSITIVE EDGE, <= -0.05R NEGATIVE, else FLAT; n < 10 = INSUFFICIENT DATA (tentative)",
    "min_sample_gate": 10,
    "calls": "PROMOTE: best adequate variant exp >= +0.05R and n >= 10; DEMOTE (remove from config channels): best adequate variant <= -0.05R; DUPLICATE: identical trade set as another watched channel (mirror); else STAY SHADOW",
    "duplicate_detection": "channels with identical variant-A AND variant-B trade fingerprints (side, entry-bar open, outcome R; >= 3 trades) are exact mirrors; >= 80% A-overlap with a cluster leader = near-mirror; pooled_deduped counts every unique trade (content key) exactly once across all channels",
    "server_offset_s": 10800,
    "server_offset_method": "freshest tick across XAUUSD/EURUSD/GBPUSD/US30/XAGUSD/AUDUSD",
    "tick_times_at_run": {
      "XAUUSD": 1792189106,
      "EURUSD": 1792189106,
      "GBPUSD": 1792189105,
      "XAGUSD": 1792189106,
      "AUDUSD": 1792189106
    },
    "symbols_selected_for_data": [],
    "session": "telethon-mass.session (sqlite backup copy of telethon.session; live session never connected/written)",
    "mt5_access": "read-only: initialize/shutdown + copy_rates/symbol_info/symbol_info_tick/symbol_select; order_send never called"
  },
  "channels": [
    {
      "id": -1003723702011,
      "name": "FOREX GOLD SIGNALS XAUUSD",
      "plain_name": "SIGNALS_XAUUSD_FOREX_GOLD",
      "username": "SIGNALS_XAUUSD_FOREX_GOLD",
      "messages": 300,
      "media_only": 131,
      "not_signal": 65,
      "unparseable": 1,
      "unverifiable": 21,
      "recap_posts": 67,
      "no_data": 0,
      "pending": 0,
      "degenerate": 0,
      "stale": 0,
      "error": null,
      "signals": [
        {
          "msg_id": 1019,
          "date_utc": "2026-10-07T10:34:10+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4108.0,
          "sl": 4000.0,
          "tps": [
            4115.0,
            4120.0,
            4125.0
          ],
          "price_at_signal": 4114.12,
          "entry_gap_pct": 0.149,
          "sim_entry": 4113.09,
          "variants": {
            "A": {
              "init_sl": 4000.0,
              "r_init": 113.09,
              "outcome": "sl",
              "r": 1.0,
              "exit": 4000.0,
              "exit_time_server": "2026-10-07T13:45:00+srv"
            },
            "B": {
              "init_sl": 4124.17513,
              "r_init": 11.08513,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4124.17513,
              "exit_time_server": "2026-10-07T15:00:00+srv"
            }
          },
          "atr14_m15": 5.54256
        },
        {
          "msg_id": 997,
          "date_utc": "2026-10-02T15:35:08+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4145.0,
          "sl": 4139.0,
          "tps": [
            4151.0,
            4155.0,
            4161.0
          ],
          "price_at_signal": 4142.29,
          "entry_gap_pct": 0.065,
          "sim_entry": 4134.69,
          "variants": {
            "A": {
              "init_sl": 4139.0,
              "r_init": 4.31,
              "outcome": "sl",
              "r": 1.0,
              "exit": 4139.0,
              "exit_time_server": "2026-10-02T18:45:00+srv"
            },
            "B": {
              "init_sl": 4106.28106,
              "r_init": 28.40894,
              "outcome": "timeout",
              "r": 0.455,
              "exit": 4147.62,
              "exit_time_server": "2026-10-02T23:00:00+srv"
            }
          },
          "atr14_m15": 14.20447
        },
        {
          "msg_id": 994,
          "date_utc": "2026-10-02T12:24:01+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4180.0,
          "sl": 4190.0,
          "tps": [
            4155.0,
            4165.0,
            4174.0
          ],
          "price_at_signal": 4177.7,
          "entry_gap_pct": 0.055,
          "sim_entry": 4185.48,
          "variants": {
            "A": {
              "init_sl": 4190.0,
              "r_init": 4.52,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4190.0,
              "exit_time_server": "2026-10-02T15:30:00+srv"
            },
            "B": {
              "init_sl": 4201.48191,
              "r_init": 16.00191,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4201.48191,
              "exit_time_server": "2026-10-02T15:30:00+srv"
            }
          },
          "atr14_m15": 8.00096
        },
        {
          "msg_id": 954,
          "date_utc": "2026-09-25T11:33:42+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4306.0,
          "sl": 4311.0,
          "tps": [
            4288.0,
            4292.0,
            4297.0
          ],
          "price_at_signal": 4304.61,
          "entry_gap_pct": 0.032,
          "sim_entry": 4301.56,
          "variants": {
            "A": {
              "init_sl": 4311.0,
              "r_init": 9.44,
              "outcome": "trail",
              "r": 2.017,
              "exit": 4282.52,
              "exit_time_server": "2026-09-25T16:30:00+srv"
            },
            "B": {
              "init_sl": 4316.41745,
              "r_init": 14.85745,
              "outcome": "trail",
              "r": 1.4,
              "exit": 4280.75872,
              "exit_time_server": "2026-09-25T16:45:00+srv"
            }
          },
          "atr14_m15": 7.42872
        },
        {
          "msg_id": 940,
          "date_utc": "2026-09-24T13:14:28+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4280.0,
          "sl": 4386.0,
          "tps": [
            4260.0,
            4270.0,
            4272.0
          ],
          "price_at_signal": 4281.02,
          "entry_gap_pct": 0.024,
          "sim_entry": 4278.15,
          "variants": {
            "A": {
              "init_sl": 4386.0,
              "r_init": 107.85,
              "outcome": "timeout",
              "r": -0.12,
              "exit": 4291.11,
              "exit_time_server": "2026-09-25T23:00:00+srv"
            },
            "B": {
              "init_sl": 4296.09179,
              "r_init": 17.94179,
              "outcome": "trail",
              "r": 1.367,
              "exit": 4253.6309,
              "exit_time_server": "2026-09-24T18:15:00+srv"
            }
          },
          "atr14_m15": 8.9709
        },
        {
          "msg_id": 926,
          "date_utc": "2026-09-23T12:20:32+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4315.0,
          "sl": 4322.0,
          "tps": [
            4300.0,
            4308.0,
            4395.0
          ],
          "price_at_signal": 4318.81,
          "entry_gap_pct": 0.088,
          "sim_entry": 4311.08,
          "variants": {
            "A": {
              "init_sl": 4322.0,
              "r_init": 10.92,
              "outcome": "be",
              "r": 0.009,
              "exit": 4310.98,
              "exit_time_server": "2026-09-23T16:15:00+srv"
            },
            "B": {
              "init_sl": 4324.39119,
              "r_init": 13.31119,
              "outcome": "trail",
              "r": 1.789,
              "exit": 4287.26559,
              "exit_time_server": "2026-09-23T17:00:00+srv"
            }
          },
          "atr14_m15": 6.65559
        },
        {
          "msg_id": 907,
          "date_utc": "2026-09-22T05:24:00+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4335.0,
          "sl": 4341.0,
          "tps": [
            4324.0,
            4327.0,
            4330.0
          ],
          "price_at_signal": 4345.86,
          "entry_gap_pct": 0.25,
          "sim_entry": 4331.8,
          "variants": {
            "A": {
              "init_sl": 4341.0,
              "r_init": 9.2,
              "outcome": "trail",
              "r": 1.203,
              "exit": 4320.73,
              "exit_time_server": "2026-09-22T08:45:00+srv"
            },
            "B": {
              "init_sl": 4348.67205,
              "r_init": 16.87205,
              "outcome": "trail",
              "r": 1.413,
              "exit": 4307.96602,
              "exit_time_server": "2026-09-22T11:00:00+srv"
            }
          },
          "atr14_m15": 8.43602
        },
        {
          "msg_id": 889,
          "date_utc": "2026-09-16T13:31:48+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4355.0,
          "sl": 4365.0,
          "tps": [
            4333.0,
            4345.0,
            4348.0
          ],
          "price_at_signal": 4351.92,
          "entry_gap_pct": 0.071,
          "sim_entry": 4340.43,
          "variants": {
            "A": {
              "init_sl": 4365.0,
              "r_init": 24.57,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4365.0,
              "exit_time_server": "2026-09-16T21:00:00+srv"
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
          "msg_id": 884,
          "date_utc": "2026-09-14T12:54:42+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4275.0,
          "sl": 4378.0,
          "tps": [
            4255.0,
            4263.0,
            4270.0
          ],
          "price_at_signal": 4283.4,
          "entry_gap_pct": 0.196,
          "sim_entry": 4271.0,
          "variants": {
            "A": {
              "init_sl": 4378.0,
              "r_init": 107.0,
              "outcome": "timeout",
              "r": -0.715,
              "exit": 4347.48,
              "exit_time_server": "2026-09-16T16:00:00+srv"
            },
            "B": {
              "init_sl": 4291.36229,
              "r_init": 20.36229,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4291.36229,
              "exit_time_server": "2026-09-14T18:30:00+srv"
            }
          },
          "atr14_m15": 10.18115
        },
        {
          "msg_id": 850,
          "date_utc": "2026-09-09T03:11:42+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4380.0,
          "sl": 4388.0,
          "tps": [
            4355.0,
            4369.0,
            4373.0
          ],
          "price_at_signal": 4382.35,
          "entry_gap_pct": 0.054,
          "sim_entry": 4379.04,
          "variants": {
            "A": {
              "init_sl": 4388.0,
              "r_init": 8.96,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4388.0,
              "exit_time_server": "2026-09-09T08:15:00+srv"
            },
            "B": {
              "init_sl": 4395.73185,
              "r_init": 16.69185,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4395.73185,
              "exit_time_server": "2026-09-09T08:45:00+srv"
            }
          },
          "atr14_m15": 8.34592
        },
        {
          "msg_id": 825,
          "date_utc": "2026-09-04T13:10:41+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4388.0,
          "sl": 4493.0,
          "tps": [
            4368.0,
            4375.0,
            4382.0
          ],
          "price_at_signal": 4393.71,
          "entry_gap_pct": 0.13,
          "sim_entry": 4394.05,
          "variants": {
            "A": {
              "init_sl": 4493.0,
              "r_init": 98.95,
              "outcome": "timeout",
              "r": -0.41,
              "exit": 4434.66,
              "exit_time_server": "2026-09-04T23:00:00+srv"
            },
            "B": {
              "init_sl": 4424.30426,
              "r_init": 30.25426,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4424.30426,
              "exit_time_server": "2026-09-04T16:45:00+srv"
            }
          },
          "atr14_m15": 15.12713
        },
        {
          "msg_id": 753,
          "date_utc": "2026-08-21T05:54:33+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4547.0,
          "sl": 4540.0,
          "tps": [
            4556.0,
            4567.0,
            4587.0
          ],
          "price_at_signal": 4543.03,
          "entry_gap_pct": 0.087,
          "sim_entry": 4553.57,
          "variants": {
            "A": {
              "init_sl": 4540.0,
              "r_init": 13.57,
              "outcome": "trail",
              "r": 2.95,
              "exit": 4593.595,
              "exit_time_server": "2026-08-21T12:15:00+srv"
            },
            "B": {
              "init_sl": 4535.28667,
              "r_init": 18.28333,
              "outcome": "trail",
              "r": 2.06,
              "exit": 4591.23834,
              "exit_time_server": "2026-08-21T12:15:00+srv"
            }
          },
          "atr14_m15": 9.14166
        },
        {
          "msg_id": 750,
          "date_utc": "2026-08-20T06:13:44+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4490.0,
          "sl": 4486.0,
          "tps": [
            4495.0,
            4500.0,
            4520.0
          ],
          "price_at_signal": 4481.22,
          "entry_gap_pct": 0.196,
          "sim_entry": 4492.72,
          "variants": {
            "A": {
              "init_sl": 4486.0,
              "r_init": 6.72,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4486.0,
              "exit_time_server": "2026-08-20T10:15:00+srv"
            },
            "B": {
              "init_sl": 4477.00665,
              "r_init": 15.71335,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4477.00665,
              "exit_time_server": "2026-08-20T14:30:00+srv"
            }
          },
          "atr14_m15": 7.85668
        },
        {
          "msg_id": 749,
          "date_utc": "2026-08-20T05:42:12+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4480.0,
          "sl": 4487.0,
          "tps": [
            4352.0,
            4370.0,
            4475.0
          ],
          "price_at_signal": 4483.15,
          "entry_gap_pct": 0.07,
          "sim_entry": 4480.65,
          "variants": {
            "A": {
              "init_sl": 4487.0,
              "r_init": 6.35,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4487.0,
              "exit_time_server": "2026-08-20T09:00:00+srv"
            },
            "B": {
              "init_sl": 4495.82111,
              "r_init": 15.17111,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4495.82111,
              "exit_time_server": "2026-08-20T09:15:00+srv"
            }
          },
          "atr14_m15": 7.58555
        },
        {
          "msg_id": 747,
          "date_utc": "2026-08-19T13:05:47+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4430.0,
          "sl": 4440.0,
          "tps": [
            4321.0,
            4323.0,
            4427.0
          ],
          "price_at_signal": 4438.64,
          "entry_gap_pct": 0.195,
          "sim_entry": 4455.82,
          "variants": {
            "A": {
              "init_sl": 4440.0,
              "r_init": 15.82,
              "outcome": "sl",
              "r": 1.0,
              "exit": 4440.0,
              "exit_time_server": "2026-08-19T16:15:00+srv"
            },
            "B": {
              "init_sl": 4481.97579,
              "r_init": 26.15579,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4481.97579,
              "exit_time_server": "2026-08-19T17:15:00+srv"
            }
          },
          "atr14_m15": 13.07789
        }
      ],
      "variants": {
        "A": {
          "trades": 15,
          "wins": 7,
          "losses": 8,
          "win_pct": 46.7,
          "net_r": 2.93,
          "avg_r": 0.196,
          "expectancy_after_costs_r": 0.126,
          "max_dd_r": 3.41,
          "verdict": "POSITIVE EDGE",
          "pending": 0,
          "no_atr": 0,
          "classes": {
            "sl": 8,
            "be": 1,
            "trail": 3,
            "timeout": 3
          }
        },
        "B": {
          "trades": 15,
          "wins": 6,
          "losses": 9,
          "win_pct": 40.0,
          "net_r": -0.52,
          "avg_r": -0.034,
          "expectancy_after_costs_r": -0.104,
          "max_dd_r": 5.5,
          "verdict": "NEGATIVE",
          "pending": 0,
          "no_atr": 0,
          "classes": {
            "sl": 9,
            "be": 0,
            "trail": 5,
            "timeout": 1
          }
        }
      },
      "duplicate_of": null,
      "recommendation": {
        "call": "PROMOTE",
        "winning_variant": "A",
        "params": {
          "sl_mode": "channel",
          "tp_mode": "none"
        },
        "exp_after_costs_r": 0.126,
        "trades": 15,
        "win_pct": 46.7,
        "max_dd_r": 3.41,
        "reason": "variant A clears the bar: +0.126R expectancy after costs over 15 resolved trades (win% 46.7, maxDD 3.41R)"
      },
      "prior_evidence": "no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set)"
    },
    {
      "id": -1001713690419,
      "name": "Forex GDP - Free Signals",
      "plain_name": "forexgdp_forex_gdp",
      "username": "forexgdp_forex_gdp",
      "messages": 300,
      "media_only": 77,
      "not_signal": 202,
      "unparseable": 3,
      "unverifiable": 1,
      "recap_posts": 7,
      "no_data": 0,
      "pending": 0,
      "degenerate": 0,
      "stale": 0,
      "error": null,
      "signals": [
        {
          "msg_id": 30948,
          "date_utc": "2026-10-16T02:37:03+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4160.0,
          "sl": 4149.0,
          "tps": [
            4170.0,
            4175.0,
            4185.0
          ],
          "price_at_signal": 4161.75,
          "entry_gap_pct": 0.042,
          "sim_entry": 4162.64,
          "variants": {
            "A": {
              "init_sl": 4149.0,
              "r_init": 13.64,
              "outcome": "trail",
              "r": 1.036,
              "exit": 4176.77,
              "exit_time_server": "2026-10-16T07:00:00+srv"
            },
            "B": {
              "init_sl": 4149.5512,
              "r_init": 13.0888,
              "outcome": "trail",
              "r": 1.101,
              "exit": 4177.0456,
              "exit_time_server": "2026-10-16T07:00:00+srv"
            }
          },
          "atr14_m15": 6.5444
        },
        {
          "msg_id": 30916,
          "date_utc": "2026-10-15T10:54:36+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4150.0,
          "sl": 4139.0,
          "tps": [
            4160.0,
            4165.0,
            4170.0
          ],
          "price_at_signal": 4152.8,
          "entry_gap_pct": 0.067,
          "sim_entry": 4154.72,
          "variants": {
            "A": {
              "init_sl": 4139.0,
              "r_init": 15.72,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4139.0,
              "exit_time_server": "2026-10-15T15:30:00+srv"
            },
            "B": {
              "init_sl": 4143.31103,
              "r_init": 11.40897,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4143.31103,
              "exit_time_server": "2026-10-15T15:30:00+srv"
            }
          },
          "atr14_m15": 5.70449
        },
        {
          "msg_id": 30856,
          "date_utc": "2026-10-14T01:44:23+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4153.0,
          "sl": 4164.0,
          "tps": [
            4135.0,
            4140.0,
            4145.0
          ],
          "price_at_signal": 4164.56,
          "entry_gap_pct": 0.278,
          "sim_entry": 4146.07,
          "variants": {
            "A": {
              "init_sl": 4164.0,
              "r_init": 17.93,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4164.0,
              "exit_time_server": "2026-10-14T05:45:00+srv"
            },
            "B": {
              "init_sl": 4160.76128,
              "r_init": 14.69128,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4160.76128,
              "exit_time_server": "2026-10-14T05:00:00+srv"
            }
          },
          "atr14_m15": 7.34564
        },
        {
          "msg_id": 30854,
          "date_utc": "2026-10-14T01:17:02+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4153.0,
          "sl": 4164.0,
          "tps": [
            4135.0,
            4140.0,
            4145.0
          ],
          "price_at_signal": 4151.58,
          "entry_gap_pct": 0.034,
          "sim_entry": 4164.56,
          "variants": {
            "A": {
              "init_sl": 4164.0,
              "r_init": 0.56,
              "outcome": "sl",
              "r": 1.0,
              "exit": 4164.0,
              "exit_time_server": "2026-10-14T04:30:00+srv"
            },
            "B": {
              "init_sl": 4177.2783,
              "r_init": 12.7183,
              "outcome": "trail",
              "r": 1.099,
              "exit": 4150.57915,
              "exit_time_server": "2026-10-14T05:00:00+srv"
            }
          },
          "atr14_m15": 6.35915
        },
        {
          "msg_id": 30817,
          "date_utc": "2026-10-13T10:45:01+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4183.0,
          "sl": 4194.0,
          "tps": [
            4165.0,
            4170.0,
            4175.0
          ],
          "price_at_signal": 4180.09,
          "entry_gap_pct": 0.07,
          "sim_entry": 4181.57,
          "variants": {
            "A": {
              "init_sl": 4194.0,
              "r_init": 12.43,
              "outcome": "trail",
              "r": 1.027,
              "exit": 4168.805,
              "exit_time_server": "2026-10-13T17:30:00+srv"
            },
            "B": {
              "init_sl": 4191.77455,
              "r_init": 10.20455,
              "outcome": "trail",
              "r": 1.36,
              "exit": 4167.69227,
              "exit_time_server": "2026-10-13T17:30:00+srv"
            }
          },
          "atr14_m15": 5.10227
        },
        {
          "msg_id": 30790,
          "date_utc": "2026-10-13T01:23:54+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4165.0,
          "sl": 4176.0,
          "tps": [
            4145.0,
            4150.0,
            4155.0
          ],
          "price_at_signal": 4167.03,
          "entry_gap_pct": 0.049,
          "sim_entry": 4156.57,
          "variants": {
            "A": {
              "init_sl": 4176.0,
              "r_init": 19.43,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4176.0,
              "exit_time_server": "2026-10-13T05:45:00+srv"
            },
            "B": {
              "init_sl": 4169.82141,
              "r_init": 13.25141,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4169.82141,
              "exit_time_server": "2026-10-13T05:15:00+srv"
            }
          },
          "atr14_m15": 6.6257
        },
        {
          "msg_id": 30752,
          "date_utc": "2026-10-12T11:01:11+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4175.0,
          "sl": 4187.0,
          "tps": [
            4149.0,
            4158.0,
            4165.0
          ],
          "price_at_signal": 4177.08,
          "entry_gap_pct": 0.05,
          "sim_entry": 4171.56,
          "variants": {
            "A": {
              "init_sl": 4187.0,
              "r_init": 15.44,
              "outcome": "be",
              "r": 0.006,
              "exit": 4171.46,
              "exit_time_server": "2026-10-12T16:00:00+srv"
            },
            "B": {
              "init_sl": 4181.56289,
              "r_init": 10.00289,
              "outcome": "trail",
              "r": 1.204,
              "exit": 4159.52145,
              "exit_time_server": "2026-10-12T15:45:00+srv"
            }
          },
          "atr14_m15": 5.00145
        },
        {
          "msg_id": 30718,
          "date_utc": "2026-10-12T04:10:48+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4203.0,
          "sl": 4214.0,
          "tps": [
            4185.0,
            4190.0,
            4195.0
          ],
          "price_at_signal": 4203.05,
          "entry_gap_pct": 0.001,
          "sim_entry": 4198.74,
          "variants": {
            "A": {
              "init_sl": 4214.0,
              "r_init": 15.26,
              "outcome": "trail",
              "r": 1.471,
              "exit": 4176.29,
              "exit_time_server": "2026-10-12T13:15:00+srv"
            },
            "B": {
              "init_sl": 4212.17079,
              "r_init": 13.43079,
              "outcome": "trail",
              "r": 1.74,
              "exit": 4175.37539,
              "exit_time_server": "2026-10-12T13:15:00+srv"
            }
          },
          "atr14_m15": 6.71539
        },
        {
          "msg_id": 30715,
          "date_utc": "2026-10-12T02:26:46+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4212.0,
          "sl": 4201.0,
          "tps": [
            4220.0,
            4225.0,
            4230.0
          ],
          "price_at_signal": 4213.38,
          "entry_gap_pct": 0.033,
          "sim_entry": 4211.11,
          "variants": {
            "A": {
              "init_sl": 4201.0,
              "r_init": 10.11,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4201.0,
              "exit_time_server": "2026-10-12T07:00:00+srv"
            },
            "B": {
              "init_sl": 4196.05074,
              "r_init": 15.05926,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4196.05074,
              "exit_time_server": "2026-10-12T07:45:00+srv"
            }
          },
          "atr14_m15": 7.52963
        },
        {
          "msg_id": 30712,
          "date_utc": "2026-10-12T01:37:19+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4203.0,
          "sl": 4214.0,
          "tps": [
            4185.0,
            4190.0,
            4195.0
          ],
          "price_at_signal": 4207.3,
          "entry_gap_pct": 0.102,
          "sim_entry": 4202.31,
          "variants": {
            "A": {
              "init_sl": 4214.0,
              "r_init": 11.69,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4214.0,
              "exit_time_server": "2026-10-12T05:00:00+srv"
            },
            "B": {
              "init_sl": 4217.64059,
              "r_init": 15.33059,
              "outcome": "trail",
              "r": 1.005,
              "exit": 4186.90529,
              "exit_time_server": "2026-10-12T08:45:00+srv"
            }
          },
          "atr14_m15": 7.66529
        }
      ],
      "variants": {
        "A": {
          "trades": 10,
          "wins": 5,
          "losses": 5,
          "win_pct": 50.0,
          "net_r": -0.46,
          "avg_r": -0.046,
          "expectancy_after_costs_r": -0.116,
          "max_dd_r": 2.14,
          "verdict": "NEGATIVE",
          "pending": 0,
          "no_atr": 0,
          "classes": {
            "sl": 6,
            "be": 1,
            "trail": 3,
            "timeout": 0
          }
        },
        "B": {
          "trades": 10,
          "wins": 6,
          "losses": 4,
          "win_pct": 60.0,
          "net_r": 3.51,
          "avg_r": 0.351,
          "expectancy_after_costs_r": 0.281,
          "max_dd_r": 2.14,
          "verdict": "POSITIVE EDGE",
          "pending": 0,
          "no_atr": 0,
          "classes": {
            "sl": 4,
            "be": 0,
            "trail": 6,
            "timeout": 0
          }
        }
      },
      "duplicate_of": null,
      "duplicate_cluster_members": [
        -1001912261779,
        -1001713690419
      ],
      "recommendation": {
        "call": "PROMOTE",
        "winning_variant": "B",
        "params": {
          "sl_mode": "atr",
          "atr_mult": 2.0,
          "tp_mode": "none"
        },
        "exp_after_costs_r": 0.281,
        "trades": 10,
        "win_pct": 60.0,
        "max_dd_r": 2.14,
        "reason": "variant B clears the bar: +0.281R expectancy after costs over 10 resolved trades (win% 60.0, maxDD 2.14R) NOTE: content is mirrored by 1 other watched channel(s) (FX PREMIERE VIP GOLD BTC SIGNALS (`-1001912261779`)); promote at most ONE channel of this cluster."
      },
      "prior_evidence": "no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set)"
    },
    {
      "id": -1003376522019,
      "name": "XAUUSD GOLD SIGNALS",
      "plain_name": "XAUUSD_GOLD_VIP_SIGNALS_pip",
      "username": "XAUUSD_GOLD_VIP_SIGNALS_pip",
      "messages": 300,
      "media_only": 131,
      "not_signal": 62,
      "unparseable": 1,
      "unverifiable": 24,
      "recap_posts": 70,
      "no_data": 0,
      "pending": 0,
      "degenerate": 0,
      "stale": 0,
      "error": null,
      "signals": [
        {
          "msg_id": 19659,
          "date_utc": "2026-10-07T10:34:21+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4108.0,
          "sl": 4000.0,
          "tps": [
            4115.0,
            4120.0,
            4125.0
          ],
          "price_at_signal": 4114.12,
          "entry_gap_pct": 0.149,
          "sim_entry": 4113.09,
          "variants": {
            "A": {
              "init_sl": 4000.0,
              "r_init": 113.09,
              "outcome": "sl",
              "r": 1.0,
              "exit": 4000.0,
              "exit_time_server": "2026-10-07T13:45:00+srv"
            },
            "B": {
              "init_sl": 4124.17513,
              "r_init": 11.08513,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4124.17513,
              "exit_time_server": "2026-10-07T15:00:00+srv"
            }
          },
          "atr14_m15": 5.54256
        },
        {
          "msg_id": 19637,
          "date_utc": "2026-10-02T15:36:02+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4145.0,
          "sl": 4139.0,
          "tps": [
            4151.0,
            4155.0,
            4161.0
          ],
          "price_at_signal": 4142.29,
          "entry_gap_pct": 0.065,
          "sim_entry": 4134.69,
          "variants": {
            "A": {
              "init_sl": 4139.0,
              "r_init": 4.31,
              "outcome": "sl",
              "r": 1.0,
              "exit": 4139.0,
              "exit_time_server": "2026-10-02T18:45:00+srv"
            },
            "B": {
              "init_sl": 4106.28106,
              "r_init": 28.40894,
              "outcome": "timeout",
              "r": 0.455,
              "exit": 4147.62,
              "exit_time_server": "2026-10-02T23:00:00+srv"
            }
          },
          "atr14_m15": 14.20447
        },
        {
          "msg_id": 19634,
          "date_utc": "2026-10-02T12:24:44+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4180.0,
          "sl": 4190.0,
          "tps": [
            4155.0,
            4165.0,
            4174.0
          ],
          "price_at_signal": 4177.7,
          "entry_gap_pct": 0.055,
          "sim_entry": 4185.48,
          "variants": {
            "A": {
              "init_sl": 4190.0,
              "r_init": 4.52,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4190.0,
              "exit_time_server": "2026-10-02T15:30:00+srv"
            },
            "B": {
              "init_sl": 4201.48191,
              "r_init": 16.00191,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4201.48191,
              "exit_time_server": "2026-10-02T15:30:00+srv"
            }
          },
          "atr14_m15": 8.00096
        },
        {
          "msg_id": 19594,
          "date_utc": "2026-09-25T11:33:54+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4306.0,
          "sl": 4311.0,
          "tps": [
            4288.0,
            4292.0,
            4297.0
          ],
          "price_at_signal": 4304.61,
          "entry_gap_pct": 0.032,
          "sim_entry": 4301.56,
          "variants": {
            "A": {
              "init_sl": 4311.0,
              "r_init": 9.44,
              "outcome": "trail",
              "r": 2.017,
              "exit": 4282.52,
              "exit_time_server": "2026-09-25T16:30:00+srv"
            },
            "B": {
              "init_sl": 4316.41745,
              "r_init": 14.85745,
              "outcome": "trail",
              "r": 1.4,
              "exit": 4280.75872,
              "exit_time_server": "2026-09-25T16:45:00+srv"
            }
          },
          "atr14_m15": 7.42872
        },
        {
          "msg_id": 19593,
          "date_utc": "2026-09-25T08:53:42+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4292.0,
          "sl": 4300.0,
          "tps": [
            4280.0,
            4282.0,
            4285.0
          ],
          "price_at_signal": 4292.18,
          "entry_gap_pct": 0.004,
          "sim_entry": 4293.3,
          "variants": {
            "A": {
              "init_sl": 4300.0,
              "r_init": 6.7,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4300.0,
              "exit_time_server": "2026-09-25T13:00:00+srv"
            },
            "B": {
              "init_sl": 4307.36638,
              "r_init": 14.06638,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4307.36638,
              "exit_time_server": "2026-09-25T13:00:00+srv"
            }
          },
          "atr14_m15": 7.03319
        },
        {
          "msg_id": 19579,
          "date_utc": "2026-09-24T13:14:34+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4280.0,
          "sl": 4386.0,
          "tps": [
            4260.0,
            4270.0,
            4272.0
          ],
          "price_at_signal": 4281.02,
          "entry_gap_pct": 0.024,
          "sim_entry": 4278.15,
          "variants": {
            "A": {
              "init_sl": 4386.0,
              "r_init": 107.85,
              "outcome": "timeout",
              "r": -0.12,
              "exit": 4291.11,
              "exit_time_server": "2026-09-25T23:00:00+srv"
            },
            "B": {
              "init_sl": 4296.09179,
              "r_init": 17.94179,
              "outcome": "trail",
              "r": 1.367,
              "exit": 4253.6309,
              "exit_time_server": "2026-09-24T18:15:00+srv"
            }
          },
          "atr14_m15": 8.9709
        },
        {
          "msg_id": 19567,
          "date_utc": "2026-09-23T12:21:21+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4315.0,
          "sl": 4322.0,
          "tps": [
            4300.0,
            4308.0,
            4395.0
          ],
          "price_at_signal": 4318.81,
          "entry_gap_pct": 0.088,
          "sim_entry": 4311.08,
          "variants": {
            "A": {
              "init_sl": 4322.0,
              "r_init": 10.92,
              "outcome": "be",
              "r": 0.009,
              "exit": 4310.98,
              "exit_time_server": "2026-09-23T16:15:00+srv"
            },
            "B": {
              "init_sl": 4324.39119,
              "r_init": 13.31119,
              "outcome": "trail",
              "r": 1.789,
              "exit": 4287.26559,
              "exit_time_server": "2026-09-23T17:00:00+srv"
            }
          },
          "atr14_m15": 6.65559
        },
        {
          "msg_id": 19551,
          "date_utc": "2026-09-22T05:24:38+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4335.0,
          "sl": 4341.0,
          "tps": [
            4324.0,
            4327.0,
            4330.0
          ],
          "price_at_signal": 4345.86,
          "entry_gap_pct": 0.25,
          "sim_entry": 4331.8,
          "variants": {
            "A": {
              "init_sl": 4341.0,
              "r_init": 9.2,
              "outcome": "trail",
              "r": 1.203,
              "exit": 4320.73,
              "exit_time_server": "2026-09-22T08:45:00+srv"
            },
            "B": {
              "init_sl": 4348.67205,
              "r_init": 16.87205,
              "outcome": "trail",
              "r": 1.413,
              "exit": 4307.96602,
              "exit_time_server": "2026-09-22T11:00:00+srv"
            }
          },
          "atr14_m15": 8.43602
        },
        {
          "msg_id": 19532,
          "date_utc": "2026-09-16T13:32:02+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4355.0,
          "sl": 4365.0,
          "tps": [
            4333.0,
            4345.0,
            4348.0
          ],
          "price_at_signal": 4351.92,
          "entry_gap_pct": 0.071,
          "sim_entry": 4340.43,
          "variants": {
            "A": {
              "init_sl": 4365.0,
              "r_init": 24.57,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4365.0,
              "exit_time_server": "2026-09-16T21:00:00+srv"
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
          "msg_id": 19527,
          "date_utc": "2026-09-14T12:54:53+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4275.0,
          "sl": 4378.0,
          "tps": [
            4255.0,
            4263.0,
            4270.0
          ],
          "price_at_signal": 4283.4,
          "entry_gap_pct": 0.196,
          "sim_entry": 4271.0,
          "variants": {
            "A": {
              "init_sl": 4378.0,
              "r_init": 107.0,
              "outcome": "timeout",
              "r": -0.715,
              "exit": 4347.48,
              "exit_time_server": "2026-09-16T16:00:00+srv"
            },
            "B": {
              "init_sl": 4291.36229,
              "r_init": 20.36229,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4291.36229,
              "exit_time_server": "2026-09-14T18:30:00+srv"
            }
          },
          "atr14_m15": 10.18115
        },
        {
          "msg_id": 19493,
          "date_utc": "2026-09-09T03:11:48+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4380.0,
          "sl": 4388.0,
          "tps": [
            4355.0,
            4369.0,
            4373.0
          ],
          "price_at_signal": 4382.35,
          "entry_gap_pct": 0.054,
          "sim_entry": 4379.04,
          "variants": {
            "A": {
              "init_sl": 4388.0,
              "r_init": 8.96,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4388.0,
              "exit_time_server": "2026-09-09T08:15:00+srv"
            },
            "B": {
              "init_sl": 4395.73185,
              "r_init": 16.69185,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4395.73185,
              "exit_time_server": "2026-09-09T08:45:00+srv"
            }
          },
          "atr14_m15": 8.34592
        },
        {
          "msg_id": 19468,
          "date_utc": "2026-09-04T13:11:21+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4388.0,
          "sl": 4493.0,
          "tps": [
            4368.0,
            4375.0,
            4382.0
          ],
          "price_at_signal": 4393.71,
          "entry_gap_pct": 0.13,
          "sim_entry": 4394.05,
          "variants": {
            "A": {
              "init_sl": 4493.0,
              "r_init": 98.95,
              "outcome": "timeout",
              "r": -0.41,
              "exit": 4434.66,
              "exit_time_server": "2026-09-04T23:00:00+srv"
            },
            "B": {
              "init_sl": 4424.30426,
              "r_init": 30.25426,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4424.30426,
              "exit_time_server": "2026-09-04T16:45:00+srv"
            }
          },
          "atr14_m15": 15.12713
        }
      ],
      "variants": {
        "A": {
          "trades": 12,
          "wins": 5,
          "losses": 7,
          "win_pct": 41.7,
          "net_r": -0.02,
          "avg_r": -0.001,
          "expectancy_after_costs_r": -0.071,
          "max_dd_r": 3.59,
          "verdict": "NEGATIVE",
          "pending": 0,
          "no_atr": 0,
          "classes": {
            "sl": 6,
            "be": 1,
            "trail": 2,
            "timeout": 3
          }
        },
        "B": {
          "trades": 12,
          "wins": 5,
          "losses": 7,
          "win_pct": 41.7,
          "net_r": -0.58,
          "avg_r": -0.048,
          "expectancy_after_costs_r": -0.118,
          "max_dd_r": 4.28,
          "verdict": "NEGATIVE",
          "pending": 0,
          "no_atr": 0,
          "classes": {
            "sl": 7,
            "be": 0,
            "trail": 4,
            "timeout": 1
          }
        }
      },
      "duplicate_of": null,
      "recommendation": {
        "call": "DEMOTE (remove from config.json channels)",
        "winning_variant": "A",
        "params": null,
        "exp_after_costs_r": -0.071,
        "trades": 12,
        "win_pct": 41.7,
        "max_dd_r": 3.59,
        "reason": "best variant A is -0.071R after costs over 12 trades - at or below -0.05R: verified NEGATIVE, do not relay (other variant n=12 exp -0.118)"
      },
      "prior_evidence": "no prior verification evidence - first simulation run (new batch; not present in scan-inventory.md / full-sweep.md verified set)"
    },
    {
      "id": -1001912261779,
      "name": "FX PREMIERE VIP GOLD BTC SIGNALS",
      "plain_name": "fx_premiere_vip_gold_btc_xauusd",
      "username": "fx_premiere_vip_gold_btc_xauusd",
      "messages": 300,
      "media_only": 77,
      "not_signal": 202,
      "unparseable": 3,
      "unverifiable": 1,
      "recap_posts": 7,
      "no_data": 0,
      "pending": 0,
      "degenerate": 0,
      "stale": 0,
      "error": null,
      "signals": [
        {
          "msg_id": 24089,
          "date_utc": "2026-10-16T02:37:03+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4160.0,
          "sl": 4149.0,
          "tps": [
            4170.0,
            4175.0,
            4185.0
          ],
          "price_at_signal": 4161.75,
          "entry_gap_pct": 0.042,
          "sim_entry": 4162.64,
          "variants": {
            "A": {
              "init_sl": 4149.0,
              "r_init": 13.64,
              "outcome": "trail",
              "r": 1.036,
              "exit": 4176.77,
              "exit_time_server": "2026-10-16T07:00:00+srv"
            },
            "B": {
              "init_sl": 4149.5512,
              "r_init": 13.0888,
              "outcome": "trail",
              "r": 1.101,
              "exit": 4177.0456,
              "exit_time_server": "2026-10-16T07:00:00+srv"
            }
          },
          "atr14_m15": 6.5444
        },
        {
          "msg_id": 24056,
          "date_utc": "2026-10-15T10:54:35+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4150.0,
          "sl": 4139.0,
          "tps": [
            4160.0,
            4165.0,
            4170.0
          ],
          "price_at_signal": 4152.8,
          "entry_gap_pct": 0.067,
          "sim_entry": 4154.72,
          "variants": {
            "A": {
              "init_sl": 4139.0,
              "r_init": 15.72,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4139.0,
              "exit_time_server": "2026-10-15T15:30:00+srv"
            },
            "B": {
              "init_sl": 4143.31103,
              "r_init": 11.40897,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4143.31103,
              "exit_time_server": "2026-10-15T15:30:00+srv"
            }
          },
          "atr14_m15": 5.70449
        },
        {
          "msg_id": 23997,
          "date_utc": "2026-10-14T01:44:22+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4153.0,
          "sl": 4164.0,
          "tps": [
            4135.0,
            4140.0,
            4145.0
          ],
          "price_at_signal": 4164.56,
          "entry_gap_pct": 0.278,
          "sim_entry": 4146.07,
          "variants": {
            "A": {
              "init_sl": 4164.0,
              "r_init": 17.93,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4164.0,
              "exit_time_server": "2026-10-14T05:45:00+srv"
            },
            "B": {
              "init_sl": 4160.76128,
              "r_init": 14.69128,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4160.76128,
              "exit_time_server": "2026-10-14T05:00:00+srv"
            }
          },
          "atr14_m15": 7.34564
        },
        {
          "msg_id": 23995,
          "date_utc": "2026-10-14T01:17:01+

... (truncated, 207699 total bytes) ...

