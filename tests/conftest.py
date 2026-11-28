"""Shared fixtures: a small synthetic ROS 1 bag shaped like Outdoor01.

The bag is generated during the test session instead of being committed:
nothing large enters git, and no part of the M3DGR dataset is redistributed.
It contains the cases that matter for conversion:

- ``std_msgs/Header`` with a ``seq`` counter (dropped by ROS 2),
- types with constants (``sensor_msgs/NavSatFix``),
- a NaN field value,
- a custom type not in the standard type store (``livox_ros_driver/CustomMsg``,
  registered from the definitions in ``ros2_ws/src``).
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from rosbags.rosbag1 import Writer
from rosbags.typesys import Stores, get_types_from_msg, get_typestore
from rosbags.typesys.store import Typestore

REPO = Path(__file__).resolve().parents[1]
LIVOX_MSG_DIR = REPO / "ros2_ws" / "src" / "livox_ros_driver" / "msg"

N_MESSAGES = 20  # per topic: small enough that check 2 samples every message
T0_NS = 1_735_900_000_000_000_000  # 2025-01-03, the recording date of Outdoor01


@dataclass(frozen=True)
class Mutation:
    """A deliberate difference to write into one bag."""

    imu_accel_x_offset: float = 0.0  # added to linear_acceleration.x of IMU message 7
    record_time_shift_ns: int = 0  # added to the record time of IMU message 7
    extra_topic: bool = False  # add a topic that the other bag does not have


def _typestore() -> Typestore:
    store = get_typestore(Stores.ROS1_NOETIC)
    for name in ("CustomPoint", "CustomMsg"):
        text = (LIVOX_MSG_DIR / f"{name}.msg").read_text()
        store.register(get_types_from_msg(text, f"livox_ros_driver/msg/{name}"))
    return store


def _header(store: Typestore, seq: int, t_ns: int, frame_id: str) -> Any:
    time = store.types["builtin_interfaces/msg/Time"]
    header = store.types["std_msgs/msg/Header"]
    return header(
        seq=seq,
        stamp=time(sec=t_ns // 1_000_000_000, nanosec=t_ns % 1_000_000_000),
        frame_id=frame_id,
    )


def _imu(store: Typestore, i: int, t_ns: int, accel_x_offset: float) -> Any:
    t = store.types
    vec = t["geometry_msgs/msg/Vector3"]
    no_orientation = np.zeros(9)
    no_orientation[0] = -1.0  # ROS convention: orientation not provided
    return t["sensor_msgs/msg/Imu"](
        header=_header(store, i, t_ns, "imu_link"),
        orientation=t["geometry_msgs/msg/Quaternion"](x=0.0, y=0.0, z=0.0, w=1.0),
        orientation_covariance=no_orientation,
        angular_velocity=vec(x=0.01 * i, y=-0.02, z=float("nan") if i == 3 else 0.03),
        angular_velocity_covariance=np.zeros(9),
        linear_acceleration=vec(x=0.1 * i + accel_x_offset, y=0.0, z=9.81),
        linear_acceleration_covariance=np.zeros(9),
    )


def _fix(store: Typestore, i: int, t_ns: int) -> Any:
    t = store.types
    return t["sensor_msgs/msg/NavSatFix"](
        header=_header(store, i, t_ns, "gps"),
        status=t["sensor_msgs/msg/NavSatStatus"](status=2, service=1),
        latitude=22.5 + 1e-6 * i,
        longitude=113.9,
        altitude=40.0,
        position_covariance=np.diag([0.49, 0.49, 1.0]).ravel(),
        position_covariance_type=2,
    )


def _livox(store: Typestore, i: int, t_ns: int) -> Any:
    t = store.types
    point = t["livox_ros_driver/msg/CustomPoint"]
    points = [
        point(offset_time=k * 1000, x=1.0 + k, y=0.5, z=-0.2, reflectivity=k, tag=0, line=k % 6)
        for k in range(5)
    ]
    return t["livox_ros_driver/msg/CustomMsg"](
        header=_header(store, i, t_ns, "livox_frame"),
        timebase=123_456_789 + i,
        point_num=len(points),
        lidar_id=0,
        rsvd=np.zeros(3, dtype=np.uint8),
        points=points,
    )


def write_synthetic_bag(path: Path, mutation: Mutation = Mutation()) -> Path:
    """Write a synthetic ROS 1 bag to ``path`` and return the path."""
    store = _typestore()
    topics: list[tuple[str, str, Callable[[int, int], Any]]] = [
        (
            "/imu",
            "sensor_msgs/msg/Imu",
            lambda i, t: _imu(store, i, t, mutation.imu_accel_x_offset if i == 7 else 0.0),
        ),
        ("/fix", "sensor_msgs/msg/NavSatFix", lambda i, t: _fix(store, i, t)),
        ("/livox/lidar", "livox_ros_driver/msg/CustomMsg", lambda i, t: _livox(store, i, t)),
    ]
    if mutation.extra_topic:
        topics.append(("/fix_extra", "sensor_msgs/msg/NavSatFix", lambda i, t: _fix(store, i, t)))

    with Writer(path) as writer:
        conns = [(writer.add_connection(n, m, typestore=store), m, f) for n, m, f in topics]
        for i in range(N_MESSAGES):
            for k, (conn, msgtype, make) in enumerate(conns):
                stamp = T0_NS + i * 10_000_000 + k * 1_000  # 100 Hz, topics 1 µs apart
                record = stamp + 5_000_000  # arrives 5 ms after its stamp
                if conn.topic == "/imu" and i == 7:
                    record += mutation.record_time_shift_ns
                writer.write(conn, record, store.serialize_ros1(make(i, stamp), msgtype))
    return path


def convert_to_mcap(src: Path, dst: Path) -> Path:
    """Convert like scripts/convert_bag.sh step 1 does: the rosbags-convert CLI."""
    subprocess.run(
        [
            sys.executable,
            "-m",
            "rosbags.convert",
            "--src",
            str(src),
            "--dst",
            str(dst),
            "--dst-storage",
            "mcap",
        ],
        check=True,
        capture_output=True,
    )
    return dst


@pytest.fixture(scope="session")
def raw_bag(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """An unmodified synthetic ROS 1 bag."""
    return write_synthetic_bag(tmp_path_factory.mktemp("raw") / "synthetic.bag")


@pytest.fixture(scope="session")
def converted_bag(raw_bag: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """``raw_bag`` converted to ROS 2 MCAP."""
    return convert_to_mcap(raw_bag, tmp_path_factory.mktemp("conv") / "synthetic_ros2")
