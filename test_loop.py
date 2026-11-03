# -*- coding: utf-8 -*-
"""END-TO-END lifecycle test: synthetic signal -> parser -> REAL demo order -> position
verify -> SL-to-breakeven -> opposite-deal close -> history verify -> ledger verify.

Run ONCE:
    cd C:/Users/voidk/.hermes/workspace/signal-relay
    PYTHONPATH= C:/Users/voidk/miniconda3/python.exe test_loop.py

Safety rails baked in:
  - HARD ABORT before any order unless the logged-in MT5 account is a DEMO
    (account_info().trade_mode == 0).
  - HARD ABORT if the account is netting AND an XAUUSD position already exists
    (opening would merge into it; closing would then close the daemon's trade too).
  - Cleanup closes ONLY the ticket this test opened. Never close_all_positions.
  - executor.execute() is called exactly ONCE. A broker_rejected result is recorded,
    never retried.
  - Findings are ALWAYS written to agent-reports/loop-test.md before the summary.
"""
import json
import os
import sqlite3
import sys
import time
import traceback

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
sys.path.insert(0, BASE)

try:  # Windows console is cp1252; emoji in the signal text would crash printing
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import MetaTrader5 as mt5  # noqa: E402
import parser as sigparser  # noqa: E402  (daemon.py uses the same import name)
import executor  # noqa: E402

CHANNEL_ID = -1002369502254   # "Best Signal Forex" - approved trading channel
LOT = 0.01                    # smallest safe lot
MAGIC = 20261014              # user-approved relay magic
SIGNAL_TEXT = "\U0001F7E1 XAUUSD SIGNAL \U0001F7E1\nBUY NOW\nSL: 2650\nTP1: 2700\nTP2: 2750"
REPORT_PATH = os.path.join(BASE, "agent-reports", "loop-test.md")
DB = os.path.join(BASE, "signals.db")

STAGES = []   # (num, name, status, detail)
LOG = []      # every printed line, replayed into the report


def log(msg=""):
    print(msg)
    LOG.append(str(msg))


def stage(num, name, status, detail=""):
    STAGES.append((num, name, status, detail))
    log(f"[{status}] stage {num} {name}" + (f" :: {detail}" if detail else ""))


def deal_line(d):
    return (f"deal#{d.ticket} order={d.order} pos_id={getattr(d, 'position_id', '?')} "
            f"entry={d.entry} type={d.type} price={d.price} vol={d.volume} "
            f"profit={d.profit} comm={d.commission} swap={d.swap} comment={d.comment!r}")


RETCODE_HINTS = {
    10004: "requote - deviation too small for XAUUSD volatility (executor order request)",
    10006: "request rejected by broker - check MT5 journal",
    10013: "invalid request - request-building code in executor.execute()",
    10014: "invalid volume - executor._norm_volume vs XAUUSD volume_min/step",
    10015: "invalid price - stale price from executor.tick_price at send time",
    10016: "invalid stops - SL/TP too close to market or wrong side "
           "(executor._validate_stops / executor.sl_to_breakeven buffer)",
    10017: "trade disabled for symbol - symbol trade mode",
    10018: "market closed - XAUUSD session hours",
    10019: "not enough money - free margin (risk.min_free_margin_pct guard)",
    10027: "AutoTrading disabled in the MT5 terminal UI - not a code bug; "
           "executor._guards already reports it as a skip reason",
    10030: "unsupported filling mode - executor._fill_type mask logic for this symbol",
    10044: "only position-close allowed by symbol",
}


def retcode_hint(code):
    return RETCODE_HINTS.get(int(code), "unknown retcode - see MT5 docs / terminal journal")


def close_ticket(ticket, sym, volume, is_buy, comment, deviation=100):
    """One targeted close attempt (opposite TRADE_ACTION_DEAL). Returns (res, req)."""
    tick = mt5.symbol_info_tick(sym)
    price = (tick.bid if is_buy else tick.ask) if tick else 0.0
    req = {"action": mt5.TRADE_ACTION_DEAL, "position": ticket, "symbol": sym,
           "volume": volume, "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
           "price": price, "deviation": deviation, "magic": MAGIC, "comment": comment,
           "type_time": mt5.ORDER_TIME_GTC, "type_filling": executor._fill_type(sym)}
    res = mt5.order_send(req)
    return res, req


