"""Broker send reconciliation for the MT5 execution path (backlog P0
``broker_send_reconciliation``).

Problem: ``mt5.order_send`` can lose its acknowledgement (returns None, raises,
or times out). Before this module the executor had no way to learn whether the
order actually reached the broker, so a retry could silently duplicate a live
position, a native SL attachment was assumed rather than verified, and partial
fills were never accounted.

This module answers, **without ever placing an order**:

1. Lost ack: did the order reach the broker? Read broker state back
   (positions_get / history_deals_get / history_orders_get filtered by magic
   and by the order's identifying comment / msg_id / ticket) and report
   CONFIRMED_FILLED, CONFIRMED_PLACED, CONFIRMED_ABSENT or UNKNOWN.
2. Native stop: verify a protective stop actually exists at the expected
   distance on the filled position; report missing/mismatch, never assume.
3. Partial fills: detect filled volume < requested volume and report both.
4. Idempotence: a Reconciler registry keyed by (magic, msg_id) never
   recommends a second submission once an order identity is confirmed.

Design contract:
  * PURE: the module never imports MetaTrader5. The MT5 handle is injected,
    so every path is testable offline with a fake (see test_reconciliation.py).
  * It NEVER calls ``mt5.order_send``. Read-only reconciliation only.
  * Read failures are distinguished: an empty tuple () is a confirmed empty
    answer; ``None`` or an exception is an API error -> UNKNOWN (must NOT
    retry; surface for human/operator review).
  * Matching strength is explicit: exact ticket, then identifying comment /
    msg_id fragment, then (conservatively) a weak same-magic window match
    that yields UNKNOWN rather than a false CONFIRMED_FILLED.

Reference: MT5_INTEGRATION.md "Broker response policy"
(10008 PLACED is not a fill, 10009 DONE still requires read-back, 10010 PARTIAL
needs separate accounting, 10012/absent are ambiguous and must not be resent
before reconciliation).
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable, Optional

# ---- statuses ----------------------------------------------------------------
STATUS_FILLED = "CONFIRMED_FILLED"      # order reached broker and is/was filled
STATUS_PLACED = "CONFIRMED_PLACED"      # order accepted at broker, not yet filled
STATUS_ABSENT = "CONFIRMED_ABSENT"      # nothing at broker; safe to retry
STATUS_UNKNOWN = "UNKNOWN"              # cannot prove either way; DO NOT retry

# MT5 deal entry kinds (values from the MQL5 docs; the injected handle may or
# may not expose the constants, so fall back to the documented values).
_DEAL_ENTRY_IN = 0
_DEAL_ENTRY_OUT = 1
_DEAL_ENTRY_INOUT = 2

#: Statuses that mean "the order identity is already confirmed at the broker".
CONFIRMED_STATUSES = (STATUS_FILLED, STATUS_PLACED)

#: Default look-back window for history queries (seconds). A lost-ack
#: reconciliation normally runs seconds after the send, so 10 minutes covers
#: broker/terminal clock skew without scanning the whole history.
DEFAULT_WINDOW_S = 600.0

#: Floats closer than this are treated as equal when comparing volumes.
_VOLUME_EPS = 1e-12


# ---- result ------------------------------------------------------------------
@dataclass
class ReconciliationResult:
    """Outcome of one reconciliation. ``safe_to_retry`` is the only field a
    caller should branch on for a retry decision; everything else is evidence
    for the operator."""

    status: str
    identity: str
    safe_to_retry: bool
    detail: str
    ticket: Optional[int] = None          # position ticket at the broker
    deal_ticket: Optional[int] = None     # history deal ticket (if via deals)
    fill_price: Optional[float] = None
    filled_volume: Optional[float] = None
    requested_volume: Optional[float] = None
    partial: bool = False
    partial_info: Optional[dict] = None
    native_stop: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    duplicate: bool = False               # True when served from the registry

    def as_dict(self) -> dict:
        return asdict(self)


# ---- helpers -----------------------------------------------------------------
def identity_key(magic: int, msg_id: str) -> str:
    """Canonical order identity for the idempotence registry."""
    return f"{int(magic)}:{msg_id or ''}"


def build_comment(msg_id: str, prefix: str = "sigrelay") -> str:
    """Mirror executor.py's comment format so reconciler-side matching uses the
    exact string the caller put on the wire (executor truncates to 31 chars;
    the caller passes the truncated value)."""
    return f"{prefix} {msg_id or ''}"[:31]


def _safe_read(call: Callable, *args, **kwargs) -> tuple[bool, Any]:
    """Run a read-only MT5 call. Returns (ok, value).

    ok=False means the call raised or returned None (API error) - the caller
    must treat the answer as UNKNOWN. An empty tuple () is ok=True: that is a
    confirmed-empty broker answer.
    """
    try:
        value = call(*args, **kwargs)
    except Exception as e:  # noqa: BLE001 - any broker/IO error -> unknown
        return False, f"{type(e).__name__}: {e}"
    if value is None:
        return False, "returned None (API error)"
    return True, value


def _read_history(call: Callable, since: datetime, until: datetime,
                  symbol: Optional[str]) -> tuple[bool, Any]:
    """history_*_get with a symbol filter. The official API takes symbol as a
    keyword; on older handles that reject it, retry unfiltered (the result is
    then filtered by magic/comment anyway)."""
    ok, value = _safe_read(call, since, until, symbol=symbol)
    if not ok and isinstance(value, str) and value.startswith("TypeError"):
        ok, value = _safe_read(call, since, until)
    return ok, value


def _matches(obj: Any, *, magic: Optional[int], comment: Optional[str],
             fragment: Optional[str],
             ticket_hint: Optional[int]) -> Optional[str]:
    """Return the match strength ('ticket' | 'comment' | None).

    Magic must always match (it scopes this relay's orders from every other
    strategy's). Within that scope an exact ticket is conclusive, then the
    identifying comment / msg_id fragment."""
    if magic is not None and getattr(obj, "magic", None) != magic:
        return None
    # A deal's own ticket is the deal id; the order it filled is deal.order.
    if ticket_hint is not None and (
            getattr(obj, "ticket", None) == ticket_hint
            or getattr(obj, "order", None) == ticket_hint):
        return "ticket"
    c = getattr(obj, "comment", "") or ""
    if comment and c == comment:
        return "comment"
    if fragment and fragment in c:
        return "comment"
    return None


def _entry_in(deal: Any, mt5: Any) -> bool:
    """True when a deal opens (or reverses into) a position."""
    in_code = getattr(mt5, "DEAL_ENTRY_IN", _DEAL_ENTRY_IN)
    inout_code = getattr(mt5, "DEAL_ENTRY_INOUT", _DEAL_ENTRY_INOUT)
    out_code = getattr(mt5, "DEAL_ENTRY_OUT", _DEAL_ENTRY_OUT)
    entry = getattr(deal, "entry", in_code)
    return entry in (in_code, inout_code, out_code) and entry != out_code


def _as_tuple(value: Any) -> tuple:
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return ()  # defensive: an unexpected scalar is treated as no records


def partial_fill(filled: Optional[float], requested: Optional[float]) -> Optional[dict]:
    """Return partial-fill accounting when filled < requested, else None."""
    if filled is None or requested is None:
        return None
    if filled + _VOLUME_EPS < requested:
        return {
            "filled": filled,
            "requested": requested,
            "remaining": round(requested - filled, 10),
            "fill_ratio": round(filled / requested, 6) if requested else None,
        }
    return None


def verify_native_stop(mt5: Any, *, symbol: Optional[str] = None,
                       ticket: Optional[int] = None, position: Any = None,
                       expected_sl: Optional[float] = None,
                       expected_tp: Optional[float] = None,
                       side: Optional[str] = None,
                       sl_tolerance: Optional[float] = None,
                       tp_tolerance: Optional[float] = None) -> dict:
    """Read the position back and verify the native protective stop actually
    attaches at the expected distance. Never assumes success.

    Returns a dict with state in:
      attached   - stop present at the expected level (within tolerance)
      missing    - position exists but has no stop (sl == 0/None)
      mismatch   - stop present but at the WRONG level (reports both levels)
      unknown    - position not visible / could not be read
      not_requested - no expected level was supplied; actual levels are reported
    """
    out = {"state": "unknown", "actual_sl": None, "actual_tp": None,
           "expected_sl": expected_sl, "expected_tp": expected_tp,
           "detail": ""}
    if position is None and ticket is not None:
        ok, pos_ok = _safe_read(mt5.positions_get, symbol=symbol) if symbol \
            else _safe_read(mt5.positions_get)
        if not ok:
            out["detail"] = f"positions_get failed: {pos_ok}"
            return out
        position = next((p for p in _as_tuple(pos_ok)
                         if getattr(p, "ticket", None) == ticket), None)
    if position is None:
        out["detail"] = (f"position #{ticket} not visible to reconcile"
                         if ticket is not None else "no position supplied")
        return out
    actual_sl = getattr(position, "sl", 0.0) or 0.0
    actual_tp = getattr(position, "tp", 0.0) or 0.0
    entry = getattr(position, "price_open", None)
    out["actual_sl"] = actual_sl
    out["actual_tp"] = actual_tp
    out["entry"] = entry
    out["ticket"] = getattr(position, "ticket", ticket)

    def _tolerance(explicit: Optional[float], tick_default: float) -> float:
        if explicit is not None:
            return explicit
        try:
            info = mt5.symbol_info(symbol or getattr(position, "symbol", ""))
            tick = getattr(info, "trade_tick_size", None) or \
                getattr(info, "point", None) or 0.0
            return 2 * tick if tick else 0.0
        except Exception:  # noqa: BLE001 - no market data -> exact match
            return 0.0

    if expected_sl is None and expected_tp is None:
        out["state"] = "not_requested"
        out["detail"] = f"position open at {entry}, sl={actual_sl}, tp={actual_tp}"
        return out
    if expected_sl is not None:
        tol = _tolerance(sl_tolerance, 0.0)
        delta = abs(actual_sl - expected_sl)
        out["expected_distance"] = (abs(entry - expected_sl)
                                    if entry is not None else None)
        out["actual_distance"] = (abs(entry - actual_sl)
                                  if entry is not None else None)
        out["sl_tolerance"] = tol
        if actual_sl == 0.0:
            out["state"] = "missing"
            out["detail"] = (f"NATIVE STOP MISSING on #{out['ticket']}: expected "
                             f"sl={expected_sl}, position has no stop")
            return out
        if delta > tol:
            out["state"] = "mismatch"
            out["detail"] = (f"NATIVE STOP MISMATCH on #{out['ticket']}: expected "
                             f"sl={expected_sl}, actual={actual_sl}, "
                             f"delta={delta} (tol={tol})")
            return out
        out["state"] = "attached"
        out["detail"] = f"native stop attached on #{out['ticket']}: sl={actual_sl}"
    if expected_tp is not None and out["state"] in ("attached", "unknown"):
        tol = _tolerance(tp_tolerance, 0.0)
        delta = abs(actual_tp - expected_tp)
        out["tp_tolerance"] = tol
        if actual_tp == 0.0:
            out["state"] = "missing"
            out["detail"] += (f"; TP MISSING on #{out['ticket']}: expected "
                              f"tp={expected_tp}")
            return out
        if delta > tol:
            out["state"] = "mismatch"
            out["detail"] += (f"; TP MISMATCH on #{out['ticket']}: expected "
                              f"tp={expected_tp}, actual={actual_tp}")
            return out
        out["detail"] += f"; tp={actual_tp}"
    return out


# ---- main lost-ack reconciliation --------------------------------------------
def reconcile_send(mt5: Any, *, symbol: str, side: str, magic: int,
                   msg_id: str, requested_volume: float,
                   expected_sl: Optional[float] = None,
                   expected_tp: Optional[float] = None,
                   ticket_hint: Optional[int] = None,
                   comment: Optional[str] = None,
                   fragment: Optional[str] = None,
                   window_s: float = DEFAULT_WINDOW_S,
                   now: Optional[datetime] = None,
                   sl_tolerance: Optional[float] = None,
                   tp_tolerance: Optional[float] = None) -> ReconciliationResult:
    """Reconcile one order whose acknowledgement was lost (order_send returned
    None / raised / timed out). READ-ONLY: never submits an order.

    Decision procedure:
      1. positions_get(symbol)  - a live position with our magic AND matching
         comment/ticket  -> CONFIRMED_FILLED (ticket, fill price=price_open,
         volume=position volume).
      2. history_deals_get     - an IN/INOUT deal with our magic AND matching
         comment/ticket        -> CONFIRMED_FILLED (deal price/volume); an OUT
         deal proves the position was closed (exit read-back).
      3. history_orders_get    - a pending order with our magic AND matching
         comment/ticket        -> CONFIRMED_PLACED (accepted, not filled).
      4. All reads empty       -> CONFIRMED_ABSENT (safe to retry).
      5. Any read None/raised, or an unmatched same-magic order inside the
         window                      -> UNKNOWN (DO NOT retry; operator review).
    """
    ident = identity_key(magic, msg_id)
    frag = fragment if fragment is not None else (msg_id or None)
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(seconds=max(float(window_s), 0.0))

    def _unknown(detail: str, **evidence) -> ReconciliationResult:
        return ReconciliationResult(
            status=STATUS_UNKNOWN, identity=ident, safe_to_retry=False,
            detail=detail, requested_volume=requested_volume,
            evidence={"read_errors": evidence})

    # ---- 1. open positions -------------------------------------------------
    ok, pos_value = _safe_read(mt5.positions_get, symbol=symbol)
    if not ok:
        return _unknown(f"positions_get({symbol}) failed: {pos_value}",
                        positions_get=str(pos_value))
    positions = _as_tuple(pos_value)
    hit = next((p for p in positions if _matches(
        p, magic=magic, comment=comment, fragment=frag,
        ticket_hint=ticket_hint) == "ticket"), None)
    if hit is None:
        hit = next((p for p in positions if _matches(
            p, magic=magic, comment=comment, fragment=frag,
            ticket_hint=ticket_hint) == "comment"), None)
    if hit is not None:
        partial = partial_fill(getattr(hit, "volume", None), requested_volume)
        stop = verify_native_stop(mt5, position=hit,
                                  expected_sl=expected_sl,
                                  expected_tp=expected_tp, side=side,
                                  sl_tolerance=sl_tolerance,
                                  tp_tolerance=tp_tolerance)
        return ReconciliationResult(
            status=STATUS_FILLED, identity=ident, safe_to_retry=False,
            ticket=getattr(hit, "ticket", None),
            fill_price=getattr(hit, "price_open", None),
            filled_volume=getattr(hit, "volume", None),
            requested_volume=requested_volume,
            partial=partial is not None, partial_info=partial,
            native_stop=stop,
            evidence={"source": "positions_get",
                      "match_strength": _matches(
                          hit, magic=magic, comment=comment, fragment=frag,
                          ticket_hint=ticket_hint),
                      "comment": getattr(hit, "comment", None)},
            detail=f"position #{getattr(hit, 'ticket', None)} open at "
                   f"{getattr(hit, 'price_open', None)}")

    # ---- 2. deal history ---------------------------------------------------
    ok, deals_value = _read_history(mt5.history_deals_get, since, now, symbol)
    if not ok:
        return _unknown(f"history_deals_get failed: {deals_value}",
                        history_deals_get=str(deals_value))
    deals = _as_tuple(deals_value)
    fill_deal = next((d for d in deals if _entry_in(d, mt5) and _matches(
        d, magic=magic, comment=comment, fragment=frag,
        ticket_hint=ticket_hint)), None)
    exit_deal = next((d for d in deals if not _entry_in(d, mt5) and _matches(
        d, magic=magic, comment=comment, fragment=frag,
        ticket_hint=ticket_hint)), None)
    if fill_deal is not None:
        vol = getattr(fill_deal, "volume", None)
        partial = partial_fill(vol, requested_volume)
        return ReconciliationResult(
            status=STATUS_FILLED, identity=ident, safe_to_retry=False,
            ticket=getattr(fill_deal, "position_id", None)
                    or getattr(fill_deal, "order", None),
            deal_ticket=getattr(fill_deal, "ticket", None),
            fill_price=getattr(fill_deal, "price", None),
            filled_volume=vol, requested_volume=requested_volume,
            partial=partial is not None, partial_info=partial,
            evidence={"source": "history_deals_get",
                      "match_strength": _matches(
                          fill_deal, magic=magic, comment=comment,
                          fragment=frag, ticket_hint=ticket_hint),
                      "exit_deal_ticket": (getattr(exit_deal, "ticket", None)
                                           if exit_deal is not None else None),
                      "comment": getattr(fill_deal, "comment", None)},
            detail=f"deal #{getattr(fill_deal, 'ticket', None)} filled "
                   f"{vol} @ {getattr(fill_deal, 'price', None)}")

    # ---- 3. pending orders --------------------------------------------------
    ok, orders_value = _read_history(mt5.history_orders_get, since, now, symbol)
    if not ok:
        return _unknown(f"history_orders_get failed: {orders_value}",
                        history_orders_get=str(orders_value))
    orders = _as_tuple(orders_value)
    pend = next((o for o in orders if _matches(
        o, magic=magic, comment=comment, fragment=frag,
        ticket_hint=ticket_hint)), None)
    if pend is not None:
        return ReconciliationResult(
            status=STATUS_PLACED, identity=ident, safe_to_retry=False,
            ticket=getattr(pend, "ticket", None),
            requested_volume=requested_volume,
            evidence={"source": "history_orders_get",
                      "match_strength": _matches(
                          pend, magic=magic, comment=comment,
                          fragment=frag, ticket_hint=ticket_hint),
                      "comment": getattr(pend, "comment", None)},
            detail=f"order #{getattr(pend, 'ticket', None)} accepted at broker "
                   f"but not filled - do NOT resubmit")

    # ---- 4/5. confirmed absent vs ambiguous --------------------------------
    same_magic_recent = [
        o for o in orders if getattr(o, "magic", None) == magic
        and getattr(o, "comment", "") != comment]
    if same_magic_recent:
        return _unknown(
            f"{len(same_magic_recent)} order(s) with magic {magic} in window "
            f"do not match our comment/ticket - cannot prove absence",
            unmatched_same_magic=[getattr(o, "ticket", None)
                                  for o in same_magic_recent])
    return ReconciliationResult(
        status=STATUS_ABSENT, identity=ident, safe_to_retry=True,
        requested_volume=requested_volume,
        evidence={"source": "read_back_empty",
                  "reads": ["positions_get", "history_deals_get",
                            "history_orders_get"],
                  "window_s": window_s},
        detail=f"no position, deal or pending order for {ident} at broker - "
               f"safe to retry")


# ---- idempotent wrapper ------------------------------------------------------
class Reconciler:
    """Stateful reconciler: remembers confirmed order identities per
    (magic, msg_id) so a lost-ack retry never double-submits.

    ``state_path`` optionally persists the registry to JSON so the guard
    survives process restarts (a crash between order_send and the ledger write
    must not open the door to a duplicate).
    """

    def __init__(self, state_path: Optional[str] = None):
        self._state_path = state_path
        self._registry: dict[str, ReconciliationResult] = {}
        if state_path:
            self._load()

    # -- registry mechanics ----------------------------------------------------
    @staticmethod
    def key(magic: int, msg_id: str) -> str:
        return identity_key(magic, msg_id)

    def is_confirmed(self, magic: int, msg_id: str) -> Optional[ReconciliationResult]:
        return self._registry.get(self.key(magic, msg_id))

    def record(self, result: ReconciliationResult) -> None:
        """Record a CONFIRMED_* outcome; UNKNOWN/ABSENT are deliberately not
        recorded (absence is not proof, and an error state must not poison
        the identity)."""
        if result.status in CONFIRMED_STATUSES:
            self._registry[result.identity] = result
            self._save()

    def _load(self) -> None:
        try:
            with open(self._state_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for ident, data in (raw or {}).items():
                self._registry[ident] = ReconciliationResult(**data)
        except FileNotFoundError:
            pass
        except Exception as e:  # noqa: BLE001 - corrupt state must not crash
            print(f"reconciliation: registry load failed, starting empty: "
                  f"{type(e).__name__}: {e}")

    def _save(self) -> None:
        if not self._state_path:
            return
        try:
            tmp = self._state_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({k: v.as_dict() for k, v in self._registry.items()}, f,
                          indent=1)
            os.replace(tmp, self._state_path)
        except Exception as e:  # noqa: BLE001 - persistence is best-effort
            print(f"reconciliation: registry save failed: "
                  f"{type(e).__name__}: {e}")

    # -- main entry ------------------------------------------------------------
    def reconcile(self, mt5: Any, **kwargs) -> ReconciliationResult:
        """Idempotent reconcile. If this (magic, msg_id) is already confirmed
        at the broker, return the stored outcome marked ``duplicate=True``
        with ``safe_to_retry=False`` - never recommend a second submission."""
        key = self.key(kwargs.get("magic", 0), str(kwargs.get("msg_id", "")))
        prev = self._registry.get(key)
        if prev is not None:
            dup = replace(prev, duplicate=True)
            dup.safe_to_retry = False
            dup.detail = (f"duplicate suppressed - {key} already confirmed as "
                          f"{prev.status}: {prev.detail}")
            return dup
        result = reconcile_send(mt5, **kwargs)
        self.record(result)
        return result
