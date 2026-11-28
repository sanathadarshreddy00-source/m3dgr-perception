"""Dump the first messages of each topic in a ROS 2 bag, decoded by ROS 2 itself.

Runs inside the ROS 2 container. Messages are deserialised with the message
types installed in ROS 2 (``rclpy``), which is how ``ros2 bag play`` and every
subscriber interpret the bytes. Comparing this output with values read from the
raw ROS 1 bag shows whether a conversion is faithful.

Topics whose type is not installed are reported, not skipped silently.

Usage (inside the container):
    python3 scripts/ros2_dump_messages.py data/interim/<bag_dir> --count 3
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from typing import Any

import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.convert import message_to_ordereddict
from rosidl_runtime_py.utilities import get_message


def plain(obj: Any) -> Any:
    """Convert arrays, bytes and numpy values into plain lists and scalars."""
    if isinstance(obj, dict):
        return {k: plain(v) for k, v in obj.items()}
    if isinstance(obj, (bytes, bytearray)):
        return list(obj)
    if hasattr(obj, "tolist"):  # numpy arrays and scalars, array.array
        return plain(obj.tolist())
    if isinstance(obj, (list, tuple)):
        return [plain(v) for v in obj]
    return obj


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("bag")
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()

    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=args.bag, storage_id="mcap"),
        rosbag2_py.ConverterOptions("cdr", "cdr"),
    )
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}

    msg_classes: dict[str, Any] = {}
    missing: dict[str, str] = {}
    for topic, typename in types.items():
        try:
            msg_classes[topic] = get_message(typename)
        except (AttributeError, ModuleNotFoundError, ValueError) as exc:
            missing[topic] = f"{typename}: {exc!r}"

    out: dict[str, list[Any]] = defaultdict(list)
    while reader.has_next():
        topic, data, _ = reader.read_next()
        if topic not in msg_classes or len(out[topic]) >= args.count:
            continue
        msg = deserialize_message(data, msg_classes[topic])
        out[topic].append(plain(message_to_ordereddict(msg)))
        if all(len(out[t]) >= args.count for t in msg_classes):
            break

    # No default= fallback: an unconverted type should fail loudly, not become a string.
    print(json.dumps({"messages": out, "type_not_installed": missing}))  # noqa: T201 - stdout is piped to a file


if __name__ == "__main__":
    main()