def cleanup(ticket, sym):
    """Close OUR position if somehow still open. Never touches other tickets."""
    if not ticket:
        log("cleanup: nothing to close (no position was opened)")
        return True
    pos = mt5.positions_get(ticket=ticket)
    if not pos:
        log(f"cleanup: position #{ticket} already closed - nothing to do")
        return True
    p = pos[0]
    for attempt in (1, 2, 3):
        res, req = close_ticket(ticket, sym, p.volume, p.type == mt5.POSITION_TYPE_BUY,
                                f"looptest cleanup {attempt}")
        if res is None:
            log(f"cleanup attempt {attempt}: order_send None, last_error={mt5.last_error()}")
        else:
            log(f"cleanup attempt {attempt}: retcode={res.retcode} comment={res.comment!r}")
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                time.sleep(1.0)
                if not mt5.positions_get(ticket=ticket):
                    log(f"cleanup: position #{ticket} closed OK (attempt {attempt})")
                    return True
        time.sleep(2.0)
    still = mt5.positions_get(ticket=ticket)
    if still:
        log(f"!!! CLEANUP FAILED: position #{ticket} STILL OPEN - manual close needed !!!")
        return False
    log(f"cleanup: position #{ticket} confirmed closed")
    return True


def write_report(context, diag_lines, cleanup_ok):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    rows = "\n".join(
        f"| {n} | {name} | **{st}** | {detail.replace('|', '/')} |"
        for n, name, st, detail in STAGES)
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    md = [
        "# End-to-end loop test: signal -> MT5 -> manage -> close -> ledger",
        "",
        f"- **When (local):** {now}",
        f"- **Account:** {context.get('acct')}",
        f"- **Channel policy:** channel_id {CHANNEL_ID} "
        f"(sl_mode={context.get('pol_sl_mode')}, tp_mode={context.get('pol_tp_mode')}, "
        f"atr_mult={context.get('pol_atr_mult')})",
        f"- **Signal text:** {SIGNAL_TEXT!r}",
        f"- **msg_id:** `{context.get('msg_id')}`  |  **requested lot:** {LOT}",
        "",
        "## Stage results",
        "",
        "| # | Stage | Status | Detail |",
        "|---|-------|--------|--------|",
        rows,
        "",
        "## Raw log",
        "",
        "```",
        *LOG,
        "```",
        "",
        "## Diagnosis",
        "",
        *(diag_lines if diag_lines else ["All stages passed - no fix required."]),
        "",
        f"## Cleanup: {'OK' if cleanup_ok else 'FAILED - position possibly still open'}",
        "",
    ]
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    log(f"report written: {REPORT_PATH}")


