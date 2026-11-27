"""One-off check: is the reference trajectory derived from a GNSS fix topic?

Compares a TUM trajectory file with a ``sensor_msgs/NavSatFix`` topic:

1. timestamps: one-to-one match between file rows and ``header.stamp``;
2. geometry: distance of each fix from the first fix (local tangent-plane
   approximation, adequate over a few hundred metres) against the distance of
   each file position from the first position. Distances from a common origin
   do not depend on how the file's axes are rotated, so no alignment is needed;
3. fix status and reported covariance, as a hint of RTK quality.

Usage:
    uv run python scripts/check_gt_source.py data/raw/Outdoor01.bag data/raw/Outdoor01.txt \
        /mavros/global_position/raw/fix outputs/inventory/gt_source.json
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from collections import Counter
from pathlib import Path

import numpy as np
from rosbags.highlevel import AnyReader

log = logging.getLogger(__name__)

EARTH_RADIUS_M = 6_378_137.0  # WGS-84 equatorial radius


def to_ns(s: str) -> int:
    """Decimal-seconds string to integer nanoseconds, without float rounding."""
    whole, _, frac = s.partition(".")
    return int(whole) * 1_000_000_000 + int((frac + "000000000")[:9])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("bag", type=Path)
    parser.add_argument("traj", type=Path)
    parser.add_argument("topic")
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    rows = [ln.split() for ln in args.traj.read_text().splitlines() if ln.strip()]
    t_file = np.array([to_ns(r[0]) for r in rows], dtype=np.int64)
    xyz_file = np.array([[float(v) for v in r[1:4]] for r in rows])

    t_fix, lla, status, cov_type, cov_diag = [], [], [], [], []
    with AnyReader([args.bag]) as reader:
        conns = [c for c in reader.connections if c.topic == args.topic]
        # An empty list would make rosbags yield *every* message, so fail here.
        if not conns:
            raise ValueError(f"topic {args.topic!r} not in bag")
        for conn, _, raw in reader.messages(connections=conns):
            m = reader.deserialize(raw, conn.msgtype)
            t_fix.append(m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec)
            lla.append((m.latitude, m.longitude, m.altitude))
            status.append(int(m.status.status))
            cov_type.append(int(m.position_covariance_type))
            cov_diag.append([float(m.position_covariance[i]) for i in (0, 4, 8)])
    t_fix_a = np.array(t_fix, dtype=np.int64)
    lla_a = np.array(lla)

    # Timestamp correspondence (file stored at microsecond precision).
    n = min(len(t_file), len(t_fix_a))
    dt_us = (t_fix_a[:n] - t_file[:n]) / 1e3

    # Local tangent-plane coordinates (east, north, up) relative to the first fix.
    lat0 = math.radians(lla_a[0, 0])
    east = np.radians(lla_a[:, 1] - lla_a[0, 1]) * EARTH_RADIUS_M * math.cos(lat0)
    north = np.radians(lla_a[:, 0] - lla_a[0, 0]) * EARTH_RADIUS_M
    up = lla_a[:, 2] - lla_a[0, 2]
    enu = np.stack([east, north, up], axis=1)

    d_fix_h = np.linalg.norm(enu[:n, :2], axis=1)
    d_file_h = np.linalg.norm(xyz_file[:n, :2] - xyz_file[0, :2], axis=1)
    resid = d_fix_h - d_file_h

    report = {
        "topic": args.topic,
        "n_file_rows": len(t_file),
        "n_fix_msgs": len(t_fix_a),
        "stamp_diff_us": {"min": float(dt_us.min()), "max": float(dt_us.max()), "abs_max": float(np.abs(dt_us).max())},
        "horizontal_dist_from_origin_residual_m": {
            "abs_max": float(np.abs(resid).max()),
            "rms": float(np.sqrt(np.mean(resid**2))),
        },
        "up_vs_file_z_residual_m": {
            "abs_max": float(np.abs(up[:n] - (xyz_file[:n, 2] - xyz_file[0, 2])).max()),
        },
        "enu_extent_m": {"min": enu.min(axis=0).tolist(), "max": enu.max(axis=0).tolist()},
        "file_extent_m": {"min": xyz_file.min(axis=0).tolist(), "max": xyz_file.max(axis=0).tolist()},
        "first_fix_lla": lla_a[0].tolist(),
        "fix_status_counts": dict(Counter(status)),
        "covariance_type_counts": dict(Counter(cov_type)),
        "cov_diag_median_m2": np.median(np.array(cov_diag), axis=0).tolist(),
        "cov_diag_max_m2": np.max(np.array(cov_diag), axis=0).tolist(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
