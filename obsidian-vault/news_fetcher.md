---
slug: news_fetcher
type: note
graph: gitnexus
---

"""High-impact USD news calendar fetcher + entry gate for the signal relay.

Feed: https://nfs.faireconomy.media/ff_calendar_thisweek.json (ForexFactory
weekly calendar; free, no key). Only High-impact USD events are kept and
written to news_calendar.json (atomic: tmp + os.replace) as a list of
{dt_utc, title, impact}. Past events (whose pre/post window has fully
elapsed) are purged on every refresh, so the file stays tiny.

Refresh is safe to run every 15 min (the watchdog calls it):
  - 3 fetch attempts, 30s timeout each
  - schema drift tolerated (several key/date aliases, unknown -> skipped)
  - on ANY failure the existing calendar file is left untouched

executor.execute() consults block_reason() AFTER its HALT/dedupe guards and
skips NEW entries that fall inside [event - pre_minutes, event + post_minutes]
of any High USD event (status 'skipped_news_window'). Open positions, stops
and manage.py are never touched by this module.

Standalone:  C:/Users/voidk/miniconda3/python.exe news_fetcher.py
             (exit 0 = calendar refreshed, 1 = failed, old file kept)
"""
import json
import os
import sys
import time as _time_mod
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen as _urlopen

BASE = os.path.dirname(os.path.abspath(__file__))
CALENDAR = os.path.join(BASE, "news_calendar.json")
CONFIG = os.path.join(BASE, "config.json")
DAEMON_LOG = os.path.join(BASE, "daemon.log")
FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
FETCH_TIMEOUT = 30
FETCH_RETRIES = 3
_sleep = _time_mod.sleep  # module alias so tests can stub the retry backoff


