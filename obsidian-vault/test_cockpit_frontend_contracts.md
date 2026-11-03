---
slug: test_cockpit_frontend_contracts
type: note
graph: gitnexus
---

"""Offline VELA DOM/controller contracts. No backend imports, broker or network."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.elements = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    handle_startendtag = handle_starttag


class FrontendContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'cockpit_ui.html').read_text(encoding='utf-8')
        cls.js = (ROOT / 'cockpit_assets/quant.js').read_text(encoding='utf-8')
        cls.client = (ROOT / 'cockpit_assets/quant-client.js').read_text(encoding='utf-8')
        cls.css = (ROOT / 'cockpit_assets/hq-shell.css').read_text(encoding='utf-8')
        cls.elements = Document(cls.html).elements
        cls.by_id = {a['id']: (t, a) for t, a in cls.elements if 'id' in a}

    def test_ids_unique(self):
        counts = Counter(a['id'] for _, a in self.elements if 'id' in a)
        self.assertGreater(len(counts), 80, 'The parser must reach the real dashboard body')
        self.assertFalse({k: v for k, v in counts.items() if v > 1})

    def test_all_literal_controller_targets_exist(self):
        targets = set(re.findall(r"(?:document\.getElementById|\$)\(\s*['\"]([^'\"]+)['\"]\s*\)", self.js))
        self.assertGreater(len(targets), 30)
        self.assertEqual(targets - self.by_id.keys(), set())

    def test_six_views_use_contract_class(self):
        names = {'overview', 'chart', 'signals', 'strategies', 'intelligence', 'system'}
        actual = {a['id'] for _, a in self.elements if 'view' in a.get('class', '').split()}
        self.assertEqual(actual, {'view-' + name for name in names})
        for name in names:
            attrs = self.by_id['view-' + name][1]
            self.assertEqual('hidden' in attrs, name != 'overview')

    def test_dynamic_feature_containers(self):
        for name in ('signals', 'strategies', 'intelligence', 'system'):
            attrs = self.by_id[name + '-content'][1]
            self.assertIn('feature-grid', attrs.get('class', '').split())
        self.assertNotIn("querySelectorAll('.feature-grid').forEach(n=>n.replaceChildren())", self.js,
                         'Scope cache clearing to dynamic hosts, not static overview sections')

    def test_assets_are_whitelisted_and_present(self):
        runtime = (ROOT / 'cockpit_runtime.py').read_text(encoding='utf-8')
        allowed = set(re.findall(r"['\"](/assets/[^'\"]+)['\"]\s*:", runtime))
        assets = {a[k] for _, a in self.elements for k in ('src', 'href')
                  if a.get(k, '').startswith('/assets/')}
        self.assertTrue(assets)
        self.assertFalse(assets - allowed)
        for asset in assets:
            self.assertTrue((ROOT / 'cockpit_assets' / asset.rsplit('/', 1)[-1]).is_file(), asset)

    def test_client_loads_before_controller_once(self):
        scripts = [a.get('src') for tag, a in self.elements if tag == 'script']
        self.assertEqual(scripts, ['/assets/quant-client.js', '/assets/quant.js',
                                   '/assets/matrix-panels.js', '/assets/strategy-registry.js',
                                   '/assets/matrix-terminal.js'])
        self.assertEqual(len(scripts), len(set(scripts)))
        for tag, attrs in self.elements:
            if tag == 'script':
                self.assertIn('defer', attrs)

    def test_no_browser_persistent_credentials(self):
        for source in (self.html, self.js, self.client):
            self.assertNotRegex(source, r'(?:localStorage|sessionStorage)\.(?:setItem|\w+\s*=)')
        self.assertEqual(self.by_id['token'][1].get('type'), 'password')

    def test_pine_execution_stays_explicitly_disabled(self):
        for id_ in ('compile', 'load-overlay'):
            self.assertIn('disabled', self.by_id[id_][1])
            self.assertEqual(self.by_id[id_][1]['aria-describedby'], 'pine-boundary')
        self.assertNotRegex(self.js, r"api\(['\"](?:compile|pine_series)")

    def test_no_synthetic_market_background(self):
        self.assertNotIn('Math.random', self.js)
        self.assertNotIn('requestAnimationFrame(draw)', self.js)
        self.assertIn('prefers-reduced-motion', self.css)
        self.assertIn('motion-toggle', self.by_id)
        self.assertIn('tape-toggle', self.by_id)

    def test_labels_point_to_inputs(self):
        for tag, attrs in self.elements:
            if tag == 'label' and 'for' in attrs:
                self.assertIn(attrs['for'], self.by_id)
                self.assertIn(self.by_id[attrs['for']][0], ('input', 'textarea', 'select'))


if __name__ == '__main__':
    unittest.main()

