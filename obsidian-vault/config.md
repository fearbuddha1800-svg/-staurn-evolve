---
slug: config
type: note
graph: gitnexus
---

{
  "mode": "auto",
  "notify_chat_id": "8877588890",
  "channels": [
    -1002369502254,
    -1001920020352,
    -1002165799093,
    -1001284268486,
    -1001207746934,
    -1001189068380,
    -1001175463265,
    -1003723702011,
    -1001713690419,
    -1003762554260,
    -1003011435611,
    -1003196282951,
    -1003576321949,
    -1002010239852,
    -1002620653001,
    -1003924380674,
    -1002520344727,
    -1002281357812,
    -1001248393106,
    -1002073061621,
    -1001601213792,
    -1001904158438,
    -1002698908514,
    -1001346757271,
    -1001127580919,
    -1003751867978,
    -1001095525244,
    -1002477522071,
    -1003629327586,
    -1003884507657,
    -1003376522019,
    -1002639725270,
    -1001932578394,
    -1003022356169,
    -1003034749723,
    -1003114012204,
    -1003811991226,
    -1001335852535,
    -1001715953952,
    -1001215049720
  ],
  "channels_note": "Fill with channel/group usernames or numeric IDs after first Telethon login (run: python daemon.py --list-dialogs). Signals are ONLY taken from chats listed here.",
  "risk": {
    "max_lot_per_trade": 0.1,
    "max_open_positions": 15,
    "max_trades_per_day": 20,
    "allowed_symbols": [],
    "allowed_symbols_note": "Empty list = all broker symbols allowed. Restrict e.g. [\"XAUUSD\", \"EURUSD\", \"BTCUSD\"] to trade only those.",
    "min_free_margin_pct": 30,
    "require_sl": true,
    "daily_loss_limit": 50
  },
  "sizing": {
    "mode": "risk_pct",
    "risk_pct": 1.0,
    "fallback_lot": 0.1,
    "note": "risk_pct sizes each trade so an SL hit loses ~risk_pct% of balance; falls back to fixed lot when a signal has no SL."
  },
  "manage": {
    "be_at_r": 0.8,
    "trail_from_r": 1.2,
    "trail_dist_r": 0.3,
    "secure_at_r": 2.0,
    "secure_lock_at_r": 1.0,
    "tp_levels": [
      {"id": "tp1", "r": 1.0, "close_pct": 50},
      {"id": "tp2", "r": 2.0, "close_pct": 100}
    ],
    "default_sl_distance": 30.0,
    "interval_s": 10,
    "broker_utc_offset_s": 10800,
    "broker_clock_note": "MetaQuotes-Demo tick epochs encode server UTC+3; measured across advancing XAUUSD/USDJPY/USDCAD ticks 2026-10-19. Subtract this explicit offset before the unchanged five-second freshness guard. Reverify after broker DST/server changes; never infer freshness from a single tick.",
    "note": "used by manage.py: SL moves to entry at +1R, then trails 0.5R behind price from +1.5R.",
    "adopt_tickets": [
      58944000186,
      58941113344,
      58941116250
    ],
    "adopt_note": "manual/other tickets adopted 2026-10-19 per user ownership grant; BE/trail same as managed magics"
  },
  "news_filter": {
    "enabled": true,
    "pre_minutes": 5,
    "post_minutes": 3,
    "note": "Blocks NEW entries (executor.execute) within pre/post minutes of any High-impact USD event. Calendar: news_calendar.json, refreshed every ~15 min by the watchdog via news_fetcher.py. Open positions, SLs and manage.py are never touched. Skip status: skipped_news_window."
  },
  "algo": {
    "symbols": [
      "XAUUSD",
      "EURUSD"
    ],
    "risk_pct": 1.0,
    "max_positions_total": 10,
    "daily_loss_cap_pct": 2.0,
    "rsi_buy": 35,
    "rsi_sell": 65,
    "atr_sl_mult": 2.0,
    "atr_tp_mult": 3.0,
    "use_tp": false,
    "strength": 1.0,
    "skip_hours_utc": [
      22,
      23
    ],
    "note": "Backtested 2023-2026 H1: XAUUSD +11.3R PF 1.12, EURUSD +10.2R PF 1.10 (SL-first conservative sim, 0.07R costs). GBPUSD excluded (negative). Exits via manage.py trailing.",
    "algo_entry_authority": true
  },
  "strategy2": {
    "enabled": true,
    "symbols": [
      "XAUUSD"
    ],
    "risk_pct": 0.5,
    "max_positions": 5,
    "algo_entry_authority": true
  },
  "paper_mode": false,
  "pine_strategies": [
    {
      "name": "RSI + EMA Trend",
      "path": "strategies/rsi_ema_trend.pine",
      "symbol": "XAUUSD",
      "timeframe": "H1",
      "enabled": true,
      "paper": true,
      "note": "Registered Pine strategy (PineTS). RUN is dry-run only: never places orders."
    },
    {
      "name": "EMA Cross Signals",
      "path": "strategies/ema_cross.pine",
      "symbol": "XAUUSD",
      "timeframe": "H1",
      "enabled": true,
      "paper": true,
      "note": "Registered Pine strategy (PineTS). RUN is dry-run only: never places orders."
    },
    {
      "name": "V01D AGI // VELA LUX QUANT",
      "path": "strategies/v01d_agi.pine",
      "symbol": "XAUUSD",
      "timeframe": "H1",
      "enabled": true,
      "paper": true,
      "note": "V01D AGI Pine Script v6 multi-engine strategy (PineTS). Dry-run only — never places orders."
    },
    {
      "name": "GOLDEN EYE | Trend / Regime",
      "path": "strategies/golden_eye_trend_regime.pine",
      "symbol": "XAUUSD",
      "timeframe": "H1",
      "enabled": true,
      "paper": true,
      "note": "GOLDEN EYE Trend/Regime v0.1 Pine Script v6 indicator (PineTS). Dry-run only — plots and diagnostics, never places orders."
    }
  ],
  "strategy_identities": {
    "signal-relay": {
      "id": "signal-relay",
      "version": "1.0.0",
      "kind": "signal",
      "label": "Telegram Signal Relay",
      "magic": 20261014,
      "note": "Legacy magic 20261014 - Telegram signal relay"
    },
    "algo-engine": {
      "id": "algo-engine",
      "version": "1.0.0",
      "kind": "algo",
      "label": "Algo Engine (RSI Pullback + London Breakout)",
      "magic": 20261015,
      "note": "Legacy magic 20261015 - algo engine"
    },
    "manual": {
      "id": "manual",
      "version": "0.0.0",
      "kind": "manual",
      "label": "Manual / Other",
      "magic": 0,
      "note": "Manual trades and unrecognized magic numbers"
    }
  },
  "pine_note": "Pine Script runner (dry run): strategies live in strategies/*.pine; register entries here with name/enabled/paper/path/symbol/timeframe. Signals are logged to signals.db only — no MT5 order is ever placed by this runner.",
  "ai": {
    "enabled": true,
    "min_confidence": 0.65,
    "provider": "openrouter",
    "model": "meta-llama/llama-3.3-70b-instruct:free",
    "timeout_s": 12,
    "max_concurrency": 2,
    "concurrency_timeout_s": 5,
    "budget_total": 500,
    "price_tolerance_pct": 0.6,
    "note": "Tier 2: Windows OCR on image signals + LLM extraction for hard-to-read text; invoked ONLY when the regex fast-path fails. Explicit OpenRouter free-model pin uses OPENROUTER_API_KEY from ~/.hermes/.env (key present; live availability unverified). Remove provider/model together to follow Hermes only when it selects a supported chat-completions API-key provider. OAuth subscriptions are not silently substituted. Dedupe window 10min; market-entry sanity vs live price."
  },
  "signal_policy": {
    "_default": {
      "mode": "auto"
    },
    "-1002165799093": {
      "sl_mode": "atr",
      "atr_mult": 2.0,
      "tp_mode": "none",
      "note": "XAUUSD FREE SIGNALS - exit-geometry validated: +0.963R expectancy after costs (V2-B)"
    },
    "-1002369502254": {
      "sl_mode": "channel",
      "atr_mult": 2.0,
      "tp_mode": "none",
      "note": "Best Signal Forex - V3-A: +0.924R after costs, 31 trades, 80.6% win, maxDD 2.26R - GO-LIVE variant A (channel SL)"
    },
    "-1001207746934": {
      "sl_mode": "channel",
      "atr_mult": 2.0,
      "tp_mode": "none",
      "note": "XAUHQ 🏛️ - V3-A: +0.579R after costs, 37 trades, 81.1% win, maxDD 2.14R - GO-LIVE variant A (channel SL)"
    },
    "-1002010239852": {
      "sl_mode": "channel",
      "tp_mode": "none",
      "note": "XAUUSD TRADING MASTER - full-sweep V2-A: +0.279R after costs, 30 trades (from archive)"
    },
    "-1002620653001": {
      "sl_mode": "atr",
      "tp_mode": "none",
      "note": "XAUUSD GOLD PRO TRADER - V3-B: +0.086R after costs, 33 trades, 57.6% win, maxDD 4.56R - GO-LIVE variant B (2x ATR SL)",
      "atr_mult": 2.0
    },
    "-1003924380674": {
      "sl_mode": "atr",
      "tp_mode": "none",
      "note": "FX SIGNAL TEAM - V3-B: +0.152R after costs, 24 trades, 58.3% win, maxDD 3.27R - GO-LIVE variant B (2x ATR SL)",
      "atr_mult": 2.0
    },
    "-1002520344727": {
      "sl_mode": "atr",
      "tp_mode": "none",
      "note": "GOLD PRO TRADER - V3-B: +0.096R after costs, 20 trades, 55.0% win, maxDD 3.27R - GO-LIVE variant B (2x ATR SL)",
      "atr_mult": 2.0
    },
    "-1003576321949": {
      "sl_mode": "atr",
      "atr_mult": 2.0,
      "tp_mode": "none",
      "note": "xauusd_signalsq - mass-verify V2-B: +0.303R after costs, 14 trades, 71.4% win"
    },
    "-1001713690419": {
      "sl_mode": "atr",
      "atr_mult": 2.0,
      "tp_mode": "none",
      "note": "Forex GDP Free - mass-verify V2-B: +0.281R after costs, 10 trades (mirror FX PREMIERE removed)"
    },
    "-1003196282951": {
      "sl_mode": "atr",
      "atr_mult": 2.0,
      "tp_mode": "none",
      "note": "GOLD FOREX SIGNALS VIP - mass-verify V2-B: +0.161R after costs, 47 trades (largest sample)"
    },
    "-1003762554260": {
      "sl_mode": "channel",
      "tp_mode": "none",
      "note": "Gold Signals Daily - verified POSITIVE EDGE variant A (+0.206R, 16 trades, 68.8% win) - switched from B to A"
    },
    "-1003723702011": {
      "sl_mode": "channel",
      "tp_mode": "none",
      "note": "FOREX GOLD SIGNALS XAUUSD - mass-verify V2-A: +0.126R after costs, 15 trades"
    },
    "-1001920020352": {
      "mode": "auto",
      "note": "Grow Trading - negative, recorded only"
    },
    "-1001284268486": {
      "mode": "auto",
      "note": "Easy Forex OFFICIAL - zero verifiable signals, recorded only"
    },
    "-1002281357812": {
      "mode": "auto",
      "note": "TYL - TRADING - new channel, shadow until verified"
    },
    "-1001248393106": {
      "mode": "auto",
      "note": "HIRN SIGNALS v7.8 - new channel, shadow until verified"
    },
    "-1002073061621": {
      "mode": "auto",
      "note": "Simple Forex Tools - new channel, shadow until verified"
    },
    "-1001601213792": {
      "sl_mode": "atr",
      "atr_mult": 2.0,
      "tp_mode": "none",
      "note": "XAUUSD GOLD PRO TRADER (alt ID) - VERIFIED POSITIVE EDGE variant B (+0.086R, 33 trades, 57.6% win) - promoted from shadow"
    },
    "-1001904158438": {
      "mode": "auto",
      "note": "MQL5 Algo Trading - new channel, shadow until verified"
    },
    "-1002698908514": {
      "mode": "auto",
      "note": "XAUUSD TRADING MASTERS - new channel, shadow until verified"
    },
    "-1001346757271": {
      "mode": "auto",
      "note": "Intelligent Trading Signals - new channel, shadow until verified"
    },
    "-1001127580919": {
      "mode": "auto",
      "note": "Whale Sniper - new channel, shadow until verified"
    },
    "-1003751867978": {
      "mode": "auto",
      "note": "Asterra Gold - verified NEGATIVE variant B (-0.182R, 37 trades) - keep shadow"
    },
    "-1001095525244": {
      "mode": "auto",
      "note": "GOLD Trader Dan - new channel, shadow until verified"
    },
    "-1002477522071": {
      "mode": "auto",
      "note": "PLATINUM .PICKS. - new channel, shadow until verified"
    },
    "-1003629327586": {
      "mode": "auto",
      "note": "Signal8 - new channel, shadow until verified"
    },
    "-1003884507657": {
      "mode": "auto",
      "note": "Certified Picks - new channel, shadow until verified"
    },
    "-1003376522019": {
      "sl_mode": "atr",
      "atr_mult": 2.0,
      "tp_mode": "none",
      "note": "XAUUSD GOLD SIGNALS - VERIFIED POSITIVE EDGE variant B (+0.080R, 15 trades, 53.3% win) - promoted from shadow"
    },
    "-1002639725270": {
      "sl_mode": "atr",
      "atr_mult": 2.0,
      "tp_mode": "none",
      "note": "PRO TRADER - VERIFIED POSITIVE EDGE variant B (+0.270R, 34 trades, 55.9% win) - promoted from shadow"
    },
    "-1001932578394": {
      "mode": "auto",
      "note": "Christopher Alan Harrison💪 - verified INSUFFICIENT DATA (n=6, tentatively POSITIVE variant B +0.069R) - keep shadow"
    },
    "-1003022356169": {
      "mode": "auto",
      "note": "Gold Signals (Free) - new channel, shadow until verified"
    },
    "-1003034749723": {
      "mode": "auto",
      "note": "Xauusd Trading Signals (Free) - new channel, shadow until verified"
    },
    "-1003114012204": {
      "mode": "auto",
      "note": "XAUUSD GOLD SIGNALS ®️ - new channel, shadow until verified"
    },
    "-1003811991226": {
      "mode": "auto",
      "note": "Forex Trading Signals (Free) - new channel, shadow until verified"
    },
    "-1001335852535": {
      "mode": "auto",
      "note": "GOLD Copy Trading - new channel, shadow until verified"
    },
    "-1001715953952": {
      "mode": "auto",
      "note": "Pockets of Rizdom 🧠 - new channel, shadow until verified"
    },
    "-1001215049720": {
      "sl_mode": "channel",
      "tp_mode": "none",
      "note": "UnitedSignals (Best Forex Signals) - full-sweep V2-A: +0.101R after costs, 46 trades, 52.2% win (verified POSITIVE EDGE)"
    }
  },
  "notes": {
    "mode": "auto = parse and execute immediately (risk-guarded). confirm = parse, post here, execute only after the user approves via the agent.",
    "kill_switch": "Create a file named HALT next to daemon.py (or ask the agent to do it) to stop new executions instantly. Delete it to resume.",
    "mt5_account": "Executes on whatever account is logged into the running MetaTrader 5 terminal. Currently: MetaQuotes-Demo."
  }
}

