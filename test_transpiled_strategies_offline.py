"""Pure fixture tests; no bridge process, broker, network or production DB."""
import math
import unittest

from pine_transpiled import EMACross, RSIEMATrend
from strategies.transpiled_strategies import (
    crossover, crossunder, ema, ema_cross_strategy, rsi, rsi_ema_trend_strategy,
)


class TranspiledStrategyTests(unittest.TestCase):
    def test_ema_aligned_sma_seed_for_installed_pinets(self):
        self.assertEqual(ema([1, 2, 3, 4, 5], 3), [None, None, 2.0, 3.0, 4.0])
        self.assertEqual(ema([1, 2], 3), [None, None])
        self.assertEqual(ema([], 3), [])

    def test_ema_period_one(self):
        self.assertEqual(ema([2, 4, 3], 1), [2.0, 4.0, 3.0])

    def test_invalid_periods(self):
        for period in (0, -1, True, 2.5, '3'):
            with self.subTest(period=period), self.assertRaises(ValueError):
                ema([1, 2, 3], period)

    def test_invalid_prices(self):
        for value in (True, '1', math.nan, math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ema_cross_strategy([1, value, 3], 1, 2)

    def test_crosses_only_on_latest_bar(self):
        self.assertFalse(crossover([0, 2, 3], [1, 1, 1]))
        self.assertFalse(crossunder([2, 0, -1], [1, 1, 1]))
        self.assertTrue(crossover([1, 2], [1, 1]))
        self.assertTrue(crossunder([1, 0], [1, 1]))

    def test_cross_missing_and_short_series(self):
        for fast, slow in ((None, None), ([], []), ([1], [1]), ([None, 2], [1, 1])):
            self.assertFalse(crossover(fast, slow))
            self.assertFalse(crossunder(fast, slow))
        with self.assertRaises(ValueError):
            crossover([1, 2], [1])

    def test_rsi_warmup_and_zero_loss(self):
        self.assertIsNone(rsi([1, 2, 3], 3))
        self.assertEqual(rsi([1, 2, 3, 4], 3), 100.0)
        self.assertEqual(rsi([4, 3, 2, 1], 3), 0.0)
        # This explicitly targets the installed PineTS zero-loss convention.
        self.assertEqual(rsi([1, 1, 1, 1], 3), 100.0)

    def test_rsi_sma_seed_not_double_counted(self):
        self.assertAlmostEqual(rsi([1, 3, 2, 4], 3), 80.0)
        self.assertAlmostEqual(rsi([1, 3, 2, 4, 2], 3), 50.0)

    def test_empty_strategies(self):
        result = ema_cross_strategy([])
        self.assertIsNone(result['signal'])
        self.assertEqual(result['fast_ema'], [])
        self.assertEqual(rsi_ema_trend_strategy([])['signals'], [])

    def test_no_stale_ema_entry(self):
        result = ema_cross_strategy([3, 2, 1, 2, 3, 4, 5], 1, 2)
        self.assertFalse(result['long_entry'])
        self.assertFalse(result['short_entry'])

    def test_ema_matches_canonical_bar_by_bar(self):
        closes = [100 + 9 * math.sin(i / 4) for i in range(120)]
        candles = [{'close': value} for value in closes]
        expected = EMACross(3, 7).evaluate(candles)
        actual = ema_cross_strategy(closes, 3, 7)
        self.assertEqual(actual['fast_ema'], expected['plots']['Fast EMA'])
        self.assertEqual(actual['slow_ema'], expected['plots']['Slow EMA'])
        orders = {o['bar_index']: o['direction'] for o in expected['orders']}
        for i in range(len(closes)):
            result = ema_cross_strategy(closes[:i + 1], 3, 7)
            self.assertEqual(result['long_entry'], orders.get(i) == 'long')
            self.assertEqual(result['short_entry'], orders.get(i) == 'short')

    def test_rsi_signal_only_does_not_invent_atr(self):
        result = rsi_ema_trend_strategy([100, 90, 80, 70, 80, 90], 2, 2)
        self.assertEqual(result['mode'], 'signal_only')
        self.assertEqual(result['atr_values'], [None] * 6)
        for row in result['signals']:
            self.assertIsNone(row['sl'])
            self.assertIsNone(row['tp'])
        # RSI crosses 35 on bar 4, but must not re-emit on bar 5.
        self.assertTrue(result['signals'][4]['long_entry'])
        self.assertFalse(result['signals'][5]['long_entry'])

    def test_rsi_ohlc_matches_canonical_and_preserves_pine_exits(self):
        closes = [100 + 9 * math.sin(i / 4) for i in range(120)]
        highs, lows = [p + 2 for p in closes], [p - 2 for p in closes]
        candles = [dict(close=c, high=h, low=l) for c, h, l in zip(closes, highs, lows)]
        expected = RSIEMATrend(3, 4, 3).evaluate(candles)
        actual = rsi_ema_trend_strategy(closes, 3, 4, 3, high_prices=highs, low_prices=lows)
        self.assertEqual(actual['mode'], 'offline_ohlc')
        for key, title in [('ema_values', 'EMA'), ('rsi_values', 'RSI'), ('atr_values', 'ATR')]:
            self.assertEqual(actual[key], expected['plots'][title])
        orders = {o['bar_index']: o for o in expected['orders']}
        self.assertTrue(orders, 'fixture must exercise entries and exits')
        for i, row in enumerate(actual['signals']):
            order = orders.get(i)
            self.assertEqual(row['long_entry'], bool(order and order['direction'] == 'long'))
            self.assertEqual(row['short_entry'], bool(order and order['direction'] == 'short'))
            if order:
                self.assertAlmostEqual(row['sl'], order['sl'])
                self.assertAlmostEqual(row['tp'], order['tp'])
            else:
                self.assertIsNone(row['sl'])
                self.assertIsNone(row['tp'])

    def test_ohlc_validation(self):
        for kwargs in ({'high_prices': [2, 3]},
                       {'high_prices': [2], 'low_prices': [0]},
                       {'high_prices': [0, 0], 'low_prices': [2, 3]}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                rsi_ema_trend_strategy([1, 2], **kwargs)

    def test_rsi_prefix_invariance(self):
        closes = [100 + 9 * math.sin(i / 4) for i in range(60)]
        full = rsi_ema_trend_strategy(closes, 3, 4, 3)
        for n in range(1, len(closes)):
            prefix = rsi_ema_trend_strategy(closes[:n], 3, 4, 3)
            self.assertEqual(prefix['signals'], full['signals'][:n])


if __name__ == '__main__':
    unittest.main()
