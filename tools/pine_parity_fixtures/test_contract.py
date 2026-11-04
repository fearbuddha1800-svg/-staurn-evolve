"""Compare hand-computed outputs and enforce absence of future-data leakage."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.pine_parity_fixtures.contract import evaluate

CASES = json.loads(Path(__file__).with_name("cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_expected_records(case: dict) -> None:
    assert evaluate(case) == case["expected"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_future_data_cannot_change_records(case: dict) -> None:
    changed = copy.deepcopy(case)
    for bar in changed["bars"]:
        if bar["open"] + case["duration"] > case["asof"]:
            bar["close"] = 999999
    changed["bars"].append({"open": case["asof"] + 60,
                            "close": -999999, "session": "future"})
    for bar in changed["htf"]:
        if bar["open"] + case["htf_duration"] > case["asof"]:
            bar["close"] = 999999
    changed["htf"].append({"open": case["asof"] + 180, "close": -999999})
    assert evaluate(changed) == evaluate(case)


def test_fixture_coverage() -> None:
    assert {case["name"] for case in CASES} == {
        "crossovers", "partial-bar", "warmup", "missing-close",
        "timestamp-gap", "session-reset", "htf-boundary",
    }
