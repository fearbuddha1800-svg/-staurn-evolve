---
slug: test_gateway
type: note
graph: gitnexus
---

"""Gateway integration tests use isolated HTTP services/SQLite, never MT5."""
import http.client
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import types
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import yaml
import gateway


class Upstream(BaseHTTPRequestHandler):
    calls = []

    def do_GET(self):
        self.calls.append((self.path, self.headers.get('Authorization')))
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', 'http://example.com/')
            self.end_headers()
            return
        body = json.dumps({'path': self.path}).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class GatewayTests(unittest.TestCase):
    def setUp(self):
        scratch = Path.home() / '.hermes' / 'cache' / 'scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temp.name)
        self.upstream = ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
        self.upthread = threading.Thread(target=self.upstream.serve_forever, daemon=True)
        self.upthread.start()
        self.config = gateway.load_config(Path(gateway.__file__).with_name('gateway.yaml'))
        self.config['port'] = 0
        self.config['services']['trade-relay']['url'] = f'http://127.0.0.1:{self.upstream.server_port}'
        self.configpath = self.root / 'gateway.yaml'
        self.configpath.write_text(yaml.safe_dump(self.config))
        self.backend = types.SimpleNamespace(BASE=str(self.root))
        # Legacy dispatcher eagerly builds its whole simple-route map.
        import re
        runtime = Path(gateway.__file__).with_name('cockpit_runtime.py').read_text()
        for name in set(re.findall(r'\bb\.(\w+)', runtime)):
            setattr(self.backend, name, lambda: {'adapter': True})
        self.backend.BASE = str(self.root)
        from event_bus import EventBus
        self.bus = EventBus(str(self.root / 'signals.db'))
        self.server = gateway.create_server(self.configpath, backend=self.backend, token='test-owner')
        self.server.refresh()
        self.server.start_workers()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.upstream.shutdown()
        self.upstream.server_close()
        self.temp.cleanup()

    def request(self, path, token='test-owner', method='GET', extra=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=4)
        headers = {'Authorization': 'Bearer ' + token} if token else {}
        headers.update(extra or {})
        conn.request(method, path, headers=headers)
        response = conn.getresponse()
        status, raw = response.status, response.read()
        conn.close()
        return status, json.loads(raw)

    def test_auth_and_host(self):
        for path in ['/api/services', '/api/gateway/health', '/api/gateway/events',
                     '/api/services/neural', '/api/trade-relay/status', '/api/cockpit/neural']:
            self.assertEqual(self.request(path, token=None)[0], 401, path)
        self.assertEqual(self.request('/api/services', extra={'Host': 'evil.invalid'})[0], 403)
        self.assertEqual(self.request('/api/services?token=test-owner', token=None)[0], 401)

    def test_discovery_health_and_local_routes(self):
        status, data = self.request('/api/services')
        self.assertEqual(status, 200)
        self.assertEqual({s['name'] for s in data['services']}, set(self.config['services']))
        self.assertNotIn('token', json.dumps(data))
        self.assertEqual(self.request('/api/gateway/health')[1]['status'], 'up')
        for path in ['/api/services/neural', '/api/services/strategies',
                     '/api/services/luxalgo', '/api/cockpit/neural', '/api/neural']:
            self.assertEqual(self.request(path), (200, {'adapter': True}))

    def test_proxy_credentials_and_write_denial(self):
        with patch.dict(os.environ, {'TRADE_RELAY_AGENT_TOKEN': 'upstream-only'}):
            status, data = self.request('/api/trade-relay/status?detail=1')
        self.assertEqual((status, data), (200, {'path': '/api/status?detail=1'}))
        self.assertEqual(Upstream.calls[-1], ('/api/status?detail=1', 'Bearer upstream-only'))
        count = len(Upstream.calls)
        self.assertEqual(self.request('/api/trade-relay/orders', method='POST')[0], 404)
        self.assertEqual(len(Upstream.calls), count)
        self.assertEqual(self.request('/api/trade-relayish/status')[0], 404)

    def test_sse_live_and_replay(self):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=4)
        connection.request('GET', '/api/gateway/events', headers={'Authorization': 'Bearer test-owner'})
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn(b'event: ready', response.readline())
        response.readline()
        response.readline()
        from event_bus import make_event
        self.bus.publish(make_event('signal_logged', 'gateway-test', {'ticket': 42}))
        lines = []
        for _ in range(12):
            line = response.readline()
            lines.append(line)
            if line.startswith(b'data:'):
                break
        self.assertIn(b'id: 1\n', lines)
        self.assertIn(b'"ticket": 42', b''.join(lines))
        connection.close()
        client = self.server.event_stream.subscribe(0)
        self.assertEqual(client.get(timeout=1)[0], 1)
        self.server.event_stream.unsubscribe(client)
        self.assertEqual(self.request('/api/gateway/events', extra={'Last-Event-ID': '-1'})[0], 409)

    def test_health_failure_and_config_validation(self):
        self.server.config['services']['trade-relay']['url'] = 'http://127.0.0.1:1'
        self.server.refresh()
        self.assertEqual(self.request('/api/gateway/health')[1]['status'], 'degraded')
        self.assertEqual(self.request('/api/trade-relay/status')[0], 503)
        self.config['services']['trade-relay']['url'] = 'http://example.com'
        self.configpath.write_text(yaml.safe_dump(self.config))
        with self.assertRaises(ValueError):
            gateway.load_config(self.configpath)


if __name__ == '__main__':
    unittest.main()

