---
slug: scout-verification
type: note
graph: gitnexus
---

{
  "generated_utc": "2026-10-16T17:37:50.345847+00:00",
  "research": "SCOUT VERIFICATION: 3 scout-verified channels x relay trailing exit (POLICY V2, fixed parser)",
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
    "verdict_bands": "expectancy after costs >= +0.05R POSITIVE EDGE, <= -0.05R NEGATIVE, else FLAT; n < 8 = INSUFFICIENT DATA (tentative)",
    "min_sample_gate": 8,
    "server_offset_s": 10801,
    "server_offset_method": "freshest tick across XAUUSD/EURUSD/GBPUSD/US30/XAGUSD/AUDUSD",
    "tick_times_at_run": {
      "XAUUSD": 1792183064,
      "EURUSD": 1792183064,
      "GBPUSD": 1792183064,
      "US30": 1792183064,
      "XAGUSD": 1792183064,
      "AUDUSD": 1792183064
    },
    "symbols_selected_for_data": [],
    "session": "telethon-scout-verify.session (sqlite backup copy of telethon.session; live session never connected/written)",
    "mt5_access": "read-only: initialize/shutdown + copy_rates/symbol_info/symbol_info_tick/symbol_select; order_send never called"
  },
  "channels": [
    {
      "id": -1001207746934,
      "name": "XAUHQ \ud83c\udfdb\ufe0f",
      "plain_name": "XAUHQ",
      "username": "t.me/Goldsignals",
      "messages": 300,
      "media_only": 37,
      "not_signal": 125,
      "unparseable": 18,
      "unverifiable": 1,
      "recap_posts": 87,
      "no_data": 0,
      "pending": 0,
      "degenerate": 0,
      "stale": 0,
      "error": null,
      "signals": [
        {
          "msg_id": 10441,
          "date_utc": "2026-10-16T13:10:44+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4184.0,
          "sl": 4195.0,
          "tps": [
            4145.0,
            4155.0,
            4165.0,
            4175.0
          ],
          "price_at_signal": 4166.49,
          "entry_gap_pct": 0.42,
          "sim_entry": 4167.22,
          "variants": {
            "A": {
              "init_sl": 4195.0,
              "r_init": 27.78,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4195.0,
              "exit_time_server": "2026-10-16T17:15:00+srv"
            },
            "B": {
              "init_sl": 4180.41205,
              "r_init": 13.19205,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4180.41205,
              "exit_time_server": "2026-10-16T16:45:00+srv"
            }
          },
          "atr14_m15": 6.59603
        },
        {
          "msg_id": 10436,
          "date_utc": "2026-10-15T14:51:36+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4135.0,
          "sl": 4127.0,
          "tps": [
            4152.0,
            4162.0,
            4175.0,
            4190.0
          ],
          "price_at_signal": 4156.84,
          "entry_gap_pct": 0.525,
          "sim_entry": 4157.78,
          "variants": {
            "A": {
              "init_sl": 4127.0,
              "r_init": 30.78,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4127.0,
              "exit_time_server": "2026-10-16T01:00:00+srv"
            },
            "B": {
              "init_sl": 4138.53419,
              "r_init": 19.24581,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4138.53419,
              "exit_time_server": "2026-10-16T01:00:00+srv"
            }
          },
          "atr14_m15": 9.62291
        },
        {
          "msg_id": 10425,
          "date_utc": "2026-10-09T16:41:41+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4182.0,
          "sl": 4179.0,
          "tps": [
            4187.0,
            4192.0,
            4200.0,
            4210.0
          ],
          "price_at_signal": 4188.35,
          "entry_gap_pct": 0.152,
          "sim_entry": 4190.81,
          "variants": {
            "A": {
              "init_sl": 4179.0,
              "r_init": 11.81,
              "outcome": "timeout",
              "r": 0.372,
              "exit": 4195.2,
              "exit_time_server": "2026-10-09T23:00:00+srv"
            },
            "B": {
              "init_sl": 4177.63662,
              "r_init": 13.17338,
              "outcome": "timeout",
              "r": 0.333,
              "exit": 4195.2,
              "exit_time_server": "2026-10-09T23:00:00+srv"
            }
          },
          "atr14_m15": 6.58669
        },
        {
          "msg_id": 10422,
          "date_utc": "2026-10-08T00:59:44+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4105.0,
          "sl": 4098.0,
          "tps": [
            4118.0,
            4128.0,
            4138.0,
            4148.0
          ],
          "price_at_signal": 4105.97,
          "entry_gap_pct": 0.024,
          "sim_entry": 4116.81,
          "variants": {
            "A": {
              "init_sl": 4098.0,
              "r_init": 18.81,
              "outcome": "be",
              "r": 0.005,
              "exit": 4116.91,
              "exit_time_server": "2026-10-08T08:45:00+srv"
            },
            "B": {
              "init_sl": 4103.04956,
              "r_init": 13.76044,
              "outcome": "trail",
              "r": 1.429,
              "exit": 4136.47978,
              "exit_time_server": "2026-10-08T05:45:00+srv"
            }
          },
          "atr14_m15": 6.88022
        },
        {
          "msg_id": 10420,
          "date_utc": "2026-10-05T17:59:25+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4147.0,
          "sl": 4170.0,
          "tps": [
            4070.0,
            4100.0,
            4115.0,
            4131.0
          ],
          "price_at_signal": 4132.3,
          "entry_gap_pct": 0.356,
          "sim_entry": 4136.79,
          "variants": {
            "A": {
              "init_sl": 4170.0,
              "r_init": 33.21,
              "outcome": "be",
              "r": 0.003,
              "exit": 4136.69,
              "exit_time_server": "2026-10-06T05:45:00+srv"
            },
            "B": {
              "init_sl": 4151.29186,
              "r_init": 14.50186,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4151.29186,
              "exit_time_server": "2026-10-06T04:00:00+srv"
            }
          },
          "atr14_m15": 7.25093
        },
        {
          "msg_id": 10414,
          "date_utc": "2026-10-01T15:25:05+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4177.0,
          "sl": 4189.0,
          "tps": [
            4130.0,
            4145.0,
            4157.0,
            4167.0
          ],
          "price_at_signal": 4156.3,
          "entry_gap_pct": 0.498,
          "sim_entry": 4166.27,
          "variants": {
            "A": {
              "init_sl": 4189.0,
              "r_init": 22.73,
              "outcome": "be",
              "r": 0.004,
              "exit": 4166.17,
              "exit_time_server": "2026-10-02T05:45:00+srv"
            },
            "B": {
              "init_sl": 4185.95001,
              "r_init": 19.68001,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4185.95001,
              "exit_time_server": "2026-10-01T20:30:00+srv"
            }
          },
          "atr14_m15": 9.84
        },
        {
          "msg_id": 10408,
          "date_utc": "2026-09-29T12:19:11+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4135.0,
          "sl": 4122.0,
          "tps": [
            4155.0,
            4170.0,
            4190.0,
            4210.0
          ],
          "price_at_signal": 4152.67,
          "entry_gap_pct": 0.426,
          "sim_entry": 4155.03,
          "variants": {
            "A": {
              "init_sl": 4122.0,
              "r_init": 33.03,
              "outcome": "trail",
              "r": 1.445,
              "exit": 4202.755,
              "exit_time_server": "2026-09-30T16:00:00+srv"
            },
            "B": {
              "init_sl": 4141.75002,
              "r_init": 13.27998,
              "outcome": "trail",
              "r": 1.01,
              "exit": 4168.44001,
              "exit_time_server": "2026-09-29T17:30:00+srv"
            }
          },
          "atr14_m15": 6.63999
        },
        {
          "msg_id": 10406,
          "date_utc": "2026-09-29T05:17:32+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4133.0,
          "sl": 4141.0,
          "tps": [
            4080.0,
            4105.0,
            4117.0,
            4126.0
          ],
          "price_at_signal": 4128.59,
          "entry_gap_pct": 0.107,
          "sim_entry": 4130.08,
          "variants": {
            "A": {
              "init_sl": 4141.0,
              "r_init": 10.92,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4141.0,
              "exit_time_server": "2026-09-29T08:45:00+srv"
            },
            "B": {
              "init_sl": 4142.67767,
              "r_init": 12.59767,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4142.67767,
              "exit_time_server": "2026-09-29T08:45:00+srv"
            }
          },
          "atr14_m15": 6.29883
        },
        {
          "msg_id": 10403,
          "date_utc": "2026-09-28T19:53:18+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4136.0,
          "sl": 4151.0,
          "tps": [
            4080.0,
            4100.0,
            4115.0,
            4126.0
          ],
          "price_at_signal": 4129.24,
          "entry_gap_pct": 0.164,
          "sim_entry": 4108.33,
          "variants": {
            "A": {
              "init_sl": 4151.0,
              "r_init": 42.67,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4151.0,
              "exit_time_server": "2026-09-29T13:30:00+srv"
            },
            "B": {
              "init_sl": 4126.17117,
              "r_init": 17.84117,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4126.17117,
              "exit_time_server": "2026-09-29T01:15:00+srv"
            }
          },
          "atr14_m15": 8.92059
        },
        {
          "msg_id": 10400,
          "date_utc": "2026-09-28T19:51:06+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4145.0,
          "sl": 4160.0,
          "tps": [
            4090.0,
            4110.0,
            4125.0,
            4135.0
          ],
          "price_at_signal": 4129.24,
          "entry_gap_pct": 0.382,
          "sim_entry": 4108.33,
          "variants": {
            "A": {
              "init_sl": 4160.0,
              "r_init": 51.67,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4160.0,
              "exit_time_server": "2026-09-29T14:15:00+srv"
            },
            "B": {
              "init_sl": 4126.17117,
              "r_init": 17.84117,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4126.17117,
              "exit_time_server": "2026-09-29T01:15:00+srv"
            }
          },
          "atr14_m15": 8.92059
        },
        {
          "msg_id": 10391,
          "date_utc": "2026-09-22T15:08:17+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4327.0,
          "sl": 4326.0,
          "tps": [
            4336.0,
            4345.0,
            4360.0,
            4375.0
          ],
          "price_at_signal": 4328.14,
          "entry_gap_pct": 0.026,
          "sim_entry": 4336.23,
          "variants": {
            "A": {
              "init_sl": 4326.0,
              "r_init": 10.23,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4326.0,
              "exit_time_server": "2026-09-22T18:45:00+srv"
            },
            "B": {
              "init_sl": 4312.65797,
              "r_init": 23.57203,
              "outcome": "be",
              "r": 0.004,
              "exit": 4336.33,
              "exit_time_server": "2026-09-23T05:15:00+srv"
            }
          },
          "atr14_m15": 11.78601
        },
        {
          "msg_id": 10384,
          "date_utc": "2026-09-22T14:41:14+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4331.0,
          "sl": 4327.0,
          "tps": [
            4335.0,
            4340.0,
            4350.0,
            4360.0
          ],
          "price_at_signal": 4327.97,
          "entry_gap_pct": 0.07,
          "sim_entry": 4319.86,
          "variants": {
            "A": {
              "init_sl": 4327.0,
              "r_init": 7.14,
              "outcome": "sl",
              "r": 1.0,
              "exit": 4327.0,
              "exit_time_server": "2026-09-22T17:45:00+srv"
            },
            "B": {
              "init_sl": 4296.6825,
              "r_init": 23.1775,
              "outcome": "trail",
              "r": 1.257,
              "exit": 4349.00125,
              "exit_time_server": "2026-09-22T21:30:00+srv"
            }
          },
          "atr14_m15": 11.58875
        },
        {
          "msg_id": 10373,
          "date_utc": "2026-09-17T18:41:42+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4368.0,
          "sl": 4383.5,
          "tps": [
            4310.0,
            4325.0,
            4342.0,
            4356.0
          ],
          "price_at_signal": 4356.42,
          "entry_gap_pct": 0.266,
          "sim_entry": 4352.13,
          "variants": {
            "A": {
              "init_sl": 4383.5,
              "r_init": 31.37,
              "outcome": "be",
              "r": 0.003,
              "exit": 4352.03,
              "exit_time_server": "2026-09-18T03:00:00+srv"
            },
            "B": {
              "init_sl": 4369.83736,
              "r_init": 17.70736,
              "outcome": "trail",
              "r": 1.405,
              "exit": 4327.25368,
              "exit_time_server": "2026-09-18T01:15:00+srv"
            }
          },
          "atr14_m15": 8.85368
        },
        {
          "msg_id": 10362,
          "date_utc": "2026-09-16T05:40:28+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4321.5,
          "sl": 4318.0,
          "tps": [
            4326.0,
            4330.0,
            4340.0,
            4350.0
          ],
          "price_at_signal": 4324.77,
          "entry_gap_pct": 0.076,
          "sim_entry": 4332.71,
          "variants": {
            "A": {
              "init_sl": 4318.0,
              "r_init": 14.71,
              "outcome": "trail",
              "r": 1.16,
              "exit": 4349.775,
              "exit_time_server": "2026-09-16T16:15:00+srv"
            },
            "B": {
              "init_sl": 4317.81032,
              "r_init": 14.89968,
              "outcome": "trail",
              "r": 1.139,
              "exit": 4349.68016,
              "exit_time_server": "2026-09-16T16:15:00+srv"
            }
          },
          "atr14_m15": 7.44984
        },
        {
          "msg_id": 10356,
          "date_utc": "2026-09-15T15:51:24+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4272.0,
          "sl": 4265.0,
          "tps": [
            4286.0,
            4295.0,
            4310.0,
            4330.0
          ],
          "price_at_signal": 4287.71,
          "entry_gap_pct": 0.366,
          "sim_entry": 4289.3,
          "variants": {
            "A": {
              "init_sl": 4265.0,
              "r_init": 24.3,
              "outcome": "trail",
              "r": 1.623,
              "exit": 4328.73,
              "exit_time_server": "2026-09-16T06:30:00+srv"
            },
            "B": {
              "init_sl": 4271.89626,
              "r_init": 17.40374,
              "outcome": "be",
              "r": 0.006,
              "exit": 4289.4,
              "exit_time_server": "2026-09-16T01:00:00+srv"
            }
          },
          "atr14_m15": 8.70187
        },
        {
          "msg_id": 10353,
          "date_utc": "2026-09-15T13:12:14+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4272.0,
          "sl": 4265.0,
          "tps": [
            4286.0,
            4295.0,
            4310.0,
            4330.0
          ],
          "price_at_signal": 4290.22,
          "entry_gap_pct": 0.425,
          "sim_entry": 4286.78,
          "variants": {
            "A": {
              "init_sl": 4265.0,
              "r_init": 21.78,
              "outcome": "be",
              "r": 0.005,
              "exit": 4286.88,
              "exit_time_server": "2026-09-16T01:00:00+srv"
            },
            "B": {
              "init_sl": 4270.72301,
              "r_init": 16.05699,
              "outcome": "be",
              "r": 0.006,
              "exit": 4286.88,
              "exit_time_server": "2026-09-16T01:00:00+srv"
            }
          },
          "atr14_m15": 8.02849
        },
        {
          "msg_id": 10341,
          "date_utc": "2026-09-09T16:38:48+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4393.0,
          "sl": 4391.0,
          "tps": [
            4400.0,
            4410.0,
            4420.0,
            4430.0
          ],
          "price_at_signal": 4401.67,
          "entry_gap_pct": 0.197,
          "sim_entry": 4407.29,
          "variants": {
            "A": {
              "init_sl": 4391.0,
              "r_init": 16.29,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4391.0,
              "exit_time_server": "2026-09-10T03:00:00+srv"
            },
            "B": {
              "init_sl": 4382.15802,
              "r_init": 25.13198,
              "outcome": "be",
              "r": 0.004,
              "exit": 4407.39,
              "exit_time_server": "2026-09-10T10:30:00+srv"
            }
          },
          "atr14_m15": 12.56599
        },
        {
          "msg_id": 10335,
          "date_utc": "2026-09-08T18:57:57+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4396.0,
          "sl": 4410.0,
          "tps": [
            4355.0,
            4365.0,
            4375.0,
            4385.0
          ],
          "price_at_signal": 4385.62,
          "entry_gap_pct": 0.237,
          "sim_entry": 4375.52,
          "variants": {
            "A": {
              "init_sl": 4410.0,
              "r_init": 34.48,
              "outcome": "be",
              "r": 0.003,
              "exit": 4375.42,
              "exit_time_server": "2026-09-09T04:30:00+srv"
            },
            "B": {
              "init_sl": 4395.08262,
              "r_init": 19.56262,
              "outcome": "trail",
              "r": 1.284,
              "exit": 4350.41131,
              "exit_time_server": "2026-09-09T01:15:00+srv"
            }
          },
          "atr14_m15": 9.78131
        },
        {
          "msg_id": 10320,
          "date_utc": "2026-09-03T14:29:06+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4464.0,
          "sl": 4454.0,
          "tps": [
            4474.0,
            4484.0,
            4494.0,
            4510.0
          ],
          "price_at_signal": 4469.18,
          "entry_gap_pct": 0.116,
          "sim_entry": 4477.22,
          "variants": {
            "A": {
              "init_sl": 4454.0,
              "r_init": 23.22,
              "outcome": "be",
              "r": 0.004,
              "exit": 4477.32,
              "exit_time_server": "2026-09-03T21:30:00+srv"
            },
            "B": {
              "init_sl": 4452.61256,
              "r_init": 24.60744,
              "outcome": "be",
              "r": 0.004,
              "exit": 4477.32,
              "exit_time_server": "2026-09-03T21:30:00+srv"
            }
          },
          "atr14_m15": 12.30372
        },
        {
          "msg_id": 10311,
          "date_utc": "2026-09-03T07:11:35+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4420.0,
          "sl": 4416.0,
          "tps": [
            4424.0,
            4430.0,
            4440.0,
            4450.0
          ],
          "price_at_signal": 4420.45,
          "entry_gap_pct": 0.01,
          "sim_entry": 4422.01,
          "variants": {
            "A": {
              "init_sl": 4416.0,
              "r_init": 6.01,
              "outcome": "trail",
              "r": 3.086,
              "exit": 4440.555,
              "exit_time_server": "2026-09-03T11:15:00+srv"
            },
            "B": {
              "init_sl": 4404.1992,
              "r_init": 17.8108,
              "outcome": "be",
              "r": 0.006,
              "exit": 4422.11,
              "exit_time_server": "2026-09-03T13:15:00+srv"
            }
          },
          "atr14_m15": 8.9054
        },
        {
          "msg_id": 10308,
          "date_utc": "2026-09-02T16:14:35+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4365.0,
          "sl": 4360.0,
          "tps": [
            4373.0,
            4383.0,
            4395.0,
            4410.0
          ],
          "price_at_signal": 4373.06,
          "entry_gap_pct": 0.184,
          "sim_entry": 4372.3,
          "variants": {
            "A": {
              "init_sl": 4360.0,
              "r_init": 12.3,
              "outcome": "trail",
              "r": 1.039,
              "exit": 4385.08,
              "exit_time_server": "2026-09-03T01:00:00+srv"
            },
            "B": {
              "init_sl": 4350.99911,
              "r_init": 21.30089,
              "outcome": "trail",
              "r": 1.236,
              "exit": 4398.62956,
              "exit_time_server": "2026-09-03T04:15:00+srv"
            }
          },
          "atr14_m15": 10.65044
        },
        {
          "msg_id": 10297,
          "date_utc": "2026-09-01T16:54:11+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4370.0,
          "sl": 4380.0,
          "tps": [
            4310.0,
            4330.0,
            4345.0,
            4360.0
          ],
          "price_at_signal": 4354.75,
          "entry_gap_pct": 0.35,
          "sim_entry": 4351.33,
          "variants": {
            "A": {
              "init_sl": 4380.0,
              "r_init": 28.67,
              "outcome": "trail",
              "r": 1.062,
              "exit": 4320.895,
              "exit_time_server": "2026-09-02T01:15:00+srv"
            },
            "B": {
              "init_sl": 4374.21554,
              "r_init": 22.88554,
              "outcome": "trail",
              "r": 1.456,
              "exit": 4318.00277,
              "exit_time_server": "2026-09-02T01:15:00+srv"
            }
          },
          "atr14_m15": 11.44277
        },
        {
          "msg_id": 10289,
          "date_utc": "2026-08-26T19:10:30+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4605.3,
          "sl": 4630.0,
          "tps": [
            4540.0,
            4560.0,
            4575.0,
            4590.0
          ],
          "price_at_signal": 4593.77,
          "entry_gap_pct": 0.251,
          "sim_entry": 4594.37,
          "variants": {
            "A": {
              "init_sl": 4630.0,
              "r_init": 35.63,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4630.0,
              "exit_time_server": "2026-08-27T04:30:00+srv"
            },
            "B": {
              "init_sl": 4611.28072,
              "r_init": 16.91072,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4611.28072,
              "exit_time_server": "2026-08-27T01:15:00+srv"
            }
          },
          "atr14_m15": 8.45536
        },
        {
          "msg_id": 10283,
          "date_utc": "2026-08-24T16:59:28+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4662.0,
          "sl": 4682.0,
          "tps": [
            4600.0,
            4615.0,
            4630.0,
            4647.0
          ],
          "price_at_signal": 4659.52,
          "entry_gap_pct": 0.053,
          "sim_entry": 4644.87,
          "variants": {
            "A": {
              "init_sl": 4682.0,
              "r_init": 37.13,
              "outcome": "be",
              "r": 0.003,
              "exit": 4644.77,
              "exit_time_server": "2026-08-25T01:15:00+srv"
            },
            "B": {
              "init_sl": 4671.83327,
              "r_init": 26.96327,
              "outcome": "trail",
              "r": 1.124,
              "exit": 4614.56164,
              "exit_time_server": "2026-08-25T01:15:00+srv"
            }
          },
          "atr14_m15": 13.48164
        },
        {
          "msg_id": 10273,
          "date_utc": "2026-08-20T18:58:25+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4512.0,
          "sl": 4505.0,
          "tps": [
            4525.0,
            4535.0,
            4550.0,
            4560.0
          ],
          "price_at_signal": 4520.19,
          "entry_gap_pct": 0.181,
          "sim_entry": 4522.02,
          "variants": {
            "A": {
              "init_sl": 4505.0,
              "r_init": 17.02,
              "outcome": "be",
              "r": 0.006,
              "exit": 4522.12,
              "exit_time_server": "2026-08-21T05:00:00+srv"
            },
            "B": {
              "init_sl": 4501.70668,
              "r_init": 20.31332,
              "outcome": "be",
              "r": 0.005,
              "exit": 4522.12,
              "exit_time_server": "2026-08-21T05:00:00+srv"
            }
          },
          "atr14_m15": 10.15666
        },
        {
          "msg_id": 10270,
          "date_utc": "2026-08-19T16:08:00+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4478.0,
          "sl": 4475.0,
          "tps": [
            4490.0,
            4500.0,
            4510.0,
            4520.0
          ],
          "price_at_signal": 4493.76,
          "entry_gap_pct": 0.351,
          "sim_entry": 4497.68,
          "variants": {
            "A": {
              "init_sl": 4475.0,
              "r_init": 22.68,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4475.0,
              "exit_time_server": "2026-08-19T21:15:00+srv"
            },
            "B": {
              "init_sl": 4472.26557,
              "r_init": 25.41443,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4472.26557,
              "exit_time_server": "2026-08-19T21:30:00+srv"
            }
          },
          "atr14_m15": 12.70721
        },
        {
          "msg_id": 10258,
          "date_utc": "2026-08-14T17:12:25+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4393.0,
          "sl": 4397.0,
          "tps": [
            4360.0,
            4370.0,
            4380.0,
            4386.0
          ],
          "price_at_signal": 4385.95,
          "entry_gap_pct": 0.161,
          "sim_entry": 4382.34,
          "variants": {
            "A": {
              "init_sl": 4397.0,
              "r_init": 14.66,
              "outcome": "timeout",
              "r": 0.432,
              "exit": 4376.0,
              "exit_time_server": "2026-08-14T23:00:00+srv"
            },
            "B": {
              "init_sl": 4398.31737,
              "r_init": 15.97737,
              "outcome": "timeout",
              "r": 0.397,
              "exit": 4376.0,
              "exit_time_server": "2026-08-14T23:00:00+srv"
            }
          },
          "atr14_m15": 7.98869
        },
        {
          "msg_id": 10248,
          "date_utc": "2026-08-13T15:21:05+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4386.0,
          "sl": 4402.0,
          "tps": [
            4325.0,
            4340.0,
            4355.0,
            4370.0
          ],
          "price_at_signal": 4369.71,
          "entry_gap_pct": 0.373,
          "sim_entry": 4365.35,
          "variants": {
            "A": {
              "init_sl": 4402.0,
              "r_init": 36.65,
              "outcome": "be",
              "r": 0.003,
              "exit": 4365.25,
              "exit_time_server": "2026-08-14T14:45:00+srv"
            },
            "B": {
              "init_sl": 4386.66022,
              "r_init": 21.31022,
              "outcome": "trail",
              "r": 1.202,
              "exit": 4339.74511,
              "exit_time_server": "2026-08-14T04:00:00+srv"
            }
          },
          "atr14_m15": 10.65511
        },
        {
          "msg_id": 10239,
          "date_utc": "2026-08-11T15:30:23+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4396.5,
          "sl": 4405.0,
          "tps": [
            4350.0,
            4370.0,
            4380.0,
            4389.0
          ],
          "price_at_signal": 4386.75,
          "entry_gap_pct": 0.222,
          "sim_entry": 4375.7,
          "variants": {
            "A": {
              "init_sl": 4405.0,
              "r_init": 29.3,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4405.0,
              "exit_time_server": "2026-08-12T05:30:00+srv"
            },
            "B": {
              "init_sl": 4395.8139,
              "r_init": 20.1139,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4395.8139,
              "exit_time_server": "2026-08-12T04:45:00+srv"
            }
          },
          "atr14_m15": 10.05695
        },
        {
          "msg_id": 10230,
          "date_utc": "2026-08-10T17:53:39+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4350.0,
          "sl": 4344.0,
          "tps": [
            4364.0,
            4374.0,
            4384.0,
            4400.0
          ],
          "price_at_signal": 4360.18,
          "entry_gap_pct": 0.233,
          "sim_entry": 4360.16,
          "variants": {
            "A": {
              "init_sl": 4344.0,
              "r_init": 16.16,
              "outcome": "trail",
              "r": 1.667,
              "exit": 4387.1,
              "exit_time_server": "2026-08-11T01:00:00+srv"
            },
            "B": {
              "init_sl": 4345.10683,
              "r_init": 15.05317,
              "outcome": "trail",
              "r": 1.011,
              "exit": 4375.38342,
              "exit_time_server": "2026-08-10T21:45:00+srv"
            }
          },
          "atr14_m15": 7.52658
        },
        {
          "msg_id": 10180,
          "date_utc": "2026-08-04T15:47:08+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4078.0,
          "sl": 4074.0,
          "tps": [
            4085.0,
            4095.0,
            4105.0,
            4120.0
          ],
          "price_at_signal": 4083.97,
          "entry_gap_pct": 0.146,
          "sim_entry": 4087.3,
          "variants": {
            "A": {
              "init_sl": 4074.0,
              "r_init": 13.3,
              "outcome": "be",
              "r": 0.008,
              "exit": 4087.4,
              "exit_time_server": "2026-08-04T20:45:00+srv"
            },
            "B": {
              "init_sl": 4067.87253,
              "r_init": 19.42747,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4067.87253,
              "exit_time_server": "2026-08-05T01:00:00+srv"
            }
          },
          "atr14_m15": 9.71373
        },
        {
          "msg_id": 10151,
          "date_utc": "2026-07-30T15:57:29+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4083.0,
          "sl": 4065.0,
          "tps": [
            4100.0,
            4115.0,
            4130.0,
            4150.0
          ],
          "price_at_signal": 4105.35,
          "entry_gap_pct": 0.544,
          "sim_entry": 4108.09,
          "variants": {
            "A": {
              "init_sl": 4065.0,
              "r_init": 43.09,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4065.0,
              "exit_time_server": "2026-07-31T11:00:00+srv"
            },
            "B": {
              "init_sl": 4081.79235,
              "r_init": 26.29765,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4081.79235,
              "exit_time_server": "2026-07-31T01:00:00+srv"
            }
          },
          "atr14_m15": 13.14882
        }
      ],
      "variants": {
        "A": {
          "trades": 32,
          "wins": 21,
          "losses": 11,
          "win_pct": 65.6,
          "net_r": 1.93,
          "avg_r": 0.06,
          "expectancy_after_costs_r": -0.01,
          "max_dd_r": 4.94,
          "verdict": "FLAT",
          "pending": 0,
          "no_atr": 0,
          "classes": {
            "sl": 12,
            "be": 11,
            "trail": 7,
            "timeout": 2
          }
        },
        "B": {
          "trades": 32,
          "wins": 20,
          "losses": 12,
          "win_pct": 62.5,
          "net_r": 2.32,
          "avg_r": 0.072,
          "expectancy_after_costs_r": 0.002,
          "max_dd_r": 4.99,
          "verdict": "FLAT",
          "pending": 0,
          "no_atr": 0,
          "classes": {
            "sl": 12,
            "be": 7,
            "trail": 11,
            "timeout": 2
          }
        }
      },
      "recommendation": {
        "call": "STAY SHADOW",
        "winning_variant": "B",
        "params": null,
        "exp_after_costs_r": 0.002,
        "trades": 32,
        "reason": "best variant B is +0.002R after costs over 32 trades - does not clear +0.05R (other variant A n=32 exp -0.01)"
      },
      "prior_evidence": "full-sweep (old parser, 200 msgs): 0 complete signals - not verified"
    },
    {
      "id": -1001588519179,
      "name": "SureShot GOLD",
      "plain_name": "SureShotFX free gold",
      "username": "ssfgold",
      "messages": 300,
      "media_only": 31,
      "not_signal": 83,
      "unparseable": 5,
      "unverifiable": 0,
      "recap_posts": 155,
      "no_data": 0,
      "pending": 0,
      "degenerate": 0,
      "stale": 0,
      "error": null,
      "signals": [
        {
          "msg_id": 18386,
          "date_utc": "2026-10-16T06:20:00+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4177.4,
          "sl": 4167.4,
          "tps": [
            4197.4
          ],
          "price_at_signal": 4169.52,
          "entry_gap_pct": 0.189,
          "sim_entry": 4176.06,
          "variants": {
            "A": {
              "init_sl": 4167.4,
              "r_init": 8.66,
              "outcome": "trail",
              "r": 1.075,
              "exit": 4185.37,
              "exit_time_server": "2026-10-16T10:45:00+srv"
            },
            "B": {
              "init_sl": 4161.84915,
              "r_init": 14.21085,
              "outcome": "be",
              "r": 0.007,
              "exit": 4176.16,
              "exit_time_server": "2026-10-16T13:00:00+srv"
            }
          },
          "atr14_m15": 7.10542
        },
        {
          "msg_id": 18383,
          "date_utc": "2026-10-16T06:03:29+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4161.48,
          "sl": 4151.48,
          "tps": [
            4181.48
          ],
          "price_at_signal": 4174.71,
          "entry_gap_pct": 0.317,
          "sim_entry": 4169.52,
          "variants": {
            "A": {
              "init_sl": 4151.48,
              "r_init": 18.04,
              "outcome": "be",
              "r": 0.006,
              "exit": 4169.62,
              "exit_time_server": "2026-10-16T15:45:00+srv"
            },
            "B": {
              "init_sl": 4155.35293,
              "r_init": 14.16707,
              "outcome": "trail",
              "r": 1.028,
              "exit": 4184.08647,
              "exit_time_server": "2026-10-16T12:15:00+srv"
            }
          },
          "atr14_m15": 7.08353
        },
        {
          "msg_id": 18365,
          "date_utc": "2026-10-15T06:02:43+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4136.44,
          "sl": 4126.44,
          "tps": [
            4156.44
          ],
          "price_at_signal": 4138.15,
          "entry_gap_pct": 0.041,
          "sim_entry": 4133.01,
          "variants": {
            "A": {
              "init_sl": 4126.44,
              "r_init": 6.57,
              "outcome": "trail",
              "r": 1.127,
              "exit": 4140.415,
              "exit_time_server": "2026-10-15T10:15:00+srv"
            },
            "B": {
              "init_sl": 4118.46987,
              "r_init": 14.54013,
              "outcome": "trail",
              "r": 1.278,
              "exit": 4151.58994,
              "exit_time_server": "2026-10-15T11:30:00+srv"
            }
          },
          "atr14_m15": 7.27006
        },
        {
          "msg_id": 18339,
          "date_utc": "2026-10-14T05:09:37+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4159.05,
          "sl": 4149.05,
          "tps": [
            4179.05
          ],
          "price_at_signal": 4165.53,
          "entry_gap_pct": 0.156,
          "sim_entry": 4162.41,
          "variants": {
            "A": {
              "init_sl": 4149.05,
              "r_init": 13.36,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4149.05,
              "exit_time_server": "2026-10-14T08:45:00+srv"
            },
            "B": {
              "init_sl": 4149.39424,
              "r_init": 13.01576,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4149.39424,
              "exit_time_server": "2026-10-14T08:45:00+srv"
            }
          },
          "atr14_m15": 6.50788
        },
        {
          "msg_id": 18329,
          "date_utc": "2026-10-13T04:26:12+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4191.99,
          "sl": 4201.99,
          "tps": [
            4171.99
          ],
          "price_at_signal": 4189.25,
          "entry_gap_pct": 0.065,
          "sim_entry": 4191.04,
          "variants": {
            "A": {
              "init_sl": 4201.99,
              "r_init": 10.95,
              "outcome": "trail",
              "r": 1.182,
              "exit": 4178.095,
              "exit_time_server": "2026-10-13T16:15:00+srv"
            },
            "B": {
              "init_sl": 4204.58135,
              "r_init": 13.54135,
              "outcome": "trail",
              "r": 1.601,
              "exit": 4169.36068,
              "exit_time_server": "2026-10-13T17:30:00+srv"
            }
          },
          "atr14_m15": 6.77068
        },
        {
          "msg_id": 18322,
          "date_utc": "2026-10-12T08:22:41+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4164.5,
          "sl": 4154.5,
          "tps": [
            4184.5
          ],
          "price_at_signal": 4177.09,
          "entry_gap_pct": 0.301,
          "sim_entry": 4176.6,
          "variants": {
            "A": {
              "init_sl": 4154.5,
              "r_init": 22.1,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4154.5,
              "exit_time_server": "2026-10-13T03:45:00+srv"
            },
            "B": {
              "init_sl": 4165.7873,
              "r_init": 10.8127,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4165.7873,
              "exit_time_server": "2026-10-12T15:15:00+srv"
            }
          },
          "atr14_m15": 5.40635
        },
        {
          "msg_id": 18312,
          "date_utc": "2026-10-12T04:33:33+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4198.02,
          "sl": 4188.02,
          "tps": [
            4218.02
          ],
          "price_at_signal": 4200.47,
          "entry_gap_pct": 0.058,
          "sim_entry": 4197.73,
          "variants": {
            "A": {
              "init_sl": 4188.02,
              "r_init": 9.71,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4188.02,
              "exit_time_server": "2026-10-12T08:00:00+srv"
            },
            "B": {
              "init_sl": 4185.15468,
              "r_init": 12.57532,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4185.15468,
              "exit_time_server": "2026-10-12T08:15:00+srv"
            }
          },
          "atr14_m15": 6.28766
        },
        {
          "msg_id": 18295,
          "date_utc": "2026-10-09T07:27:48+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4192.0,
          "sl": 4182.0,
          "tps": [
            4212.0
          ],
          "price_at_signal": 4193.64,
          "entry_gap_pct": 0.039,
          "sim_entry": 4194.42,
          "variants": {
            "A": {
              "init_sl": 4182.0,
              "r_init": 12.42,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4182.0,
              "exit_time_server": "2026-10-09T13:30:00+srv"
            },
            "B": {
              "init_sl": 4181.74218,
              "r_init": 12.67782,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4181.74218,
              "exit_time_server": "2026-10-09T13:30:00+srv"
            }
          },
          "atr14_m15": 6.33891
        },
        {
          "msg_id": 18273,
          "date_utc": "2026-10-08T05:55:13+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4117.34,
          "sl": 4107.34,
          "tps": [
            4137.34
          ],
          "price_at_signal": 4125.94,
          "entry_gap_pct": 0.208,
          "sim_entry": 4117.57,
          "variants": {
            "A": {
              "init_sl": 4107.34,
              "r_init": 10.23,
              "outcome": "trail",
              "r": 1.014,
              "exit": 4127.945,
              "exit_time_server": "2026-10-08T11:30:00+srv"
            },
            "B": {
              "init_sl": 4103.52569,
              "r_init": 14.04431,
              "outcome": "be",
              "r": 0.007,
              "exit": 4117.67,
              "exit_time_server": "2026-10-08T13:15:00+srv"
            }
          },
          "atr14_m15": 7.02215
        },
        {
          "msg_id": 18256,
          "date_utc": "2026-10-07T06:53:42+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4133.01,
          "sl": 4143.01,
          "tps": [
            4113.01
          ],
          "price_at_signal": 4133.3,
          "entry_gap_pct": 0.007,
          "sim_entry": 4130.45,
          "variants": {
            "A": {
              "init_sl": 4143.01,
              "r_init": 12.56,
              "outcome": "trail",
              "r": 1.219,
              "exit": 4115.14,
              "exit_time_server": "2026-10-07T13:45:00+srv"
            },
            "B": {
              "init_sl": 4141.11898,
              "r_init": 10.66898,
              "outcome": "trail",
              "r": 1.524,
              "exit": 4114.19449,
              "exit_time_server": "2026-10-07T13:45:00+srv"
            }
          },
          "atr14_m15": 5.33449
        },
        {
          "msg_id": 18235,
          "date_utc": "2026-10-06T02:01:04+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4129.98,
          "sl": 4119.98,
          "tps": [
            4149.98
          ],
          "price_at_signal": 4129.99,
          "entry_gap_pct": 0.0,
          "sim_entry": 4130.35,
          "variants": {
            "A": {
              "init_sl": 4119.98,
              "r_init": 10.37,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4119.98,
              "exit_time_server": "2026-10-06T05:30:00+srv"
            },
            "B": {
              "init_sl": 4116.99299,
              "r_init": 13.35701,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4116.99299,
              "exit_time_server": "2026-10-06T05:30:00+srv"
            }
          },
          "atr14_m15": 6.67851
        },
        {
          "msg_id": 18223,
          "date_utc": "2026-10-05T05:53:33+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "sell",
          "entry": 4135.94,
          "sl": 4145.94,
          "tps": [
            4115.94
          ],
          "price_at_signal": 4140.43,
          "entry_gap_pct": 0.108,
          "sim_entry": 4134.51,
          "variants": {
            "A": {
              "init_sl": 4145.94,
              "r_init": 11.43,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4145.94,
              "exit_time_server": "2026-10-05T09:00:00+srv"
            },
            "B": {
              "init_sl": 4150.1424,
              "r_init": 15.6324,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4150.1424,
              "exit_time_server": "2026-10-05T09:00:00+srv"
            }
          },
          "atr14_m15": 7.8162
        },
        {
          "msg_id": 18192,
          "date_utc": "2026-10-02T04:46:25+00:00",
          "raw_symbol": "XAUUSD",
          "resolved": "XAUUSD",
          "side": "buy",
          "entry": 4182.88,
          "sl": 4172.88,
          "tps": [
            4202.88
          ],
          "price_at_signal": 4182.16,
          "entry_gap_pct": 0.017,
          "sim_entry": 4184.76,
          "variants": {
            "A": {
              "init_sl": 4172.88,
              "r_init": 11.88,
              "outcome": "be",
              "r": 0.008,
              "exit": 4184.86,
              "exit_time_server": "2026-10-02T09:30:00+srv"
            },
            "B": {
              "init_sl": 4168.57801,
              "r_init": 16.18199,
              "outcome": "sl",
              "r": -1.0,
              "exit": 4168.57801,
              "exit_time_server": "2026-10-02T13:15:00+srv"
            }
          },
          "atr14_m15": 8.09099
        },
        {
          "msg_id": 18180,
          "date_utc": "2026-10-01T07:16:29+00:00",
          "raw_symbol": "

... (truncated, 116362 total bytes) ...

