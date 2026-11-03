"""Tests for strategy_identity: magic -> identity resolution and attribution.

Proves:
  1. Every known magic resolves to a stable identity (id, version, kind, label).
  2. An unknown magic resolves to an explicit 'unknown' — never guessed.
  3. Identity ids and versions are unique across the registry.
  4. Attribution (P&L + counts) can be filtered by strategy_id and by version.

Run: PYTHONPATH= python test_strategy_identity.py
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import strategy_identity as si  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))


def _fake_deal(magic, profit, commission=0, swap=0, fee=0):
    """Deal dict shaped like mt5.history_deals_get() entries."""
    return {"magic": magic, "profit": profit, "commission": commission,
            "swap": swap, "fee": fee}


class MagicResolutionTests(unittest.TestCase):
    """resolve_magic: known magics -> stable identity, unknown -> explicit unknown."""

    @classmethod
    def setUpClass(cls):
        cls.registry = si.load_registry()
        # The registry must have loaded from the real config.json
        assert cls.registry, "registry is empty — config.json strategy_identities missing?"

    def test_signal_relay_magic_resolves(self):
        identity = si.resolve_magic(20261014, self.registry)
        self.assertEqual(identity.id, "signal-relay")
        self.assertEqual(identity.version, "1.0.0")
        self.assertEqual(identity.kind, "signal")
        self.assertIn("Signal Relay", identity.label)
        self.assertEqual(identity.magic, 20261014)

    def test_algo_engine_magic_resolves(self):
        identity = si.resolve_magic(20261015, self.registry)
        self.assertEqual(identity.id, "algo-engine")
        self.assertEqual(identity.version, "1.0.0")
        self.assertEqual(identity.kind, "algo")
        self.assertIn("Algo", identity.label)
        self.assertEqual(identity.magic, 20261015)

    def test_manual_magic_resolves(self):
        identity = si.resolve_magic(0, self.registry)
        self.assertEqual(identity.id, "manual")
        self.assertEqual(identity.kind, "manual")
        self.assertEqual(identity.magic, 0)

    def test_unknown_magic_resolves_to_explicit_unknown(self):
        """An unregistered magic must NEVER guess — it gets id='unknown'."""
        identity = si.resolve_magic(999999, self.registry)
        self.assertEqual(identity.id, "unknown")
        self.assertEqual(identity.kind, "unknown")
        self.assertEqual(identity.version, "0.0.0")
        self.assertEqual(identity.label, "Unknown")
        # Distinct from every registered identity
        self.assertNotIn(identity.id, {i.id for i in self.registry.values()})

    def test_negative_magic_resolves_to_unknown(self):
        identity = si.resolve_magic(-1, self.registry)
        self.assertEqual(identity.id, "unknown")

    def test_string_magic_resolves(self):
        """String '20261014' must resolve identically to int 20261014."""
        identity = si.resolve_magic("20261014", self.registry)
        self.assertEqual(identity.id, "signal-relay")

    def test_none_magic_resolves_to_unknown(self):
        identity = si.resolve_magic(None, self.registry)
        self.assertEqual(identity.id, "unknown")

    def test_registry_constants_match_legacy_magics(self):
        """The module constants must equal the legacy magic numbers."""
        self.assertEqual(si.MAGIC_SIGNAL_RELAY, 20261014)
        self.assertEqual(si.MAGIC_ALGO_ENGINE, 20261015)
        self.assertEqual(si.MAGIC_MANUAL, 0)


class RegistryIntegrityTests(unittest.TestCase):
    """Ids and versions must be unique; every identity must have a magic."""

    @classmethod
    def setUpClass(cls):
        cls.registry = si.load_registry()

    def test_ids_are_unique(self):
        ids = [i.id for i in self.registry.values()]
        self.assertEqual(len(ids), len(set(ids)), f"duplicate ids: {ids}")

    def test_versions_are_unique_per_id(self):
        """Each id must have exactly one version (1:1 id -> version)."""
        id_to_versions: dict[str, set] = {}
        for i in self.registry.values():
            id_to_versions.setdefault(i.id, set()).add(i.version)
        for sid, versions in id_to_versions.items():
            self.assertEqual(len(versions), 1, f"{sid} has multiple versions: {versions}")

    def test_every_identity_has_positive_magic_or_zero(self):
        for i in self.registry.values():
            self.assertIsInstance(i.magic, int)
            self.assertGreaterEqual(i.magic, 0)

    def test_resolve_all_magics_returns_full_map(self):
        all_magics = si.resolve_all_magics(self.registry)
        self.assertEqual(all_magics, self.registry)

    def test_legacy_magics_present_in_registry(self):
        """Backward compat: 20261014, 20261015, 0 must all be registered."""
        self.assertIn(20261014, self.registry)
        self.assertIn(20261015, self.registry)
        self.assertIn(0, self.registry)


class AttributionReportTests(unittest.TestCase):
    """attribution_report: per-identity P&L and counts."""

    @classmethod
    def setUpClass(cls):
        cls.registry = si.load_registry()
        cls.deals = [
            _fake_deal(20261014, 100.0, commission=-5.0, swap=-1.0, fee=-0.5),
            _fake_deal(20261014, -50.0, commission=-5.0, swap=0, fee=-0.5),
            _fake_deal(20261015, 200.0, commission=-10.0, swap=-2.0, fee=-1.0),
            _fake_deal(20261015, -80.0, commission=-10.0, swap=0, fee=-1.0),
            _fake_deal(0, 30.0, commission=-3.0, swap=0, fee=0),
            _fake_deal(999999, 999.0),  # unknown magic
        ]

    def test_total_count_and_pl(self):
        report = si.attribution_report(self.deals, self.registry)
        self.assertEqual(report["total"]["count"], 6)
        # 100-5-1-0.5 + (-50-5-0.5) + 200-10-2-1 + (-80-10-1) + 30-3 + 999
        expected_pl = 100 - 5 - 1 - 0.5 - 50 - 5 - 0.5 + 200 - 10 - 2 - 1 - 80 - 10 - 1 + 30 - 3 + 999
        self.assertAlmostEqual(report["total"]["pl"], expected_pl, places=2)

    def test_per_identity_breakdown(self):
        report = si.attribution_report(self.deals, self.registry)
        by_id = report["by_identity"]

        self.assertEqual(by_id["signal-relay"]["count"], 2)
        self.assertAlmostEqual(by_id["signal-relay"]["pl"], 100 - 5 - 1 - 0.5 - 50 - 5 - 0.5, places=2)

        self.assertEqual(by_id["algo-engine"]["count"], 2)
        self.assertAlmostEqual(by_id["algo-engine"]["pl"], 200 - 10 - 2 - 1 - 80 - 10 - 1, places=2)

        self.assertEqual(by_id["manual"]["count"], 1)
        self.assertAlmostEqual(by_id["manual"]["pl"], 30 - 3, places=2)

    def test_unknown_magic_tracked_separately(self):
        report = si.attribution_report(self.deals, self.registry)
        self.assertIn(999999, report["unknown_magic"])
        self.assertIn("unknown", report["by_identity"])
        self.assertEqual(report["by_identity"]["unknown"]["count"], 1)
        self.assertAlmostEqual(report["by_identity"]["unknown"]["pl"], 999.0, places=2)

    def test_empty_deals(self):
        report = si.attribution_report([], self.registry)
        self.assertEqual(report["total"]["count"], 0)
        self.assertEqual(report["total"]["pl"], 0.0)
        self.assertEqual(report["by_identity"], {})
        self.assertEqual(report["unknown_magic"], [])

    def test_deal_objects_with_attributes(self):
        """Objects with .magic/.profit attributes (like MT5 deal structs) must work."""
        class Deal:
            def __init__(self, magic, profit, commission=0, swap=0, fee=0):
                self.magic = magic
                self.profit = profit
                self.commission = commission
                self.swap = swap
                self.fee = fee

        deals = [Deal(20261014, 50.0, commission=-2.0),
                 Deal(20261015, -20.0, commission=-2.0)]
        report = si.attribution_report(deals, self.registry)
        self.assertEqual(report["total"]["count"], 2)
        self.assertAlmostEqual(report["by_identity"]["signal-relay"]["pl"], 48.0, places=2)
        self.assertAlmostEqual(report["by_identity"]["algo-engine"]["pl"], -22.0, places=2)


class FilterAttributionTests(unittest.TestCase):
    """filter_attribution: P&L and counts filterable by strategy and version."""

    @classmethod
    def setUpClass(cls):
        cls.registry = si.load_registry()
        cls.deals = [
            _fake_deal(20261014, 100.0),
            _fake_deal(20261014, -40.0),
            _fake_deal(20261015, 200.0),
            _fake_deal(20261015, -60.0),
            _fake_deal(0, 25.0),
            _fake_deal(999999, 999.0),
        ]

    def test_filter_by_strategy_id_signal_relay(self):
        report = si.filter_attribution(self.deals, strategy_id="signal-relay", registry=self.registry)
        self.assertEqual(report["total"]["count"], 2)
        self.assertAlmostEqual(report["total"]["pl"], 60.0, places=2)
        self.assertIn("signal-relay", report["by_identity"])
        self.assertNotIn("algo-engine", report["by_identity"])
        self.assertNotIn("manual", report["by_identity"])

    def test_filter_by_strategy_id_algo_engine(self):
        report = si.filter_attribution(self.deals, strategy_id="algo-engine", registry=self.registry)
        self.assertEqual(report["total"]["count"], 2)
        self.assertAlmostEqual(report["total"]["pl"], 140.0, places=2)
        self.assertNotIn("signal-relay", report["by_identity"])

    def test_filter_by_strategy_id_manual(self):
        report = si.filter_attribution(self.deals, strategy_id="manual", registry=self.registry)
        self.assertEqual(report["total"]["count"], 1)
        self.assertAlmostEqual(report["total"]["pl"], 25.0, places=2)

    def test_filter_by_strategy_id_unknown(self):
        """Filtering for 'unknown' must return only unregistered magics."""
        report = si.filter_attribution(self.deals, strategy_id="unknown", registry=self.registry)
        self.assertEqual(report["total"]["count"], 1)
        self.assertAlmostEqual(report["total"]["pl"], 999.0, places=2)
        self.assertIn("unknown", report["by_identity"])

    def test_filter_by_version(self):
        """All identities are version 1.0.0 (except manual at 0.0.0)."""
        report = si.filter_attribution(self.deals, version="1.0.0", registry=self.registry)
        # signal-relay + algo-engine are both 1.0.0
        self.assertEqual(report["total"]["count"], 4)
        self.assertIn("signal-relay", report["by_identity"])
        self.assertIn("algo-engine", report["by_identity"])
        self.assertNotIn("manual", report["by_identity"])

    def test_filter_by_strategy_and_version(self):
        report = si.filter_attribution(
            self.deals, strategy_id="signal-relay", version="1.0.0", registry=self.registry
        )
        self.assertEqual(report["total"]["count"], 2)
        self.assertAlmostEqual(report["total"]["pl"], 60.0, places=2)

    def test_no_filter_returns_all(self):
        report = si.filter_attribution(self.deals, registry=self.registry)
        self.assertEqual(report["total"]["count"], 6)

    def test_filter_nothing_matches(self):
        report = si.filter_attribution(self.deals, strategy_id="nonexistent", registry=self.registry)
        self.assertEqual(report["total"]["count"], 0)
        self.assertEqual(report["by_identity"], {})


class ConfigBackwardCompatibilityTests(unittest.TestCase):
    """The existing config.json must still parse and pine_strategies must be intact."""

    def test_config_parses(self):
        with open(os.path.join(ROOT, "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIsInstance(cfg, dict)

    def test_pine_strategies_intact(self):
        with open(os.path.join(ROOT, "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        pine = cfg.get("pine_strategies")
        self.assertIsInstance(pine, list)
        self.assertGreaterEqual(len(pine), 2)
        names = {p.get("name") for p in pine}
        self.assertIn("RSI + EMA Trend", names)
        self.assertIn("EMA Cross Signals", names)

    def test_strategy_identities_block_exists(self):
        with open(os.path.join(ROOT, "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        si_block = cfg.get("strategy_identities")
        self.assertIsInstance(si_block, dict)
        self.assertIn("signal-relay", si_block)
        self.assertIn("algo-engine", si_block)
        self.assertIn("manual", si_block)

    def test_algo_block_intact(self):
        with open(os.path.join(ROOT, "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        algo = cfg.get("algo")
        self.assertIsInstance(algo, dict)
        self.assertIn("symbols", algo)
        self.assertIn("algo_entry_authority", algo)

    def test_strategy2_block_intact(self):
        with open(os.path.join(ROOT, "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        s2 = cfg.get("strategy2")
        self.assertIsInstance(s2, dict)
        self.assertIn("enabled", s2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
