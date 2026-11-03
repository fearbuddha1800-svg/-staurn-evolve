"""Local read-only HTTP boundary. Unisolated Pine execution is denied over HTTP."""
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import threading
import time
import urllib.error
import urllib.request
from whale_bridge import whale_data
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, unquote, urlsplit

MAX_BODY = 131072
MAX_SOURCE = 65536
PINE_SLOTS = threading.BoundedSemaphore(2)
BOOTSTRAP_TTL = 180
_BOOTSTRAP = {}
_BOOTSTRAP_LOCK = threading.Lock()


def issue_bootstrap():
    """Mint a single-use, short-lived nonce so a loopback page can auto-establish a session.

    The nonce only ever reaches a request that already passed loopback Host validation,
    it expires in BOOTSTRAP_TTL seconds and is consumed on first use. The dashboard
    token remains the root secret; this just removes the manual paste step locally.
    """
    nonce = secrets.token_hex(16)
    now = time.time()
    with _BOOTSTRAP_LOCK:
        for stale in [key for key, expiry in _BOOTSTRAP.items() if expiry < now]:
            _BOOTSTRAP.pop(stale, None)
        _BOOTSTRAP[nonce] = now + BOOTSTRAP_TTL
    return nonce


def _read_env_token():
    """Read DASHBOARD_TOKEN from trade-relay .env for proxy auth (same machine only)."""
    env_path = Path(__file__).resolve().parent.parent / 'trade-relay' / '.env'
    try:
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith('DASHBOARD_TOKEN='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return None

def consume_bootstrap(nonce):
    if not isinstance(nonce, str) or len(nonce) != 32:
        return False
    with _BOOTSTRAP_LOCK:
        expiry = _BOOTSTRAP.pop(nonce, None)
    return expiry is not None and expiry >= time.time()


def token_matches(value, expected):
    return isinstance(value, str) and hmac.compare_digest(value.encode('utf-8'), expected.encode('utf-8'))


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('Nonfinite JSON number')


def load_token(base):
    token = os.environ.get('COCKPIT_TOKEN')
    if token:
        return token
    path = Path(base) / '.cockpit-token'
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        token = path.read_text(encoding='utf-8').strip()
    else:
        token = secrets.token_hex(32)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(token + '\n')
    if len(token) < 32:
        raise RuntimeError('Invalid local cockpit credential file')
    return token


class ApiError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def bounded_int(value, low, high):
    if isinstance(value, bool):
        raise ApiError(400, 'Invalid integer')
    try:
        n = int(value)
    except (ValueError, TypeError):
        raise ApiError(400, 'Invalid integer') from None
    if str(n) != str(value) or not low <= n <= high:
        raise ApiError(400, f'Integer must be between {low} and {high}')
    return n


def chart_args(symbol, timeframe, count):
    if not isinstance(symbol, str) or not re.fullmatch(r'[A-Za-z0-9_. /-]{1,40}', symbol):
        raise ApiError(400, 'Invalid symbol')
    if not isinstance(timeframe, str) or timeframe.upper() not in ('M1','M5','M15','M30','H1','H4','D1'):
        raise ApiError(400, 'Unsupported timeframe')
    return symbol, timeframe.upper(), bounded_int(count, 20, 1500)


def run_pine(backend, source, symbol='XAUUSD', timeframe='H1', count=220):
    """Execute the existing real PineTS series bridge; never call a trading runner.

    Source/bars/time/concurrency are bounded. This is NOT a security sandbox;
    authenticated owners must trust their scripts. No broker order API is used.
    """
    symbol, timeframe, count = chart_args(symbol, timeframe, count)
    if not isinstance(source, str) or not source.strip() or len(source.encode('utf-8')) > MAX_SOURCE:
        raise ApiError(400, 'Pine source must be nonempty and at most 65536 UTF-8 bytes')
    if not PINE_SLOTS.acquire(blocking=False):
        raise ApiError(429, 'Pine runtime busy')
    try:
        # Research runs on CLOSED bars only, matching executor/backtest/quant.
        cd = backend.candles_data(symbol, timeframe, count, closed_only=True)
        if cd.get('error') or not cd.get('candles'):
            raise ApiError(503, 'MT5 candle data unavailable')
        candles = [{'openTime': c[0]*1000, 'open': c[1], 'high': c[2], 'low': c[3],
                    'close': c[4], 'volume': c[5]} for c in cd['candles']]
        # TemporaryDirectory also removes source/data on timeout or bridge failure.
        scratch = os.environ.get('TMPDIR') or str(Path(backend.BASE) / '.cache')
        Path(scratch).mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='cockpit-pine-', dir=scratch) as directory:
            script = Path(directory) / 'owner.pine'
            data = Path(directory) / 'candles.json'
            script.write_text(source, encoding='utf-8')
            data.write_text(json.dumps(candles), encoding='utf-8')
            tf = {'M1':'1','M5':'5','M15':'15','M30':'30','H1':'60','H4':'240','D1':'D'}[timeframe]
            result = backend.subprocess.run(
                ['node', str(Path(backend.BASE) / 'pine_series_bridge.js'), str(script), str(data),
                 cd.get('symbol') or symbol, tf], cwd=backend.BASE,
                capture_output=True, text=True, encoding='utf-8', timeout=30)
            if result.returncode:
                raise ApiError(422, 'PineTS bridge execution failed')
            try:
                payload = json.loads(result.stdout.strip())
            except (ValueError, TypeError):
                raise ApiError(502, 'Invalid PineTS bridge response') from None
            if not isinstance(payload, dict):
                raise ApiError(502, 'Invalid PineTS bridge response')
            if not payload.get('ok'):
                # Runtime compiler errors can include source text; never expose credentials.
                raise ApiError(422, 'PineTS rejected this script')
            payload.setdefault('series', {})
            payload.setdefault('marks', [])
            return payload
    except backend.subprocess.TimeoutExpired:
        raise ApiError(504, 'PineTS execution timed out') from None
    except FileNotFoundError:
        raise ApiError(503, 'PineTS runtime unavailable') from None
    finally:
        PINE_SLOTS.release()


