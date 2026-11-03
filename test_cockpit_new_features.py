"""New-feature tests: auto-login nonce, /api/token, /api/events limit boundary."""
import hashlib
import hmac
import http.client
import json
import re
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock

from cockpit_runtime import CockpitHandler, _BOOTSTRAP, _BOOTSTRAP_LOCK, issue_bootstrap


class CockpitNewFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile, os
        from pathlib import Path
        scratch = os.environ.get('TMPDIR') or str(Path(__file__).parent / '.cache')
        Path(scratch).mkdir(parents=True, exist_ok=True)
        cls.tmp = tempfile.TemporaryDirectory(dir=scratch)
        root = Path(cls.tmp.name)
        (root / 'cockpit_assets').mkdir()
        (root / 'cockpit_assets/quant.css').write_text('body{}')
        (root / 'cockpit_assets/quant.js').write_text('void 0;')
        (root / 'index.html').write_text('<html><head></head><body>login</body></html>')
        b = SimpleNamespace(BASE=str(root), UI_FILE=str(root/'index.html'), LUXALGO_DIR=str(root))
        # Match the original test's attribute naming: b.state, b.inbox_data, b.journal_data, etc.
        b.state = Mock(return_value={'route': 'state'})
        for name in ('inbox', 'journal', 'neural', 'latency', 'lineage', 'pine',
                     'strategies', 'health', 'channels', 'news', 'luxalgo', 'edge', 'quant',
                     'identity', 'portfolio', 'attribution'):
            setattr(b, name + '_data', Mock(return_value={'route': name}))
        b.token_data = Mock(return_value={'token': 'a' * 32, 'available': True})
        b.mobile_html = Mock(return_value='<div>mobile</div>')
        b.candles_data = Mock(return_value={'candles': [], 'error': 'unavailable'})
        b.pine_series_data = Mock(return_value={'ok': True})
        b.prop_sim_data = Mock(return_value={'available': False})
        b.market_intel_data = Mock(return_value={'rows': []})
        b.trace = Mock(return_value=[])
        b.compile_pine = Mock(return_value={'ok': True})
        b.bus = SimpleNamespace(history=Mock(return_value=[{'event_id': 'offline'}]))
        cls.b = b
        handler = type('IsolatedHandler', (CockpitHandler,), {'backend': b})
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        cls.server.cockpit_token = 'offline-test-credential-not-a-real-token'
        cls.port = cls.server.server_port
        cls.origin = f'http://127.0.0.1:{cls.port}'
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)
        cls.tmp.cleanup()

    def request(self, path, method='GET', body=None, auth=True, headers=None):
        h = {'Authorization': 'Bearer ' + self.server.cockpit_token} if auth else {}
        h.update(headers or {})
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=4)
        conn.request(method, path, body=body, headers=h)
        resp = conn.getresponse()
        result = resp.status, dict(resp.getheaders()), resp.read()
        conn.close()
        return result

    def post(self, body, path='/api/session', **kwargs):
        headers = {'Origin': self.origin, 'Content-Type': 'application/json'}
        headers.update(kwargs.pop('headers', {}))
        return self.request(path, 'POST', body, headers=headers, **kwargs)

    # --- /api/token ---

    def test_token_endpoint_returns_401_unauthenticated(self):
        code, _, _ = self.request('/api/token', auth=False)
        self.assertEqual(code, 401)

    def test_token_endpoint_returns_token_key_when_authenticated(self):
        code, _, body = self.request('/api/token', auth=True)
        self.assertEqual(code, 200)
        data = json.loads(body)
        self.assertIn('token', data)
        self.assertIsInstance(data['token'], str)
        self.assertTrue(len(data['token']) >= 32)

    # --- /api/bootstrap expired nonce ---

    def test_bootstrap_rejects_expired_nonce_with_401(self):
        # Inject a nonce with an expiry in the past
        expired_nonce = 'a' * 32
        with _BOOTSTRAP_LOCK:
            _BOOTSTRAP[expired_nonce] = time.time() - 1  # already expired
        code, _, _ = self.post(json.dumps({'nonce': expired_nonce}), path='/api/bootstrap', auth=False)
        self.assertEqual(code, 401)
        # Clean up
        with _BOOTSTRAP_LOCK:
            _BOOTSTRAP.pop(expired_nonce, None)

    # --- /api/bootstrap with GET method ---

    def test_bootstrap_get_method_returns_404(self):
        # GET /api/bootstrap with auth should return 404 (route not found for GET)
        code, _, _ = self.request('/api/bootstrap', method='GET', auth=True)
        self.assertEqual(code, 404)
        # GET /api/bootstrap without auth should return 401 (auth check comes first)
        code2, _, _ = self.request('/api/bootstrap', method='GET', auth=False)
        self.assertEqual(code2, 401)

    # --- /api/events limit boundary ---

    def test_events_limit_500_accepted_501_rejected(self):
        self.assertEqual(self.request('/api/events?limit=500')[0], 200)
        self.assertEqual(self.request('/api/events?limit=501')[0], 400)

    # --- Nonce format and uniqueness ---

    def test_injected_nonce_is_32_hex_and_differs_between_loads(self):
        # First load
        code1, _, body1 = self.request('/', auth=False)
        self.assertEqual(code1, 200)
        match1 = re.search(rb'window.__hqBootstrap="([0-9a-f]{32})"', body1)
        self.assertIsNotNone(match1, "First page load should contain a 32-hex nonce")
        nonce1 = match1.group(1).decode('ascii')
        self.assertEqual(len(nonce1), 32)
        self.assertTrue(all(c in '0123456789abcdef' for c in nonce1))

        # Second load
        code2, _, body2 = self.request('/', auth=False)
        self.assertEqual(code2, 200)
        match2 = re.search(rb'window.__hqBootstrap="([0-9a-f]{32})"', body2)
        self.assertIsNotNone(match2, "Second page load should contain a 32-hex nonce")
        nonce2 = match2.group(1).decode('ascii')
        self.assertEqual(len(nonce2), 32)
        self.assertTrue(all(c in '0123456789abcdef' for c in nonce2))

        # Nonces must differ
        self.assertNotEqual(nonce1, nonce2, "Nonce must not be reused between page loads")


if __name__ == '__main__':
    unittest.main()
