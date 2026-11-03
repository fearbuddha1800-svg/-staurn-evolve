---
slug: quant_analytics
type: note
graph: gitnexus
---

"""Read-only, source-labelled Quant HQ diagnostics (no execution or ML claims).

Closed observed-bar price statistics are not strategy performance, forecasts,
portfolio VaR, or trading recommendations. No annualization assumes 24/7 FX.
Stop loss valuation calls the broker's read-only order_calc_profit, never sends
or modifies an order. Unknown values stay null, including incomplete totals.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from numbers import Real
import statistics
import time

MIN_RETURNS = 100
SYMBOLS = ('XAUUSD', 'EURUSD')
METHODS = [
    'MT5 H1 closes, at most 500 completed observed bars; final received candle is conservatively excluded.',
    'Bar times are supplied by the broker, unadjusted; as_of is the raw broker epoch, not guaranteed UTC.',
    'Simple close-to-close price returns, including session gaps; these are not strategy or portfolio returns.',
    'Volatility is sample standard deviation per observed bar, not annualized. Drawdown is historical long-only price peak-to-trough.',
    'Historical VaR95 is nearest-rank 95% loss quantile; ES95 is the average worst ceil(5% × n) losses, floored at zero.',
    'Tail metrics require at least 100 returns and may use few tail observations. Historical estimates are not forecasts.',
    'Correlation uses identical start AND end timestamps; no interpolation, forward filling, or causal claim.',
    'Current-stop risk uses mark-to-stop order_calc_profit in account currency, before fees, gaps, slippage and stop execution uncertainty.',
    'Stale means last received closed bar is older than six clock hours; no exchange/session calendar is implied.',
    'No orders, risk changes, neural promotion or strategy activation are performed by this endpoint.',
]


def _number(value):
    return (not isinstance(value, bool) and isinstance(value, Real)
            and math.isfinite(float(value)))


def _closed(candles):
    """Validate rather than quietly imputing. Drop newest bar in one place."""
    if not isinstance(candles, (list, tuple)) or len(candles) > 1500:
        raise ValueError('Invalid or oversized candle collection')
    rows = []
    for c in candles:
        if not isinstance(c, (list, tuple)) or len(c) < 5:
            raise ValueError('Malformed candle')
        stamp, close = c[0], c[4]
        if not _number(stamp) or stamp <= 0 or int(stamp) != stamp:
            raise ValueError('Invalid broker bar timestamp')
        if not _number(close) or close <= 0:
            raise ValueError('Invalid nonpositive or nonfinite close')
        rows.append((int(stamp), float(close)))
    rows.sort()
    if len({t for t, _ in rows}) != len(rows):
        raise ValueError('Duplicate broker bar timestamp')
    return rows[:-1]  # never analyse a potentially forming last bar


def _interval_returns(rows):
    return {(a[0], b[0]): b[1]/a[1]-1 for a, b in zip(rows, rows[1:])}


def market_metrics(symbol, candles, now=None):
    result = {
        'symbol': symbol, 'timeframe': 'H1', 'bars': 0, 'returns': 0,
        'as_of': None, 'timestamp_basis': 'broker as supplied', 'stale': None,
        'last_close': None, 'bar_return_pct': None, 'volatility_per_bar_pct': None,
        'max_drawdown_pct': None, 'historical_var95_pct': None,
        'historical_es95_pct': None, 'tail_samples': 0, 'available': False,
        'reason': None, 'warnings': ['Historical sample estimates, not a forecast or strategy edge.'],
    }
    try:
        rows = _closed(candles)
    except (ValueError, TypeError, OverflowError) as exc:
        result['reason'] = str(exc)
        return result
    if not rows:
        result['reason'] = 'No completed bars available'
        return result
    result.update(bars=len(rows), last_close=rows[-1][1], as_of=rows[-1][0],
                  stale=(time.time() if now is None else now)-rows[-1][0] > 6*3600)
    returns = list(_interval_returns(rows).values())
    result['returns'] = len(returns)
    peak, drawdown = rows[0][1], 0.0
    for _, close in rows:
        peak = max(peak, close)
        drawdown = max(drawdown, 1-close/peak)
    result['max_drawdown_pct'] = drawdown * 100
    if returns:
        result['bar_return_pct'] = returns[-1] * 100
    if len(returns) < MIN_RETURNS:
        result['reason'] = f'Insufficient closed-bar returns ({len(returns)}/{MIN_RETURNS})'
        return result
    losses = sorted(-r for r in returns)
    n = len(losses)
    k = math.ceil(n*.05)
    result.update(available=True, volatility_per_bar_pct=statistics.stdev(returns)*100,
                  historical_var95_pct=max(0, losses[math.ceil(.95*n)-1])*100,
                  historical_es95_pct=max(0, statistics.mean(losses[-k:]))*100,
                  tail_samples=k)
    if k < 30:
        result['warnings'].append(f'Only {k} tail observations; estimates are unstable.')
    return result


def aligned_correlation(symbol_a, candles_a, symbol_b, candles_b):
    result = {'symbols': [symbol_a, symbol_b], 'n': 0, 'value': None,
              'available': False, 'reason': None, 'basis': 'exact observed-bar intervals'}
    try:
        a, b = _interval_returns(_closed(candles_a)), _interval_returns(_closed(candles_b))
    except (ValueError, TypeError, OverflowError) as exc:
        result['reason'] = str(exc)
        return result
    keys = sorted(a.keys() & b.keys())
    result['n'] = len(keys)
    if len(keys) < MIN_RETURNS:
        result['reason'] = f'Insufficient aligned returns ({len(keys)}/{MIN_RETURNS})'
        return result
    xs, ys = [a[k] for k in keys], [b[k] for k in keys]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    xx = math.fsum((x-mx)**2 for x in xs)
    yy = math.fsum((y-my)**2 for y in ys)
    if xx <= 0 or yy <= 0:
        result['reason'] = 'Correlation undefined for zero-variance returns'
        return result
    value = math.fsum((x-mx)*(y-my) for x, y in zip(xs, ys)) / math.sqrt(xx*yy)
    if not math.isfinite(value):
        result['reason'] = 'Nonfinite correlation'
        return result
    result.update(available=True, value=max(-1.0, min(1.0, value)))
    return result


def stop_risk(broker, positions, balance, currency=None):
    result = {
        'available': False, 'balance': float(balance) if _number(balance) and balance > 0 else None,
        'currency': currency, 'open_positions': None, 'protected_positions': None,
        'unprotected_tickets': [], 'current_stop_risk_money': None,
        'known_stop_risk_money': None, 'current_stop_risk_pct': None,
        'risk_complete': False, 'unpriced_tickets': [], 'positions': [], 'reason': None,
    }
    if positions is None:
        result['reason'] = 'Broker positions unavailable; empty account not assumed'
        return result
    result.update(open_positions=len(positions), protected_positions=0)
    total = 0.0
    for p in positions:
        stop = getattr(p, 'sl', None)
        protected = _number(stop) and stop > 0
        item = {'ticket': p.ticket, 'symbol': p.symbol, 'protected': protected,
                'stop_risk_money': None, 'reason': None}
        if not protected:
            item['reason'] = 'No valid native stop supplied by broker'
            result['unprotected_tickets'].append(p.ticket)
        else:
            result['protected_positions'] += 1
            try:
                side, mark, volume = p.type, p.price_current, p.volume
                if not _number(mark) or mark <= 0 or not _number(volume) or volume <= 0:
                    raise ValueError('Invalid current mark or volume')
                if side == broker.POSITION_TYPE_BUY:
                    order_type, valid = broker.ORDER_TYPE_BUY, stop < mark
                elif side == broker.POSITION_TYPE_SELL:
                    order_type, valid = broker.ORDER_TYPE_SELL, stop > mark
                else:
                    raise ValueError('Unknown position side')
                if not valid:
                    raise ValueError('Stop at/beyond current mark; valuation not reliable')
                pl = broker.order_calc_profit(order_type, p.symbol, volume, mark, stop)
                if not _number(pl) or pl > 0:
                    raise ValueError('Broker stop valuation unavailable or inconsistent')
                item['stop_risk_money'] = -float(pl)
                total += -float(pl)
            except (AttributeError, ValueError, TypeError, OSError):
                item['reason'] = 'Broker mark-to-stop valuation unavailable or invalid'
                result['unpriced_tickets'].append(p.ticket)
        result['positions'].append(item)
    result['known_stop_risk_money'] = total
    result['risk_complete'] = not result['unprotected_tickets'] and not result['unpriced_tickets']
    result['available'] = result['risk_complete']
    if result['risk_complete']:
        result['current_stop_risk_money'] = total
        if result['balance'] is not None:
            result['current_stop_risk_pct'] = total / result['balance'] * 100
    else:
        result['reason'] = 'Incomplete risk valuation; known subtotal is not the account total'
    return result


def quant_snapshot(backend):
    """One bounded observation. Backend supplies its read-only broker adapter."""
    now = time.time()
    data, markets = {}, []
    for symbol in SYMBOLS:
        try:
            received = backend.candles_data(symbol, 'H1', 501)
            if not isinstance(received, dict) or received.get('error'):
                raise ValueError('Candle source unavailable')
            data[symbol] = received.get('candles', [])
            m = market_metrics(received.get('symbol') or symbol, data[symbol], now)
        except (OSError, ValueError, TypeError, AttributeError):
            data[symbol] = []
            m = market_metrics(symbol, [], now)
            m['reason'] = 'MT5 candle source unavailable'
        markets.append(m)
    broker, account, positions = backend.mt5, None, None
    try:
        if broker.terminal_info():
            account, positions = broker.account_info(), broker.positions_get()
    except (AttributeError, OSError, ValueError, TypeError):
        pass
    risk = stop_risk(broker, positions, getattr(account, 'balance', None), getattr(account, 'currency', None))
    return {'observed_at': datetime.fromtimestamp(now, timezone.utc).isoformat(),
            'available': any(m['available'] for m in markets), 'market': markets,
            'correlation': aligned_correlation(SYMBOLS[0], data[SYMBOLS[0]], SYMBOLS[1], data[SYMBOLS[1]]),
            'risk': risk, 'methodology': METHODS, 'broker_orders_enabled': False}

## Links from
- [[cockpit]]
- [[portfolio_risk]]
- [[test_portfolio_risk]]
- [[test_quant_analytics]]
- [[test_redevelop_auxiliary]]
