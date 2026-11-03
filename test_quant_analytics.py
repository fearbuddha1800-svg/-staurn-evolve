"""Offline quant contracts. Synthetic prices, fake broker, no orders/network."""
import json
import math
import statistics
from types import SimpleNamespace

import pytest

from quant_analytics import market_metrics, aligned_correlation, stop_risk, quant_snapshot


def bars(prices, start=1700000000, step=3600):
    return [[start+i*step, p, p+1, max(.01, p-1), p, 10] for i, p in enumerate(prices)]


def prices(n=140):
    out = [100.0]
    for i in range(n-1):
        out.append(out[-1] * (1 + ((i % 11)-5)*.001))
    return out


def test_drop_final_bar_and_real_price_drawdown():
    result = market_metrics('unit', bars([100, 120, 90, 110, 9999]), now=1800000000)
    assert result['bars'] == 4
    assert result['last_close'] == 110
    assert result['bar_return_pct'] == pytest.approx((110/90-1)*100)
    assert result['max_drawdown_pct'] == pytest.approx(25)
    assert result['historical_var95_pct'] is None
    assert not result['available']
    assert result['stale'] is True


def test_stats_match_independent_reference_and_tail_sample_count():
    p = prices(140)
    result = market_metrics('unit', bars(p), now=1700000000+140*3600)
    returns = [b/a-1 for a, b in zip(p[:-2], p[1:-1])]
    losses = sorted([-x for x in returns])
    n = len(returns)
    k = math.ceil(.05*n)
    assert result['available']
    assert result['returns'] == n
    assert result['volatility_per_bar_pct'] == pytest.approx(statistics.stdev(returns)*100)
    assert result['historical_var95_pct'] == pytest.approx(max(0, losses[math.ceil(.95*n)-1])*100)
    assert result['historical_es95_pct'] == pytest.approx(max(0, statistics.mean(losses[-k:]))*100)
    assert result['tail_samples'] == k
    assert result['historical_es95_pct'] >= result['historical_var95_pct']
    assert 'not a forecast' in ' '.join(result['warnings']).lower()
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -1, 0, True, 'bad'])
def test_invalid_close_never_silently_zero_filled(bad):
    data = bars(prices())
    data[12][4] = bad
    result = market_metrics('unit', data)
    assert not result['available']
    assert result['last_close'] is None
    assert result['historical_var95_pct'] is None
    json.dumps(result, allow_nan=False)


def test_duplicate_timestamps_rejected_and_unordered_bars_sorted():
    b = bars(prices())
    assert market_metrics('unit', list(reversed(b)))['available']
    b[5][0] = b[4][0]
    assert not market_metrics('unit', b)['available']


def test_empty_short_and_all_rising_data():
    assert not market_metrics('unit', [])['available']
    r = market_metrics('unit', bars([100+i for i in range(120)]))
    assert r['historical_var95_pct'] == 0
    assert r['historical_es95_pct'] == 0
    assert r['max_drawdown_pct'] == 0
    assert not market_metrics('unit', bars([100]))['available']


def test_correlation_exact_intervals_and_flat_variance():
    b = bars(prices())
    c = aligned_correlation('a', b, 'b', b)
    assert c['available']
    assert c['value'] == pytest.approx(1)
    assert c['n'] == len(b)-2
    shifted = bars(prices(), start=1700000001)
    assert not aligned_correlation('a', b, 'b', shifted)['available']
    assert not aligned_correlation('a', bars([100]*140), 'b', b)['available']
    # Missing earlier close means one same end timestamp is still a different interval.
    missing = b[:40] + b[41:]
    assert aligned_correlation('a', b, 'b', missing)['n'] == len(b)-4


def position(ticket=1, side=0, sl=95, current=100):
    return SimpleNamespace(ticket=ticket, type=side, symbol='UNIT', volume=1.,
                           price_current=current, price_open=98., sl=sl)


class Broker:
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    def __init__(self):
        self.calls = []
    def order_calc_profit(self, side, symbol, volume, entry, exit):
        self.calls.append((side, symbol, volume, entry, exit))
        return (exit-entry)*volume*10*(1 if side == 0 else -1)
    def order_send(self, *args, **kwargs):
        pytest.fail('order_send forbidden')


def test_stop_risk_uses_current_mark_broker_currency_and_both_sides():
    b = Broker()
    r = stop_risk(b, [position(), position(2, side=1, sl=105)], 1000, 'USD')
    assert r['available'] and r['risk_complete']
    assert r['current_stop_risk_money'] == pytest.approx(100)
    assert r['current_stop_risk_pct'] == pytest.approx(10)
    assert len(b.calls) == 2
    assert b.calls[0][3] == 100  # mark, not original entry
    assert r['currency'] == 'USD'


def test_unprotected_and_unpriced_never_reduce_total_to_zero():
    b = Broker()
    r = stop_risk(b, [position(), position(2, sl=0)], 1000)
    assert r['unprotected_tickets'] == [2]
    assert r['current_stop_risk_money'] is None
    assert r['known_stop_risk_money'] == 50
    assert not r['risk_complete']
    assert not r['available']
    assert stop_risk(b, None, 1000)['open_positions'] is None
    assert stop_risk(b, [], 1000)['current_stop_risk_money'] == 0
    b.order_calc_profit = lambda *args: float('nan')
    assert stop_risk(b, [position()], 1000)['unpriced_tickets'] == [1]
    assert stop_risk(b, [position()], 1000)['current_stop_risk_pct'] is None


@pytest.mark.parametrize('sl', [100, 101, float('nan'), float('inf')])
def test_invalid_or_crossed_stop_is_unknown(sl):
    r = stop_risk(Broker(), [position(sl=sl)], 1000)
    assert r['current_stop_risk_money'] is None
    json.dumps(r, allow_nan=False)


def test_snapshot_bounded_two_symbols_and_missing_broker():
    b = Broker()
    b.terminal_info = lambda: object()
    b.account_info = lambda: SimpleNamespace(balance=1000, currency='USD')
    b.positions_get = lambda: [position()]
    calls = []
    def candles(symbol, tf, n):
        calls.append((symbol, tf, n))
        return {'candles': bars(prices()), 'symbol': symbol}
    backend = SimpleNamespace(mt5=b, candles_data=candles)
    report = quant_snapshot(backend)
    assert report['available']
    assert len(calls) == 2
    assert all(c[1:] == ('H1', 501) for c in calls)
    assert report['risk']['current_stop_risk_money'] == 50
    assert len(report['market']) == 2
    json.dumps(report, allow_nan=False)
    b.positions_get = lambda: None
    assert quant_snapshot(backend)['risk']['open_positions'] is None
    b.terminal_info = lambda: None
    b.initialize = lambda: False
    unavailable = quant_snapshot(backend)
    assert unavailable['risk']['current_stop_risk_money'] is None
