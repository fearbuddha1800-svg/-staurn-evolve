"""Offline contract and rejection tests; never imports legacy scripts."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from offline_pipeline import build, validate

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / 'source_manifest.json').read_text())

    def test_valid_and_reproducible(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            build(ROOT, self.manifest, out)
            first = {p.name: p.read_bytes() for p in out.iterdir()}
            build(ROOT, self.manifest, out)
            self.assertEqual(first, {p.name: p.read_bytes() for p in out.iterdir()})
            self.assertEqual(len(first), 2)

    def test_reject_tampering(self):
        bad = copy.deepcopy(self.manifest)
        bad['sources'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            validate(ROOT, bad)

    def test_reject_escape(self):
        bad = copy.deepcopy(self.manifest)
        bad['sources'][0]['path'] = '../AGENTS.md'
        with self.assertRaisesRegex(ValueError, 'outside curated'):
            validate(ROOT, bad)

    def test_reject_unofficial_url(self):
        bad = copy.deepcopy(self.manifest)
        bad['sources'][0]['url'] = 'https://www.mql5.com.evil.test/en/docs/x'
        with self.assertRaisesRegex(ValueError, 'official'):
            validate(ROOT, bad)

    def test_reject_duplicates_and_empty(self):
        for sources in ([], self.manifest['sources'] * 2):
            bad = copy.deepcopy(self.manifest)
            bad['sources'] = sources
            with self.assertRaises(ValueError):
                validate(ROOT, bad)

    def test_fail_closed_training_rights(self):
        bad = copy.deepcopy(self.manifest)
        bad['sources'][0]['training_allowed'] = True
        with self.assertRaisesRegex(ValueError, 'training'):
            validate(ROOT, bad)


if __name__ == '__main__':
    unittest.main()
