---
slug: test_stop_legality
type: note
graph: gitnexus
---

"""Offline planning + read-back tests. No MT5 import or submission path."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace as NS

import pytest
from stop_legality import (StopChange, assess_stop_change, classify_stop_change,
                           confirm_stop_change, plan_position_stop)


class Broker:
    POSITION_TYPE_BUY, POSITION_TYPE_SELL = 0, 1

    def __init__(self):
        self.info = NS(point=.01, trade_stops_level=10, trade_freeze_level=0,
                       trade_tick_size=.01)
        self.tick = NS(bid=100, ask=100.02, time=1000, time_msc=1000000)
        self.positions = [NS(ticket=42, symbol='TEST', type=0, sl=99, tp=0)]

    def symbol_info(self, symbol):
        return self.info

    def symbol_info_tick(self, symbol):
        return self.tick

    def positions_get(self, **kwargs):
        return self.positions


@pytest.fixture
def broker():
    return Broker()


def assess(broker, side='BUY', old=99, new=99.8, **kwargs):
    return assess_stop_change(broker, 'TEST', side, old, new, now=1001, **kwargs)


@pytest.mark.parametrize('side,old,new', [('BUY', 99, 99.95), ('SELL', 101, 100.05)])
def test_inside_stops_level_rejected(broker, side, old, new):
    d = assess(broker, side, old, new)
    assert not d.should_apply and 'trade_stops_level' in d.reason


def test_missing_tick_rejected(broker):
    broker.tick = None
    assert 'missing tick' in assess(broker).reason
    assert not assess(broker).allowed


@pytest.mark.parametrize('time_msc', [995999, 1002000, -1])
def test_stale_future_invalid_tick_rejected(broker, time_msc):
    broker.tick.time_msc = time_msc
    assert not assess(broker).allowed
    assert 'stale or future' in assess(broker).reason


def test_age_boundary_and_seconds_fallback(broker):
    broker.tick.time_msc = 996000
    assert assess(broker).allowed  # exactly max age is fresh
    broker.tick.time_msc = 0
    broker.tick.time = 995
    assert not assess(broker).allowed
    broker.tick.time = 1000
    assert assess(broker).allowed


@pytest.mark.parametrize('side,old,new', [('BUY', 99, 99.8), ('SELL', 101, 100.2)])
def test_tighten_allowed_both_sides(broker, side, old, new):
    d = assess(broker, side, old, new)
    assert d.allowed and d.should_apply and d.change == StopChange.TIGHTEN
    assert not d.requires_widen_opt_in
    assert 'not broker-confirmed' in d.reason


@pytest.mark.parametrize('side,old,new', [('BUY', 99, 98), ('SELL', 101, 102),
                                        ('BUY', 99, 0), ('SELL', 101, 0)])
def test_widen_always_flagged_requires_explicit_opt_in(broker, side, old, new):
    d = assess(broker, side, old, new)
    assert d.change == StopChange.WIDEN and d.requires_widen_opt_in
    assert not d.should_apply and 'opt-in required' in d.reason
    approved = assess(broker, side, old, new, allow_widen=True)
    assert approved.should_apply and approved.requires_widen_opt_in
    assert 'increases risk' in approved.reason
    assert not assess(broker, side, old, new, allow_widen='yes').allowed


@pytest.mark.parametrize('side,sl', [('BUY', 99), ('SELL', 101), ('BUY', 0)])
def test_unchanged_noop(broker, side, sl):
    d = assess(broker, side, sl, sl)
    assert d.change == StopChange.UNCHANGED
    assert not d.should_apply and 'no-op' in d.reason


@pytest.mark.parametrize('side,sl', [('BUY', 99), ('SELL', 101)])
def test_adding_missing_protection_tightens(broker, side, sl):
    assert assess(broker, side, 0, sl).change == StopChange.TIGHTEN
    assert assess(broker, side, 0, sl).allowed


@pytest.mark.parametrize('side,new', [('BUY', 99.9), ('SELL', 100.12)])
def test_exact_minimum_distance_legal(broker, side, new):
    old = 99 if side == 'BUY' else 101
    assert assess(broker, side, old, new).allowed


def test_freeze_level_and_grid_not_rounded_or_widened(broker):
    assert not assess(broker, new=99.805).allowed
    broker.info.trade_freeze_level = 30
    assert not assess(broker, new=99.8).allowed


@pytest.mark.parametrize('attribute,value', [('point', 0), ('trade_stops_level', -1),
                                            ('trade_tick_size', 0)])
def test_bad_metadata_fails_closed(broker, attribute, value):
    setattr(broker.info, attribute, value)
    assert not assess(broker).allowed


@pytest.mark.parametrize('old,new', [(float('nan'), 99), (99, float('inf')), (-1, 99)])
def test_invalid_stops_rejected(broker, old, new):
    assert not assess(broker, old=old, new=new).allowed


def test_missing_metadata_and_crossed_quotes_rejected(broker):
    broker.info = None
    assert not assess(broker).allowed
    broker = Broker()
    broker.tick.ask = 99
    assert not assess(broker).allowed
    assert not assess(broker, side='UNKNOWN').allowed


def test_broker_confirmed_tighten_not_assumed_from_plan(broker):
    d = plan_position_stop(broker, 42, 99.8, now=1001)
    assert d.should_apply
    assert not confirm_stop_change(broker, d)[0]  # broker still has old SL
    broker.positions[0].sl = 99.8  # fake separate authorized broker effect
    assert confirm_stop_change(broker, d) == (True, 'broker-confirmed TIGHTEN: SL=99.8')
    broker.positions[0].sl = 98  # actual widened risk must NOT appear confirmed
    assert not confirm_stop_change(broker, d)[0]


@pytest.mark.parametrize('field,value', [('ticket', 43), ('symbol', 'OTHER'), ('type', 1)])
def test_readback_exact_identity_required(broker, field, value):
    d = plan_position_stop(broker, 42, 99.8, now=1001)
    broker.positions[0].sl = 99.8
    setattr(broker.positions[0], field, value)
    assert not confirm_stop_change(broker, d)[0]


@pytest.mark.parametrize('positions', [None, []])
def test_unknown_position_refuses_plan_and_confirmation(broker, positions):
    d = plan_position_stop(broker, 42, 99.8, now=1001)
    broker.positions = positions
    assert not plan_position_stop(broker, 42, 99.8, now=1001).allowed
    assert not confirm_stop_change(broker, d)[0]


def test_sell_readback(broker):
    broker.positions[0].type = 1
    broker.positions[0].sl = 101
    d = plan_position_stop(broker, 42, 100.2, now=1001)
    assert d.allowed and d.change == StopChange.TIGHTEN
    broker.positions[0].sl = 100.2
    assert confirm_stop_change(broker, d)[0]


def test_no_real_broker_or_submission_dependency():
    assert classify_stop_change('BUY', 99, 98) == StopChange.WIDEN
    assert classify_stop_change('SELL', 101, 102) == StopChange.WIDEN


def _broker_clock(broker, offset_s, age_s=1, *, milliseconds=True):
    """Encode a known UTC tick in a deliberately offset fake broker clock."""
    now = 1_800_000_000
    stamp = Decimal(now) + Decimal(offset_s) - Decimal(str(age_s))
    broker.tick.time = int(stamp)
    broker.tick.time_msc = int(stamp * 1000) if milliseconds else 0
    return now


def test_offset_default_still_rejects_three_hour_future_tick(broker):
    now = _broker_clock(broker, 10800)
    decision = assess_stop_change(broker, 'TEST', 'BUY', 99, 99.8, now=now)
    assert not decision.should_apply and 'stale or future tick' in decision.reason


@pytest.mark.parametrize('offset_s', [0, 900, -900, 10800, -10800,
                                      14 * 3600, -14 * 3600])
def test_offset_normalizes_explicit_signed_broker_clock(broker, offset_s):
    now = _broker_clock(broker, offset_s)
    decision = assess_stop_change(broker, 'TEST', 'BUY', 99, 99.8,
                                now=now, broker_utc_offset_s=offset_s)
    assert decision.should_apply and decision.change == StopChange.TIGHTEN
    assert decision.tick_age_s == 1


@pytest.mark.parametrize('age_s,allowed', [(0, True), (5, True),
                                          (5.001, False), (-0.001, False)])
@pytest.mark.parametrize('offset_s', [10800, -10800])
def test_offset_does_not_relax_freshness_boundary(broker, offset_s, age_s, allowed):
    now = _broker_clock(broker, offset_s, age_s)
    decision = assess_stop_change(broker, 'TEST', 'BUY', 99, 99.8,
                                now=now, broker_utc_offset_s=offset_s)
    assert decision.allowed is allowed
    assert decision.tick_age_s == pytest.approx(age_s)
    if not allowed:
        assert 'stale or future tick' in decision.reason


@pytest.mark.parametrize('offset_s', [True, False, None, '10800', 10800.0,
                                      Decimal('10800'), [], {}, 1, -1,
                                      14 * 3600 + 900, -14 * 3600 - 900])
def test_offset_rejects_invalid_type_grid_or_range_without_broker_read(broker, offset_s):
    def forbidden_read(symbol):
        pytest.fail('invalid offset must be rejected before broker reads')
    broker.symbol_info = forbidden_read
    broker.symbol_info_tick = forbidden_read
    decision = assess_stop_change(broker, 'TEST', 'BUY', 99, 99.8,
                                now=1001, broker_utc_offset_s=offset_s)
    assert not decision.should_apply
    assert 'broker_utc_offset_s' in decision.reason
    assert decision.tick_age_s is None


def test_offset_seconds_fallback_retains_same_age_guard(broker):
    now = _broker_clock(broker, 10800, 5, milliseconds=False)
    decision = assess_stop_change(broker, 'TEST', 'BUY', 99, 99.8,
                                now=now, broker_utc_offset_s=10800)
    assert decision.should_apply and decision.tick_age_s == 5
    broker.tick.time -= 1
    assert not assess_stop_change(broker, 'TEST', 'BUY', 99, 99.8,
                                 now=now, broker_utc_offset_s=10800).allowed


@pytest.mark.parametrize('now_zone', [timezone.utc, timezone(timedelta(hours=2))])
def test_offset_accepts_aware_datetime_now(broker, now_zone):
    epoch = _broker_clock(broker, 10800)
    now = datetime.fromtimestamp(epoch, now_zone)
    assert assess_stop_change(broker, 'TEST', 'BUY', 99, 99.8,
                              now=now, broker_utc_offset_s=10800).should_apply
    decision = assess_stop_change(broker, 'TEST', 'BUY', 99, 99.8,
                                 now=now.replace(tzinfo=None), broker_utc_offset_s=10800)
    assert not decision.allowed and 'timezone-aware' in decision.reason


def test_offset_milliseconds_take_priority_over_seconds(broker):
    now = _broker_clock(broker, 10800, 5.001)
    broker.tick.time = now + 10800  # seconds appear fresh; milliseconds do not
    assert not assess_stop_change(broker, 'TEST', 'BUY', 99, 99.8,
                                 now=now, broker_utc_offset_s=10800).allowed


@pytest.mark.parametrize('raw_time,offset_s,now', [(-1, -900, 900), (0, -900, 901),
                                                  (900, 900, 1)])
def test_offset_cannot_rescue_invalid_raw_or_normalized_timestamp(broker, raw_time, offset_s, now):
    broker.tick.time_msc = raw_time * 1000
    broker.tick.time = raw_time
    decision = assess_stop_change(broker, 'TEST', 'BUY', 99, 99.8,
                                 now=now, broker_utc_offset_s=offset_s)
    assert not decision.allowed and 'stale or future tick' in decision.reason


def test_offset_is_forwarded_by_ticket_bound_plan_and_readback_still_required(broker):
    now = _broker_clock(broker, 10800)
    decision = plan_position_stop(broker, 42, 99.8, now=now, broker_utc_offset_s=10800)
    assert decision.should_apply and decision.ticket == 42
    assert not confirm_stop_change(broker, decision)[0]
    broker.positions[0].sl = 99.8
    assert confirm_stop_change(broker, decision)[0]


def test_offset_does_not_relax_geometry_or_widen_opt_in(broker):
    now = _broker_clock(broker, 10800)
    options = {'now': now, 'broker_utc_offset_s': 10800}
    off_grid = assess_stop_change(broker, 'TEST', 'BUY', 99, 99.805, **options)
    assert not off_grid.allowed and 'tick grid' in off_grid.reason
    too_close = assess_stop_change(broker, 'TEST', 'BUY', 99, 99.95, **options)
    assert not too_close.allowed and 'trade_stops_level' in too_close.reason
    widen = assess_stop_change(broker, 'TEST', 'BUY', 99, 98, **options)
    assert not widen.allowed and widen.requires_widen_opt_in
    assert 'opt-in required' in widen.reason

