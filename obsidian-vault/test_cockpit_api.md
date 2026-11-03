---
slug: test_cockpit_api
type: note
graph: gitnexus
---

"""Real ephemeral loopback HTTP tests with an entirely offline backend."""
import hashlib
import hmac
import http.client
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from cockpit_runtime import CockpitHandler


class CockpitHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = os.environ.get('TMPDIR') or str(Path(__file__).parent / '.cache')
        Path(scratch).mkdir(parents=True, exist_ok=True)
        cls.tmp = tempfile.TemporaryDirectory(dir=scratch)
        root = Path(cls.tmp.name)
        (root / 'cockpit_assets').mkdir()
        (root / 'cockpit_assets/quant.css').write_text('body{}')
        (root / 'cockpit_assets/quant.js').write_text('void 0;')
        (root / 'index.html').write_text('<html>login</html>')
        b = SimpleNamespace(BASE=str(root), UI_FILE=str(root/'index.html'), LUXALGO_DIR=str(root))
        cls.simple = ('state', 'inbox', 'journal', 'neural', 'latency', 'lineage', 'pine',
                      'strategies', 'health', 'channels', 'news', 'luxalgo', 'edge', 'quant',
                      'token', 'identity', 'portfolio', 'attribution')
        for name in cls.simple:
            setattr(b, {'state': 'state', 'inbox': 'inbox_data', 'journal': 'journal_data'}.get(name, name+'_data'), Mock(return_value={'route':name}))
        b.mobile_html = Mock(return_value='<div>mobile</div>')
        b.candles_data = Mock(return_value={'candles': [], 'error': 'unavailable'})
        b.pine_series_data = Mock(return_value={'ok': True})
        b.prop_sim_data = Mock(return_value={'available': False})
        b.market_intel_data = Mock(return_value={'rows': []})
        b.trace = Mock(return_value=[])
        b.compile_pine = Mock(return_value={'ok': True})
        b.bus = SimpleNamespace(history=Mock(return_value=[{'event_id':'offline'}]))
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
        h = {'Authorization':'Bearer '+self.server.cockpit_token} if auth else {}
        h.update(headers or {})
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=4)
        conn.request(method, path, body=body, headers=h)
        resp = conn.getresponse()
        result = resp.status, dict(resp.getheaders()), resp.read()
        conn.close()
        return result

    def post(self, body, path='/api/session', **kwargs):
        headers = {'Origin':self.origin, 'Content-Type':'application/json'}
        headers.update(kwargs.pop('headers', {}))
        return self.request(path, 'POST', body, headers=headers, **kwargs)

    def test_public_allowlisted_assets_and_no_file_disclosure(self):
        for path, mime in (('/assets/quant.css','text/css'),('/assets/quant.js','application/javascript')):
            code, headers, body = self.request(path, auth=False)
            self.assertEqual(code, 200)
            self.assertTrue(headers['Content-Type'].startswith(mime))
            self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
            self.assertTrue(body)
        for path in ('/assets/../config.json', '/assets/%2e%2e/config.json', '/assets/.cockpit-token',
                     '/assets/quant.css/other', '/assets/quant.js?bad=1', '/assets/other.js'):
            self.assertEqual(self.request(path, auth=False)[0], 404, path)
        self.assertEqual(self.request('/', auth=False)[0], 200)

    def test_every_existing_route_and_quant_is_preserved(self):
        for name in self.simple:
            code, _, body = self.request('/api/'+name)
            self.assertEqual(code, 200, name)
            self.assertEqual(json.loads(body)['route'], name)
            self.assertEqual(self.request('/api/'+name, auth=False)[0], 401)
        for path, expected in (('/api/mobile',200),('/api/candles',503),('/api/pine_series',200),
                               ('/api/prop_sim',200),('/api/market_intel',200),('/api/events',200),
                               ('/api/trace/123',200),('/vela/vela.global.js',404)):
            self.assertEqual(self.request(path)[0], expected, path)
        self.assertEqual(self.request('/vela/vela.global.js',auth=False)[0],401)

    def test_session_cookie_integrity_expiry_logout_and_wrong_token(self):
        code, headers, _ = self.post(json.dumps({'token':self.server.cockpit_token}), auth=False)
        self.assertEqual(code, 200)
        cookie = headers['Set-Cookie']
        for flag in ('HttpOnly', 'SameSite=Strict', 'Max-Age=28800'):
            self.assertIn(flag, cookie)
        cookie = cookie.split(';')[0]
        self.assertEqual(self.request('/api/quant',auth=False,headers={'Cookie':cookie})[0],200)
        self.assertEqual(self.request('/api/quant',auth=False,headers={'Cookie':cookie+'x'})[0],401)
        msg = 'offline.'+str(int(time.time())-1)
        sig = hmac.new(self.server.cockpit_token.encode(), msg.encode(),hashlib.sha256).hexdigest()
        self.assertEqual(self.request('/api/state',auth=False,headers={'Cookie':f'cockpit_session={msg}.{sig}'})[0],401)
        self.assertEqual(self.post('{"token":"wrong"}')[0],401)
        self.assertEqual(self.post('{"token":"\\u00e9"}')[0],401)
        code, headers, _ = self.request('/api/session','DELETE',headers={'Origin':self.origin})
        self.assertEqual(code,200)
        self.assertIn('Max-Age=0',headers['Set-Cookie'])

    def test_origin_and_host_defenses(self):
        for host in ('evil.example:'+str(self.port), 'localhost:invalid', '[broken'):
            self.assertEqual(self.request('/',headers={'Host':host})[0],403)
        for origin in ('https://evil.example','null',''):
            self.assertEqual(self.post('{}',headers={'Origin':origin})[0],403)
            self.assertEqual(self.post('{"script":"trusted"}',path='/api/pine/compile',headers={'Origin':origin})[0],403)
        self.assertEqual(self.post('{}',headers={'Sec-Fetch-Site':'cross-site'})[0],403)
        self.assertEqual(self.post('{"script":"trusted"}',path='/api/pine/compile')[0],503)

    def test_invalid_json_fields_sizes_queries_and_encodings(self):
        for body in ('[]','null','{','{"token":NaN}','{"token":"a","token":"b"}', '{"token":"a","extra":1}'):
            self.assertEqual(self.post(body)[0],400,body)
        self.assertEqual(self.post('{}',headers={'Content-Type':'text/plain'})[0],415)
        self.assertEqual(self.post('x'*131073)[0],413)
        self.assertEqual(self.post('{"script":"trusted","extra":1}',path='/api/pine/compile')[0],400)
        for path in ('/api/candles?count=1','/api/candles?count=20&count=21','/api/quant?x=1',
                     '/api/candles?timeframe=W1','/api/events?stream=2','/api/trace/0',
                     '/api/market_intel?kind=unknown','/api/state?bad=%zz','/assets/%ff','/assets/%xx'):
            self.assertEqual(self.request(path)[0],400,path)

    def test_finite_sse_is_explicit_snapshot(self):
        code, headers, body = self.request('/api/events?stream=1')
        self.assertEqual(code,200)
        self.assertEqual(headers['X-Event-Stream-Mode'],'snapshot-replay')
        self.assertIn(b'finite event replay snapshot',body)
        self.assertTrue(body.endswith(b'data: [DONE]\n\n'))

    def test_events_limit_is_accepted_and_bounded(self):
        self.assertEqual(self.request('/api/events?limit=30')[0], 200)
        for bad in ('0', '501', 'abc', '1.5', 'true'):
            self.assertEqual(self.request('/api/events?limit='+bad)[0], 400, bad)

    def test_root_page_carries_single_use_autologin_nonce(self):
        code, _, body = self.request('/', auth=False)
        self.assertEqual(code, 200)
        self.assertIn(b'window.__hqBootstrap=', body)

    def test_bootstrap_autologin_is_single_use_origin_bound_and_shaped(self):
        from cockpit_runtime import issue_bootstrap
        nonce = issue_bootstrap()
        code, headers, _ = self.post(json.dumps({'nonce': nonce}), path='/api/bootstrap', auth=False)
        self.assertEqual(code, 200)
        cookie = headers['Set-Cookie'].split(';')[0]
        self.assertEqual(self.request('/api/state', auth=False, headers={'Cookie': cookie})[0], 200)
        # Consumed: the same nonce can never mint a second session.
        self.assertEqual(self.post(json.dumps({'nonce': nonce}), path='/api/bootstrap', auth=False)[0], 401)
        # Unknown/overshort nonces and unexpected fields are refused.
        self.assertEqual(self.post(json.dumps({'nonce': 'x'}), path='/api/bootstrap', auth=False)[0], 401)
        self.assertEqual(self.post(json.dumps({'nonce': issue_bootstrap(), 'extra': 1}),
                                   path='/api/bootstrap', auth=False)[0], 400)
        # Cross-site origins cannot mint a session even with a valid nonce.
        self.assertEqual(self.post(json.dumps({'nonce': issue_bootstrap()}), path='/api/bootstrap',
                                   auth=False, headers={'Origin': 'https://evil.example'})[0], 403)


if __name__ == '__main__':
    unittest.main()

## Links from
- [[test_audit_ledger]]
- [[test_cockpit_boundary_v2]]