def main():
    ctx = {}
    diag = []
    ticket = None
    sym = None
    exec_result = None
    parsed = None
    pos_obj = None
    cleanup_ok = True
    abort = None
    try:
        # ---------------- stage 0: environment + demo gate ----------------
        if not mt5.initialize():
            stage(0, "MT5 attach", "FAIL", f"mt5.initialize() failed: {mt5.last_error()}")
            abort = "MT5 not attached"
        else:
            ti = mt5.terminal_info()
            ai = mt5.account_info()
            if ti is None or ai is None:
                stage(0, "MT5 attach", "FAIL",
                      f"terminal_info={ti is not None} account_info={ai is not None}")
                abort = "MT5 API not responding"
            else:
                sym = executor.resolve_symbol("XAUUSD")
                info = mt5.symbol_info(sym) if sym else None
                tick = mt5.symbol_info_tick(sym) if sym else None
                con = sqlite3.connect(DB, timeout=5)
                try:
                    n_today = con.execute(
                        "SELECT COUNT(*) FROM trades WHERE ts LIKE ? AND status!='skipped'",
                        (time.strftime("%Y-%m-%d") + "%",)).fetchone()[0]
                finally:
                    con.close()
                positions = mt5.positions_get() or []
                xau_open = [p for p in positions if sym and p.symbol == sym]
                ctx["acct"] = (f"login={ai.login} server={ai.server} trade_mode={ai.trade_mode} "
                               f"(0=demo) margin_mode={ai.margin_mode} "
                               f"(0=netting, 1=exchange, 2=hedging) "
                               f"balance={ai.balance} equity={ai.equity}")
                log(f"pre-flight: trade_allowed={ti.trade_allowed} halt_file="
                    f"{os.path.exists(os.path.join(BASE, 'HALT'))}")
                log(f"pre-flight: account={ctx['acct']}")
                log(f"pre-flight: symbol={sym} bid={getattr(tick, 'bid', None)} "
                    f"ask={getattr(tick, 'ask', None)} point={getattr(info, 'point', None)} "
                    f"digits={getattr(info, 'digits', None)} "
                    f"vol_min={getattr(info, 'volume_min', None)} "
                    f"stops_level={getattr(info, 'trade_stops_level', None)}")
                log(f"pre-flight: open positions total={len(positions)} "
                    f"(magic {MAGIC}: {sum(1 for p in positions if p.magic == MAGIC)}, "
                    f"{sym} specifically: {len(xau_open)})")
                log(f"pre-flight: ledger non-skipped today={n_today} (cap 20)")
                if ai.trade_mode != 0:
                    stage(0, "environment+demo gate", "FAIL",
                          f"NOT A DEMO ACCOUNT (trade_mode={ai.trade_mode}) - aborting "
                          f"before any order per safety rule")
                    abort = "not demo"
                elif ai.margin_mode == mt5.ACCOUNT_MARGIN_MODE_RETAIL_NETTING and xau_open:
                    stage(0, "environment+demo gate", "FAIL",
                          f"NETTING account with {len(xau_open)} existing {sym} position(s) - "
                          f"a new order would MERGE into them; aborting to protect live trades")
                    abort = "netting merge hazard"
                elif sym is None or tick is None or info is None:
                    stage(0, "environment+demo gate", "FAIL", "XAUUSD not resolvable/visible")
                    abort = "no XAUUSD"
                else:
                    warns = []
                    if not ti.trade_allowed:
                        warns.append("AutoTrading OFF in terminal (expect retcode 10027)")
                    if os.path.exists(os.path.join(BASE, "HALT")):
                        warns.append("HALT file present (executor will skip)")
                    if len(positions) >= 5:
                        warns.append(f"positions_total={len(positions)} >= cap 5")
                    if n_today >= 20:
                        warns.append(f"today non-skipped={n_today} >= cap 20")
                    stage(0, "environment+demo gate", "PASS",
                          "; ".join(warns) or "demo account, XAUUSD live, guards clear")

        # ---------------- stage 1: parse ----------------
        if not abort:
            parsed = sigparser.parse_signal(SIGNAL_TEXT)
            slim = {k: v for k, v in parsed.items() if k != "raw"}
            log(f"parse result: {json.dumps(slim)}")
            ok = (parsed.get("is_signal") and parsed.get("parse_ok")
                  and parsed.get("action") == "buy" and parsed.get("symbol") == "XAUUSD"
                  and parsed.get("order_type") == "market" and parsed.get("sl") is not None)
            stage(1, "parse_signal", "PASS" if ok else "FAIL", json.dumps(slim))
            if not ok:
                abort = "parse failed - refusing to execute an unparseable signal"

        # ---------------- stage 2: execute (REAL order, called ONCE) ----------------
        if not abort:
            cfg = executor.load_config()
            pol = (cfg.get("signal_policy") or {}).get(str(CHANNEL_ID), {})
            ctx["pol_sl_mode"] = pol.get("sl_mode")
            ctx["pol_tp_mode"] = pol.get("tp_mode")
            ctx["pol_atr_mult"] = pol.get("atr_mult")
            ctx["msg_id"] = f"looptest-{int(time.time())}"
            log(f"execute(): msg_id={ctx['msg_id']} lot={LOT} channel_id={CHANNEL_ID} "
                f"policy={pol} (sl_mode=atr will REPLACE the parsed SL; tp_mode=none strips TPs)")
            exec_result = executor.execute(parsed, msg_id=ctx["msg_id"], lot=LOT,
                                           channel_id=CHANNEL_ID)
            log(f"execute() result: {json.dumps(exec_result)}")
            ok = exec_result.get("status") == "executed" and exec_result.get("ticket")
            detail = (f"status={exec_result.get('status')} ticket={exec_result.get('ticket')} "
                      f"fill={exec_result.get('fill_price')} lot={exec_result.get('lot')} "
                      f"sl={exec_result.get('sl')} detail={exec_result.get('detail', '')}")
            stage(2, "executor.execute REAL order", "PASS" if ok else "FAIL", detail)
            if ok:
                ticket = exec_result["ticket"]
            else:
                d = exec_result.get("detail", "")
                hint = ""
                if d.startswith("retcode "):
                    try:
                        hint = retcode_hint(int(d.split()[1].rstrip(":")))
                    except (ValueError, IndexError):
                        hint = ""
                diag.append(f"- Stage 2 failed: `{d}`. Channel policy={pol}. "
                            f"Retcode hint: {hint or 'n/a (guard-chain skip, not a broker reject)'}. "
                            "Module to fix: whichever guard rejected it - "
                            "executor.py (guards) or the MT5 terminal state itself.")
                abort = "execute failed - NOT retrying per test contract"

        # ---------------- stage 3: position + SL verify ----------------
        pos_found_via = None
        if not abort:
            time.sleep(1.5)
            pos = mt5.positions_get(ticket=ticket)
            if pos:
                pos_found_via = f"positions_get(ticket={ticket})"
            else:  # diagnostic fallback: prove whether the order ticket became a position
                cand = [p for p in (mt5.positions_get(symbol=sym) or [])
                        if p.magic == MAGIC and str(p.comment).startswith("sigrelay looptest")]
                pos = tuple(cand[-1:]) if cand else ()
                pos_found_via = ("fallback scan by magic+comment"
                                 if cand else "none (ticket and fallback both empty)")
            log(f"position lookup via {pos_found_via}: "
                f"{[(p.ticket, p.symbol, p.type, p.volume, p.price_open, p.sl, p.tp, p.magic, p.comment) for p in pos]}")
            if not pos:
                stage(3, "position+SL verify", "FAIL",
                      f"no position found for ticket {ticket} ({pos_found_via})")
                abort = "no position"
            else:
                p = pos[0]
                pos_obj = p
                ticket = p.ticket  # authoritative position ticket
                exp_sl = exec_result.get("sl")
                is_buy = parsed.get("action") == "buy"
                checks = [
                    (p.magic == MAGIC, f"magic={p.magic}"),
                    (p.type == (mt5.POSITION_TYPE_BUY if is_buy else mt5.POSITION_TYPE_SELL),
                     f"type={p.type} (0=BUY,1=SELL)"),
                    (p.sl != 0.0, f"sl={p.sl}"),
                    ((p.sl < p.price_open) if is_buy else (p.sl > p.price_open),
                     f"SL side: sl={p.sl} vs open={p.price_open}"),
                    (abs(p.price_open - p.sl) >= 10 * (mt5.symbol_info(sym).point or 0.01),
                     f"SL distance={abs(p.price_open - p.sl)}"),
                    (exp_sl is not None and abs(p.sl - exp_sl) < 1e-9,
                     f"SL matches execute() result sl ({exp_sl})"),
                    (abs(p.volume - (exec_result.get("lot") or LOT)) < 1e-9,
                     f"volume={p.volume}"),
                    (str(p.comment).startswith("sigrelay looptest"), f"comment={p.comment!r}"),
                ]
                ok = all(c for c, _ in checks)
                fails = "; ".join(t for c, t in checks if not c)
                stage(3, "position+SL verify", "PASS" if ok else "FAIL",
                      (f"all checks OK; " if ok else f"FAILED: {fails}; ")
                      + f"via {pos_found_via}, open={p.price_open} sl={p.sl} tp={p.tp} vol={p.volume}")

        # ---------------- stage 4: SL to breakeven ----------------
        if not abort:
            p = pos_obj
            is_buy = p.type == mt5.POSITION_TYPE_BUY
            before_sl = p.sl
            be_ret = executor.sl_to_breakeven(p)
            log(f"sl_to_breakeven() returned: {be_ret!r}")
            time.sleep(0.8)
            pos2 = mt5.positions_get(ticket=ticket)
            p2 = pos2[0] if pos2 else None
            moved = p2 is not None and p2.sl != before_sl
            protected = (p2 is not None
                         and ((is_buy and p2.sl >= p2.price_open)
                              or ((not is_buy) and p2.sl <= p2.price_open)))
            ok = bool(moved and protected)
            detail = (f"return={be_ret!r} sl {before_sl} -> "
                      f"{p2.sl if p2 else 'n/a'} (entry={p.price_open})")
            stage(4, "executor.sl_to_breakeven", "PASS" if ok else "FAIL", detail)
            if not ok:
                diag.append(
                    f"- Stage 4 failed: `{be_ret}`. Root cause analysis: for a fresh "
                    f"{'BUY' if is_buy else 'SELL'} fill, entry={p.price_open} sits "
                    f"{('above' if is_buy else 'below')} the current "
                    f"{'bid' if is_buy else 'ask'}, so SL=entry±buffer is on the "
                    f"trigger side of the market - no broker accepts that; expect "
                    f"retcode 10016 'Invalid stops'. Module to fix: "
                    f"**executor.py sl_to_breakeven()** - it should check the live tick "
                    f"and refuse/defer when price has not moved beyond "
                    f"entry+buffer+stops_level, instead of sending a guaranteed-reject "
                    f"modify. (Production callers manage.py BE@+1R and daemon TP-hit "
                    f"updates only fire after favorable movement, so this bites mainly "
                    f"when BE is requested at ~0R, as in this test.)")
                # 4b: prove the SLTP-modify mechanism itself with a market-legal stop
                info = mt5.symbol_info(sym)
                pt = info.point if info else 0.01
                dig = info.digits if info else 2
                # tighten to the midpoint between original SL and entry: always on the
                # legal side of the market, never worsens the stop
                target = round((before_sl + p.price_open) / 2.0, dig)
                req = {"action": mt5.TRADE_ACTION_SLTP, "symbol": sym, "position": ticket,
                       "sl": target, "tp": p.tp}
                r4b = mt5.order_send(req)
                time.sleep(0.8)
                pos4b = mt5.positions_get(ticket=ticket)
                p4b = pos4b[0] if pos4b else None
                ok4b = (r4b is not None and r4b.retcode == mt5.TRADE_RETCODE_DONE
                        and p4b is not None and abs(p4b.sl - target) < pt / 2)
                stage("4b", "SLTP-modify mechanism (diagnostic)",
                      "PASS" if ok4b else "FAIL",
                      f"SL -> {target} retcode={getattr(r4b, 'retcode', None)} "
                      f"comment={getattr(r4b, 'comment', None)!r} now_sl="
                      f"{p4b.sl if p4b else 'n/a'}")
                if ok4b:
                    diag.append(
                        "- 4b confirms the SLTP-modify leg works: retcode 10009 with a "
                        "market-legal SL. So stage 4's failure is purely the "
                        "breakeven-at-fill legality issue in executor.sl_to_breakeven, "
                        "not a broken MT5 modify path.")
                else:
                    diag.append(
                        f"- 4b ALSO failed: retcode={getattr(r4b, 'retcode', None)} "
                        f"{getattr(r4b, 'comment', '')!r} - then the SLTP-modify path "
                        f"itself is broken (executor/MT5 connection), a deeper problem "
                        f"than the buffer issue.")
                pos_obj = p4b or p

        # ---------------- stage 5: close via opposite DEAL + history ----------------
        if not abort:
            p = pos_obj
            is_buy = p.type == mt5.POSITION_TYPE_BUY
            res5, req5 = close_ticket(ticket, sym, p.volume, is_buy, "looptest close")
            if res5 is None:
                stage(5, "close + history verify", "FAIL",
                      f"order_send None: {mt5.last_error()}")
            else:
                log(f"close order_send: retcode={res5.retcode} comment={res5.comment!r} "
                    f"order={res5.order} deal={getattr(res5, 'deal', None)} "
                    f"price={res5.price} volume={req5['volume']}")
                time.sleep(1.2)
                gone = not (mt5.positions_get(ticket=ticket) or ())
                deals = mt5.history_deals_get(position=ticket)
                if not deals:
                    time.sleep(1.5)
                    deals = mt5.history_deals_get(position=ticket)
                for d in (deals or []):
                    log("  " + deal_line(d))
                out_deals = [d for d in (deals or []) if d.entry == mt5.DEAL_ENTRY_OUT]
                rc_ok = res5.retcode == mt5.TRADE_RETCODE_DONE
                ok = rc_ok and gone and bool(out_deals)
                pl = sum(d.profit + d.commission + d.swap for d in (deals or []))
                stage(5, "close + history verify", "PASS" if ok else "FAIL",
                      f"close retcode={res5.retcode} gone_from_positions={gone} "
                      f"out_deals={[d.ticket for d in out_deals]} "
                      f"close_price={out_deals[0].price if out_deals else 'n/a'} "
                      f"roundtrip_pl={pl:.2f}")
                if not ok:
                    diag.append(
                        f"- Stage 5 failed: close retcode={res5.retcode} "
                        f"({retcode_hint(res5.retcode)}), position_gone={gone}, "
                        f"out_deals={[d.ticket for d in out_deals]}. Module: close "
                        f"request construction (filling mode / deviation / price) or "
                        f"history visibility timing.")

        # ---------------- stage 6: ledger row verify ----------------
        if exec_result is not None:
            con = sqlite3.connect(DB, timeout=5)
            try:
                rows = con.execute(
                    "SELECT id,ts,symbol,side,lot,entry,sl,tp,order_type,ticket,status,detail"
                    " FROM trades WHERE msg_id=? ORDER BY id", (ctx.get("msg_id"),)).fetchall()
            finally:
                con.close()
            log(f"ledger rows for msg_id={ctx.get('msg_id')}: {rows}")
            if not rows:
                stage(6, "ledger row", "FAIL",
                      f"no row found in signals.db for msg_id={ctx.get('msg_id')}")
                diag.append("- Stage 6 failed: executor._record did not persist the row "
                             "- executor.py DB write path is broken.")
            else:
                r = rows[-1]
                n_rows_ok = len(rows) == 1
                st_ok = r[10] == exec_result.get("status")
                sym_ok = r[0] is not None and r[2] == (exec_result.get("resolved") or sym)
                side_ok = r[3] == exec_result.get("side")
                tk_ok = r[9] == exec_result.get("ticket")
                sl_ok = r[6] is not None and r[6] != 0
                lot_ok = r[4] is None or abs((r[4] or 0) - (exec_result.get("lot") or 0)) < 1e-9 \
                    if exec_result.get("status") == "executed" else True
                ok = all([n_rows_ok, st_ok, sym_ok, side_ok, tk_ok, sl_ok, lot_ok])
                fails = [t for c, t in [
                    (n_rows_ok, f"rows={len(rows)} (want 1)"),
                    (st_ok, f"status={r[10]!r} vs {exec_result.get('status')!r}"),
                    (sym_ok, f"symbol={r[2]!r} vs {exec_result.get('resolved')!r}"),
                    (side_ok, f"side={r[3]!r} vs {exec_result.get('side')!r}"),
                    (tk_ok, f"ticket={r[9]} vs {exec_result.get('ticket')}"),
                    (sl_ok, f"sl={r[6]}"),
                    (lot_ok, f"lot={r[4]}"),
                ] if not c]
                stage(6, "ledger row", "PASS" if ok else "FAIL",
                      f"row={tuple(r)}" + (f" ; mismatch: {'; '.join(fails)}" if fails else ""))

    except Exception:
        log("EXCEPTION DURING TEST:\n" + traceback.format_exc())
        stage("X", "unexpected exception", "FAIL", traceback.format_exc().splitlines()[-1])
        diag.append("- Test crashed with an exception (see raw log) - fix the harness "
                    "or the module named in the traceback.")
    finally:
        try:
            cleanup_ok = cleanup(ticket, sym)
            if not cleanup_ok:
                diag.append("- Cleanup could not close the test position - manual "
                            "intervention required; report the ticket above.")
        except Exception:
            log("cleanup exception:\n" + traceback.format_exc())
            cleanup_ok = False
        try:
            write_report(ctx, diag, cleanup_ok)
        except Exception:
            log("report write failed:\n" + traceback.format_exc())
        try:
            mt5.shutdown()
        except Exception:
            pass

    log("")
    log("STAGE SUMMARY")
    for n, name, st, detail in STAGES:
        log(f"  [{st:>4}] {n}: {name} :: {detail[:220]}")
    failed = [s for s in STAGES if s[2] == "FAIL"]
    log(f"RESULT: {len(failed)} FAIL / {len(STAGES)} stages"
        + ("" if not failed else f" -> {', '.join(str(f[0]) for f in failed)}"))
    return 0 if not failed and cleanup_ok else 1


if __name__ == "__main__":
    sys.exit(main())
