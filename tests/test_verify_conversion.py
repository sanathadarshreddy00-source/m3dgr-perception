"""Tests for scripts/verify_conversion.py.

The end-to-end tests run the script on the synthetic bag from conftest.py:
a faithful conversion must pass, and each kind of deliberate difference must
fail. Check 3 (decoding by ROS 2 itself) needs the ROS container and is not
covered here.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from conftest import REPO, Mutation, write_synthetic_bag
from verify_conversion import first_difference, normalize

SCRIPT = REPO / "scripts" / "verify_conversion.py"


def run_verify(raw: Path, converted: Path, out: Path) -> tuple[int, dict[str, Any]]:
    """Run the script as convert_bag.sh does; return exit code and report."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(raw), str(converted), str(out)],
        capture_output=True,
        text=True,
    )
    report: dict[str, Any] = json.loads(out.read_text())
    return proc.returncode, report


# --- normalize -----------------------------------------------------------


def test_normalize_drops_header_seq_and_constants() -> None:
    msg = {
        "header": {"seq": 5, "stamp": {"sec": 1, "nanosec": 2}, "frame_id": "a"},
        "COVARIANCE_TYPE_KNOWN": 3,
        "status": {"STATUS_FIX": 0, "status": 2},
    }
    assert normalize(msg) == {
        "header": {"stamp": {"sec": 1, "nanosec": 2}, "frame_id": "a"},
        "status": {"status": 2},
    }


def test_normalize_keeps_seq_outside_header() -> None:
    # Only header.seq is an intended difference; a data field named seq is data.
    assert normalize({"seq": 5, "points": [{"seq": 1}]}) == {"seq": 5, "points": [{"seq": 1}]}


# --- first_difference ------------------------------------------------------


def test_first_difference_equal_is_none() -> None:
    assert first_difference({"a": [1, 2.5]}, {"a": [1, 2.5]}) is None


def test_first_difference_nan_equals_nan() -> None:
    assert first_difference([math.nan], [math.nan]) is None


def test_first_difference_floats_compared_exactly() -> None:
    assert first_difference([1.0], [1.0 + 1e-12]) is not None


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ({"x": {"y": 1}}, {"x": {"y": 2}}, ".x.y: 1 != 2"),
        ({"x": [1, 2]}, {"x": [1, 3]}, ".x[1]: 2 != 3"),
        ({"x": [1]}, {"x": [1, 2]}, ".x: length 1 != 2"),
        ({"x": 1}, {"y": 1}, ": keys ['x'] != ['y']"),
    ],
)
def test_first_difference_reports_path(a: Any, b: Any, expected: str) -> None:
    assert first_difference(a, b) == expected


# --- end to end on the synthetic bag -------------------------------------


def test_faithful_conversion_passes(raw_bag: Path, converted_bag: Path, tmp_path: Path) -> None:
    code, report = run_verify(raw_bag, converted_bag, tmp_path / "verify.json")
    assert code == 0, report["failures"]
    assert report["passed"]
    assert set(report["topics"]) == {"/imu", "/fix", "/livox/lidar"}
    for entry in report["topics"].values():
        assert entry["type_equal"] and entry["count_equal"] and entry["record_times_equal"]
        assert entry["sampled"] == 20  # every message of the small bag
        assert entry["sample_mismatches"] == []


def test_changed_value_fails(converted_bag: Path, tmp_path: Path) -> None:
    # Same as the raw bag except one acceleration value, changed by 1e-6.
    raw = write_synthetic_bag(tmp_path / "raw.bag", Mutation(imu_accel_x_offset=1e-6))
    code, report = run_verify(raw, converted_bag, tmp_path / "verify.json")
    assert code == 1
    original = 0.1 * 7  # as conftest computes it, not the literal 0.7
    assert report["topics"]["/imu"]["sample_mismatches"] == [
        f"msg[7].linear_acceleration.x: {original + 1e-6!r} != {original!r}"
    ]
    assert len(report["failures"]) == 1


def test_shifted_record_time_fails(converted_bag: Path, tmp_path: Path) -> None:
    raw = write_synthetic_bag(tmp_path / "raw.bag", Mutation(record_time_shift_ns=1))
    code, report = run_verify(raw, converted_bag, tmp_path / "verify.json")
    assert code == 1
    assert report["failures"] == ["/imu: record_times_equal is false"]


def test_missing_topic_fails(converted_bag: Path, tmp_path: Path) -> None:
    raw = write_synthetic_bag(tmp_path / "raw.bag", Mutation(extra_topic=True))
    code, report = run_verify(raw, converted_bag, tmp_path / "verify.json")
    assert code == 1
    assert "topic sets differ: ['/fix_extra']" in report["failures"]
