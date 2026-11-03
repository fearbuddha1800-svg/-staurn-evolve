"""AI tier for the signal relay: OCR for image signals, LLM extraction for
hard-to-read text, price-sanity and cross-channel dedupe. Only invoked when the
fast regex path fails - clean text signals still execute in milliseconds."""
import json
import os
import re
import subprocess
import threading
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
OCR_PS1 = os.path.join(BASE, "ocr.ps1")
CONFIG = os.path.join(BASE, "config.json")
DEDUPE = os.path.join(BASE, "dedupe.json")
OCR_TMP = os.path.join(BASE, "ocr_tmp")
_env = None

SYS_PROMPT = (
    "You extract trading signals from messy Telegram trading-channel posts. "
    "Reply with ONLY a JSON object, no markdown, no explanation:\n"
    '{"is_signal": true, "action": "buy|sell", "symbol": "XAUUSD", '
    '"entry": 2650.5, "sl": 2640.0, "tps": [2660.0, 2675.0], '
    '"order_type": "market|limit|stop", "confidence": 0.0, "reason": "short note"}\n'
    "or {\"is_signal\": false, \"reason\": \"...\"}. Rules: is_signal=false for recaps of "
    "past trades, results/win screenshots, news, education, promo, or opinion. "
    "Map GOLD->XAUUSD, BTC->BTCUSD, US30/DOW->US30, NAS100->US100, GER40/DAX->GER40. "
    "entry='market' for immediate entries. sl/tps null when absent. "
    "Set confidence below 0.6 when anything is ambiguous. "
    "If the post describes an ALREADY-RUNNING or completed trade, is_signal=false."
)


def _load_env():
    global _env
    if _env is None:
        _env = {}
        p = os.path.join(os.path.expanduser("~"), ".hermes", ".env")
        if os.path.exists(p):
            with open(p, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = re.match(r"\s*([A-Za-z0-9_]+)\s*=\s*(\S+)", line)
                    if m:
                        _env[m.group(1).upper()] = m.group(2).strip().strip('"').strip("'")
    return _env


def ai_cfg():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f).get("ai", {}) or {}


