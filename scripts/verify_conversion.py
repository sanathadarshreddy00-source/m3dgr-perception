"""Verify that a converted ROS 2 bag carries the same messages as the raw ROS 1 bag.

Checks, per topic:

1. Same message type and count, and an identical sequence of record
   timestamps (every message, no deserialisation needed).
2. Identical field values on a uniform sample of messages (first and last
   included), both bags decoded with rosbags.
3. Optional: identical field values between the raw bag and a dump of the first
   messages decoded by ROS 2 itself (``scripts/ros2_dump_messages.py``, run in
   the ROS container). This checks the converted bytes the way ``ros2 bag play``
   and subscribers read them.

Exits non-zero on any mismatch and writes a JSON report.

Usage:
    uv run python scripts/verify_conversion.py data/raw/Outdoor01.bag \
        data/interim/Outdoor01_ros2 outputs/conversion/verify.json \
        [--ros2-dump outputs/conversion/ros2_dump.json]
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from rosbags.highlevel import AnyReader

log = logging.getLogger(__name__)

SAMPLES_PER_TOPIC = 50


def to_plain(obj: Any) -> Any:
    """Recursively convert a rosbags message into plain Python values."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: to_plain(getattr(obj, k)) for k in obj.__dataclass_fields__ if k != "__msgtype__"}
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if isinstance(obj, (list, tuple)):
        return [to_plain(v) for v in obj]
    if isinstance(obj, bytes):
        return list(obj)
    return obj


def normalize(obj: Any) -> Any:
    """Remove the differences that ROS 1 -> ROS 2 conversion makes on purpose.

    Exactly two, and nothing else:
    - ``header.seq``: ROS 2's ``std_msgs/Header`` has no sequence counter.
      Message order and timing are covered by the record-timestamp check.
    - Constants (all-uppercase names such as ``COVARIANCE_TYPE_KNOWN``): rosbags
      lists a type's constants next to its fields. They belong to the type
      definition and are not message data.
    """
    if isinstance(obj, dict):
        out = {k: normalize(v) for k, v in obj.items() if not k.isupper()}
        header = out.get("header")
        if isinstance(header, dict):
            header.pop("seq", None)
        return out
    if isinstance(obj, list):
        return [normalize(v) for v in obj]
    return obj


def first_difference(a: Any, b: Any, path: str = "") -> str | None:
    """Return the path of the first differing value, or None if equal.

    Floats are compared exactly, except that NaN equals NaN: conversion must not
    change values at all.
    """
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            return f"{path}: keys {sorted(a)} != {sorted(b)}"
        for k in a:
            d = first_difference(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f"{path}: length {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_difference(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return None
    if a != b:
        return f"{path}: {a!r} != {b!r}"
    return None


def read_index(bag: Path) -> tuple[dict[str, str], dict[str, list[int]]]:
    """Message type and record timestamps of every message, per topic."""
    types: dict[str, str] = {}
    times: dict[str, list[int]] = defaultdict(list)
    with AnyReader([bag]) as reader:
        for conn, t_ns, _ in reader.messages():
            types[conn.topic] = conn.msgtype
            times[conn.topic].append(t_ns)
    return types, dict(times)


def read_samples(bag: Path, wanted: dict[str, set[int]]) -> dict[str, dict[int, Any]]:
    """Deserialise the messages at the given per-topic indices."""
    out: dict[str, dict[int, Any]] = defaultdict(dict)
    counters: dict[str, int] = defaultdict(int)
    with AnyReader([bag]) as reader:
        for conn, _, raw in reader.messages():
            i = counters[conn.topic]
            counters[conn.topic] += 1
            if i in wanted.get(conn.topic, ()):
                out[conn.topic][i] = normalize(to_plain(reader.deserialize(raw, conn.msgtype)))
    return dict(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("raw", type=Path)
    parser.add_argument("converted", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--ros2-dump", type=Path, default=None)
    parser.add_argument(
        "--allow-uninstalled",
        nargs="*",
        default=[],
        metavar="MSGTYPE",
        help="message types allowed to be missing from ROS 2 in check 3 (reported, not failed)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    failures: list[str] = []
    report: dict[str, Any] = {"raw": str(args.raw), "converted": str(args.converted), "topics": {}}

    log.info("check 1: types, counts, record timestamps")
    raw_types, raw_times = read_index(args.raw)
    conv_types, conv_times = read_index(args.converted)
    if raw_types.keys() != conv_types.keys():
        failures.append(f"topic sets differ: {sorted(raw_types.keys() ^ conv_types.keys())}")
    for topic in sorted(raw_types.keys() & conv_types.keys()):
        entry = {
            "msgtype": raw_types[topic],
            "count": len(raw_times[topic]),
            "type_equal": raw_types[topic] == conv_types[topic],
            "count_equal": len(raw_times[topic]) == len(conv_times[topic]),
            "record_times_equal": raw_times[topic] == conv_times[topic],
        }
        report["topics"][topic] = entry
        for key in ("type_equal", "count_equal", "record_times_equal"):
            if not entry[key]:
                failures.append(f"{topic}: {key} is false")

    log.info("check 2: field values on %d sampled messages per topic", SAMPLES_PER_TOPIC)
    wanted: dict[str, set[int]] = {}
    for topic, times in raw_times.items():
        n = len(times)
        step = max(1, n // SAMPLES_PER_TOPIC)
        wanted[topic] = set(range(0, n, step)) | {n - 1}
    raw_s = read_samples(args.raw, wanted)
    conv_s = read_samples(args.converted, wanted)
    for topic, idx in wanted.items():
        diffs = []
        for i in sorted(idx):
            d = first_difference(raw_s.get(topic, {}).get(i), conv_s.get(topic, {}).get(i), f"msg[{i}]")
            if d:
                diffs.append(d)
        report["topics"].setdefault(topic, {})["sampled"] = len(idx)
        report["topics"][topic]["sample_mismatches"] = diffs[:5]
        if diffs:
            failures.append(f"{topic}: {len(diffs)} sampled messages differ, first: {diffs[0]}")

    if args.ros2_dump:
        log.info("check 3: raw bag vs messages decoded by ROS 2")
        dump = json.loads(args.ros2_dump.read_text())
        allowed = set(args.allow_uninstalled)
        not_installed = {t: raw_types[t] for t in dump["type_not_installed"]}
        report["ros2_types_not_installed"] = not_installed
        report["ros2_types_allowed_missing"] = sorted(allowed)
        unexpected = {t: m for t, m in not_installed.items() if m not in allowed}
        if unexpected:
            failures.append(f"types not installed in ROS 2: {unexpected}")
        first_raw = read_samples(args.raw, {t: set(range(len(m))) for t, m in dump["messages"].items()})
        for topic, msgs in dump["messages"].items():
            for i, ros_msg in enumerate(msgs):
                d = first_difference(first_raw[topic][i], normalize(ros_msg), f"{topic} msg[{i}]")
                report["topics"][topic].setdefault("ros2_decode_mismatches", [])
                if d:
                    report["topics"][topic]["ros2_decode_mismatches"].append(d)
                    failures.append(d)
            report["topics"][topic]["ros2_decoded"] = len(msgs)
        missing = sorted(set(raw_types) - set(dump["messages"]) - set(not_installed))
        if missing:
            failures.append(f"no ROS 2-decoded messages for: {missing}")

    report["failures"] = failures
    report["passed"] = not failures
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    for f in failures:
        log.error(f)
    log.info("%s: %d topics, report at %s", "PASSED" if not failures else "FAILED", len(report["topics"]), args.out)
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()
