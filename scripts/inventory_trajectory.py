"""One-off inventory of a whitespace-separated trajectory file (expected TUM).

TUM format: one pose per line, ``t tx ty tz qx qy qz qw``, with ``t`` in
seconds. This script checks that assumption rather than trusting it, and
reports: column count, duplicated rows and timestamps, sampling intervals,
time span, quaternion norms, and the spatial extent and path length.

Usage:
    uv run python scripts/inventory_trajectory.py data/raw/Outdoor01.txt \
        outputs/inventory/trajectory.json
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
from collections import Counter
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("traj", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    lines = [
        ln for ln in args.traj.read_text().splitlines() if ln.strip() and not ln.startswith("#")
    ]
    ncols = Counter(len(ln.split()) for ln in lines)
    if set(ncols) != {8}:
        raise ValueError(f"expected 8 columns on every line, got column counts {dict(ncols)}")

    # Timestamps parsed as decimal strings to integer ns, to avoid float rounding.
    def to_ns(s: str) -> int:
        whole, _, frac = s.partition(".")
        return int(whole) * 1_000_000_000 + int((frac + "000000000")[:9])

    t_ns = np.array([to_ns(ln.split()[0]) for ln in lines], dtype=np.int64)
    data = np.array([[float(v) for v in ln.split()[1:]] for ln in lines])
    xyz, quat = data[:, :3], data[:, 3:]

    row_counts = Counter(lines)
    t_counts = Counter(t_ns.tolist())
    unique_rows = len(row_counts)
    dt = np.diff(t_ns)

    # Collapse exact duplicate rows (keeping order) before computing motion stats.
    _, first_idx = np.unique(np.array(lines), return_index=True)
    keep = np.sort(first_idx)
    xyz_u, t_u = xyz[keep], t_ns[keep]
    dt_u = np.diff(t_u)
    step = np.linalg.norm(np.diff(xyz_u, axis=0), axis=1)

    report = {
        "file": str(args.traj),
        "rows": len(lines),
        "unique_rows": unique_rows,
        "row_multiplicity": dict(Counter(row_counts.values())),
        "unique_timestamps": len(t_counts),
        "timestamp_multiplicity": dict(Counter(t_counts.values())),
        "monotonic_non_decreasing": bool((dt >= 0).all()),
        "first_t_ns": int(t_ns[0]),
        "last_t_ns": int(t_ns[-1]),
        "span_s": float((t_ns[-1] - t_ns[0]) / 1e9),
        "dt_unique_rows_s": {
            "min": float(dt_u.min() / 1e9),
            "median": float(statistics.median(dt_u.tolist()) / 1e9),
            "max": float(dt_u.max() / 1e9),
        },
        "quat_norm": {
            "min": float(np.linalg.norm(quat, axis=1).min()),
            "max": float(np.linalg.norm(quat, axis=1).max()),
        },
        "rows_identity_rotation": int((np.abs(quat - [0, 0, 0, 1]) < 1e-9).all(axis=1).sum()),
        "rows_zero_z": int((np.abs(xyz[:, 2]) < 1e-9).sum()),
        "xyz_min_m": xyz.min(axis=0).tolist(),
        "xyz_max_m": xyz.max(axis=0).tolist(),
        "path_length_m": float(step.sum()),
        "max_step_m": float(step.max()),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    log.info("wrote %s", args.out)
    print(json.dumps(report, indent=2))  # noqa: T201 - the report is the output


if __name__ == "__main__":
    main()
