"""One-off inventory of a ROS bag: topics, rates, time bases, frames, calibration.

Reads the bag without modifying it and writes a JSON report. Per topic:

- message type, count, and the time span and rate of the *record* timestamps
  (when the recorder received each message), over every message;
- for messages that carry a ``std_msgs/Header``: the ``header.stamp`` span and
  the offset ``record_time - header.stamp``, from a uniform sample of messages
  (deserialising every LiDAR scan in pure Python would take very long);
- frame ids seen in the sample.

It also dumps the full first message of every CameraInfo topic, all of
``/tf_static``, the frame pairs seen on ``/tf``, and the message definitions of
every non-standard message type (for example the Livox custom messages).

Usage:
    uv run python scripts/inventory_bag.py data/raw/Outdoor01.bag outputs/inventory/bag.json
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
from collections import defaultdict
from itertools import pairwise
from pathlib import Path
from typing import Any

from rosbags.highlevel import AnyReader

log = logging.getLogger(__name__)

SAMPLES_PER_TOPIC = 400
STANDARD_PREFIXES = (
    "std_msgs/",
    "sensor_msgs/",
    "geometry_msgs/",
    "nav_msgs/",
    "tf2_msgs/",
    "builtin_interfaces/",
)


def stamp_ns(stamp: Any) -> int:
    """Convert a ROS time (``sec``, ``nanosec``) to integer nanoseconds."""
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def to_plain(obj: Any) -> Any:
    """Recursively convert a deserialised ROS message into JSON-friendly types."""
    if hasattr(obj, "__dataclass_fields__"):
        return {
            k: to_plain(getattr(obj, k)) for k in obj.__dataclass_fields__ if k != "__msgtype__"
        }
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if isinstance(obj, (list, tuple)):
        return [to_plain(v) for v in obj]
    if isinstance(obj, bytes):
        return f"<{len(obj)} bytes>"
    return obj


def summarise(values: list[int]) -> dict[str, float] | None:
    """Min / median / max of a list of nanosecond values, reported in seconds."""
    if not values:
        return None
    return {
        "min_s": min(values) / 1e9,
        "median_s": statistics.median(values) / 1e9,
        "max_s": max(values) / 1e9,
    }


def inventory(bag_path: Path) -> dict[str, Any]:
    report: dict[str, Any] = {"bag": str(bag_path), "topics": {}}
    with AnyReader([bag_path]) as reader:
        report["start_ns"] = reader.start_time
        report["end_ns"] = reader.end_time
        report["duration_s"] = (reader.end_time - reader.start_time) / 1e9

        # Pass 1: record timestamps of every message (cheap, no deserialisation).
        record_times: dict[str, list[int]] = defaultdict(list)
        msgtypes: dict[str, str] = {}
        for conn, t_ns, _ in reader.messages():
            record_times[conn.topic].append(t_ns)
            msgtypes[conn.topic] = conn.msgtype

        # Message definitions of non-standard types, as stored in the bag.
        report["custom_msgdefs"] = {
            conn.msgtype: conn.msgdef.data
            for conn in reader.connections
            if not conn.msgtype.startswith(STANDARD_PREFIXES)
        }

        # Pass 2: deserialise a uniform sample per topic.
        sample_idx: dict[str, set[int]] = {}
        for topic, times in record_times.items():
            n = len(times)
            step = max(1, n // SAMPLES_PER_TOPIC)
            sample_idx[topic] = set(range(0, n, step)) | {n - 1}

        counters: dict[str, int] = defaultdict(int)
        offsets: dict[str, list[int]] = defaultdict(list)
        header_stamps: dict[str, list[int]] = defaultdict(list)
        frame_ids: dict[str, set[str]] = defaultdict(set)
        camera_info: dict[str, Any] = {}
        tf_static: list[dict[str, Any]] = []
        tf_pairs: set[tuple[str, str]] = set()
        deserialise_errors: dict[str, str] = {}

        for conn, t_ns, raw in reader.messages():
            topic = conn.topic
            i = counters[topic]
            counters[topic] += 1
            always = conn.msgtype in ("tf2_msgs/msg/TFMessage",) or (
                conn.msgtype == "sensor_msgs/msg/CameraInfo" and topic not in camera_info
            )
            if i not in sample_idx[topic] and not always:
                continue
            try:
                # Class built at runtime from the bag's own definitions: no static type.
                msg: Any = reader.deserialize(raw, conn.msgtype)
            except Exception as exc:  # noqa: BLE001 - recorded per topic in the report
                deserialise_errors[topic] = repr(exc)
                continue

            if conn.msgtype == "sensor_msgs/msg/CameraInfo" and topic not in camera_info:
                camera_info[topic] = to_plain(msg)
            if conn.msgtype == "tf2_msgs/msg/TFMessage":
                for tf in msg.transforms:
                    if topic == "/tf_static":
                        tf_static.append(to_plain(tf))
                    else:
                        tf_pairs.add((tf.header.frame_id, tf.child_frame_id))
                if i not in sample_idx[topic]:
                    continue

            header = getattr(msg, "header", None)
            if header is not None and hasattr(header, "stamp"):
                h_ns = stamp_ns(header.stamp)
                header_stamps[topic].append(h_ns)
                offsets[topic].append(t_ns - h_ns)
                frame_ids[topic].add(header.frame_id)

        for topic, times in sorted(record_times.items()):
            n = len(times)
            span = (times[-1] - times[0]) / 1e9 if n > 1 else 0.0
            gaps = [b - a for a, b in pairwise(times)]
            hs = header_stamps.get(topic, [])
            report["topics"][topic] = {
                "msgtype": msgtypes[topic],
                "count": n,
                "record_first_ns": times[0],
                "record_last_ns": times[-1],
                "record_span_s": span,
                "mean_rate_hz": (n - 1) / span if span > 0 else None,
                "record_gap": summarise(gaps),
                "header_sampled": len(hs),
                "header_first_ns": min(hs) if hs else None,
                "header_last_ns": max(hs) if hs else None,
                "record_minus_header": summarise(offsets.get(topic, [])),
                "frame_ids": sorted(frame_ids.get(topic, set())),
            }

        report["camera_info"] = camera_info
        report["tf_static"] = tf_static
        report["tf_pairs"] = sorted(tf_pairs)
        report["deserialise_errors"] = deserialise_errors
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("bag", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    report = inventory(args.bag)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    log.info("wrote %s (%d topics)", args.out, len(report["topics"]))
    if report["deserialise_errors"]:
        log.warning("deserialisation failed on: %s", sorted(report["deserialise_errors"]))


if __name__ == "__main__":
    main()
