---
slug: agent-reports.portfolio-live-responses
type: note
graph: gitnexus
---

{
  "portfolio": {
    "available": false,
    "observed_at": "2026-10-17T17:32:01.075904+00:00",
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
  "attribution": {
    "available": true,
    "total": {
      "count": 8,
      "pl": -0.08
    },
    "by_identity": {
      "[\"manual\",\"0.0.0\"]": {
        "id": "manual",
        "version": "0.0.0",
        "kind": "manual",
        "label": "Manual / Other",
        "magic": 0,
        "count": 3,
        "pl": 0.0,
        "magics": [
          0
        ]
      },
      "[\"signal-relay\",\"1.0.0\"]": {
        "id": "signal-relay",
        "version": "1.0.0",
        "kind": "signal",
        "label": "Telegram Signal Relay",
        "magic": 20261014,
        "count": 5,
        "pl": -0.08,
        "magics": [
          20261014
        ]
      }
    },
    "unknown_magic": [],
    "grouping": [
      "strategy_id",
      "version"
    ],
    "methodology": "MT5 BUY/SELL deals profit + commission + swap + fee, including entry costs; counts are deals, not trades. Current registry magic mapping only; shared legacy magic cannot distinguish underlying engines or historical versions.",
    "period_start": "2026-07-19T17:32:01.368959+00:00",
    "period_end": "2026-10-17T17:32:01.368959+00:00",
    "observed_at": "2026-10-17T17:32:01.368959+00:00",
    "account_currency": "USD",
    "broker_orders_enabled": false
  }
}

