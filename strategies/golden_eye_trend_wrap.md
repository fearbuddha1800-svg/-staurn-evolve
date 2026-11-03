# Golden Eye PineTS strategy companion

`golden_eye_trend_wrap.pine` retains the indicator's local Gaussian, adaptive DMI, SuperTrend ensemble and direction/regime/strength computation. It does not import or modify `golden_eye_trend_regime.pine`. MTF/vortex diagnostics, UDT state and the visual dashboard are excluded; they do not feed the retained trading scores.

## Trading rules

- Warmup: at least 120 bars with valid ATR and strength.
- Entry: confirmed bar, flat position, trend or expansion regime (1 or 3), strength >= 0.35 (configurable), and direction +1/-1.
- One fixed unit, no pyramiding; simulated entries processed on close.
- Initial stop: entry close minus/plus 2 x ATR(14).
- Each confirmed close ratchets the stop using close minus/plus 2 x ATR. The stop cannot widen. No take profit and no direction-flip market exit.
- Minimum symbol tick input defaults to 0.01 for the XAUUSD sample. Configure it for other instruments; the current provider lacks usable `syminfo.mintick` metadata.

## Run offline

From the signal-relay root:

```sh
node pinets_bridge.js strategies/golden_eye_trend_wrap.pine strategies/test_candles.json XAUUSD H1
node test_golden_eye_wrapper.js
```

`test_candles.json` is a deterministic **synthetic** 720-bar H1 OHLCV fixture, not MT5 or historical gold prices. It deliberately exercises multiple rising/falling segments. Do not interpret the resulting P&L as market performance.

Verified output: `ok: true`, 720 bars, four closed trades, one open short. The test checks copied-engine integrity, candle ordering/values, initial 2 ATR stops and 575 in-position stop-ratchet updates, plus unchanged indicator hash during execution.

## Compatibility

The bridge now preserves native v6 source in memory instead of applying the legacy v5 downgrade, which produced `Syntax error at 10:95: Expected RPAREN but got LBRACKET` for v6 `input.string(options=[...])`. H1 is normalized to Pine timeframe 60. Existing v5 scripts keep their legacy preprocessing path; no .pine source is downgraded on disk.

This validates trusted local PineTS execution, not TradingView fill parity or live broker trading. The companion is available for the existing file watcher/runner to select; this task does not register it, start a watcher, or send orders.
