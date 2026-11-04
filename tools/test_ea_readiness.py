"""Source triage regression cases; no broker or terminal calls."""
import tempfile
import unittest
from pathlib import Path

from ea_readiness import inspect


class ReadinessTests(unittest.TestCase):
    def test_missing_entry_is_blocked_not_a_compiler_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            result = inspect(root, root / "absent.mq5")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["findings"][0]["code"], "missing_source")
        self.assertFalse(result["compiled"])

    def check_source(self, source: str, include: str | None = None) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            entry = root / "test.mq5"
            entry.write_text(source)
            if include is not None:
                (root / "params.mqh").write_text(include)
            return inspect(root, entry)

    def test_resolves_quoted_include_and_inputs(self):
        result = self.check_source('#include "params.mqh"\nvoid OnTick(){Print(InpRisk);}',
                                   'input double InpRisk=0.5;')
        self.assertEqual(result["findings"], [])
        self.assertFalse(result["compiled"])

    def test_detects_undefined_input(self):
        result = self.check_source('void OnTick(){Print(InpMissing);}')
        self.assertEqual(result["findings"][0]["detail"], "InpMissing")

    def test_ignores_comments_and_strings(self):
        result = self.check_source('// delegate_task(); InpFake\n'
                                   'void OnTick(){Print("InpFake // delegate_task()");}')
        self.assertEqual(result["findings"], [])

    def test_rejects_agent_tool_syntax(self):
        result = self.check_source('#| invalid header\nvoid OnInit(){delegate_task();}')
        self.assertEqual({f["code"] for f in result["findings"]},
                         {"unsupported_agent_api", "invalid_preprocessor"})

    def test_detects_missing_local_include(self):
        result = self.check_source('#include "missing.mqh"')
        self.assertEqual(result["findings"][0]["code"], "missing_include")

    def test_rejects_include_escape(self):
        result = self.check_source('#include "../outside.mqh"')
        self.assertEqual(result["findings"][0]["code"], "include_escape")


if __name__ == "__main__":
    unittest.main()
