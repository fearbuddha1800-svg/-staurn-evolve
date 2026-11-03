"""Read-only portfolio diagnostics. Stop estimates are NOT maximum possible losses.

Uses quant_analytics.stop_risk verbatim for mark-to-stop account-currency risk.
Directional exposures are native units, never summed across unlike currencies.
Only linear FX contracts support the two-currency notional decomposition here.
"""
from datetime import datetime, timezone
import math
from numbers import Real

from quant_analytics import stop_risk


def _positive(value):
    return (isinstance(value, Real) and not isinstance(value, bool)
            and math.isfinite(value) and value > 0)


def portfolio_risk(broker, positions, account, risk_config=None):
    """Defensive pure snapshot; inject an already attached read-only broker.

    Optional risk config keys: max_total_open_risk_money (account currency),
    max_total_open_risk_pct (% of balance), plus existing max_open_positions.
    Missing caps are unconfigured, NOT inferred from per-trade sizing/daily caps.
    """
    try:
        return _portfolio_risk(broker, positions, account, risk_config or {})
    except Exception as exc:
        return {'available': False, 'reason': 'Portfolio snapshot unavailable: ' + type(exc).__name__,
                'total_open_risk_money': None, 'cap_breached': None}


def _portfolio_risk(broker, positions, account, cfg):
    risk = stop_risk(broker, positions, getattr(account, 'balance', None),
                     getattr(account, 'currency', None))
    complete = risk['risk_complete'] and bool(getattr(account, 'currency', None))
    total = risk['current_stop_risk_money'] if complete else None
    concentration = None
    if total is not None and total > 0:
        concentration = max(p['stop_risk_money'] for p in risk['positions']) / total
    symbols, currencies, unknown = {}, {}, []
    def add_currency(currency, signed):
        rec = currencies.setdefault(currency, {'gross_units': 0.0, 'net_units': 0.0})
        rec['gross_units'] += abs(signed)
        rec['net_units'] += signed
    for p in positions if positions is not None else ():
        try:
            if not _positive(p.volume) or p.type not in (broker.POSITION_TYPE_BUY, broker.POSITION_TYPE_SELL):
                raise ValueError('Invalid position size or side')
            sign = 1 if p.type == broker.POSITION_TYPE_BUY else -1
            rec = symbols.setdefault(p.symbol, {'gross_lots': 0.0, 'net_lots': 0.0})
            rec['gross_lots'] += p.volume
            rec['net_lots'] += sign * p.volume
            info = broker.symbol_info(p.symbol)
            # MT5: 0=FOREX, 5=FOREX_NO_LEVERAGE. Do not pretend CFD/index
            # profit currencies imply a deliverable two-currency FX contract.
            if info is None or info.trade_calc_mode not in (0, 5):
                raise ValueError('Currency decomposition unsupported for non-FX or missing contract metadata')
            if not info.currency_base or not info.currency_profit or not _positive(info.trade_contract_size) or not _positive(p.price_current):
                raise ValueError('Missing currency, contract size or mark')
            base = p.volume * info.trade_contract_size
            add_currency(info.currency_base, sign * base)
            add_currency(info.currency_profit, -sign * base * p.price_current)
        except Exception as exc:
            unknown.append({'ticket': getattr(p, 'ticket', None), 'symbol': getattr(p, 'symbol', None),
                            'reason': str(exc)})
    exposures_complete = positions is not None and not unknown
    caps = []
    for key, observed in (('max_total_open_risk_money', total),
                          ('max_total_open_risk_pct', risk['current_stop_risk_pct'] if complete else None),
                          ('max_open_positions', risk['open_positions'])):
        value = cfg.get(key)
        configured = key in cfg
        valid = _positive(value)
        caps.append({'key': key, 'configured': configured, 'limit': value if valid else None,
                     'observed': observed, 'breached': observed > value if valid and observed is not None else None,
                     'reason': None if valid else ('Invalid configured cap' if configured else 'Not configured')})
    active = [c for c in caps if c['configured']]
    breached = (True if any(c['breached'] is True for c in active) else
                False if active and all(c['breached'] is False for c in active) else None)
    return {'available': complete and exposures_complete, 'observed_at': datetime.now(timezone.utc).isoformat(),
            'reason': None if complete and exposures_complete else 'Incomplete valuation or currency decomposition; null totals are unknown',
            'account_currency': getattr(account, 'currency', None), 'risk': risk,
            'total_open_risk_money': total, 'risk_complete': complete,
            'unprotected_positions': len(risk['unprotected_tickets']) if positions is not None else None,
            'concentration_largest_risk_share': concentration,
            'by_symbol': symbols if positions is not None else None,
            'by_currency': currencies if exposures_complete else None,
            'known_currency_exposure_subtotal': currencies if positions is not None else None,
            'exposure_complete': exposures_complete, 'unvalued_currency_exposures': unknown,
            'caps': caps, 'cap_breached': breached, 'broker_orders_enabled': False,
            'methodology': ['Stop risk: quant_analytics.stop_risk; current mark to native stop via read-only order_calc_profit in account currency.',
                            'Stop risk is an estimate, not a guaranteed maximum loss; excludes fees, gaps, slippage and execution uncertainty.',
                            'Symbol gross/net are lots within each symbol, not comparable notionals across symbols.',
                            'Currency gross/net are native FX units: signed lots x contract size in base, opposite mark-valued quote leg. Not account-currency equivalents.',
                            'CFDs, metals, indices and missing metadata remain unknown for currency decomposition.',
                            'Concentration is undefined for zero or incomplete total risk. Caps are diagnostics only; no trading guard is changed.']}
