---
slug: stop_legality
type: note
graph: gitnexus
---

"""Read-only stop-change planning and broker read-back; NEVER sends orders.

Prices are exact Decimal(str(value)) values; invalid/non-finite data fail closed.
now is explicit UTC epoch seconds (or aware datetime). A tick is fresh iff
0 <= now - normalized_tick_timestamp <= max_tick_age_s (default 5 seconds).
An explicit broker_utc_offset_s (default zero) is subtracted from the raw tick
timestamp only; it is never inferred from a tick or applied to now. Prefer
time_msc when available; future timestamps remain invalid after normalization.

BUY stops use bid, SELL stops use ask. Both stops/freeze levels (POINTS) are
respected conservatively. No auto-rounding/widening/retry. Authorization is
not broker confirmation: separately authorized callers must use fresh plans,
then confirm_stop_change after submission before recording BE/trail success.
These additive guards do not patch existing manager/executor send paths.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class StopChange(str, Enum):
    TIGHTEN = 'TIGHTEN'
    WIDEN = 'WIDEN'
    UNCHANGED = 'UNCHANGED'


def _number(value):
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('non-finite number')
    return result


def _side(side):
    if side not in ('BUY', 'SELL'):
        raise ValueError('side must be BUY or SELL')
    return side


def classify_stop_change(side, current_sl, proposed_sl):
    """Zero means no stop: adding protection tightens, removing it widens."""
    _side(side)
    current, proposed = _number(current_sl), _number(proposed_sl)
    if min(current, proposed) < 0:
        raise ValueError('stops cannot be negative')
    if current == proposed:
        return StopChange.UNCHANGED
    if proposed == 0:
        return StopChange.WIDEN
    if current == 0:
        return StopChange.TIGHTEN
    tighter = proposed > current if side == 'BUY' else proposed < current
    return StopChange.TIGHTEN if tighter else StopChange.WIDEN


@dataclass(frozen=True)
class StopDecision:
    symbol: str
    side: str
    current_sl: object
    proposed_sl: object
    change: StopChange | None
    allowed: bool
    reason: str
    requires_widen_opt_in: bool = False
    tick_age_s: float | None = None
    ticket: int | None = None

    @property
    def should_apply(self):
        return self.allowed and self.change != StopChange.UNCHANGED


def assess_stop_change(broker, symbol, side, current_sl, proposed_sl, *, now,
                       max_tick_age_s=5, allow_widen=False, ticket=None,
                       broker_utc_offset_s=0, allow_stale_for_protection=False):
    """Preflight only. Use plan_position_stop for a broker-read current SL.

    A WIDEN always carries requires_widen_opt_in=True, even when approved.
    An unchanged stop is a no-op (allowed=False), not a successful modify.
    Stop deletion (zero) also requires explicit widening opt-in and fresh data.
    broker_utc_offset_s is the configured broker clock minus UTC, in integer
    seconds: no bools, quarter-hour increments only, within +/-14 hours. Zero
    preserves strict UTC behavior. This corrects clock representation, never
    relaxes the freshness boundary or repairs a malformed raw timestamp.

    allow_stale_for_protection: when True and current_sl==0 (no existing
    protection) and the change is TIGHTEN, the tick freshness check is
    bypassed — leaving a position unprotected is riskier than a stop set on
    a slightly aged tick.
    """
    change, age = None, None

    def result(allowed, reason):
        return StopDecision(symbol, side, current_sl, proposed_sl, change,
                            allowed, reason, change == StopChange.WIDEN, age, ticket)

    try:
        change = classify_stop_change(side, current_sl, proposed_sl)
        if type(allow_widen) is not bool:
            return result(False, 'allow_widen must be an explicit bool')
        if (type(broker_utc_offset_s) is not int
                or abs(broker_utc_offset_s) > 14 * 3600
                or broker_utc_offset_s % 900 != 0):
            return result(False, 'broker_utc_offset_s must be an int (not bool), '
                          'in 900-second increments within +/-14 hours')
        if isinstance(now, datetime):
            if now.tzinfo is None or now.utcoffset() is None:
                return result(False, 'now must be timezone-aware')
            now = now.timestamp()
        now, max_age = _number(now), _number(max_tick_age_s)
        if max_age <= 0:
            return result(False, 'max_tick_age_s must be positive')
        info = broker.symbol_info(symbol)
        tick = broker.symbol_info_tick(symbol)
        if info is None:
            return result(False, 'missing symbol metadata')
        if tick is None:
            return result(False, 'missing tick')
        milliseconds = getattr(tick, 'time_msc', 0)
        raw_stamp = _number(milliseconds) / 1000 if milliseconds else _number(tick.time)
        stamp = raw_stamp - broker_utc_offset_s
        age = float(now - stamp)
        # Freshness guard: bypass for any risk-reducing TIGHTEN move, since
        # tightening a stop never increases exposure even on a stale tick.
        if not (allow_stale_for_protection
                and change == StopChange.TIGHTEN):
            if min(raw_stamp, stamp) <= 0 or now - stamp < 0 or now - stamp > max_age:
                return result(False, 'stale or future tick')
        bid, ask = _number(tick.bid), _number(tick.ask)
        if bid <= 0 or ask < bid:
            return result(False, 'invalid bid/ask')
        point = _number(info.point)
        stops = _number(info.trade_stops_level)
        freeze = _number(getattr(info, 'trade_freeze_level', 0))
        grid = _number(getattr(info, 'trade_tick_size', point))
        if point <= 0 or min(stops, freeze) < 0 or grid <= 0:
            return result(False, 'invalid stop metadata')
        if change == StopChange.UNCHANGED:
            return result(False, 'unchanged: no-op')
        proposed = _number(proposed_sl)
        if proposed:
            if proposed % grid != 0:
                return result(False, 'stop is off broker tick grid; no auto-rounding')
            distance = bid - proposed if side == 'BUY' else proposed - ask
            if distance <= 0 or distance < max(stops, freeze) * point:
                return result(False, 'stop violates trade_stops_level/freeze_level or market side')
        if change == StopChange.WIDEN:
            if not allow_widen:
                return result(False, 'WIDEN increases risk: explicit opt-in required')
            return result(True, 'WIDEN increases risk: explicitly opted in; not broker-confirmed')
        return result(True, 'TIGHTEN legal preflight; not broker-confirmed')
    except Exception as exc:
        return result(False, f'invalid or unavailable broker data: {exc}')


def plan_position_stop(broker, ticket, proposed_sl, *, now, **options):
    """Read exact position then assess; unknown/missing position cannot proceed.

    Pass explicit clock/guard options, including broker_utc_offset_s, through
    unchanged to assess_stop_change; an offset never establishes identity.
    """
    try:
        positions = broker.positions_get(ticket=ticket)
        if positions is None or len(positions) != 1 or positions[0].ticket != ticket:
            raise ValueError('exact position unavailable')
        p = positions[0]
        if p.type == broker.POSITION_TYPE_BUY:
            side = 'BUY'
        elif p.type == broker.POSITION_TYPE_SELL:
            side = 'SELL'
        else:
            raise ValueError('unknown position side')
        return assess_stop_change(broker, p.symbol, side, p.sl, proposed_sl,
                                  now=now, ticket=ticket, **options)
    except Exception as exc:
        return StopDecision('', '', None, proposed_sl, None, False,
                            f'position unavailable: {exc}', ticket=ticket)


def confirm_stop_change(broker, decision):
    """Read-only exact ticket/symbol/side/SL verification (never an ack guess).

    Returns (confirmed, reason). No cached decision is marked applied. An
    order response alone cannot establish protection. Failure/absence is UNKNOWN.
    """
    if not decision.should_apply or decision.ticket is None:
        return False, 'no authorized ticket-bound stop change'
    try:
        positions = broker.positions_get(ticket=decision.ticket)
        if positions is None or len(positions) != 1:
            return False, 'broker position unavailable; protection UNKNOWN'
        p = positions[0]
        expected_type = (broker.POSITION_TYPE_BUY if decision.side == 'BUY'
                         else broker.POSITION_TYPE_SELL)
        if (p.ticket != decision.ticket or p.symbol != decision.symbol
                or p.type != expected_type or _number(p.sl) != _number(decision.proposed_sl)):
            return False, 'broker protection does not match planned stop'
        return True, f'broker-confirmed {decision.change.value}: SL={p.sl}'
    except Exception as exc:
        return False, f'broker protection UNKNOWN: {exc}'

## Links from
- [[manage]]
- [[test_manager_protection]]
- [[test_stop_legality]]
