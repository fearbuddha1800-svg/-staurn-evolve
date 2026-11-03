---
slug: pine_transpiled_verification
type: note
graph: gitnexus
---

{
  "ok": false,
  "generated_at_utc": "2026-11-02T18:21:09.872733+00:00",
  "architecture": "Python indicators/entry/exit conditions; PineTS order-tape execution/accounting via existing pinets_bridge.js",
  "data": {
    "path": "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\strategy2_data_XAUUSD.csv",
    "sha256": "5e26fd492fa7e5d1757013a6da7ab8992f909e6187ecd4100174075ad3af3c39",
    "rows": 29999,
    "bars": 500,
    "symbol": "XAUUSD",
    "timeframe": "H1",
    "first_open_time_ms": 1789538400000,
    "last_open_time_ms": 1792184400000,
    "last_close": 4160.08,
    "provenance": "Existing local MT5-format historical CSV supplied by workspace; not independently vendor-authenticated."
  },
  "runtime": {
    "bridge_sha256": "0f6e8cd3e2945f46573a3a82b19cd6a8f55aaee6b70fecdf91eb6afc9e773a51",
    "pinets_dist_sha256": "ec878943c8977e0522c362485855448b554e9978eccbaefe3e435f742c9cc4ec"
  },
  "delivery_ledger": {
    "expected": {
      "open_trades": 1,
      "closed_trades": 20,
      "direction": "long",
      "entry_price": 4145.62,
      "netprofit": -310.28,
      "max_drawdown": 393.01,
      "equity": 999712.87
    },
    "observed": {
      "open_trades": 1,
      "closed_trades": 20,
      "direction": "long",
      "entry_price": 4145.62,
      "netprofit": -286.51,
      "max_drawdown": 393.01,
      "equity": 999727.95
    }
  },
  "checks": [
    {
      "name": "ema_cross.bars",
      "passed": true
    },
    {
      "name": "ema_cross.last_close",
      "passed": true
    },
    {
      "name": "ema_cross.open_trades",
      "passed": true
    },
    {
      "name": "ema_cross.closed_trades",
      "passed": true
    },
    {
      "name": "ema_cross.ledger",
      "passed": true
    },
    {
      "name": "ema_cross.position",
      "passed": true
    },
    {
      "name": "ema_cross.stats",
      "passed": true
    },
    {
      "name": "ema_cross.latest_signal",
      "passed": true
    },
    {
      "name": "ema_cross.indicator.Fast EMA",
      "passed": true
    },
    {
      "name": "ema_cross.indicator.Slow EMA",
      "passed": true
    },
    {
      "name": "rsi_ema_trend.bars",
      "passed": true
    },
    {
      "name": "rsi_ema_trend.last_close",
      "passed": true
    },
    {
      "name": "rsi_ema_trend.open_trades",
      "passed": true
    },
    {
      "name": "rsi_ema_trend.closed_trades",
      "passed": true
    },
    {
      "name": "rsi_ema_trend.ledger",
      "passed": true
    },
    {
      "name": "rsi_ema_trend.position",
      "passed": true
    },
    {
      "name": "rsi_ema_trend.stats",
      "passed": true
    },
    {
      "name": "rsi_ema_trend.latest_signal",
      "passed": true
    },
    {
      "name": "rsi_ema_trend.indicator.RSI",
      "passed": true
    },
    {
      "name": "rsi_ema_trend.indicator.EMA",
      "passed": true
    },
    {
      "name": "rsi_ema_trend.indicator.ATR",
      "passed": true
    },
    {
      "name": "delivery_ledger.open_trades",
      "passed": true
    },
    {
      "name": "delivery_ledger.closed_trades",
      "passed": true
    },
    {
      "name": "delivery_ledger.direction",
      "passed": true
    },
    {
      "name": "delivery_ledger.entry_price",
      "passed": true
    },
    {
      "name": "delivery_ledger.netprofit",
      "passed": false
    },
    {
      "name": "delivery_ledger.max_drawdown",
      "passed": true
    },
    {
      "name": "delivery_ledger.equity",
      "passed": false
    }
  ],
  "strategies": {
    "ema_cross": {
      "source_sha256": "35b3baf1ba0b142d8f1f91e036343200103c2a18186aef43af985a633ef4875d",
      "python_order_count": 29,
      "python_orders": [
        {
          "bar_index": 30,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 67,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 103,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 113,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 159,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 171,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 209,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 233,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 244,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 247,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 250,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 255,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 257,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 262,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 265,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 276,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 315,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 330,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 352,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 356,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 357,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 361,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 362,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 364,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 366,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 402,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 419,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 429,
          "direction": "short",
          "entry_id": "Short",
          "sl": null,
          "tp": null
        },
        {
          "bar_index": 462,
          "direction": "long",
          "entry_id": "Long",
          "sl": null,
          "tp": null
        }
      ],
      "original": {
        "ok": true,
        "symbol": "XAUUSD",
        "timeframe": "60",
        "bars": 500,
        "plots": {
          "Fast EMA": {
            "latest": 4168.838200095,
            "recent": [
              4176.6639823938,
              4176.153185915,
              4175.298548732,
              4173.5508389856,
              4175.8326711885,
              4177.7101369508,
              4175.7121095606,
              4172.8796876485,
              4171.0277501188,
              4168.838200095
            ],
            "count": 500
          },
          "Slow EMA": {
            "latest": 4168.213779867,
            "recent": [
              4166.6009770961,
              4167.2836155419,
              4167.7014686744,
              4167.5976987949,
              4169.1760898136,
              4170.6346271033,
              4170.369661003,
              4169.5678736391,
              4169.0271578537,
              4168.213779867
            ],
            "count": 500
          }
        },
        "open_trades": [
          {
            "id": "trade_28",
            "entry_id": "Long",
            "entry_price": 4145.62,
            "entry_time": 1792047600000,
            "size": 1,
            "direction": "long"
          }
        ],
        "closed_trades": [
          {
            "id": "trade_9",
            "entry_id": "Long",
            "entry_price": 4188.01,
            "exit_price": 4153.33,
            "profit": -34.68000000000029,
            "entry_time": 1790845200000,
            "exit_time": 1790856000000
          },
          {
            "id": "trade_10",
            "entry_id": "Short",
            "entry_price": 4153.33,
            "exit_price": 4182.66,
            "profit": -29.329999999999927,
            "entry_time": 1790856000000,
            "exit_time": 1790866800000
          },
          {
            "id": "trade_11",
            "entry_id": "Long",
            "entry_price": 4182.66,
            "exit_price": 4162.27,
            "profit": -20.389999999999418,
            "entry_time": 1790866800000,
            "exit_time": 1790884800000
          },
          {
            "id": "trade_12",
            "entry_id": "Short",
            "entry_price": 4162.27,
            "exit_price": 4176.91,
            "profit": -14.639999999999418,
            "entry_time": 1790884800000,
            "exit_time": 1790892000000
          },
          {
            "id": "trade_13",
            "entry_id": "Long",
            "entry_price": 4176.91,
            "exit_price": 4151.35,
            "profit": -25.55999999999949,
            "entry_time": 1790892000000,
            "exit_time": 1790917200000
          },
          {
            "id": "trade_14",
            "entry_id": "Short",
            "entry_price": 4151.35,
            "exit_price": 4184.76,
            "profit": -33.409999999999854,
            "entry_time": 1790917200000,
            "exit_time": 1790928000000
          },
          {
            "id": "trade_15",
            "entry_id": "Long",
            "entry_price": 4184.76,
            "exit_price": 4127.23,
            "profit": -57.530000000000655,
            "entry_time": 1790928000000,
            "exit_time": 1790967600000
          },
          {
            "id": "trade_16",
            "entry_id": "Short",
            "entry_price": 4127.23,
            "exit_price": 4158.36,
            "profit": -31.13000000000011,
            "entry_time": 1790967600000,
            "exit_time": 1791295200000
          },
          {
            "id": "trade_17",
            "entry_id": "Long",
            "entry_price": 4158.36,
            "exit_price": 4143.25,
            "profit": -15.109999999999673,
            "entry_time": 1791295200000,
            "exit_time": 1791356400000
          },
          {
            "id": "trade_18",
            "entry_id": "Short",
            "entry_price": 4143.25,
            "exit_price": 4136.27,
            "profit": 6.979999999999563,
            "entry_time": 1791356400000,
            "exit_time": 1791442800000
          },
          {
            "id": "trade_19",
            "entry_id": "Long",
            "entry_price": 4136.27,
            "exit_price": 4120.07,
            "profit": -16.200000000000728,
            "entry_time": 1791442800000,
            "exit_time": 1791457200000
          },
          {
            "id": "trade_20",
            "entry_id": "Short",
            "entry_price": 4120.07,
            "exit_price": 4126.27,
            "profit": -6.200000000000728,
            "entry_time": 1791457200000,
            "exit_time": 1791460800000
          },
          {
            "id": "trade_21",
            "entry_id": "Long",
            "entry_price": 4126.27,
            "exit_price": 4118.63,
            "profit": -7.640000000000327,
            "entry_time": 1791460800000,
            "exit_time": 1791475200000
          },
          {
            "id": "trade_22",
            "entry_id": "Short",
            "entry_price": 4118.63,
            "exit_price": 4129.91,
            "profit": -11.279999999999745,
            "entry_time": 1791475200000,
            "exit_time": 1791478800000
          },
          {
            "id": "trade_23",
            "entry_id": "Long",
            "entry_price": 4129.91,
            "exit_price": 4111.76,
            "profit": -18.149999999999636,
            "entry_time": 1791478800000,
            "exit_time": 1791486000000
          },
          {
            "id": "trade_24",
            "entry_id": "Short",
            "entry_price": 4111.76,
            "exit_price": 4132.68,
            "profit": -20.920000000000073,
            "entry_time": 1791486000000,
            "exit_time": 1791493200000
          },
          {
            "id": "trade_25",
            "entry_id": "Long",
            "entry_price": 4132.68,
            "exit_price": 4173.18,
            "profit": 40.5,
            "entry_time": 1791493200000,
            "exit_time": 1791810000000
          },
          {
            "id": "trade_26",
            "entry_id": "Short",
            "entry_price": 4173.18,
            "exit_price": 4195.39,
            "profit": -22.210000000000036,
            "entry_time": 1791810000000,
            "exit_time": 1791878400000
          },
          {
            "id": "trade_27",
            "entry_id": "Long",
            "entry_price": 4195.39,
            "exit_price": 4166.89,
            "profit": -28.5,
            "entry_time": 1791878400000,
            "exit_time": 1791914400000
          },
          {
            "id": "trade_28",
            "entry_id": "Short",
            "entry_price": 4166.89,
            "exit_price": 4145.62,
            "profit": 21.270000000000437,
            "entry_time": 1791914400000,
            "exit_time": 1792047600000
          }
        ],
        "ledger": [
          {
            "entry_id": "Long",
            "entry_price": 4145.62,
            "entry_time": 1792047600000,
            "entry_bar_index": 463,
            "qty": 1
          }
        ],
        "position": {
          "size": 1,
          "direction": "long",
          "avg_price": 4145.62,
          "entry_name": "Long"
        },
        "stats": {
          "netprofit": -286.5100000000011,
          "grossprofit": 205.0599999999995,
          "grossloss": 491.5700000000006,
          "openprofit": 14.460000000000036,
          "max_drawdown": 393.01000000007934,
          "equity": 999727.95,
          "initial_capital": 1000000
        },
        "latest_signal": {
          "type": "long",
          "price": 4145.62,
          "time": 1792047600000,
          "active": true,
          "size": 1
        },
        "last_close": 4160.08
      },
      "transposed": {
        "ok": true,
        "symbol": "XAUUSD",
        "timeframe": "60",
        "bars": 500,
        "plots": {
          "Close": {
            "latest": 4160.08,
            "recent": [
              4177.07,
              4174.11,
              4171.88,
              4166.56,
              4184.96,
              4185.22,
              4167.72,
              4161.55,
              4163.62,
              4160.08
            ],
            "count": 500
          }
        },
        "open_trades": [
          {
            "id": "trade_28",
            "entry_id": "Long",
            "entry_price": 4145.62,
            "entry_time": 1792047600000,
            "size": 1,
            "direction": "long"
          }
        ],
        "closed_trades": [
          {
            "id": "trade_9",
            "entry_id": "Long",
            "entry_price": 4188.01,
            "exit_price": 4153.33,
            "profit": -34.68000000000029,
            "entry_time": 1790845200000,
            "exit_time": 1790856000000
          },
          {
            "id": "trade_10",
            "entry_id": "Short",
            "entry_price": 4153.33,
            "exit_price": 4182.66,
            "profit": -29.329999999999927,
            "entry_time": 1790856000000,
            "exit_time": 1790866800000
          },
          {
            "id": "trade_11",
            "entry_id": "Long",
            "entry_price": 4182.66,
            "exit_price": 4162.27,
            "profit": -20.389999999999418,
            "entry_time": 1790866800000,
            "exit_time": 1790884800000
          },
          {
            "id": "trade_12",
            "entry_id": "Short",
            "entry_price": 4162.27,
            "exit_price": 4176.91,
            "profit": -14.639999999999418,
            "entry_time": 1790884800000,
            "exit_time": 1790892000000
          },
          {
            "id": "trade_13",
            "entry_id": "Long",
            "entry_price": 4176.91,
            "exit_price": 4151.35,
            "profit": -25.55999999999949,
            "entry_time": 1790892000000,
            "exit_time": 1790917200000
          },
          {
            "id": "trade_14",
            "entry_id": "Short",
            "entry_price": 4151.35,
            "exit_price": 4184.76,
            "profit": -33.409999999999854,
            "entry_time": 1790917200000,
            "exit_time": 1790928000000
          },
          {
            "id": "trade_15",
            "entry_id": "Long",
            "entry_price": 4184.76,
            "exit_price": 4127.23,
            "profit": -57.530000000000655,
            "entry_time": 1790928000000,
            "exit_time": 1790967600000
          },
          {
            "id": "trade_16",
            "entry_id": "Short",
            "entry_price": 4127.23,
            "exit_price": 4158.36,
            "profit": -31.13000000000011,
            "entry_time": 1790967600000,
            "exit_time": 1791295200000
          },
          {
            "id": "trade_17",
            "entry_id": "Long",
            "entry_price": 4158.36,
            "exit_price": 4143.25,
            "profit": -15.109999999999673,
            "entry_time": 1791295200000,
            "exit_time": 1791356400000
          },
          {
            "id": "trade_18",
            "entry_id": "Short",
            "entry_price": 4143.25,
            "exit_price": 4136.27,
            "profit": 6.979999999999563,
            "entry_time": 1791356400000,
            "exit_time": 1791442800000
          },
          {
            "id": "trade_19",
            "entry_id": "Long",
            "entry_price": 4136.27,
            "exit_price": 4120.07,
            "profit": -16.200000000000728,
            "entry_time": 1791442800000,
            "exit_time": 1791457200000
          },
          {
            "id": "trade_20",
            "entry_id": "Short",
            "entry_price": 4120.07,
            "exit_price": 4126.27,
            "profit": -6.200000000000728,
            "entry_time": 1791457200000,
            "exit_time": 1791460800000
          },
          {
            "id": "trade_21",
            "entry_id": "Long",
            "entry_price": 4126.27,
            "exit_price": 4118.63,
            "profit": -7.640000000000327,
            "entry_time": 1791460800000,
            "exit_time": 1791475200000
          },
          {
            "id": "trade_22",
            "entry_id": "Short",
            "entry_price": 4118.63,
            "exit_price": 4129.91,
            "profit": -11.279999999999745,
            "entry_time": 1791475200000,
            "exit_time": 1791478800000
          },
          {
            "id": "trade_23",
            "entry_id": "Long",
            "entry_price": 4129.91,
            "exit_price": 4111.76,
            "profit": -18.149999999999636,
            "entry_time": 1791478800000,
            "exit_time": 1791486000000
          },
          {
            "id": "trade_24",
            "entry_id": "Short",
            "entry_price": 4111.76,
            "exit_price": 4132.68,
            "profit": -20.920000000000073,
            "entry_time": 1791486000000,
            "exit_time": 1791493200000
          },
          {
            "id": "trade_25",
            "entry_id": "Long",
            "entry_price": 4132.68,
            "exit_price": 4173.18,
            "profit": 40.5,
            "entry_time": 1791493200000,
            "exit_time": 1791810000000
          },
          {
            "id": "trade_26",
            "entry_id": "Short",
            "entry_price": 4173.18,
            "exit_price": 4195.39,
            "profit": -22.210000000000036,
            "entry_time": 1791810000000,
            "exit_time": 1791878400000
          },
          {
            "id": "trade_27",
            "entry_id": "Long",
            "entry_price": 4195.39,
            "exit_price": 4166.89,
            "profit": -28.5,
            "entry_time": 1791878400000,
            "exit_time": 1791914400000
          },
          {
            "id": "trade_28",
            "entry_id": "Short",
            "entry_price": 4166.89,
            "exit_price": 4145.62,
            "profit": 21.270000000000437,
            "entry_time": 1791914400000,
            "exit_time": 1792047600000
          }
        ],
        "ledger": [
          {
            "entry_id": "Long",
            "entry_price": 4145.62,
            "entry_time": 1792047600000,
            "entry_bar_index": 463,
            "qty": 1
          }
        ],
        "position": {
          "size": 1,
          "direction": "long",
          "avg_price": 4145.62,
          "entry_name": "Long"
        },
        "stats": {
          "netprofit": -286.5100000000011,
          "grossprofit": 205.0599999999995,
          "grossloss": 491.5700000000006,
          "openprofit": 14.460000000000036,
          "max_drawdown": 393.01000000007934,
          "equity": 999727.95,
          "initial_capital": 1000000
        },
        "latest_signal": {
          "type": "long",
          "price": 4145.62,
          "time": 1792047600000,
          "active": true,
          "size": 1
        },
        "last_close": 4160.08
      }
    },
    "rsi_ema_trend": {
      "source_sha256": "ce747f0b2a767109cdda97708ec488071d38d59fd1d3ab25f722e63bc0399e8f",
      "python_order_count": 1,
      "python_orders": [
        {
          "bar_index": 230,
          "direction": "short",
          "entry_id": "Short",
          "sl": 4213.8170768368,
          "tp": 4122.8743847447995
        }
      ],
      "original": {
        "ok": true,
        "symbol": "XAUUSD",
        "timeframe": "60",
        "bars": 500,
        "plots": {
          "RSI": {
            "latest": 46.530969431,
            "recent": [
              57.4533699243,
              55.7024429381,
              54.3583882632,
              51.1853189447,
              59.9032434893,
              60.0119194321,
              50.1579097057,
              47.2142961925,
              48.3103078392,
              46.530969431
            ],
            "count": 500
          },
          "EMA": {
            "latest": 4160.9156865538,
            "recent": [
              4156.9198598872,
              4157.5939830289,
              4158.1542189886,
              4158.4838574596,
              4159.5221375592,
              4160.5298968706,
              4160.8118616992,
              4160.8408082993,
              4160.9497962091,
              4160.9156865538
            ],
            "count": 500
          },
          "ATR": {
            "latest": 15.6824575878,
            "recent": [
              15.1725342581,
              14.9052103825,
              14.6019810695,
              14.8811252788,
              16.3360449017,
              16.4498988373,
              16.6999060632,
              16.3363413444,
              15.9680312484,
              15.6824575878
            ],
            "count": 500
          }
        },
        "open_trades": [],
        "closed_trades": [],
        "ledger": [],
        "position": {
          "size": 0,
          "direction": "flat",
          "avg_price": null,
          "entry_name": ""
        },
        "stats": {
          "netprofit": 0,
          "grossprofit": 0,
          "grossloss": 0,
          "openprofit": 0,
          "max_drawdown": 0,
          "equity": 1000000,
          "initial_capital": 1000000
        },
        "latest_signal": null,
        "last_close": 4160.08
      },
      "transposed": {
        "ok": true,
        "symbol": "XAUUSD",
        "timeframe": "60",
        "bars": 500,
        "plots": {
          "Close": {
            "latest": 4160.08,
            "recent": [
              4177.07,
              4174.11,
              4171.88,
              4166.56,
              4184.96,
              4185.22,
              4167.72,
              4161.55,
              4163.62,
              4160.08
            ],
            "count": 500
          }
        },
        "open_trades": [],
        "closed_trades": [],
        "ledger": [],
        "position": {
          "size": 0,
          "direction": "flat",
          "avg_price": null,
          "entry_name": ""
        },
        "stats": {
          "netprofit": 0,
          "grossprofit": 0,
          "grossloss": 0,
          "openprofit": 0,
          "max_drawdown": 0,
          "equity": 1000000,
          "initial_capital": 1000000
        },
        "latest_signal": null,
        "last_close": 4160.08
      }
    }
  },
  "limitations": [
    "Bridge truncates closed_trades/ledger to last 20; EMA reports exactly 20 here and Python emits 21 reversal entries.",
    "No live MT5 access or trading; no TradingView performance/equivalence claim.",
    "Python calculations match installed PineTS SMA-seeded EMA, not first-price EMA.",
    "Node timeout is not a hostile-code security sandbox; use only trusted local strategy source."
  ]
}

