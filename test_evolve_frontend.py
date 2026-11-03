"""Offline EVOLVE browser regressions; ALL API responses are synthetic test fixtures.

Every request is intercepted before DNS/network. No broker, live cockpit, account,
Pine runner, execution module or external dependency is contacted by these tests.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent
ORIGIN = "http://evolve-offline.invalid"
BASELINE_IDS = ['account-id', 'account-mode', 'activity', 'app', 'balance', 'board-grid', 'chart', 'chart-empty', 'chart-form', 'chart-message', 'chart-title', 'compile', 'compile-message', 'connect', 'connect-form', 'connect-message', 'connect-title', 'connection', 'day-pl', 'day-pl-detail', 'day-pl-kpi', 'equity', 'exceptions', 'fabric-status', 'inbox-table', 'intelligence-content', 'last-sync', 'load-overlay', 'logout', 'main-nav', 'market-kind', 'market-load', 'matrix-canvas', 'motion-toggle', 'mt-clock', 'mt-latency', 'nav-items', 'nav-toggle', 'overview-chart', 'overview-chart-empty', 'overview-chart-message', 'overview-chart-title', 'pine-boundary', 'pine-editor', 'pine-file', 'pine-select', 'plot-legend', 'position-count', 'position-count-badge', 'positions', 'quant-content', 'quant-time', 'quote-status', 'refresh', 'risk-status', 'risk-summary', 'safety', 'signals-content', 'signals-summary', 'signals-table', 'strategies-content', 'symbol', 'system-content', 'tape-toggle', 'timeframe', 'token', 'trace', 'trace-body', 'trace-close', 'trace-title', 'unrealized', 'view-chart', 'view-description', 'view-intelligence', 'view-overview', 'view-signals', 'view-status', 'view-status-chip', 'view-strategies', 'view-system', 'view-title', 'vt-tape-bottom', 'vt-tape-top', 'workspace']


def fixture_bars(count=220):
    # Deterministic synthetic OHLCV, never a claimed broker observation.
    return [[1700000000 + i * 60, 100 + i / 10, 101 + i / 10,
             99 + i / 10, 100.5 + i / 10, 10 + i] for i in range(count)]


class EvolveFrontendBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.bars = fixture_bars()
        self.candle_status = 200
        self.requests = []
        self.unexpected = []
        self.errors = []
        self.logged_out = False
        self.fixture_login = "OFFLINE-FIXTURE"
        self.defer_candles = False
        self.pending_candle_route = None
        self.context = self.browser.new_context(service_workers="block", accept_downloads=True)
        self.context.route("**/*", self.route)
        self.page = self.context.new_page()
        self.page.set_default_timeout(6000)
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(ORIGIN)
        expect(self.page.locator("#app")).to_be_visible()
        expect(self.page.locator("#overview-chart-message")).to_contain_text("220 real MT5 bars")

    def tearDown(self):
        self.context.close()
        self.assertEqual([], self.unexpected, "An unmocked URL was attempted")
        self.assertEqual([], self.errors, "Uncaught browser JavaScript errors")

    def route(self, route):
        req = route.request
        url = urlsplit(req.url)
        self.requests.append((req.method, url.path, url.query))
        if url.netloc != "evolve-offline.invalid":
            self.unexpected.append(req.url)
            route.abort()
            return
        if url.path == "/":
            route.fulfill(content_type="text/html", body=(ROOT / "cockpit_ui.html").read_bytes())
            return
        if url.path.startswith("/assets/"):
            name = url.path.removeprefix("/assets/")
            if name in ("quant.js", "quant-client.js", "hq-tokens.css", "hq-shell.css"):
                route.fulfill(content_type="text/css" if name.endswith(".css") else "application/javascript",
                              body=(ROOT / "cockpit_assets" / name).read_bytes())
                return
        if url.path == "/api/session" and req.method == "DELETE":
            self.logged_out = True
            route.fulfill(json={"ok": True})
            return
        if url.path == "/api/state":
            if self.logged_out:
                route.fulfill(status=401, json={"error": "Offline fixture session removed"})
            else:
                route.fulfill(json={"account": {"login": self.fixture_login, "server": "TEST-ONLY",
                    "trade_mode": 0, "currency": "TEST", "balance": 100, "equity": 100, "profit": 0},
                    "mt5": {"account_available": True, "positions_available": True},
                    "positions": [], "halt": False, "pause": False, "stop": False})
            return
        if url.path == "/api/candles":
            if self.defer_candles:
                self.defer_candles = False
                self.pending_candle_route = route
                return
            route.fulfill(status=self.candle_status, json={"candles": self.bars} if self.candle_status == 200
                          else {"error": "Offline fixture broker unavailable"})
            return
        if url.path == "/api/pine":
            route.fulfill(json=[{"name": "Offline fixture", "path": "fixture.pine", "paper": True}])
            return
        if url.path == "/api/health":
            route.fulfill(json={"processes": [], "ports": {}})
            return
        if url.path == "/api/quant":
            route.fulfill(json={"available": False, "reason": "Offline fixture: analytics unavailable"})
            return
        if url.path in ("/api/events", "/api/inbox"):
            route.fulfill(json=[])
            return
        self.unexpected.append(req.url)
        route.fulfill(status=404, json={"error": "No offline fixture for this URL"})

    def chart(self):
        self.page.get_by_role("button", name="Chart Lab ↗", exact=True).click()
        expect(self.page.locator("#view-chart")).to_be_visible()
        expect(self.page.locator("#chart-window")).to_contain_text("of 220")

    def window(self):
        match = re.search(r"Bars (\d+)–(\d+) of (\d+)", self.page.locator("#chart-window").inner_text())
        self.assertIsNotNone(match)
        return tuple(map(int, match.groups()))

    def reload_chart(self):
        self.page.locator("#chart-form button[type=submit]").click()

    def test_brand_and_original_dom_contract(self):
        self.assertEqual("EVOLVE / Intelligence Terminal", self.page.title())
        expect(self.page.locator(".brand-word")).to_contain_text("EVOLVE")
        ids = self.page.locator("[id]").evaluate_all("nodes => nodes.map(n => n.id)")
        self.assertTrue(set(BASELINE_IDS).issubset(ids))
        self.assertEqual(len(ids), len(set(ids)), "Duplicate DOM IDs")
        self.assertEqual(["/assets/quant-client.js", "/assets/quant.js"],
                         self.page.locator("script[src]").evaluate_all("nodes => nodes.map(n => n.getAttribute('src'))"))

    def test_real_response_path_telemetry_and_canvas_no_price_scope_error(self):
        expect(self.page.locator("#vt-tape-top")).to_contain_text("Not a live quote")
        expect(self.page.locator("#vt-tape-top")).to_contain_text("122.4")
        self.assertGreater(self.page.locator("#overview-chart").evaluate("n => n.width"), 0)
        self.chart()
        expect(self.page.locator("#chart-renderer")).to_contain_text("Canvas renderer")
        expect(self.page.locator("#chart-readout")).to_contain_text("O ")
        expect(self.page.locator("#chart-readout")).to_contain_text("C 122.4")

    def test_zoom_pan_reset_and_single_owner(self):
        self.chart()
        first = self.window()
        overview = self.page.locator("#overview-chart").get_attribute("aria-label")
        self.page.locator("#chart-zoom-in").click()
        zoomed = self.window()
        self.assertLess(zoomed[1] - zoomed[0], first[1] - first[0])
        self.page.locator("#chart-older").click()
        older = self.window()
        self.assertEqual(zoomed[0] - (zoomed[1] - zoomed[0] + 2) // 2, older[0])
        expect(self.page.locator("#chart-newer")).to_be_enabled()
        self.page.locator("#chart-newer").click()
        self.assertEqual(zoomed, self.window())
        self.page.locator("#chart-reset").click()
        self.assertEqual(first, self.window())
        expect(self.page.locator("#chart-newer")).to_be_disabled()
        self.assertEqual(overview, self.page.locator("#overview-chart").get_attribute("aria-label"))
        for _ in range(10):
            if self.page.locator("#chart-zoom-out").is_disabled():
                break
            self.page.locator("#chart-zoom-out").click()
        self.assertEqual((1, 220, 220), self.window())
        expect(self.page.locator("#chart-older")).to_be_disabled()
        expect(self.page.locator("#chart-zoom-out")).to_be_disabled()

    def test_keyboard_and_pointer_readout(self):
        self.chart()
        canvas = self.page.locator("#chart")
        canvas.focus()
        self.page.keyboard.press("Home")
        first = self.page.locator("#chart-readout").inner_text()
        self.page.keyboard.press("ArrowRight")
        self.assertNotEqual(first, self.page.locator("#chart-readout").inner_text())
        self.page.keyboard.press("End")
        expect(self.page.locator("#chart-readout")).to_contain_text("C 122.4")
        canvas.click(position={"x": 30, "y": 100})
        self.assertNotIn("C 122.4", self.page.locator("#chart-readout").inner_text())

    def test_export_contains_only_loaded_numeric_candles_not_edited_instrument(self):
        self.chart()
        self.page.locator("#symbol").fill("EURUSD")  # Not submitted: displayed data still XAUUSD.
        before = list(self.requests)
        with self.page.expect_download() as event:
            self.page.locator("#chart-export").click()
        download = event.value
        self.assertEqual("EVOLVE-XAUUSD-H1-candles.csv", download.suggested_filename)
        text = Path(download.path()).read_text(encoding="utf-8-sig")
        rows = text.splitlines()
        self.assertEqual("time_epoch_ms,time_iso_as_supplied,open,high,low,close,volume", rows[0])
        self.assertEqual(221, len(rows))
        self.assertEqual("100", rows[1].split(",")[2])
        self.assertEqual("122.4", rows[-1].split(",")[5])
        self.assertEqual(before, self.requests, "CSV export must be browser-only")
        download.delete()

    def test_registry_is_loaded_on_first_cached_chart_visit(self):
        before = sum(p == "/api/candles" for _, p, _ in self.requests)
        self.chart()
        expect(self.page.locator("#pine-select option[value='fixture.pine']")).to_have_count(1)
        self.assertEqual(before, sum(p == "/api/candles" for _, p, _ in self.requests))
        self.page.locator("#pine-select").select_option("fixture.pine")
        expect(self.page.locator("#compile-message")).to_contain_text("Metadata only")
        self.assertEqual(1, sum(p == "/api/pine" for _, p, _ in self.requests))

    def test_pine_stays_fail_closed_even_for_dispatched_clicks(self):
        self.chart()
        expect(self.page.locator("#compile")).to_be_disabled()
        expect(self.page.locator("#load-overlay")).to_be_disabled()
        expect(self.page.locator("#run-pine")).to_be_disabled()
        self.page.locator("#compile").dispatch_event("click")
        self.page.locator("#load-overlay").dispatch_event("click")
        self.page.locator("#run-pine").dispatch_event("click")
        expect(self.page.locator("#compile-message")).to_contain_text("OS-isolated worker")
        self.assertFalse(any("compile" in path or "pine_series" in path or "execute" in path
                             for _, path, _ in self.requests))
        self.assertTrue(all(method == "GET" for method, _, _ in self.requests))

    def test_source_import_and_oversize_rejection(self):
        self.chart()
        source = ('//@version=5\n// <img src=x onerror=alert(1)>\n'
                  'indicator("keep  double spaces")\n'
                  'if close > open\n'
                  '    if high > close\n'
                  '        label.new(bar_index, high, "nested  value")\n'
                  '\t// preserve literal tabs too\n'
                  'plot(close)\n')
        self.page.locator("#pine-file").set_input_files(
            {"name": "fixture.pine", "mimeType": "text/plain", "buffer": source.encode()})
        expect(self.page.locator("#pine-editor")).to_have_value(source)
        expect(self.page.locator("#compile-message")).to_contain_text("Editing only")
        self.page.locator("#pine-file").set_input_files(
            {"name": "large.pine", "mimeType": "text/plain", "buffer": b"x" * 250001})
        expect(self.page.locator("#compile-message")).to_contain_text("250 KB")
        expect(self.page.locator("#pine-editor")).to_have_value(source)
        self.assertEqual(0, self.page.locator("#view-chart img").count())

    def test_bad_and_duplicate_rows_are_rejected_without_zero_imputation(self):
        self.chart()
        self.bars = [
            [1700000060, 20, 23, 19, 22, None],
            [1700000000, 10, 13, 9, 12, 7],
            [1700000060000, 20, 24, 18, 23, None],  # Same timestamp; last supplied row wins.
            [1700000120, "", 20, 10, 15],
            [1700000180, True, 20, 10, 15],
            [1e30, 10, 20, 9, 15],
            [1700000300, 10, 9, 11, 10],
            [1700000360, 0, 1, 0, 1],
            None,
        ]
        self.reload_chart()
        expect(self.page.locator("#chart-message")).to_contain_text("2 real MT5 bars")
        expect(self.page.locator("#chart-message")).to_contain_text("7 invalid or duplicate")
        expect(self.page.locator("#vt-tape-top")).to_contain_text("23.00")
        expect(self.page.locator("#chart-readout")).to_contain_text("V unavailable")
        with self.page.expect_download() as event:
            self.page.locator("#chart-export").click()
        download = event.value
        rows = Path(download.path()).read_text(encoding="utf-8-sig").splitlines()
        self.assertEqual(3, len(rows))
        self.assertTrue(rows[-1].endswith(",23,"), "Missing volume must remain empty, never fabricated zero")
        download.delete()

    def test_object_rows_and_numeric_strings_preserve_prices(self):
        self.chart()
        self.bars = [{"time": "1700000000", "open": "1.00123", "high": "1.00345",
                      "low": "1.00012", "close": "1.00234", "volume": "17"}]
        self.reload_chart()
        expect(self.page.locator("#chart-message")).to_contain_text("1 real MT5 bars")
        expect(self.page.locator("#vt-tape-top")).to_contain_text("1.00234")
        expect(self.page.locator("#chart-readout")).to_contain_text("V 17")
        expect(self.page.locator("#chart-older")).to_be_disabled()
        expect(self.page.locator("#chart-zoom-in")).to_be_disabled()

    def test_empty_response_clears_previous_graph_prices_and_controls(self):
        self.chart()
        self.bars = []
        self.reload_chart()
        expect(self.page.locator("#chart-message")).to_contain_text("No broker bars")
        expect(self.page.locator("#chart-empty")).to_be_visible()
        expect(self.page.locator("#vt-tape-top")).to_contain_text("unavailable")
        expect(self.page.locator("#chart-readout")).to_contain_text("No broker candles")
        for name in ("older", "newer", "zoom-in", "zoom-out", "reset", "export"):
            expect(self.page.locator("#chart-" + name)).to_be_disabled()

    def test_fetch_failure_clears_old_tape_instead_of_stale_quote(self):
        self.chart()
        self.candle_status = 503
        self.reload_chart()
        expect(self.page.locator("#chart-message")).to_contain_text("Unavailable")
        expect(self.page.locator("#vt-tape-top")).to_contain_text("unavailable")
        expect(self.page.locator("#quote-status")).to_have_text("Market unavailable")
        expect(self.page.locator("#chart-export")).to_be_disabled()

    def test_logout_removes_observations_and_does_not_persist_credentials(self):
        self.chart()
        self.page.locator("#logout").click()
        expect(self.page.locator("#connect")).to_be_visible()
        expect(self.page.locator("#vt-tape-top")).to_contain_text("Connect to view broker prices")
        self.assertEqual([], self.page.evaluate("Object.keys(localStorage).concat(Object.keys(sessionStorage))"))
        self.assertFalse(self.page.locator("#chart-export").is_enabled())

    def test_mobile_chart_controls_wrap_without_document_overflow(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.chart()
        self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        self.page.locator("#chart-zoom-in").click()
        expect(self.page.locator("#chart-window")).to_contain_text("of 220")


    def test_chart_navigation_and_selection_make_no_network_calls(self):
        self.chart()
        expect(self.page.locator("#pine-select option[value='fixture.pine']")).to_have_count(1)
        before = list(self.requests)
        for name in ("zoom-in", "older", "newer", "reset"):
            self.page.locator("#chart-" + name).click()
        self.page.locator("#chart").focus()
        self.page.keyboard.press("Home")
        self.page.keyboard.press("ArrowRight")
        self.assertEqual(before, self.requests)

    def test_interval_labels_follow_loaded_data_not_unsaved_form_edits(self):
        self.chart()
        self.page.locator("#timeframe").select_option("M5")
        expect(self.page.locator(".ribbon-scope")).to_have_text("H1 Δ")
        self.reload_chart()
        expect(self.page.locator("#chart-title")).to_have_text("XAUUSD · M5")
        expect(self.page.locator(".ribbon-scope")).to_have_text("M5 Δ")
        expect(self.page.locator("#vt-tape-top")).to_contain_text("XAUUSD · M5")
        self.assertTrue(any("timeframe=M5" in query for _, path, query in self.requests
                            if path == "/api/candles"))

    def test_inflight_candles_cannot_resurrect_data_after_logout(self):
        self.chart()
        self.defer_candles = True
        with self.page.expect_request("**/api/candles?*"):
            self.reload_chart()
        expect(self.page.locator("#chart-export")).to_be_disabled()
        self.assertIsNotNone(self.pending_candle_route)
        self.page.locator("#logout").click()
        expect(self.page.locator("#connect")).to_be_visible()
        self.pending_candle_route.fulfill(json={"candles": fixture_bars()})
        self.page.wait_for_load_state("networkidle")
        expect(self.page.locator("#vt-tape-top")).to_contain_text("Connect to view broker prices")
        expect(self.page.locator("#chart-export")).to_be_disabled()
        expect(self.page.locator("#chart-window")).to_have_text("No broker candles loaded.")

    def test_account_scope_change_discards_old_inflight_candles(self):
        self.chart()
        self.defer_candles = True
        with self.page.expect_request("**/api/candles?*"):
            self.reload_chart()
        expect(self.page.locator("#chart-export")).to_be_disabled()
        self.assertIsNotNone(self.pending_candle_route)
        self.fixture_login = "SECOND-OFFLINE-FIXTURE"
        self.bars = [[1700000000, 700, 710, 690, 705, 42]]
        self.page.locator("#refresh").click()
        expect(self.page.locator("#account-id")).to_have_text("MT5 SECOND-OFFLINE-FIXTURE")
        expect(self.page.locator("#vt-tape-top")).to_contain_text("705.00")
        self.pending_candle_route.fulfill(json={"candles": fixture_bars()})
        self.page.wait_for_load_state("networkidle")
        expect(self.page.locator("#vt-tape-top")).to_contain_text("705.00")
        expect(self.page.locator("#vt-tape-top")).not_to_contain_text("122.4")


if __name__ == "__main__":
    unittest.main(verbosity=2)