def _hermes_model_cfg():
    """Read only the model mapping; never borrow fields from other sections."""
    try:
        import yaml
        p = os.path.join(os.path.expanduser("~"), ".hermes", "config.yaml")
        with open(p, encoding="utf-8-sig") as f:
            model = (yaml.safe_load(f) or {}).get("model", {})
        return model if isinstance(model, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


# Only API-key providers with an OpenAI chat-completions contract belong here.
# OAuth subscriptions (xai-oauth/openai-codex/nous) require Hermes' auth and
# transport adapters; an unrelated .env key is NEVER a substitute for those.
_CHAT_PROVIDERS = {
    "nvidia": ("NVIDIA_API_KEY", "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    "openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    "openai": ("OPENAI_API_KEY", "OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "openai-api": ("OPENAI_API_KEY", "OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    "groq": ("GROQ_API_KEY", "GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
    "xai": ("XAI_API_KEY", "XAI_BASE_URL", "https://api.x.ai/v1"),
}


def _llm_candidates():
    """Resolve one coherent provider/base/model/key, or abstain without I/O.

    ai.provider + ai.model explicitly pin this standalone service; otherwise
    follow Hermes' model mapping. Never mix either mapping with the other.
    Presence of a key proves wiring, not credit balance or model availability.
    """
    env = _load_env()
    cfg = ai_cfg()
    hm = _hermes_model_cfg()
    pinned = bool(cfg.get("provider"))
    selected = cfg if pinned else hm
    provider = str(selected.get("provider") or "").strip().lower()
    defaults = _CHAT_PROVIDERS.get(provider)
    if defaults is None and provider != "custom":
        return []
    mode = selected.get("api_mode")
    if mode and mode not in ("chat_completions", "chat", "openai"):
        return []
    keyvar = selected.get("key_env") or (defaults[0] if defaults else None)
    key = env.get(keyvar, "").strip() if keyvar else ""
    model = selected.get("model" if pinned else "default")
    base = selected.get("base_url") or (env.get(defaults[1]) or defaults[2] if defaults else None)
    if not key or not isinstance(model, str) or not model.strip() or not isinstance(base, str):
        return []
    from urllib.parse import urlsplit
    url = urlsplit(base)
    if url.scheme not in ("http", "https") or not url.netloc or url.query or url.fragment:
        return []
    if base.rstrip("/").endswith(("/chat/completions", "/responses")):
        return []  # base_url must name the API root, not an operation.
    return [(key, base.rstrip("/"), model.strip())]


def ocr_image(path):
    """Windows OCR (offline, ~1s). Returns extracted text or ''. """
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", OCR_PS1, "-ImagePath", path],
            capture_output=True, text=True, timeout=60)
        return (r.stdout or "").strip()
    except Exception as e:  # noqa: BLE001
        print("ocr failed:", e)
        return ""


async def ocr_message(msg):
    """Download the photo from a Telethon message and OCR it. Returns text or ''."""
    os.makedirs(OCR_TMP, exist_ok=True)
    path = os.path.join(OCR_TMP, f"msg_{msg.id}.jpg")
    p = await msg.download_media(file=path)
    if not p or not os.path.exists(p):
        return ""
    return ocr_image(p)


def _call_candidates(text, cands, timeout, max_tokens):
    """Run the existing multi-candidate LLM loop. Returns (data_or_None, info)."""
    last = "no candidate ran"
    for key, base, model in cands:
        payload = json.dumps({
            "model": model, "temperature": 0, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": SYS_PROMPT},
                         {"role": "user", "content": text[:4000]}],
        }).encode()
        req = urllib.request.Request(
            base.rstrip("/") + "/chat/completions", data=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read())
            content = out["choices"][0]["message"].get("content") or \
                out["choices"][0]["message"].get("reasoning_content") or ""
            m = re.search(r"\{.*\}", content, re.S)
            if not m:
                last = "llm returned no JSON"
                continue
            data = json.loads(m.group(0))
            return data, f"{model} {time.time() - t0:.1f}s"
        except Exception as e:  # noqa: BLE001
            last = f"{model}: {type(e).__name__} {str(e)[:80]}"
    return None, last


# ---- bounded AI routing -----------------------------------------------------
# The AI tier must never block or overwhelm the trade path. At most
# ai.max_concurrency calls run at once, each bounded by ai.timeout_s, and total
# estimated spend is capped by ai.budget_total. When any bound is hit the router
# ABSTAINS and llm_extract returns (None, reason) - exactly the pre-existing
# "no AI signal" result, so the caller still falls back to the regex parse and
# no new failure mode is introduced.
_router = None
_router_lock = threading.Lock()


class _LLMProvider:
    """One Provider whose call() runs the existing multi-candidate loop."""

    name = "ai_filter"

    def __init__(self, cands, timeout, max_tokens):
        self._cands, self._timeout, self._max_tokens = cands, timeout, max_tokens

    def is_available(self):
        return bool(self._cands)

    def cost(self):
        return 1.0

    def call(self, prompt, **kwargs):
        return _call_candidates(prompt, self._cands, self._timeout, self._max_tokens)


def _router_instance(cands, cfg):
    """Lazy singleton router; returns None when model_router is unavailable."""
    global _router
    if _router is not None:
        return _router
    with _router_lock:
        if _router is None:
            try:
                import model_router as mr
            except ImportError:
                return None
            try:
                _router = mr.ModelRouter(
                    mr.RouterConfig(
                        max_concurrency=int(cfg.get("max_concurrency", 2)),
                        deadline_s=float(cfg.get("timeout_s", 12)),
                        budget_total=float(cfg.get("budget_total", 500)),
                        concurrency_timeout_s=float(cfg.get("concurrency_timeout_s", 5)),
                    ),
                    [_LLMProvider(cands, int(cfg.get("timeout_s", 12)),
                                  int(cfg.get("max_tokens", 1024)))])
            except Exception as e:  # noqa: BLE001
                print("ai_filter: model router unavailable:", type(e).__name__, e)
                return None
    return _router


def llm_extract(text):
    """LLM extraction of a signal. Returns (signal_dict_or_None, info_str).

    Routed through model_router when available so a burst of channel traffic
    cannot spawn unbounded concurrent AI calls. Abstention is reported as a
    plain failure to extract, never as a fabricated signal.
    """
    if not ai_cfg().get("enabled", True):
        return None, "ai disabled"
    cands = _llm_candidates()
    if not cands:
        return None, "no LLM key in .env"
    cfg = ai_cfg()
    router = _router_instance(cands, cfg)
    if router is None:
        # Router unavailable: preserve the original unbounded behaviour rather
        # than dropping AI extraction entirely.
        return _call_candidates(text, cands, int(cfg.get("timeout_s", 12)),
                                int(cfg.get("max_tokens", 1024)))
    result = router.route(text)
    if result.abstained:
        return None, f"ai abstained: {result.status.value} ({result.reason})"
    if not result.ok:
        return None, result.reason or "ai call failed"
    if not isinstance(result.data, tuple) or len(result.data) != 2:
        return None, "ai returned an unexpected result shape"
    return result.data


def to_parsed(ai):
    """Normalize an LLM extraction into the parser's dict shape (None if invalid)."""
    if not ai or not ai.get("is_signal"):
        return None
    action = (ai.get("action") or "").lower()
    if action not in ("buy", "sell") or not ai.get("symbol"):
        return None
    return {"is_signal": True, "parse_ok": True, "action": action,
            "symbol": str(ai["symbol"]).upper(), "entry": ai.get("entry", "market"),
            "sl": ai.get("sl"), "tps": ai.get("tps") or [],
            "order_type": ai.get("order_type", "market"),
            "confidence": float(ai.get("confidence", 0) or 0), "raw": ""}


# ---- results/recap screen --------------------------------------------------
# Telegram channels mix LIVE entry signals with OLD result/recap posts
# ('TP1 hit +180 pips', 'profit booked', win screenshots). A recap carries
# side+symbol+numbers too, so the regex fast-path happily parses it as a NEW
# trade. This cheap screen flags result/win language so the daemon can demand
# AI confirmation before such a post is ever allowed to execute.
_RESULT_EMOJIS = (
    "\U0001F3C6"  # trophy
    "\U0001F3AF"  # direct hit
    "\u2705"      # white heavy check mark
    "\U0001F4B0"  # money bag
    "\U0001F4B5"  # dollar banknote
    "\U0001F947"  # 1st-place medal
    "\U0001F389"  # party popper
    "\U0001F911"  # money-mouth face
    "\U0001F525"  # fire
)
_RESULTS_RE = re.compile(
    r"\b(?:tp|t\.p|take\s*profit|sl|s\.l|stops?|stop\s*loss|targets?|tgt)"
    r"[\s:\-]*\d{0,2}[\s:\-]*(?:is|was|has\s*been|just|already|safely|fully|partially)?\s*hit\b"
    r"|\+\s*\d+(?:[.,]\d+)?\s*(?:pips?|pts?|points?)\b"
    r"|\bbanked\b"
    r"|\bbooked\b"
    r"|\bin\s+(?:full\s+)?profit\b"
    r"|\bclosed\s+at\b"
    r"|\bclosed\s+(?:the\s+|our\s+|this\s+)?(?:trade|position|deal)\b"
    r"|\bwe\s+(?:just\s+|finally\s+)?hit\b"
    r"|\bcongrats\w*\b|\bcongratulations\b"
    r"|\bresults?\b"
    r"|\brecap\w*\b"
    r"|\bwin(?:s|\s*winning)?\s*streaks?\b"
    "|[" + _RESULT_EMOJIS + "]",
    re.IGNORECASE)


def looks_like_results(text):
    """True when the text reads like a result/recap/win post rather than a
    fresh entry signal ('tp hit', '+180 pips', 'banked', 'booked', 'closed at',
    'congrats', win emojis, ...). Cheap pre-filter - the caller confirms with
    the AI validator before routing the post away from execution."""
    return bool(text) and bool(_RESULTS_RE.search(text))


def price_sane(symbol, entry, tol_pct=None):
    """Entry-vs-live-price sanity (stale-signal killer). Returns error string or ''."""
    try:
        import MetaTrader5 as mt5
        import executor
    except Exception:  # noqa: BLE001
        return ""
    sym = executor.resolve_symbol(symbol)
    if not sym:
        return f"symbol {symbol} not on broker"
    tick = mt5.symbol_info_tick(sym)
    if not tick:
        return "no live tick"
    ref = (tick.ask + tick.bid) / 2.0
    tol = ref * float(tol_pct or ai_cfg().get("price_tolerance_pct", 0.6)) / 100.0
    if isinstance(entry, (int, float)) and abs(float(entry) - ref) > tol:
        return f"entry {entry} far from live {ref:.5g} - stale or invalid"
    return ""


def dedupe_key(parsed):
    e = parsed.get("entry")
    e = round(float(e), 2) if isinstance(e, (int, float)) else e
    return f"{parsed.get('symbol')}|{parsed.get('action')}|{e}"


def dedupe_check_and_add(parsed, msg_id, window_s=600):
    """Returns (duplicate, note). Adds an entry unless it's a duplicate."""
    try:
        with open(DEDUPE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:  # noqa: BLE001
        state = {}
    now = time.time()
    key = dedupe_key(parsed)
    for k, rec in state.items():
        if k == key and now - rec.get("t", 0) < window_s:
            return True, f"echo of earlier signal from {rec.get('src','?')} ({int(now - rec['t'])}s ago)"
    state = {k: r for k, r in state.items() if now - r.get("t", 0) < window_s}
    state[key] = {"t": now, "src": msg_id}
    try:
        with open(DEDUPE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:  # noqa: BLE001
        pass
    return False, ""
