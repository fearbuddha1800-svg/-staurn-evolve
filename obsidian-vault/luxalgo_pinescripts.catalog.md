---
slug: luxalgo_pinescripts.catalog
type: note
graph: gitnexus
---

[
  {
    "slug": "9-29-et-fair-price-reversal",
    "name": "9:29 ET Fair Price Reversal",
    "family": "trend",
    "description": "The 9:29 ET Fair Price Reversal identifies potential trend exhaustion and reversals based on the opening price action of the NQ futures contract. It monitors a significant ATR-based excursion from the 9:29 candle body, followed by a confirmable break of market structure. Traders use these signals to identify potential mean-reversion setups during the early market session, targeting failures of momentum following significant intraday price extensions.",
    "date_displayed": "2026-10-27",
    "url": "https://www.luxalgo.com/library/indicator/9-29-et-fair-price-reversal/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/n010tbbucqa84lksw1nz7t9q.png"
  },
  {
    "slug": "valid-bos-pullback",
    "name": "Valid BOS Pullback",
    "family": "market-structure",
    "description": "The Valid BOS Pullback indicator identifies trend continuations by filtering standard Break of Structure events through a retest requirement. It detects initial breakouts and waits for the price to pull back to the structural level before confirming the continuation if a new extreme is reached. This process helps traders avoid false breakouts and focus on higher probability continuation patterns by ensuring the structural level acts as support or resistance after the initial breach.",
    "date_displayed": "2026-10-07",
    "url": "https://www.luxalgo.com/library/indicator/valid-bos-pullback/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/iclsbsi3h5dhcll7rxy1ayod.png"
  },
  {
    "slug": "displacement-sweep-reversal",
    "name": "Displacement Sweep Reversal",
    "family": "smc-ict",
    "description": "The Displacement Sweep Reversal with FVG indicator detects liquidity sweeps followed by a structural reversal supported by significant price displacement and a Fair Value Gap. Traders use this tool to identify high probability entry zones by monitoring when price breaks a key swing level after a liquidity grab. The indicator highlights the entry window and FVG, helping users identify potential pullback trades that align with market structure shifts and algorithmic price delivery patterns.",
    "date_displayed": "2026-10-05",
    "url": "https://www.luxalgo.com/library/indicator/displacement-sweep-reversal/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/displacement-sweep-reversal-16b38381f2.png"
  },
  {
    "slug": "short-term-order-block-rejections",
    "name": "Short-Term Order Block Rejections",
    "family": "smc-ict",
    "description": "This indicator identifies short-term order blocks initiated by market structure shifts and monitors for price rejection signals within these zones. Traders use this tool to spot potential entry opportunities at structural extremes where momentum shifts have occurred. It incorporates structural filtering and ATR-based range assessments to minimize signals in consolidating or low-volatility conditions, helping users align their entries with broader market structural trends.",
    "date_displayed": "2026-10-05",
    "url": "https://www.luxalgo.com/library/indicator/short-term-order-block-rejections/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/short-term-order-block-rejections-8900cac5b9.png"
  },
  {
    "slug": "structure-volume-profile",
    "name": "Structure Volume Profile Setups",
    "family": "volume-orderflow",
    "description": "Structure Volume Profile Setups identifies market structure shifts using BOS and CHoCH to trigger trading opportunities. The indicator constructs volume profiles over the most recent trend leg, identifying the Point of Control as a primary entry zone. Traders use these retracement setups to target value areas or fixed ATR distances, supported by HTF trend filters and gap avoidance to ensure high quality execution.",
    "date_displayed": "2026-10-01",
    "url": "https://www.luxalgo.com/library/indicator/structure-volume-profile/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/structure-volume-profile-fbc9814a55.png"
  },
  {
    "slug": "amd-poc-trade-setup",
    "name": "AMD POC Trade Setup",
    "family": "smc-ict",
    "description": "This indicator identifies the Accumulation, Manipulation, and Distribution market structure. It detects a consolidation range, builds a volume profile to find the Point of Control, and tracks price sweeps beyond range extremes. A trade signal is triggered when price breaks the POC with momentum. The indicator plots the entry at the POC, the stop at the sweep-side range boundary, and the take profit at the opposite boundary, assisting traders in capturing potential market reversals.",
    "date_displayed": "2026-09-23",
    "url": "https://www.luxalgo.com/library/indicator/amd-poc-trade-setup/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/owgmj6j59pnduimh0u872i8d.png"
  },
  {
    "slug": "volatility-breakout",
    "name": "Volatility Breakout",
    "family": "volatility",
    "description": "Sets a buy trigger at the session open plus k times the prior range and a sell trigger the same distance below, Larry Williams' volatility breakout, with true range, average range and Crabel stretch as alternative bases. Each breakout is drawn as a trade with its stop and exit, optional NR4, NR7, inside-period or trend filters narrow the setups, and a dashboard compares breakout and quiet-day ranges.",
    "date_displayed": "2026-09-22",
    "url": "https://www.luxalgo.com/library/indicator/volatility-breakout/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/volatility-breakout-c7d33cce35.png"
  },
  {
    "slug": "spike-rules",
    "name": "Spike Rules",
    "family": "volume-orderflow",
    "description": "Detects Market Profile spikes, late-session breakouts beyond the day's range in the final 30 minutes, and applies Dalton's spike rules to the next open: beyond the spike is acceptance, inside it is weaker acceptance with the base to hold, beyond the base is rejection. Each read is tracked on 30-minute period closes, with a tally of how often reads held; an open inside the spike is only traded once a period closes through the base.",
    "date_displayed": "2026-09-17",
    "url": "https://www.luxalgo.com/library/indicator/spike-rules/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/spike-rules-e454ce4721.png"
  },
  {
    "slug": "arima-forecasts",
    "name": "ARIMA Forecasts",
    "family": "statistics",
    "description": "Fits ARIMA models to log price on closed bars only, choosing the order by AIC or by hand, and projects a labeled model forecast with prediction bands from the last closed bar. A one-bar-ahead forecast track, earlier forecast fans and out-of-sample diagnostics show how the model fared against a no-change forecast, so the bands can be read as an expected range rather than a call.",
    "date_displayed": "2026-09-16",
    "url": "https://www.luxalgo.com/library/indicator/arima-forecasts/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/arima-forecasts-3dd0390686.png"
  },
  {
    "slug": "no-wick-retest-levels",
    "name": "No-Wick Retest Levels",
    "family": "trend",
    "description": "The No-Wick Retest Levels indicator detects price levels formed by candles with little to no wick at the high or low, signaling strong directional momentum. When price returns to these levels, the indicator highlights a retest opportunity, filtered by a 1-minute EMA trend. Once a level is tapped, it manages an ATR-based trade setup with specific take-profit and stop-loss targets. Traders use this tool to identify high-interest zones where momentum was previously exhausted or confirmed.",
    "date_displayed": "2026-09-09",
    "url": "https://www.luxalgo.com/library/indicator/no-wick-retest-levels/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/tapy983ix98tutz3d15x9nzc.png"
  },
  {
    "slug": "bar-counting-h1-h2",
    "name": "Bar Counting H1/H2",
    "family": "market-structure",
    "description": "Numbers Al Brooks' pullback attempts bar by bar: H1 to H4 under bull pullbacks and L1 to L4 over bear rallies, counted once a bar makes a new trend extreme and closes beyond a rising or falling 20 EMA, and reset at each new trend extreme. Second entries trade on a stop one tick beyond the signal bar, and H2s or L2s that trigger and then break the signal bar's other end are marked failed.",
    "date_displayed": "2026-09-03",
    "url": "https://www.luxalgo.com/library/indicator/bar-counting-h1-h2/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/bar-counting-h1-h2-84236acb07.png"
  },
  {
    "slug": "churn",
    "name": "Churn",
    "family": "volume-orderflow",
    "description": "Churn flags heavy volume that buys clearly less price travel than the symbol's own volume-to-range relationship predicts, on single bars and in loud consolidations, skipping gap sessions and expiration Fridays. Each churn zone is boxed, graded as supply risk after an advance or demand lean after a decline, and resolved by the expanding-range break that names the winner.",
    "date_displayed": "2026-09-02",
    "url": "https://www.luxalgo.com/library/indicator/churn/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/churn-59897d29a1.png"
  },
  {
    "slug": "acd-method",
    "name": "ACD Method",
    "family": "time-seasonality",
    "description": "Draws Mark Fisher's ACD levels each session: the opening range, A and C levels offset by a share of the average daily range, and the prior session's pivot range. An A counts once closes hold beyond it for half the opening range, a return into the range marks a failed A, and a C after a failed A signals the reversal. Sessions are scored into a rolling number line.",
    "date_displayed": "2026-08-27",
    "url": "https://www.luxalgo.com/library/indicator/acd-method/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/acd-method-e6125e1b2a.png"
  },
  {
    "slug": "asia-sweep-reversals",
    "name": "Asia Sweep Reversals",
    "family": "time-seasonality",
    "description": "The Asia Session Range indicator helps traders identify liquidity zones established during the Asian trading session. It highlights session highs and lows and tracks breakouts or sweeps of these levels. It also integrates internal market structure analysis, identifying Break of Structure and Change of Character events. Traders use these signals to find high probability trade setups, complete with automated take profit and stop loss risk boxes based on structural triggers.",
    "date_displayed": "2026-08-26",
    "url": "https://www.luxalgo.com/library/indicator/asia-sweep-reversals/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/rg5dxw74xaw317cr0isrkf9k.png"
  },
  {
    "slug": "gann-method",
    "name": "Gann Method",
    "family": "trend",
    "description": "Applies W.D. Gann's toolkit to one swing at a time: a mechanical swing chart and its trend rule pick the anchor, angles are drawn from it at the anchor swing's own price-per-bar rate, the swing's range is divided into quarters, thirds and the 50% point, and the bar where elapsed time equals the swing's duration is marked, along with calendar-day counts from the anchor. Levels and dates are references for price to confirm.",
    "date_displayed": "2026-08-26",
    "url": "https://www.luxalgo.com/library/indicator/gann-method/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/gann-method-3003224a12.png"
  },
  {
    "slug": "dead-cat-bounce",
    "name": "Dead Cat Bounce",
    "family": "patterns",
    "description": "Detects Bulkowski's dead cat bounce event pattern: a one-day collapse of 15 to 70% (at least 3 ATR), the event trend low a few sessions later, then a rebound that stalls below the pre-event close. A close below the bounce's short-term low marks the rollover short, with the stop above the bounce high, the event low as first objective and its break confirming the pattern.",
    "date_displayed": "2026-08-19",
    "url": "https://www.luxalgo.com/library/indicator/dead-cat-bounce/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/dead-cat-bounce-4c2ad29f62.png"
  },
  {
    "slug": "value-area-reversion-signals",
    "name": "Value Area Reversion Signals",
    "family": "volume-orderflow",
    "description": "The Value Area Reversion Signals indicator helps traders identify potential market reversals by analyzing volume distribution. It generates an anchored volume profile, highlighting the Point of Control and Value Area. The indicator monitors price breakouts from these zones and flags reclaim signals when price returns to the Value Area with confirmation from engulfing candlestick patterns and volume momentum, suggesting that a preceding breakout move may be exhausting or failing.",
    "date_displayed": "2026-08-18",
    "url": "https://www.luxalgo.com/library/indicator/value-area-reversion-signals/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/value-area-reversion-signals-a53a9d0797.png"
  },
  {
    "slug": "abandoned-baby",
    "name": "Abandoned Baby",
    "family": "patterns",
    "description": "Detects the strict abandoned baby: a long trend candle, a doji whose whole range gaps clear of both neighbors, then a gap back that closes at least 30% into the first body, after a prior trend on a 10 EMA. Each pattern shades both gaps, plans an entry with the stop at the doji extreme and a 2R target, and tracks gap fills and outcomes in a dashboard.",
    "date_displayed": "2026-08-17",
    "url": "https://www.luxalgo.com/library/indicator/abandoned-baby/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/abandoned-baby-9c8399bf7a.png"
  },
  {
    "slug": "eqh-eql-fvg-breakouts",
    "name": "EQH/EQL FVG Breakouts",
    "family": "smc-ict",
    "description": "EQH/EQL identifies equal highs and equal lows, which function as key liquidity zones in the market. Traders use these patterns to spot potential breakout opportunities or to anticipate reactions once price sweeps these levels. The indicator tracks active zones and confirms significant breakout signals by requiring associated Fair Value Gaps and ATR-based strength filters. This provides a systematic way to monitor liquidity-dense areas and capture momentum following a breakout or sweep.",
    "date_displayed": "2026-08-17",
    "url": "https://www.luxalgo.com/library/indicator/eqh-eql-fvg-breakouts/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/eqh-eql-fvg-breakouts-2e2b01ec45.png"
  },
  {
    "slug": "higher-timeframe-stochastic-buckets",
    "name": "Higher Timeframe Stochastic Buckets",
    "family": "momentum",
    "description": "The Higher Timeframe Stochastic Buckets indicator visually highlights zones of market exhaustion by calculating stochastic values on a user defined higher timeframe. Traders use these buckets to identify potential overbought or oversold conditions, helping to spot reversal opportunities. The tool provides volume and delta data within these zones to gauge market sentiment and offers optional lower timeframe RSI signal confirmation for more precise trade setups.",
    "date_displayed": "2026-08-17",
    "url": "https://www.luxalgo.com/library/indicator/higher-timeframe-stochastic-buckets/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/higher-timeframe-stochastic-buckets-64996dce62.png"
  },
  {
    "slug": "momentum-thrust",
    "name": "Momentum Thrust",
    "family": "momentum",
    "description": "Detects momentum thrusts: a one to three bar burst that closes beyond a quiet base on expanded range, near its extreme, on heavy volume, while RSI swings through its midline. Thrusts late in an extended move are tagged as possible climaxes; initiation thrusts open a follow-through plan with an invalidation level and a short holding clock exit.",
    "date_displayed": "2026-08-14",
    "url": "https://www.luxalgo.com/library/indicator/momentum-thrust/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/momentum-thrust-3817fa3c74.png"
  },
  {
    "slug": "average-daily-range",
    "name": "Average Daily Range",
    "family": "volatility",
    "description": "The Average Daily Range indicator calculates the historical mean range of daily price movements to project expected price boundaries for the current session. Traders use this tool to identify potential support and resistance levels, define profit targets, or gauge the relative strength of the current day's price action. By comparing the live daily range against the calculated average, users can assess whether volatility is expanding or contracting relative to historical norms.",
    "date_displayed": "2026-08-12",
    "url": "https://www.luxalgo.com/library/indicator/average-daily-range/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/fouitbj6rkgzys1ng9q311l7.png"
  },
  {
    "slug": "mss-sweeps",
    "name": "MSS Sweeps",
    "family": "market-structure",
    "description": "MSS Sweeps identifies internal market structure liquidity sweeps, specifically targeting higher low and lower high pivot points. By calculating internal market structure breaks, the indicator isolates protected levels established after a trend confirmation. It alerts traders when these levels are swept and subsequently reclaimed, signaling potential continuation trades that align with established market structure. It is designed for traders utilizing structural order flow strategies.",
    "date_displayed": "2026-08-12",
    "url": "https://www.luxalgo.com/library/indicator/mss-sweeps/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/mss-sweeps-4ab137c729.png"
  },
  {
    "slug": "pdh-l-fvg-crt",
    "name": "PDH/L FVG (CRT)",
    "family": "smc-ict",
    "description": "The PDH/L FVG (CRT) indicator identifies key liquidity levels from previous daily highs and lows and combines them with Fair Value Gaps (FVG) to pinpoint potential institutional trading entries. By monitoring how price interacts with historical daily boundaries, this tool provides a systematic approach for traders to capture reversals following liquidity sweeps.",
    "date_displayed": "2026-08-11",
    "url": "https://www.luxalgo.com/library/indicator/pdh-l-fvg-crt/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/pdh-l-fvg-crt-a959b01460.png"
  },
  {
    "slug": "universal-signal-backtester",
    "name": "Universal Signal Backtester",
    "family": "risk-exits",
    "description": "The Universal Signal Backtester turns any signal into measurable results: predefined moving average crosses, crossovers of two external sources, or triggers piped in from your own scripts. It manages up to three take-profit and stop-loss levels, simulates spread and commission, and grades everything on a dashboard with Sharpe ratio, profit factor, and a time-based heatmap.",
    "date_displayed": "2026-08-06",
    "url": "https://www.luxalgo.com/library/indicator/universal-signal-backtester/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/universal-signal-backtester-6cee9a3668.png"
  },
  {
    "slug": "ltf-momentum-projection",
    "name": "LTF Momentum Projection",
    "family": "momentum",
    "description": "Projects a run of lower-timeframe candles beside your main chart, exposing the intra-bar action hidden inside the current chart candle. Thrust-and-exhaustion logic prints momentum-shift triangles on both the projection and the main chart, so scalpers can time entries from micro-structure without ever switching timeframes.",
    "date_displayed": "2026-08-04",
    "url": "https://www.luxalgo.com/library/indicator/ltf-momentum-projection/",
    "image_url": "https://luxalgo-images-production.s3.us-east-1.amazonaws.com/Screenshot 2026-06-04 at 3.13.58\u202fPM.png"
  },
  {
    "slug": "rsi-regime-filter",
    "name": "RSI Regime Filter",
    "family": "momentum",
    "description": "The RSI Regime Filter can validate classic RSI signals against a live classification of market conditions: with its regime filter enabled (off by default), divergences and overbought/oversold cues plot only when the selected method reads a neutral market. Four regime methods (RSI, EMA trend, ADX, or a composite vote), volume bubbles at extremes, and a context dashboard - for oscillator traders tired of fading runaway trends.",
    "date_displayed": "2026-08-04",
    "url": "https://www.luxalgo.com/library/indicator/rsi-regime-filter/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/rsi-regime-filter-836b39a4d0.png"
  },
  {
    "slug": "line-break",
    "name": "Line Break",
    "family": "meta-composition",
    "description": "Builds a three-line break chart from closes - the chart timeframe by default, where the live bar's line can appear or vanish until that bar closes and is fixed after, or confirmed closes from any higher timeframe - and draws it beside the last bar while stepped plots track the active line across chart time. Continuation and reversal trigger prices plot on the price chart and feed a dashboard, with alerts for new lines, turnarounds and 8-line extended runs.",
    "date_displayed": "2026-07-31",
    "url": "https://www.luxalgo.com/library/indicator/line-break/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/line-break-a7548447f2.png"
  },
  {
    "slug": "market-structure-scatter-dashboard",
    "name": "Market Structure & Scatter Dashboard",
    "family": "market-structure",
    "description": "Market Structure & Scatter Dashboard pairs BOS and CHoCH labels with a scatter plot that maps every price impulse against the pullback that followed, in percentage terms. Quadrant position and color-coded magnitude expose momentum shifts and overextension, while an optional heatmap paints candles with the live impulse and pullback readings.",
    "date_displayed": "2026-07-31",
    "url": "https://www.luxalgo.com/library/indicator/market-structure-scatter-dashboard/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/market-structure-scatter-dashboard-f430880f84.png"
  },
  {
    "slug": "elder-safezone-stop",
    "name": "Elder SafeZone Stop",
    "family": "risk-exits",
    "description": "Trails Alexander Elder's SafeZone stop: adverse penetrations averaged over a 20-bar lookback, multiplied by a 2.5 noise coefficient and hung from the previous bar's extreme, ratcheting so the trail never gives ground. Auto mode flips sides when the stop is hit, a dashboard reports the distance and level, and both stop hits carry alerts.",
    "date_displayed": "2026-07-29",
    "url": "https://www.luxalgo.com/library/indicator/elder-safezone-stop/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/elder-safezone-stop-7f6e209f03.png"
  },
  {
    "slug": "truncation",
    "name": "Truncation",
    "family": "elliott-harmonics",
    "description": "Detects truncated fifth waves (a five-wave impulse whose final wave stops short of the wave 3 extreme), validated against the Elliott hard rules and, by default, a five-wave subdivision inside wave 5. Shades the shortfall zone, draws confirmation at the wave 4 extreme and invalidation at wave 3, and reports divergence and volume evidence, with six alerts.",
    "date_displayed": "2026-07-29",
    "url": "https://www.luxalgo.com/library/indicator/truncation/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/truncation-381206a894.png"
  },
  {
    "slug": "volatility-signature-plot",
    "name": "Volatility Signature Plot",
    "family": "volatility",
    "description": "Plots realized volatility against sampling interval (six configurable points from 1 to 60 minutes, averaged over 20 completed days) as a curve beside price, diagnosing microstructure bias from the fine-end slope. Upward bias flags bid-ask bounce, downward bias stale quotes; the build suggests the finest flat sampling interval and alerts when the diagnosis changes.",
    "date_displayed": "2026-07-29",
    "url": "https://www.luxalgo.com/library/indicator/volatility-signature-plot/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/volatility-signature-plot-10ab01736d.png"
  },
  {
    "slug": "ascending-base",
    "name": "Ascending Base",
    "family": "patterns",
    "description": "Detects the O'Neil-style ascending base mechanically: three pullbacks of 10-20% with rising highs and lows over 40-85 bars, formed above a 50-period trend average. It outlines the structure with per-pullback depths, prints the buy level at the third-pullback high, demands 1.4x average volume on the breakout, and tracks a 7% stop after confirmation.",
    "date_displayed": "2026-07-28",
    "url": "https://www.luxalgo.com/library/indicator/ascending-base/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/ascending-base-37dcc0b6d4.png"
  },
  {
    "slug": "rising-falling-three-methods",
    "name": "Rising/falling Three Methods",
    "family": "patterns",
    "description": "Detects rising and falling three methods patterns with 2 to 5 middle candles contained inside the first candle's range, long first and resolution bodies at 1.2x a 14-bar average, and a 50-bar SMA trend filter by default. Draws the containment zone, labels completions R3M or F3M, and extends an invalidation level from the far end of the range, with three completion alerts.",
    "date_displayed": "2026-07-28",
    "url": "https://www.luxalgo.com/library/indicator/rising-falling-three-methods/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/rising-falling-three-methods-a77b53aca8.png"
  },
  {
    "slug": "structure-trend-dashboard",
    "name": "Structure & Trend Dashboard",
    "family": "market-structure",
    "description": "A multi-timeframe command center that labels BOS and CHoCH, highlights liquidity sweeps, and boxes fair value gaps while a compact table tracks whether higher- and lower-timeframe trends agree. Checkbox rows make alignment readable at a glance: made for traders who only take entries when their timeframes agree.",
    "date_displayed": "2026-07-28",
    "url": "https://www.luxalgo.com/library/indicator/structure-trend-dashboard/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/structure-trend-dashboard-ded3ec64c3.png"
  },
  {
    "slug": "gap-fill-breakouts",
    "name": "Gap Fill Breakouts",
    "family": "patterns",
    "description": "Tracks ATR-filtered fair value gaps as price works to fill them, shrinking each box to its unfilled remainder, and prints triangle signals when price breaks a structural pivot near an active gap. With breakout alerts built in, it suits traders who want imbalance and market structure aligned before acting on a break.",
    "date_displayed": "2026-07-27",
    "url": "https://www.luxalgo.com/library/indicator/gap-fill-breakouts/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/gap-fill-breakouts-7be4fc6dec.png"
  },
  {
    "slug": "gator-oscillator",
    "name": "Gator Oscillator",
    "family": "momentum",
    "description": "Plots the Alligator's line spreads as two mirrored histograms around zero (jaw minus teeth above, teeth minus lips below), built from Wilder-smoothed averages of median price at the original 13/8, 8/5 and 5/3 lengths and offsets. Columns color green as a side expands and red as it contracts, and a dashboard names the current feeding phase and how long it has lasted.",
    "date_displayed": "2026-07-27",
    "url": "https://www.luxalgo.com/library/indicator/gator-oscillator/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/gator-oscillator-bcdc88116e.png"
  },
  {
    "slug": "session-sweep-ifvg-rr",
    "name": "Session Sweep & iFVG RR",
    "family": "smc-ict",
    "description": "Session Sweep & iFVG RR automates a complete smart-money setup: it tracks a chosen session's high and low, validates liquidity sweeps that snap back inside the range, confirms entries on a trendline break, and draws a risk-reward box with stops from inverted fair value gaps or ATR - for traders who want the whole sequence handled by one tool.",
    "date_displayed": "2026-07-27",
    "url": "https://www.luxalgo.com/library/indicator/session-sweep-ifvg-rr/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/sga8xa2miq98ujyi2kfkn3ba.png"
  },
  {
    "slug": "the-range-indicator",
    "name": "The Range Indicator",
    "family": "volatility",
    "description": "Plots Jack Weinberg's TRI: each bar's true range over its close-to-close gain on up-closing bars, stochastic-normalized across 10 bars, smoothed by a 3-period EMA and bounded 0 to 100. Dashed thresholds at 80 and 20 separate churn extremes from efficient travel, and four alerts fire as the reading crosses either threshold in either direction.",
    "date_displayed": "2026-07-27",
    "url": "https://www.luxalgo.com/library/indicator/the-range-indicator/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/the-range-indicator-ef446af044.png"
  },
  {
    "slug": "cause-and-effect",
    "name": "Cause & Effect",
    "family": "wyckoff",
    "description": "Implements Wyckoff's law of cause and effect on a bar chart: trading ranges lasting 20+ bars inside a volatility-capped window are marked as the cause, and each breakout projects an objective zone by scaling the cause's size with the effect-to-cause ratios observed on that chart. Includes pending objectives, an effect path, six alerts, and a campaign dashboard.",
    "date_displayed": "2026-07-26",
    "url": "https://www.luxalgo.com/library/indicator/cause-and-effect/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/cause-and-effect-8e031bb445.png"
  },
  {
    "slug": "parabolic-phase",
    "name": "Parabolic Phase",
    "family": "market-structure",
    "description": "Confirms when a trend has bent into terminal acceleration: three consecutive impulse legs must each steepen by a 1.2 slope factor with rising structure and shrinking pullbacks, while price stretches to a 95th-percentile extreme from a 200-period average. Draws the steepening trendlines, tints the active phase, and marks the end with a labeled reason plus a 50% retracement level.",
    "date_displayed": "2026-07-25",
    "url": "https://www.luxalgo.com/library/indicator/parabolic-phase/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/parabolic-phase-329109b911.png"
  },
  {
    "slug": "channel-continuation",
    "name": "Channel Continuation",
    "family": "patterns",
    "description": "Detects corrective parallel channels inside a clear trend: least-squares parallels fitted through 5-bar pivots with at least two touches per side, a prior impulse of 3+ ATR, and a countertrend slope required by default. Decisive breaks project width and measured-move targets, while countertrend breaks and false breakouts trigger their own warnings.",
    "date_displayed": "2026-07-24",
    "url": "https://www.luxalgo.com/library/indicator/channel-continuation/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/channel-continuation-978d497bcd.png"
  },
  {
    "slug": "significant-breakout-levels-fvg",
    "name": "Significant Breakout Levels (FVG)",
    "family": "smc-ict",
    "description": "Significant Breakout Levels (FVG) plots pivot-based support and resistance, then only signals a break when the candle body clears an ATR-scaled strength test and a fair value gap confirms the direction. Green and red boxes flag validated breaks, gray boxes mark qualifying breaks of levels past their maximum age, and failed levels are cleared away, keeping the chart focused on high-conviction setups.",
    "date_displayed": "2026-07-24",
    "url": "https://www.luxalgo.com/library/indicator/significant-breakout-levels-fvg/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/significant-breakout-levels-fvg-d9bd1608b1.png"
  },
  {
    "slug": "buyback-blackout-windows",
    "name": "Buyback Blackout Windows",
    "family": "time-seasonality",
    "description": "Buyback Blackout Windows shades the recurring stretches when companies typically pause discretionary share repurchases: from 14 days before each fiscal quarter end until 2 days after results, using a 28-day estimated report lag or your own listed earnings dates. Entry and lift labels, a next-event projection and an in-versus-out return dashboard complete the overlay.",
    "date_displayed": "2026-07-23",
    "url": "https://www.luxalgo.com/library/indicator/buyback-blackout-windows/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/buyback-blackout-windows-1f7bfa0215.png"
  },
  {
    "slug": "cypher",
    "name": "Cypher",
    "family": "elliott-harmonics",
    "description": "Cypher detects bullish and bearish XABCD Cypher patterns from confirmed swings, validating the B retracement (0.382\u20130.618 of XA) and C extension (1.272\u20131.414) before projecting the D completion at the 0.786 retracement of the full XC swing. Completed patterns carry staged CD targets, an X stop line, and fourteen alerts spanning setup to final target.",
    "date_displayed": "2026-07-23",
    "url": "https://www.luxalgo.com/library/indicator/cypher/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/cypher-12e14665eb.png"
  },
  {
    "slug": "price-zone-oscillator",
    "name": "Price Zone Oscillator",
    "family": "volume-orderflow",
    "description": "Implements Khalil and Steckler's price-persistence gauge: a 14-period EMA of sign-flipped closes divided by an EMA of raw closes, plotted as a percentage swinging around zero. The authors' full zone map ships as defaults (+/-60 extremes, +/-40 trend thresholds and a +15 to -5 neutral band) with eight alerts spanning zero, threshold and zone events.",
    "date_displayed": "2026-07-23",
    "url": "https://www.luxalgo.com/library/indicator/price-zone-oscillator/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/price-zone-oscillator-cc9d6327d2.png"
  },
  {
    "slug": "correlation-trend-indicator",
    "name": "Correlation Trend Indicator",
    "family": "trend",
    "description": "John Ehlers' Correlation Trend Indicator computed as published: the Pearson correlation of the source against an ideal rising line across a 20-bar window, bounded between -1 and +1. Readings beyond the 0.5 threshold mark bullish or bearish trend regimes with an optional background tint, and alerts cover regime starts, the trendless state, and zero crosses.",
    "date_displayed": "2026-07-22",
    "url": "https://www.luxalgo.com/library/indicator/correlation-trend-indicator/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/correlation-trend-indicator-5fec1607f7.png"
  },
  {
    "slug": "dynamic-time-warping-similarity",
    "name": "Dynamic Time Warping Similarity",
    "family": "machine-learning",
    "description": "Searches history for the windows whose shape most resembles the last 30 bars, comparing z-normalized windows with dynamic time warping under a Sakoe-Chiba band. The closest non-overlapping analogs are boxed on the chart with optional aftermath zones showing what followed, ranked in a dashboard by DTW distance, with alerts when the best match crosses the strong-match threshold.",
    "date_displayed": "2026-07-22",
    "url": "https://www.luxalgo.com/library/indicator/dynamic-time-warping-similarity/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/dynamic-time-warping-similarity-dc29e42c90.png"
  },
  {
    "slug": "htf-swing-structure-signals",
    "name": "HTF Swing Structure Signals",
    "family": "market-structure",
    "description": "Labels BOS and CHoCH events, colors them by a higher timeframe EMA bias (gray when against it), and auto-draws a 50% retracement level after a CHoCH aligned with that bias. A triangle prints when price returns to that level, giving structure traders a rule-based pullback framework with adjustable pivot sensitivity and setup expiry.",
    "date_displayed": "2026-07-22",
    "url": "https://www.luxalgo.com/library/indicator/htf-swing-structure-signals/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/htf-swing-structure-signals-7307aa1e65.png"
  },
  {
    "slug": "measured-move",
    "name": "Measured Move",
    "family": "market-structure",
    "description": "Projects measured-move targets from confirmed swing structure: the A-B leg's size, in points or as a percentage ratio, projected from the correction end C into a target zone 10% of the projected distance wide. Labels report the target price and the implied reward-to-risk from C, finished second legs are measured against the projection, and six alerts track each construction.",
    "date_displayed": "2026-07-22",
    "url": "https://www.luxalgo.com/library/indicator/measured-move/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/measured-move-35b8f90574.png"
  },
  {
    "slug": "on-neck-in-neck-thrusting",
    "name": "On-neck / In-neck / Thrusting",
    "family": "patterns",
    "description": "Detects the three weak-rally continuation lines of a downtrend (on-neck closing near the prior low, in-neck marginally above the prior close, thrusting into the body but short of its midpoint) after a long dark candle, labels each with its recovery depth, and tracks each pattern, for up to 100 bars by default, to a confirmed break of the pattern low or an invalidating push above the second candle's high.",
    "date_displayed": "2026-07-20",
    "url": "https://www.luxalgo.com/library/indicator/on-neck-in-neck-thrusting/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/on-neck-in-neck-thrusting-01e7aa9744.png"
  },
  {
    "slug": "trading-range-position",
    "name": "Trading-range Position",
    "family": "wyckoff",
    "description": "Boxes confirmed trading ranges and reads where price sits inside them: the lowest subdivision fills as buy territory, the highest as sell territory, the middle as a no-trade zone, on a thirds or quarters grid. Edge bands span tested support and resistance, recovered pokes reset the effective extremes, and a dashboard plus ten alerts track position, tests and resolution.",
    "date_displayed": "2026-07-20",
    "url": "https://www.luxalgo.com/library/indicator/trading-range-position/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/trading-range-position-b645580881.png"
  },
  {
    "slug": "hanging-man",
    "name": "Hanging Man",
    "family": "patterns",
    "description": "Detects small-bodied candles near their session high with a lower shadow at least twice the body, printing only after the prior bar closes above a 50-bar advance average. Each detection draws a trigger at the body bottom and a stop at the pattern high, waits up to 3 bars for a confirming close, then keeps tracking the stop for 20 more, with alerts at every stage.",
    "date_displayed": "2026-07-19",
    "url": "https://www.luxalgo.com/library/indicator/hanging-man/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/hanging-man-e5f334514c.png"
  },
  {
    "slug": "pretty-good-oscillator",
    "name": "Pretty Good Oscillator",
    "family": "momentum",
    "description": "Expresses the close's distance from its 89-period simple moving average in units of smoothed true range, so stretch readings stay comparable across instruments and volatility regimes. Dashed thresholds at +3 and -3 frame the breakout reads of Johnson's original long-term system, with alerts on both threshold breaks and zero-line crosses in either direction.",
    "date_displayed": "2026-07-19",
    "url": "https://www.luxalgo.com/library/indicator/pretty-good-oscillator/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/pretty-good-oscillator-1e44cc347b.png"
  },
  {
    "slug": "belt-hold",
    "name": "Belt Hold",
    "family": "patterns",
    "description": "Belt Hold scans for bullish and bearish belt hold candles: a long real body opening at, or essentially at, its session extreme against a 14-bar trend and closing at least halfway into the prior candle's range. Each pattern is labeled, its opening extreme extends forward as a dashed invalidation level, and optional next-bar confirmation tightens the signal.",
    "date_displayed": "2026-07-18",
    "url": "https://www.luxalgo.com/library/indicator/belt-hold/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/belt-hold-1eea21e29f.png"
  },
  {
    "slug": "ascending-descending-symmetrical-triangle",
    "name": "Ascending/Descending/Symmetrical Triangle",
    "family": "patterns",
    "description": "Detects classical triangles from confirmed swings and names each one: ascending (flat ceiling over rising lows), descending (flat floor under falling highs) or symmetrical. Boundaries need proven touches with every close contained and genuine contraction; a decisive close through either side before the apex completes the pattern, then the widest-height target, a stop and false-breakout and apex-drift rules manage it.",
    "date_displayed": "2026-07-16",
    "url": "https://www.luxalgo.com/library/indicator/ascending-descending-symmetrical-triangle/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/ascending-descending-symmetrical-triangle-347c10aed7.png"
  },
  {
    "slug": "futures-roll-dates",
    "name": "Futures Roll Dates",
    "family": "time-seasonality",
    "description": "Tracks the futures roll from the chart's own root: front and next contract volume print side by side with open interest lines, the scheduled window ahead of quarterly or monthly expirations is shaded, and markers stamp the day volume leadership passes and the day open interest migrates. A dashboard adds the roll spread, curve state and a front OI collapse check, plus splice-gap warnings on continuous charts.",
    "date_displayed": "2026-07-11",
    "url": "https://www.luxalgo.com/library/indicator/futures-roll-dates/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/futures-roll-dates-5beb2fc6ff.png"
  },
  {
    "slug": "reflex-trendflex",
    "name": "Reflex/Trendflex",
    "family": "momentum",
    "description": "Plots Ehlers' Reflex and Trendflex from a SuperSmoother-filtered source over a 20-bar window: Reflex averages deviations from a straight-line ramp to isolate cycle swings, Trendflex from the current filter level to keep the trend read. Both self-normalize so 2 marks a typical extreme, with optional divergence drawings and eight alerts covering zero crosses, trend-aligned signals and divergences.",
    "date_displayed": "2026-07-11",
    "url": "https://www.luxalgo.com/library/indicator/reflex-trendflex/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/reflex-trendflex-27d654823e.png"
  },
  {
    "slug": "three-white-soldiers",
    "name": "Three White Soldiers",
    "family": "patterns",
    "description": "Detects three white soldiers after a decline: three long white candles, each opening in the prior body and closing near its high, with body, shadow and similarity rules. Each signal plans a pullback entry at the pattern midpoint, a stop at the pattern low and a 2R target, flags extended patterns and swing high breaks, labels advance block and stalled warnings, and logs follow-through.",
    "date_displayed": "2026-07-10",
    "url": "https://www.luxalgo.com/library/indicator/three-white-soldiers/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/three-white-soldiers-80c6d6d593.png"
  },
  {
    "slug": "mss-sweep-fib-retrace",
    "name": "MSS Sweep Fib Retrace",
    "family": "market-structure",
    "description": "Chains three institutional footprints into one setup: a sweep of a prior swing level, a momentum-confirmed market structure shift, and a pullback to the 50% retracement of the sweep leg. Entries print with ATR-sized stop and target zones, and an optional 200 EMA macro filter limits signals to reversals against the higher trend (long setups start below the EMA, short setups above it). For traders who wait for confirmation rather than the first break.",
    "date_displayed": "2026-07-09",
    "url": "https://www.luxalgo.com/library/indicator/mss-sweep-fib-retrace/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/mss-sweep-fib-retrace-a926eb9129.png"
  },
  {
    "slug": "spike-and-channel",
    "name": "Spike and Channel",
    "family": "patterns",
    "description": "Detects Al Brooks' spike and channel trend: a spike of consecutive strong trend bars with little overlap, the pullback whose extreme starts the channel, and a channel of at least two legs at a shallower slope than the spike. A trendline break followed by a failed test of the trend extreme marks the channel end and plans the countertrend trade back to the channel start.",
    "date_displayed": "2026-07-09",
    "url": "https://www.luxalgo.com/library/indicator/spike-and-channel/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/spike-and-channel-3005bda049.png"
  },
  {
    "slug": "premium-and-discount",
    "name": "Premium & Discount Dealing Range",
    "family": "smc-ict",
    "description": "Anchors the dealing range on the leg that last broke structure, splits it at equilibrium and shades premium above and discount below, with 25/75% quadrants and the 62-79% OTE band. The range ratchets on a BOS and flips on a CHoCH. Marks flag the first trade into discount in bullish ranges (premium in bearish ones), and a dashboard reads price position from 0 to 100%.",
    "date_displayed": "2026-07-08",
    "url": "https://www.luxalgo.com/library/indicator/premium-and-discount/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/premium-and-discount-c052bbfc8a.png"
  },
  {
    "slug": "crt-sweep-setup-highlighter",
    "name": "CRT Sweep & Setup Highlighter",
    "family": "smc-ict",
    "description": "Projects the previous higher-timeframe range's high and low, flags a sweep after a candle breaks one of those levels and closes back inside the range, and requires a Fair Value Gap or Market Structure Shift before confirming the setup with projected entry, stop, and target zones. A rules-based workflow for traders who fade liquidity grabs at HTF extremes.",
    "date_displayed": "2026-07-06",
    "url": "https://www.luxalgo.com/library/indicator/crt-sweep-setup-highlighter/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/crt-sweep-setup-highlighter-5ba9a57097.png"
  },
  {
    "slug": "gravestone-doji",
    "name": "Gravestone Doji",
    "family": "patterns",
    "description": "Flags inverted-T candles where the body is at most 5% of the range, the lower shadow no more than 10%, and the upper shadow at least twice the body and one 14-period ATR, by default only after price closes above a 50-bar trend average. Dashed trigger and stop levels track each pattern through a 3-bar confirmation window, with alerts on detection, confirmation and invalidation.",
    "date_displayed": "2026-07-06",
    "url": "https://www.luxalgo.com/library/indicator/gravestone-doji/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/gravestone-doji-c109ad2315.png"
  },
  {
    "slug": "market-structure-fibonacci-zones-rr",
    "name": "Market Structure & Fibonacci Zones + RR",
    "family": "market-structure",
    "description": "Market Structure & Fibonacci Zones + RR detects breaks of structure, projects a Fibonacci zone between the 38.2% and 50% retracement behind each one, and waits for price to confirm inside the zone before drawing an automatic risk/reward box: stop at the origin of the trend, target at your chosen ratio. A complete, systematic pullback-entry workflow on a single chart.",
    "date_displayed": "2026-07-06",
    "url": "https://www.luxalgo.com/library/indicator/market-structure-fibonacci-zones-rr/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/market-structure-fibonacci-zones-rr-9fb78b54f7.png"
  },
  {
    "slug": "polarized-fractal-efficiency",
    "name": "Polarized Fractal Efficiency",
    "family": "momentum",
    "description": "Scores how efficiently price traveled across a 10-bar window, smoothed by a 5-period EMA and signed by the net direction: readings near +100 or -100 mark one-way trends, values hovering near zero mark chop. Dashed trending levels at +/-50 anchor regime and decay events, with six alerts covering zero crosses, regime starts and efficiency decay on both sides.",
    "date_displayed": "2026-07-05",
    "url": "https://www.luxalgo.com/library/indicator/polarized-fractal-efficiency/",
    "image_url": "https://luxalgo-production.s3.amazonaws.com/library/cards/polarized-fractal-efficiency-38feebc616.png"
  },
  {
    "slug": "reclaimed-order-block",
    "name": "Reclaimed Order Block",
    "family": "smc-ict",
    "description": "Builds order blocks from displacement moves, then flags reclaims: zones defended again after a prior respect, or recovered after price closed through them without full acceptance. Confirmation de

... (truncated, 617002 total bytes) ...

