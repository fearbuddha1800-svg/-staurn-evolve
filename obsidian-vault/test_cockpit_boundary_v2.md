---
slug: test_cockpit_boundary_v2
type: note
graph: gitnexus
---

"""Offline real-HTTP safety regression: never start a Pine process from HTTP."""
import json
from pathlib import Path
from test_cockpit_api import CockpitHTTP


class PineHTTPBoundary(CockpitHTTP):
    def setUp(self):
        self.b.compile_pine.reset_mock()
        self.b.pine_series_data.reset_mock()

    def test_pine_never_reaches_trusted_offline_helpers(self):
        code, headers, payload = self.post(json.dumps({'script': '//@version=5\nindicator("offline")\nplot(close)'}), path='/api/pine/compile')
        self.assertEqual(code, 503)
        self.assertTrue(headers['Content-Type'].startswith('application/json'))
        self.assertIn('OS-isolated', json.loads(payload)['error'])
        self.assertEqual(self.request('/api/pine_series?strategy=strategies/example.pine')[0], 200)
        self.b.compile_pine.assert_not_called()
        self.b.pine_series_data.assert_called()

    def test_auth_origin_and_validation_precede_isolation_error(self):
        self.assertEqual(self.post('{"script":"x"}', path='/api/pine/compile', auth=False)[0], 401)
        self.assertEqual(self.request('/api/pine_series', auth=False)[0], 401)
        self.assertEqual(self.post('{"script":"x"}', path='/api/pine/compile', headers={'Origin': 'https://evil.example'})[0], 403)
        for body in ('{}', '{"script":""}', '{"script":4}', '{"script":"x","timeframe":"W1"}', '{"script":"x","count":1}'):
            self.assertEqual(self.post(body, path='/api/pine/compile')[0], 400, body)
        self.assertEqual(self.post(json.dumps({'script': 'a' * 65537}), path='/api/pine/compile')[0], 413)
        for path in ('../escape.pine', '/absolute.pine', 'strategies/test.js', 'C:/secret.pine'):
            self.assertEqual(self.request('/api/pine_series?strategy=' + path)[0], 400, path)
        self.b.compile_pine.assert_not_called()
        self.b.pine_series_data.assert_not_called()

    def test_unknown_api_is_json_404_and_new_assets_are_allowlisted(self):
        code, headers, body = self.request('/api/not-a-real-route')
        self.assertEqual(code, 404)
        self.assertTrue(headers['Content-Type'].startswith('application/json'))
        self.assertFalse(json.loads(body)['ok'])
        for name, mime in [('hq-shell.css', 'text/css'), ('quant-client.js', 'application/javascript')]:
            Path(self.tmp.name, 'cockpit_assets', name).write_text('/* offline fixture */')
            code, headers, _ = self.request('/assets/' + name, auth=False)
            self.assertEqual(code, 200)
            self.assertTrue(headers['Content-Type'].startswith(mime))