class CockpitHandler(BaseHTTPRequestHandler):
    backend = None
    server_version = 'Cockpit'

    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype='application/json; charset=utf-8', headers=None):
        if not isinstance(body, (bytes, str)):
            body = json.dumps(body, default=str, allow_nan=False)
        data = body.encode('utf-8') if isinstance(body, str) else body
        try:
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy', "frame-ancestors 'none'; object-src 'none'; base-uri 'self'")
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except OSError as exc:
            if getattr(exc, 'winerror', None) not in (10053, 10054, 10058):
                raise

    def _token(self):
        # Server owns credentials: tests may inject an isolated one before serving.
        return self.server.cockpit_token

    def _authenticated(self):
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer ') and token_matches(auth[7:], self._token()):
            return True
        try:
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            value = cookies['cockpit_session'].value
            # Signed expiring cookie; no persistent server-side session secrets.
            nonce, expires, signature = value.split('.')
            message = f'{nonce}.{expires}'
            expected = hmac.new(self._token().encode(), message.encode(), hashlib.sha256).hexdigest()
            return int(expires) > time.time() and token_matches(signature, expected)
        except (KeyError, ValueError, TypeError):
            return False

    def _local_host(self):
        host = self.headers.get('Host', '')
        try:
            parsed = urlsplit('http://' + host)
            local = parsed.hostname == 'localhost' or ipaddress.ip_address(parsed.hostname).is_loopback
            valid = (local and not (parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment)
                     and parsed.port == self.server.server_port and len(self.headers.get_all('Host', [])) == 1)
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise ApiError(403, 'Local host required')

    def _same_origin(self):
        self._local_host()
        if self.headers.get('Origin', '') != 'http://' + self.headers.get('Host', ''):
            raise ApiError(403, 'Local same-origin request required')
        if self.headers.get('Sec-Fetch-Site') not in (None, 'same-origin'):
            raise ApiError(403, 'Local same-origin request required')

    def _session_cookie(self):
        msg = f'{secrets.token_hex(16)}.{int(time.time())+28800}'
        sig = hmac.new(self._token().encode(), msg.encode(), hashlib.sha256).hexdigest()
        return f'cockpit_session={msg}.{sig}; Path=/; HttpOnly; SameSite=Strict; Max-Age=28800'

    def _json_body(self):
        if self.headers.get('Transfer-Encoding'):
            raise ApiError(400, 'Transfer-Encoding unsupported')
        raw = self.headers.get('Content-Length')
        if len(self.headers.get_all('Content-Length', [])) > 1:
            raise ApiError(400, 'Duplicate Content-Length')
        if raw is None:
            raise ApiError(411, 'Content-Length required')
        try:
            size = int(raw)
        except ValueError:
            raise ApiError(400, 'Invalid Content-Length') from None
        if size < 0:
            raise ApiError(400, 'Invalid Content-Length')
        if size > MAX_BODY:
            # Drain a bounded prefix before answering so the client can finish writing
            # and actually read the 413 instead of seeing a mid-upload connection reset.
            remaining = min(size, MAX_BODY + 1048576)
            self.connection.settimeout(2)
            try:
                while remaining > 0:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
            except OSError:
                pass
            raise ApiError(413, 'Request body too large')
        if self.headers.get_content_type() != 'application/json':
            raise ApiError(415, 'application/json required')
        self.connection.settimeout(10)
        try:
            content = self.rfile.read(size)
            if len(content) != size:
                raise ValueError()
            data = json.loads(content.decode('utf-8'), object_pairs_hook=strict_object, parse_constant=reject_constant)
        except (ValueError, UnicodeError):
            raise ApiError(400, 'Malformed JSON body') from None
        if not isinstance(data, dict):
            raise ApiError(400, 'JSON object required')
        return data

    def _request(self, method):
        try:
            self._dispatch(method)
        except ApiError as exc:
            self._send(exc.status, {'ok': False, 'error': exc.message})
        except (TimeoutError, OSError):
            self._send(503, {'ok': False, 'error': 'Resource unavailable'})
        except Exception:
            self._send(500, {'ok': False, 'error': 'Internal cockpit error'})

    def do_GET(self):
        self._request('GET')

    def do_POST(self):
        self._request('POST')

    def do_DELETE(self):
        self._request('DELETE')

    def do_OPTIONS(self):
        self._send(405, {'ok': False, 'error': 'Method not allowed'})

    def _dispatch(self, method):
        self._local_host()
        b = self.backend
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc or parsed.fragment:
            raise ApiError(400, 'Invalid request target')
        if re.search(r'%(?![0-9a-fA-F]{2})', self.path):
            raise ApiError(400, 'Malformed query encoding')
        try:
            path = unquote(parsed.path, errors='strict')
        except UnicodeError:
            raise ApiError(400, 'Invalid path encoding') from None
        try:
            query = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=20, errors='strict')
        except (ValueError, UnicodeError):
            raise ApiError(400, 'Invalid query') from None
        if any(len(v) != 1 for v in query.values()):
            raise ApiError(400, 'Duplicate query parameter')
        q = {k: v[0] for k, v in query.items()}
        if path == '/api/bootstrap' and method == 'POST':
            if q:
                raise ApiError(400, 'Unexpected query parameter')
            self._same_origin()
            data = self._json_body()
            if set(data) != {'nonce'}:
                raise ApiError(400, 'Unexpected bootstrap fields')
            if not consume_bootstrap(data.get('nonce')):
                raise ApiError(401, 'Unauthorized')
            self._send(200, {'ok': True}, headers={'Set-Cookie': self._session_cookie()})
            return
        if path == '/api/session' and method in ('POST', 'DELETE'):
            if q:
                raise ApiError(400, 'Unexpected query parameter')
            self._same_origin()
            if method == 'POST':
                data = self._json_body()
                token = data.get('token')
                if set(data) != {'token'}:
                    raise ApiError(400, 'Unexpected session fields')
                if not token_matches(token, self._token()):
                    raise ApiError(401, 'Unauthorized')
                cookie = self._session_cookie()
            else:
                cookie = 'cockpit_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'
            self._send(200, {'ok': True}, headers={'Set-Cookie': cookie})
            return
        if path.startswith(('/api/', '/vela/')) and not self._authenticated():
            raise ApiError(401, 'Unauthorized')
        if path in ('/api/matrix/snapshot', '/api/matrix/stream'):
            if method != 'GET':
                raise ApiError(405, 'Observation feed is read-only')
            if q:
                raise ApiError(400, 'Unexpected query parameter')
            from matrix_terminal import get_feed, stream
            feed = get_feed(self.server, b)
            if path.endswith('/stream'):
                stream(self, feed)
            else:
                self._send(200, feed.snapshot())
            return
        if method == 'GET' and path == '/api/strategy_registry':
            if q:
                raise ApiError(400, 'Unexpected query parameter')
            from strategy_registry import StrategyRegistry
            registry = StrategyRegistry(Path(b.BASE) / 'strategies')
            entries = registry.refresh(validate=False)
            for entry in entries:
                entry['approved'] = None
                try:
                    approved_path = registry.cache / entry['id'] / 'approved.json'
                    if approved_path.stat().st_size <= 16384:
                        approved = json.loads(approved_path.read_text(encoding='utf-8'), parse_constant=reject_constant)
                        if (approved.get('strategy_id') == entry['id'] and
                                approved.get('revision') == entry.get('revision') and
                                approved.get('gate', {}).get('passed') is True):
                            entry['approved'] = approved
                except (OSError, ValueError, AttributeError):
                    pass
                result_path = registry.cache / entry['id'] / 'backtest.json'
                entry['backtest'] = None
                try:
                    if result_path.stat().st_size > 1048576:
                        continue
                    result = json.loads(result_path.read_text(encoding='utf-8'), parse_constant=reject_constant)
                    if not isinstance(result, dict) or result.get('strategy_id') != entry['id']:
                        continue
                    entry['backtest'] = {
                        'ok': result.get('ok') is True,
                        'error': result.get('error'),
                        'stats': result.get('stats', {}),
                        'closed_trades': result.get('closed_trades', []),
                        'revision': result.get('revision'),
                        'stale': result.get('revision') != entry.get('revision'),
                        'observed_at': result.get('observed_at'),
                        'symbol': result.get('symbol'), 'timeframe': result.get('timeframe'),
                        'provenance': result.get('provenance')}
                except (OSError, ValueError):
                    pass
            from registry_release import TARGETS, read_binding
            deployments = {}
            for target in TARGETS:
                try:
                    binding = read_binding(registry, target)
                    deployments[target] = {k: v for k, v in (binding or {}).items() if k != 'snapshot'} or None
                except (OSError, ValueError):
                    deployments[target] = {'error': 'Invalid deployment; entry signals blocked'}
            self._send(200, {'strategies': entries, 'execution_available': False,
                             'deployments': deployments,
                             'notice': 'Backtests/imports run through trusted CLI only. Deploy selects owner-approved signals; never arms execution.'})
            return
        if method == 'POST' and path == '/api/strategy_registry/deploy':
            self._same_origin()
            if q:
                raise ApiError(400, 'Unexpected query parameter')
            data = self._json_body()
            if set(data) != {'strategy_id', 'revision', 'target'}:
                raise ApiError(400, 'Expected strategy_id, revision, target')
            if not all(isinstance(value, str) for value in data.values()):
                raise ApiError(400, 'Deployment values must be strings')
            from strategy_registry import StrategyRegistry
            from registry_release import deploy
            registry = StrategyRegistry(Path(b.BASE) / 'strategies')
            registry.refresh(validate=False)
            try:
                binding = deploy(registry, data['strategy_id'], data['revision'], data['target'])
            except (ValueError, OSError, StopIteration) as exc:
                raise ApiError(409, 'Deployment rejected: ' + str(exc)[:300]) from exc
            self._send(200, {'ok': True, 'deployment': binding, 'execution_armed': False})
            return
        if method == 'POST' and path == '/api/pine/compile':
            self._same_origin()
            if q:
                raise ApiError(400, 'Unexpected query parameter')
            data = self._json_body()
            if set(data) - {'script', 'symbol', 'timeframe', 'count'}:
                raise ApiError(400, 'Unexpected compile fields')
            script = data.get('script')
            if not isinstance(script, str) or not script.strip():
                raise ApiError(400, 'Nonempty Pine source required')
            if len(script.encode('utf-8')) > MAX_SOURCE:
                raise ApiError(413, 'Pine source too large')
            chart_args(data.get('symbol', 'XAUUSD'), data.get('timeframe', 'H1'), data.get('count', 220))
            # A bounded subprocess with inherited filesystem/environment is NOT an
            # isolation boundary. Keep trusted offline helpers; never call them here.
            raise ApiError(503, 'Pine simulation unavailable: credential-free OS-isolated worker not configured')
        if method != 'GET':
            raise ApiError(404, 'Route not found')
        if path == '/api/neural.health':
            if q:
                raise ApiError(400, 'Unexpected query parameter')
            from neural_pipeline import health as neural_health
            self._send(200, neural_health(b.DB))
            return
        if path == '/api/broker':
            if q:
                raise ApiError(400, 'Unexpected query parameter')
            # Pure health observation only: never expose attach/reset/enable here.
            self._send(200, b.broker_health())
            return
        simple = {'state': b.state, 'inbox': b.inbox_data, 'journal': b.journal_data,
                  'mobile': b.mobile_html, 'golden-eye': b.golden_eye_data, 'ai-brain': b.ai_brain_data,
                  'neural': b.neural_data, 'latency': b.latency_data,
                  'lineage': b.lineage_data, 'pine': b.pine_data, 'strategies': b.strategies_data,
                  'health': b.health_data, 'channels': b.channels_data, 'news': b.news_data,
                  'luxalgo': b.luxalgo_data, 'whale': whale_data, 'edge': b.edge_data, 'quant': b.quant_data,
                  'token': b.token_data, 'identity': b.identity_data,
                  'portfolio': b.portfolio_data, 'attribution': b.attribution_data}
        name = path.removeprefix('/api/')
        if path.startswith('/api/') and name in simple:
            if q:
                raise ApiError(400, 'Unexpected query parameter')
            self._send(200, simple[name](), **({'ctype':'text/html; charset=utf-8'} if name == 'mobile' else {}))
            return
        allowed_queries = {'/api/candles': {'symbol','timeframe','count'},
                           '/api/pine_series': {'strategy','symbol','timeframe','count'},
                           '/api/prop_sim': {'paths'}, '/api/market_intel': {'kind','limit'},
                           '/api/events': {'trace_id','stream','limit','exclude'}}
        if path in allowed_queries and set(q) - allowed_queries[path]:
            raise ApiError(400, 'Unexpected query parameter')
        if path in ('/api/candles', '/api/pine_series'):
            symbol, tf, count = chart_args(q.get('symbol','XAUUSD'), q.get('timeframe','H1'),
                                          q.get('count', 220 if path.endswith('pine_series') else 200))
            if path.endswith('pine_series'):
                strategy = q.get('strategy', 'strategies/rsi_ema_trend.pine')
                root = Path(b.BASE).resolve()
                target = (root / strategy).resolve()
                if (not strategy or len(strategy) > 240 or '\\' in strategy
                        or Path(strategy).is_absolute() or target.suffix != '.pine'
                        or not target.is_relative_to(root)):
                    raise ApiError(400, 'Invalid Pine strategy path')
                try:
                    result = b.pine_series_data(strategy, symbol, tf, count)
                except ApiError:
                    raise
                except Exception as e:
                    raise ApiError(503, 'Pine series unavailable: ' + str(e))
                self._send(200, result)
                return
            result = b.candles_data(symbol, tf, count)
            self._send(503 if result.get('error') else 200, result)
        elif path == '/api/prop_sim':
            self._send(200, b.prop_sim_data(bounded_int(q.get('paths',2000),100,20000)))
        elif path == '/api/market_intel':
            kind = q.get('kind','congress')
            if kind not in ('congress','insider','contracts','lobbying','short_volume'):
                raise ApiError(400, 'Unsupported market intelligence kind')
            self._send(200, b.market_intel_data(kind,bounded_int(q.get('limit',8),1,50)))
        elif path == '/api/events':
            if q.get('stream','0') not in ('0','1'):
                raise ApiError(400, 'Invalid stream flag')
            exclude = q.get('exclude') or None
            if exclude is not None and not re.fullmatch(r'[a-z_]{1,40}', exclude):
                raise ApiError(400, 'Invalid exclude type')
            events = b.bus.history(bounded_int(q.get('limit', 100), 1, 500),
                                   trace_id=q.get('trace_id') or None, exclude=exclude)
            if q.get('stream') == '1' or 'text/event-stream' in self.headers.get('Accept',''):
                # Finite replay snapshot, NOT a live subscription.
                body = ': finite event replay snapshot\n\n' + ''.join(
                    f'data: {json.dumps(e, default=str)}\n\n' for e in events) + 'data: [DONE]\n\n'
                self._send(200, body, 'text/event-stream', {'X-Event-Stream-Mode':'snapshot-replay'})
            else:
                self._send(200, events)
        elif path.startswith('/api/trade-relay/'):
            # Same-origin proxy to trade-relay (localhost:8484) so the cockpit UI can
            # read live orders/accounts without CORS or exposing the bearer token.
            if method != 'GET':
                raise ApiError(405, 'Trade-relay proxy is read-only')
            if q:
                raise ApiError(400, 'Unexpected query parameter')
            relay_path = path[len('/api/trade-relay/'):]
            if not relay_path or relay_path.startswith('..') or '\\\\' in relay_path:
                raise ApiError(400, 'Invalid trade-relay path')
            token = _read_env_token()
            req = urllib.request.Request('http://localhost:8484/api/' + relay_path, method='GET')
            if token:
                req.add_header('Authorization', 'Bearer ' + token)
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    body = resp.read()
                    ctype = resp.headers.get('Content-Type', 'application/json')
                    self._send(resp.status, body, ctype)
            except urllib.error.HTTPError as exc:
                body = exc.read()
                self._send(exc.code, body, 'application/json')
            except Exception as exc:
                raise ApiError(503, 'Trade-relay unreachable: ' + str(exc)[:200])
            return
        elif path.startswith('/api/trace/'):
            if q:
                raise ApiError(400, 'Unexpected query parameter')
            ticket = bounded_int(path[len('/api/trace/'):], 1, 9223372036854775807)
            self._send(200, b.trace(ticket))
        elif path.startswith('/vela/'):
            allowed = {'/vela/vela.global.js': ('Vela','dist','vela.global.js'),
                       '/vela/vela-pinets.global.min.js': ('Vela-pinets','dist','vela-pinets.global.min.js')}
            target = allowed.get(path)
            if not target or not Path(b.LUXALGO_DIR, *target).is_file():
                raise ApiError(404, 'Asset not found')
            self._send(200, Path(b.LUXALGO_DIR,*target).read_bytes(), 'application/javascript; charset=utf-8')
        elif path.startswith('/assets/'):
            allowed = {'/assets/staurn-logo.svg': ('staurn-logo.svg', 'image/svg+xml'),
                       '/assets/matrix-terminal.js': ('matrix-terminal.js', 'application/javascript; charset=utf-8'),
                       '/assets/matrix-terminal.css': ('matrix-terminal.css', 'text/css; charset=utf-8'),
                       '/assets/strategy-registry.js': ('strategy-registry.js', 'application/javascript; charset=utf-8'),
                       '/assets/matrix-panels.js': ('matrix-panels.js', 'application/javascript; charset=utf-8'),
                       '/assets/matrix-panels.css': ('matrix-panels.css', 'text/css; charset=utf-8'),
                       '/assets/quant.css': ('quant.css', 'text/css; charset=utf-8'),
                       '/assets/quant.js': ('quant.js', 'application/javascript; charset=utf-8'),
                       '/assets/quant-matrix.css': ('quant-matrix.css', 'text/css; charset=utf-8'),
                       '/assets/hq-tokens.css': ('hq-tokens.css', 'text/css; charset=utf-8'),
                       '/assets/hq-shell.css': ('hq-shell.css', 'text/css; charset=utf-8'),
                       '/assets/quant-client.js': ('quant-client.js', 'application/javascript; charset=utf-8'),
                       '/assets/vela.global.js': ('vela.global.js', 'application/javascript; charset=utf-8'),
                       '/assets/vela-pinets.global.js': ('vela-pinets.global.js', 'application/javascript; charset=utf-8'),
                       '/assets/vela-chart.js': ('vela-chart.js', 'application/javascript; charset=utf-8')}
            target = allowed.get(path)
            if not target or q:
                raise ApiError(404, 'Asset not found')
            root = Path(b.BASE, 'cockpit_assets').resolve()
            asset = (root / target[0]).resolve()
            if asset.parent != root or not asset.is_file():
                raise ApiError(404, 'Asset not found')
            self._send(200, asset.read_bytes(), target[1])
        elif path == '/' and not q:
            try:
                page = Path(b.UI_FILE).read_bytes()
            except OSError:
                raise ApiError(503, 'Cockpit UI unavailable') from None
            # Loopback-only auto-login: hand this one page a single-use nonce it can
            # trade for a session cookie, so the owner never pastes the token locally.
            nonce = issue_bootstrap()
            inject = f'<script>window.__hqBootstrap="{nonce}";</script>'.encode('utf-8')
            if b'</head>' in page:
                page = page.replace(b'</head>', inject + b'</head>', 1)
            elif b'</html>' in page:
                page = page.replace(b'</html>', inject + b'</html>', 1)
            else:
                page = inject + page
            self._send(200, page, 'text/html; charset=utf-8')
        else:
            raise ApiError(404, 'Route not found')