# ---- config -----------------------------------------------------------------
def settings(cfg=None):
    """Normalized news_filter settings {enabled, pre_minutes, post_minutes}.
    Defaults: disabled, pre=5, post=3. Never raises."""
    if cfg is None:
        try:
            with open(CONFIG, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:  # noqa: BLE001
            cfg = {}
    nf = cfg.get("news_filter") if isinstance(cfg, dict) else None
    nf = nf if isinstance(nf, dict) else {}
    en = nf.get("enabled", False)
    if isinstance(en, str):
        en = en.strip().lower() in ("1", "true", "yes", "on")
    try:
        pre = int(float(nf.get("pre_minutes", 5)))
    except (TypeError, ValueError):
        pre = 5
    try:
        post = int(float(nf.get("post_minutes", 3)))
    except (TypeError, ValueError):
        post = 3
    return {"enabled": bool(en), "pre_minutes": max(pre, 0), "post_minutes": max(post, 0)}


# ---- schema-drift-tolerant parsing ------------------------------------------
def _first(ev, *names):
    """First present value among `names` (case-insensitive fallback)."""
    for n in names:
        if n in ev:
            return ev[n]
    low = {str(k).strip().lower(): v for k, v in ev.items()}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    return None


def _parse_dt(v):
    """Best-effort datetime (UTC) from a feed date value. None when unusable."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        if f > 1e12:  # epoch milliseconds
            f /= 1000.0
        try:
            return datetime.fromtimestamp(f, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    s = str(v).strip()
    if not s:
        return None
    try:
        if s.endswith(("Z", "z")):
            s = s[:-1] + "+00:00"
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%m-%d-%Y %I:%M%p",
                "%d %b %Y %H:%M", "%Y-%m-%d"):
        try:
            d = datetime.strptime(s, fmt)
            return d.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _is_high(impact, title):
    """True when the event's impact (or title) indicates High impact."""
    imp = str(impact or "").strip().lower()
    if "high" in imp or "impact-high" in imp:
        return True
    return "high impact" in str(title or "").lower()


def filter_events(raw, now=None):
    """Feed (list of dicts, any schema drift tolerated) -> sorted list of
    {dt_utc, title, impact} for HIGH-impact USD events only. Never raises."""
    now = now or datetime.now(timezone.utc)
    out = []
    if not isinstance(raw, (list, tuple)):
        if isinstance(raw, dict):  # wrapped payload, e.g. {"events": [...]}
            raw = next((v for v in raw.values() if isinstance(v, list)), [])
        else:
            return out
    for ev in raw:
        try:
            if not isinstance(ev, dict):
                continue
            country = str(_first(ev, "country", "currency") or "").strip().upper()
            if country != "USD":
                continue
            title = _first(ev, "title", "event", "name")
            impact = _first(ev, "impact", "importance")
            if not _is_high(impact, title):
                continue
            dt = _parse_dt(_first(ev, "date", "datetime", "start", "time"))
            if dt is None:
                continue
            out.append({"dt_utc": dt.astimezone(timezone.utc).isoformat(),
                        "title": str(title or "USD event").strip()[:120],
                        "impact": "High"})
        except Exception:  # noqa: BLE001 - one bad event never kills the batch
            continue
    out.sort(key=lambda e: e["dt_utc"])
    return out


# ---- fetch + atomic write ----------------------------------------------------
def _fetch(url=FEED_URL, retries=FETCH_RETRIES, timeout=FETCH_TIMEOUT):
    """Raw feed bytes, or None after `retries` failed attempts."""
    last = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0 (signal-relay news filter)"})
            with _urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - network/HTTP errors are expected
            last = e
            print(f"news_fetcher: fetch attempt {attempt}/{retries} failed: "
                  f"{type(e).__name__}: {e}")
            if attempt < retries:
                _sleep(min(2 * attempt, 5))
    print(f"news_fetcher: fetch failed after {retries} attempt(s) "
          f"({type(last).__name__ if last else 'unknown'}) - keeping existing calendar")
    return None


def refresh(url=FEED_URL, retries=FETCH_RETRIES, timeout=FETCH_TIMEOUT, now=None):
    """Fetch -> keep High USD -> purge past -> atomic write.

    Returns (ok, n_events). On ANY failure (network, bad JSON, disk) the
    existing news_calendar.json is left untouched."""
    now = now or datetime.now(timezone.utc)
    raw = _fetch(url, retries, timeout)
    if raw is None:
        return False, 0
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        print("news_fetcher: feed is not valid JSON - keeping existing calendar")
        return False, 0
    events = filter_events(data, now)
    # purge past events - but keep any whose post-window may still be active
    # (post_minutes from config, +5 min slack) so a just-released event still
    # blocks entries for its configured post window.
    margin = timedelta(seconds=settings()["post_minutes"] * 60 + 300)
    kept = []
    for e in events:
        dt = _parse_dt(e.get("dt_utc"))
        if dt is not None and dt >= now - margin:
            kept.append(e)
    tmp = CALENDAR + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(kept, f, indent=1)
            f.write("\n")
        os.replace(tmp, CALENDAR)  # atomic on the same volume
    except OSError as e:
        print(f"news_fetcher: calendar write failed ({e}) - keeping existing calendar")
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False, len(kept)
    return True, len(kept)


# ---- gate --------------------------------------------------------------------
def load_events(path=None):
    """Calendar entries; [] on missing/corrupt file (fail-open)."""
    try:
        with open(path or CALENDAR, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:  # noqa: BLE001
        return []


def block_reason(cfg=None, now=None, events=None):
    """Reason string when `now` sits inside a High-USD news window, else None.

    Window = [event - pre_minutes, event + post_minutes] (config news_filter,
    defaults pre=5/post=3). Missing calendar/corrupt file/disabled filter -> None
    (fail-open: the filter must never become a reason to stop trading)."""
    st = settings(cfg)
    if not st["enabled"]:
        return None
    now = now or datetime.now(timezone.utc)
    events = load_events() if events is None else events
    pre = timedelta(minutes=st["pre_minutes"])
    post = timedelta(minutes=st["post_minutes"])
    for e in events:
        if not isinstance(e, dict):
            continue
        dt = _parse_dt(e.get("dt_utc"))
        if dt is None:
            continue
        if dt - pre <= now <= dt + post:
            return (f"High USD news window: '{e.get('title') or 'USD event'}' at "
                    f"{dt:%Y-%m-%d %H:%M} UTC (block {st['pre_minutes']}m before / "
                    f"{st['post_minutes']}m after)")
    return None


def log_daemon(line):
    """Best-effort append to daemon.log (never raises)."""
    try:
        with open(DAEMON_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC  {line}\n")
    except OSError:
        pass


def main():
    ok, n = refresh()
    if ok:
        print(f"news_fetcher: calendar refreshed - {n} upcoming High USD event(s) "
              f"in {os.path.basename(CALENDAR)}")
        return 0
    print("news_fetcher: refresh FAILED - existing calendar kept")
    return 1


if __name__ == "__main__":
    sys.exit(main())

## Links from
- [[cockpit]]
- [[executor]]
- [[executor_live_new]]
- [[test_suite]]
