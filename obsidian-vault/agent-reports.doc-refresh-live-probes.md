---
slug: agent-reports.doc-refresh-live-probes
type: note
graph: gitnexus
---

{
  "observed_at": "2026-10-17T17:31:08.222848+00:00",
  "endpoints": {
    "state": {
      "http": 200,
      "data": {
        "account_mode": 0,
        "position_count": 4
      }
    },
    "neural": {
      "http": 200,
      "data": {
        "count": 2,
        "min_needed": 300,
        "ready": false,
        "progress": 0.0067,
        "collected_count": 3,
        "completed_count": 2,
        "pending_count": 1,
        "available": true,
        "count_basis": "completed labeled outcomes",
        "last_eval": null,
        "health": {
          "available": true,
          "report": {
            "timestamp": "2026-10-17T17:31:14Z",
            "db_path": "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\signals.db",
            "db_exists": true,
            "db_accessible": true,
            "label_counts": {
              "total": 3,
              "complete": 2,
              "pending": 1
            },
            "outcome_distribution": {
              "wins": 0,
              "losses": 2
            },
            "map_consistency": {
              "map_rows": 3,
              "tickets_without_label": [],
              "labels_without_ticket": [],
              "consistent": true
            },
            "feature_dims": {
              "checked": 3,
              "malformed_count": 0,
              "malformed": []
            },
            "accumulation_rate": {
              "first_ts": 1792045335.0,
              "last_ts": 1792187662.0,
              "span_seconds": 142327.0,
              "span_days": 1.65,
              "labels_per_day": 1.821,
              "note": "ok"
            },
            "trades_summary": {
              "broker_rejected": 2,
              "executed": 3
            },
            "gate": {
              "min_labels": 300,
              "distance_to_gate": 298,
              "gate_met": false
            },
            "labels": [
              {
                "id": 3,
                "ts": 1792045335.0,
                "symbol": "EURUSD",
                "side": "buy",
                "entry": 1.1224,
                "sl": 1.1174,
                "tp": 1.1274,
                "outcome": 0,
                "profit_r": -0.002
              },
              {
                "id": 2,
                "ts": 1792183227.0,
                "symbol": "XAUUSD",
                "side": "buy",
                "entry": 4159.94,
                "sl": 4144.07,
                "tp": null,
                "outcome": 0,
                "profit_r": -0.044108
              },
              {
                "id": 1,
                "ts": 1792187662.0,
                "symbol": "XAUUSD",
                "side": "buy",
                "entry": 4158.99,
                "sl": 4143.32,
                "tp": null,
                "outcome": null,
                "profit_r": null
              }
            ],
            "status": "accumulating"
          }
        }
      }
    },
    "identity": {
      "http": 200,
      "data": {
        "available": true,
        "identities": [
          {
            "magic": 0,
            "id": "manual",
            "version": "0.0.0",
            "kind": "manual",
            "label": "Manual / Other"
          },
          {
            "magic": 20261014,
            "id": "signal-relay",
            "version": "1.0.0",
            "kind": "signal",
            "label": "Telegram Signal Relay"
          },
          {
            "magic": 20261015,
            "id": "algo-engine",
            "version": "1.0.0",
            "kind": "algo",
            "label": "Algo Engine (RSI Pullback + London Breakout)"
          }
        ],
        "open_positions": [
          {
            "ticket": 58940515230,
            "symbol": "XAUUSD",
            "magic": 20261014,
            "strategy_id": "signal-relay",
            "version": "1.0.0",
            "label": "Telegram Signal Relay"
          },
          {
            "ticket": 58941113344,
            "symbol": "USDCAD",
            "magic": 0,
            "strategy_id": "manual",
            "version": "0.0.0",
            "label": "Manual / Other"
          },
          {
            "ticket": 58941115194,
            "symbol": "EURUSD",
            "magic": 0,
            "strategy_id": "manual",
            "version": "0.0.0",
            "label": "Manual / Other"
          },
          {
            "ticket": 58941116250,
            "symbol": "USDJPY",
            "magic": 0,
            "strategy_id": "manual",
            "version": "0.0.0",
            "label": "Manual / Other"
          }
        ],
        "note": "Attribution is by broker magic; magic 0 means opened outside the system."
      }
    },
    "portfolio": {
      "error": "HTTP Error 404: Not Found"
    },
    "candles?count=20": {
      "http": 200,
      "data": {
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "timestamp_basis": "broker as supplied",
        "last_bar_closed": null,
        "forming_bar_excluded": false,
        "closed_bar_basis": "final received bar assumed still forming; closure is never inferred from broker epochs vs local time",
        "last": 4168.77,
        "error": null,
        "bar_count": 20
      }
    },
    "events?limit=30&exclude=pnl_update": {
      "http": 200,
      "data": {
        "rows": 30,
        "pnl_update_rows": 0
      }
    }
  }
}

