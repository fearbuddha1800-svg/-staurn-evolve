---
slug: test_portfolio_risk
type: note
graph: gitnexus
---

"""Offline read-only broker doubles: never imports an execution engine."""
import json
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest
from portfolio_risk import portfolio_risk
from portfolio_attribution import versioned_attribution
from quant_analytics import stop_risk
from strategy_identity import StrategyIdentity


def broker():
    return NS(POSITION_TYPE_BUY=0, POSITION_TYPE_SELL=1, ORDER_TYPE_BUY=0,
              ORDER_TYPE_SELL=1,
              order_calc_profit=Mock(side_effect=lambda side, symbol, volume, mark, stop:
                                     (stop-mark) * volume * 100000 * (1 if side == 0 else -1)),
              symbol_info=Mock(return_value=NS(trade_calc_mode=0, currency_base='EUR',
                                               currency_profit='USD', trade_contract_size=100000)))


def position(ticket=1, volume=1, side=0, stop=1.09):
    return NS(ticket=ticket, symbol='EURUSD', volume=volume, type=side,
              sl=stop, price_current=1.1)


ACCOUNT = NS(balance=100000, currency='USD')


def test_unavailable_positions_not_empty_zero():
    data = portfolio_risk(broker(), None, ACCOUNT)
    assert data['total_open_risk_money'] is None
    assert data['unprotected_positions'] is None
    assert data['by_currency'] is None
    assert not data['available']


def test_unavailable_valuation_not_zero():
    b = broker()
    b.order_calc_profit.return_value = None
    b.order_calc_profit.side_effect = None
    data = portfolio_risk(b, [position()], ACCOUNT, {'max_total_open_risk_money': 100})
    assert data['total_open_risk_money'] is None
    assert data['concentration_largest_risk_share'] is None
    assert data['cap_breached'] is None
    assert data['risk']['unpriced_tickets'] == [1]


def test_unprotected_positions_surfaced_and_total_unknown():
    data = portfolio_risk(broker(), [position(stop=0)], ACCOUNT)
    assert data['unprotected_positions'] == 1
    assert data['risk']['unprotected_tickets'] == [1]
    assert data['total_open_risk_money'] is None


def test_known_concentration_cap_and_quant_parity():
    b = broker()
    rows = [position(1, 1), position(2, 3)]
    data = portfolio_risk(b, rows, ACCOUNT, {'max_total_open_risk_pct': 3})
    assert data['total_open_risk_money'] == pytest.approx(4000)
    assert data['concentration_largest_risk_share'] == pytest.approx(.75)
    assert data['risk'] == stop_risk(b, rows, ACCOUNT.balance, ACCOUNT.currency)
    assert data['cap_breached'] is True
    assert data['caps'][1]['breached'] is True
    assert 'guaranteed maximum loss' in ' '.join(data['methodology'])


def test_money_cap_boundary_and_position_cap():
    b = broker()
    risk = stop_risk(b, [position()], ACCOUNT.balance)['current_stop_risk_money']
    assert portfolio_risk(b, [position()], ACCOUNT, {'max_total_open_risk_money': risk})['cap_breached'] is False
    assert portfolio_risk(b, [position()], ACCOUNT, {'max_total_open_risk_money': risk-1})['cap_breached'] is True
    assert portfolio_risk(b, [position(), position(2)], ACCOUNT, {'max_open_positions': 1})['cap_breached'] is True


def test_unconfigured_cap_and_zero_risk_concentration_are_unknown():
    data = portfolio_risk(broker(), [], ACCOUNT)
    assert data['available']
    assert data['total_open_risk_money'] == 0
    assert data['cap_breached'] is None
    assert data['concentration_largest_risk_share'] is None


def test_directional_symbol_and_currency_exposure():
    data = portfolio_risk(broker(), [position(), position(2, .5, 1, 1.11)], ACCOUNT)
    assert data['by_symbol']['EURUSD'] == {'gross_lots': 1.5, 'net_lots': .5}
    assert data['by_currency']['EUR'] == {'gross_units': 150000, 'net_units': 50000}
    assert data['by_currency']['USD']['gross_units'] == pytest.approx(165000)
    assert data['by_currency']['USD']['net_units'] == pytest.approx(-55000)


def test_unsupported_contract_currency_exposure_not_zero():
    b = broker()
    b.symbol_info.return_value.trade_calc_mode = 1
    data = portfolio_risk(b, [position()], ACCOUNT)
    assert data['by_currency'] is None
    assert not data['exposure_complete']
    assert data['total_open_risk_money'] == pytest.approx(1000)
    assert len(data['unvalued_currency_exposures']) == 1


def test_broker_exception_is_defensive():
    b = broker()
    b.order_calc_profit.side_effect = RuntimeError('offline')
    data = portfolio_risk(b, [position()], ACCOUNT)
    assert data['available'] is False
    assert data['total_open_risk_money'] is None


def test_attribution_groups_id_and_version_not_just_id():
    registry = {1: StrategyIdentity('same', 'v1', 'algo', 'First', 1),
                2: StrategyIdentity('same', 'v2', 'algo', 'Second', 2),
                3: StrategyIdentity('other', 'v1', 'algo', 'Third', 3)}
    deals = [dict(magic=1, profit=10, commission=-1), dict(magic=2, profit=-5, swap=-1),
             dict(magic=1, profit=3, fee=-1), dict(magic=3, profit=2)]
    data = versioned_attribution(deals, registry)
    assert data['available']
    assert len(data['by_identity']) == 3
    assert data['by_identity'][json.dumps(['same', 'v1'], separators=(',', ':'))]['pl'] == 11
    assert data['by_identity']['["same","v2"]']['pl'] == -6
    assert data['total'] == {'count': 4, 'pl': 7}


def test_attribution_none_unknown_and_empty():
    assert versioned_attribution(None, {})['total'] is None
    assert versioned_attribution([], {})['total'] == {'count': 0, 'pl': 0}
    assert versioned_attribution([dict(magic=999, profit=2)], {})['unknown_magic'] == [999]

