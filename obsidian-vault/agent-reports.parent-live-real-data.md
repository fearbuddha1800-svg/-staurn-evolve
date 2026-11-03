---
slug: agent-reports.parent-live-real-data
type: note
graph: gitnexus
---

{
  "captured_at": "2026-10-17T17:48:53.264263+00:00",
  "base": "http://localhost:8490",
  "requested": 12,
  "ok": 12,
  "records": [
    {
      "path": "state",
      "status": 200,
      "content_type": "application/json; charset=utf-8",
      "bytes": 51848
    },
    {
      "path": "journal",
      "status": 200,
      "content_type": "application/json; charset=utf-8",
      "bytes": 7760
    },
    {
      "path": "mobile",
      "status": 200,
      "content_type": "text/html; charset=utf-8",
      "bytes": 4768
    },
    {
      "path": "neural",
      "status": 200,
      "content_type": "application/json; charset=utf-8",
      "bytes": 1472
    },
    {
      "path": "identity",
      "status": 200,
      "content_type": "application/json; charset=utf-8",
      "bytes": 1020
    },
    {
      "path": "portfolio",
      "status": 200,
      "content_type": "application/json; charset=utf-8",
      "bytes": 3009
    },
    {
      "path": "attribution",
      "status": 200,
      "content_type": "application/json; charset=utf-8",
      "bytes": 941
    },
    {
      "path": "inbox",
      "status": 200,
      "content_type": "application/json; charset=utf-8",
      "bytes": 954
    },
    {
      "path": "health",
      "status": 200,
      "content_type": "application/json; charset=utf-8",
      "bytes": 338
    },
    {
      "path": "strategies",
      "status": 200,
      "content_type": "application/json; charset=utf-8",
      "bytes": 659
    },
    {
      "path": "events?limit=3&exclude=pnl_update",
      "status": 200,
      "content_type": "application/json; charset=utf-8",
      "bytes": 2169
    },
    {
      "path": "candles?symbol=XAUUSD&timeframe=H1&count=30",
      "status": 200,
      "content_type": "application/json; charset=utf-8",
      "bytes": 2062
    }
  ],
  "account_snapshot": {
    "balance": 99999.92,
    "equity": 100011.13,
    "profit": 11.21,
    "trade_mode": 0
  },
  "positions_count": 4,
  "journal_snapshot": {
    "available": true,
    "events": [
      {
        "time": "2026-10-17T17:48:12.261259Z",
        "event": "engine_status",
        "detail": "{\"observed_at\": \"2026-10-17T17:48:12.174187+00:00\", \"transport\": \"streamable-http\", \"provenance\": \"http://localhost:3333/mcp\", \"trackers\": {\"available\": false, \"reason\": \"explicit dataset missing/not in discovery\", \"provenance\": \"trackers_datasets\", \"dataset\": null}, \"regime\": {\"available\": false, \"reason\": \"public-record counts are not a validated regime model\", \"provenance\": \"trackers_latest\"}, \"whale_options\": {\"available\": false, \"reason\": \"no market-wide options-flow tool; broker trades are owner activity\", \"provenance\": \"luxalgo-mcp-server/src/tools\"}, \"edge\": {\"available\": false, \"reason\": \"explicit symbol/preset missing/not in discovery\", \"provenance\": \"edge_symbols/edge_presets\", \"observed_at\": \"2026-10-17T17:48:12.174187+00:00\", \"edge_data\": {\"symbol\": null, \"preset\": null, \"alpha_decay\": null}, \"interpretation\": \"historical statistics only; no validated decay source\"}, \"catalog_available\": [\"edge_presets\", \"edge_symbols\", \"trackers_datasets\"], \"available\": true, \"trading_policy_changed\": false}",
        "event_id": "586c23242c71404fab093237ab114908",
        "trace_id": "e4e5f021201045fea84a7a6236847a39",
        "source": "luxalgo_orchestrator",
        "data_source": "signals.db:events",
        "payload_available": true,
        "timestamp_basis": "source includes UTC offset"
      },
      {
        "time": "2026-10-17T17:48:12.242792Z",
        "event": "luxalgo_edge_stats",
        "detail": "{\"observed_at\": \"2026-10-17T17:48:12.174187+00:00\", \"available\": false, \"reason\": \"explicit symbol/preset missing/not in discovery\", \"provenance\": \"edge_symbols/edge_presets\", \"edge_data\": {\"symbol\": null, \"preset\": null, \"alpha_decay\": null}, \"interpretation\": \"historical statistics only; no validated decay source\"}",
        "event_id": "95a30f1a06ad437cbdb2f4e962ae301a",
        "trace_id": "f8681a02bc544c179feb2053a887b2cf",
        "source": "luxalgo_orchestrator",
        "data_source": "signals.db:events",
        "payload_available": true,
        "timestamp_basis": "source includes UTC offset"
      },
      {
        "time": "2026-10-17T17:48:12.205625Z",
        "event": "luxalgo_whale_options",
        "detail": "{\"observed_at\": \"2026-10-17T17:48:12.174187+00:00\", \"available\": false, \"reason\": \"no market-wide options-flow tool; broker trades are owner activity\", \"provenance\": \"luxalgo-mcp-server/src/tools\"}",
        "event_id": "d13e54f45fa04385a31cd698547fdab5",
        "trace_id": "e08f1d88d80b44c99c6e8c190b994fb3",
        "source": "luxalgo_orchestrator",
        "data_source": "signals.db:events",
        "payload_available": true,
        "timestamp_basis": "source includes UTC offset"
      },
      {
        "time": "2026-10-17T17:48:12.174298Z",
        "event": "luxalgo_regime_shift",
        "detail": "{\"observed_at\": \"2026-10-17T17:48:12.174187+00:00\", \"available\": false, \"reason\": \"public-record counts are not a validated regime model\", \"provenance\": \"trackers_latest\"}",
        "event_id": "1c97b757407c407ea6f3de9f8e80da13",
        "trace_id": "57b33e4ad31a40e1ac7b6f9d9f8c48fc",
        "source": "luxalgo_orchestrator",
        "data_source": "signals.db:events",
        "payload_available": true,
        "timestamp_basis": "source includes UTC offset"
      },
      {
        "time": "2026-10-17T17:43:12.159941Z",
        "event": "alert",
        "detail": "positions_get() returned None (API error) - cycle skipped",
        "event_id": "eb72bb412d1e4abeba98b9777fe2d96f",
        "trace_id": "5e065e040e6a4f95a4c4245ef8be1544",
        "source": "manage",
        "data_source": "signals.db:events",
        "payload_available": true,
        "timestamp_basis": "source includes UTC offset"
      },
      {
        "time": "2026-10-17T17:43:02.151706Z",
        "event": "alert",
        "detail": "positions_get() returned None (API error) - cycle skipped",
        "event_id": "1f1733a170ca4eda840962a8ad3bca0c",
        "trace_id": "2bfbb8d93e2044798d2925140110e796",
        "source": "manage",
        "data_source": "signals.db:events",
        "payload_available": true,
        "timestamp_basis": "source includes UTC offset"
      },
      {
        "time": "2026-10-17T17:42:52.143261Z",
        "event": "alert",
        "detail": "positions_get() returned None (API error) - cycle skipped",
        "event_id": "648c620a7cd449a3b30f56b7b97fb325",
        "trace_id": "8f7d921e72b24681bdf5f1539a3cb146",
        "source": "manage",
        "data_source": "signals.db:events",
        "payload_available": true,
        "timestamp_basis": "source includes UTC offset"
      },
      {
        "time": "2026-10-17T17:42:42.139738Z",
        "event": "alert",
        "detail": "positions_get() returned None (API error) - cycle skipped",
        "event_id": "873771f1e54d495ea71f8bd454b94467",
        "trace_id": "d7e69bc2788146ae988f8fb0c89c2ed9",
        "source": "manage",
        "data_source": "signals.db:events",
        "payload_available": true,
        "timestamp_basis": "source includes UTC offset"
      },
      {
        "time": "2026-10-17T17:42:32.135511Z",
        "event": "alert",
        "detail": "positions_get() returned None (API error) - cycle skipped",
        "event_id": "90d3c411379c4ce9ac4edaf5dc9c9052",
        "trace_id": "5b4b35277a704b939d41a2826a06ac60",
        "source": "manage",
        "data_source": "signals.db:events",
        "payload_available": true,
        "timestamp_basis": "source includes UTC offset"
      },
      {
        "time": "2026-10-17T17:42:30.260946Z",
        "event": "engine_status",
        "detail": "{\"observed_at\": \"2026-10-17T17:42:30.239949+00:00\", \"transport\": \"streamable-http\", \"provenance\": \"http://localhost:3333/mcp\", \"trackers\": {\"available\": false, \"reason\": \"explicit dataset missing/not in discovery\", \"provenance\": \"trackers_datasets\", \"dataset\": null}, \"regime\": {\"available\": false, \"reason\": \"public-record counts are not a validated regime model\", \"provenance\": \"trackers_latest\"}, \"whale_options\": {\"available\": false, \"reason\": \"no market-wide options-flow tool; broker trades are owner activity\", \"provenance\": \"luxalgo-mcp-server/src/tools\"}, \"edge\": {\"available\": false, \"reason\": \"explicit symbol/preset missing/not in discovery\", \"provenance\": \"edge_symbols/edge_presets\", \"observed_at\": \"2026-10-17T17:42:30.239949+00:00\", \"edge_data\": {\"symbol\": null, \"preset\": null, \"alpha_decay\": null}, \"interpretation\": \"historical statistics only; no validated decay source\"}, \"catalog_available\": [\"edge_presets\", \"edge_symbols\", \"trackers_datasets\"], \"available\": true, \"trading_policy_changed\": false}",
        "event_id": "362524a0e72540d69c71124804d9b027",
        "trace_id": "6c20d846e5ce4648853bd4a325716517",
        "source": "luxalgo_orchestrator",
        "data_source": "signals.db:events",
        "payload_available": true,
        "timestamp_basis": "source includes UTC offset"
      },
      {
        "time": "2026-10-17T17:42:30.252119Z",
        "event": "luxalgo_edge_stats",
        "detail": "{\"observed_at\": \"2026-10-17T17:42:30.239949+00:00\", \"available\": false, \"reason\": \"explicit symbol/preset missing/not in discovery\", \"provenance\": \"edge_symbols/edge_presets\", \"edge_data\": {\"symbol\": null, \"preset\": null, \"alpha_decay\": null}, \"interpretation\": \"historical statistics only; no validated decay source\"}",
        "event_id": "732ab0064f3143c9a50cfd691aa2899a",
        "trace_id": "c6161b17e53847a09fa976178626f411",
        "source": "luxalgo_orchestrator",
        "data_source": "signals.db:events",
        "payload_available": true,
        "timestamp_basis": "source includes UTC offset"
      },
      {
        "time": "2026-10-17T17:42:30.243290Z",
        "event": "luxalgo_whale_options",
        "detail": "{\"observed_at\": \"2026-10-17T17:42:30.239949+00:00\", \"available\": false, \"reason\": \"no market-wide options-flow tool; broker trades are owner activity\", \"provenance\": \"luxalgo-mcp-server/src/tools\"}",
        "event_id": "c07ae3c06ac34c228e886529b4cdbf35",
        "trace_id": "1d48df21a08145cf91b41e5aba818830",
        "source": "luxalgo_orchestrator",
        "data_source": "signals.db:events",
        "payload_available": true,
        "timestamp_basis": "source includes UTC offset"
      }
    ],
    "data_source": "signals.db:events",
    "captured_at": "2026-10-17T17:48:30.715416+00:00",
    "order": "database arrival, newest first"
  },
  "mobile_fiction_detected": [],
  "mobile_has_freshness_warning": true,
  "portfolio_snapshot": {
    "available": false,
    "observed_at": "2026-10-17T17:48:38.958174+00:00",
    "reason": "Incomplete valuation or currency decomposition; null totals are unknown",
    "account_currency": "USD",
    "risk": {
      "available": true,
      "balance": 99999.92,
      "currency": "USD",
      "open_positions": 4,
      "protected_positions": 4,
      "unprotected_tickets": [],
      "current_stop_risk_money": 48.160000000000004,
      "known_stop_risk_money": 48.160000000000004,
      "current_stop_risk_pct": 0.04816003852803082,
      "risk_complete": true,
      "unpriced_tickets": [],
      "positions": [
        {
          "ticket": 58940515230,
          "symbol": "XAUUSD",
          "protected": true,
          "stop_risk_money": 25.45,
          "reason": null
        },
        {
          "ticket": 58941113344,
          "symbol": "USDCAD",
          "protected": true,
          "stop_risk_money": 6.37,
          "reason": null
        },
        {
          "ticket": 58941115194,
          "symbol": "EURUSD",
          "protected": true,
          "stop_risk_money": 9.39,
          "reason": null
        },
        {
          "ticket": 58941116250,
          "symbol": "USDJPY",
          "protected": true,
          "stop_risk_money": 6.95,
          "reason": null
        }
      ],
      "reason": null
    },
    "total_open_risk_money": 48.160000000000004,
    "risk_complete": true,
    "unprotected_positions": 0,
    "concentration_largest_risk_share": 0.5284468438538206,
    "by_symbol": {
      "XAUUSD": {
        "gross_lots": 0.01,
        "net_lots": 0.01
      },
      "USDCAD": {
        "gross_lots": 0.03,
        "net_lots": -0.03
      },
      "EURUSD": {
        "gross_lots": 0.03,
        "net_lots": 0.03
      },
      "USDJPY": {
        "gross_lots": 0.03,
        "net_lots": -0.03
      }
    },
    "by_currency": null,
    "known_currency_exposure_subtotal": {
      "USD": {
        "gross_units": 9371.79,
        "net_units": -9371.79
      },
      "CAD": {
        "gross_units": 4242.570000000001,
        "net_units": 4242.570000000001
      },
      "EUR": {
        "gross_units": 3000.0,
        "net_units": 3000.0
      },
      "JPY": {
        "gross_units": 474087.0,
        "net_units": 474087.0
      }
    },
    "exposure_complete": false,
    "unvalued_currency_exposures": [
      {
        "ticket": 58940515230,
        "symbol": "XAUUSD",
        "reason": "Currency decomposition unsupported for non-FX or missing contract metadata"
      }
    ],
    "caps": [
      {
        "key": "max_total_open_risk_money",
        "configured": false,
        "limit": null,
        "observed": 48.160000000000004,
        "breached": null,
        "reason": "Not configured"
      },
      {
        "key": "max_total_open_risk_pct",
        "configured": false,
        "limit": null,
        "observed": 0.04816003852803082,
        "breached": null,
        "reason": "Not configured"
      },
      {
        "key": "max_open_positions",
        "configured": true,
        "limit": 5,
        "observed": 4,
        "breached": false,
        "reason": null
      }
    ],
    "cap_breached": false,
    "broker_orders_enabled": false,
    "methodology": [
      "Stop risk: quant_analytics.stop_risk; current mark to native stop via read-only order_calc_profit in account currency.",
      "Stop risk is an estimate, not a guaranteed maximum loss; excludes fees, gaps, slippage and execution uncertainty.",
      "Symbol gross/net are lots within each symbol, not comparable notionals across symbols.",
      "Currency gross/net are native FX units: signed lots x contract size in base, opposite mark-valued quote leg. Not account-currency equivalents.",
      "CFDs, metals, indices and missing metadata remain unknown for currency decomposition.",
      "Concentration is undefined for zero or incomplete total risk. Caps are diagnostics only; no trading guard is changed."
    ]
  },
  "note": "Read-only API checks verify snapshots, not fresh weekend prices, fills, or live LLM availability."
}

