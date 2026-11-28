#!/usr/bin/env bash
# Convert the raw ROS 1 bag to a ROS 2 (MCAP) bag and verify it (D-011).
#
# Steps:
#   1. rosbags-convert, default typestore mode: definitions copied from the
#      bag, which already yields ROS 2 headers (verified, see docs/data.md).
#   2. Build the Livox message packages in the ROS container (D-013).
#   3. Decode the first messages of every topic with ROS 2 itself.
#   4. Compare against the raw bag (scripts/verify_conversion.py).
#   5. Write PROVENANCE.json next to the converted bag.
#
# Usage, from the repository root in Git Bash:  bash scripts/convert_bag.sh
set -euo pipefail
export MSYS_NO_PATHCONV=1  # stop Git Bash rewriting topic names as paths

RAW=data/raw/Outdoor01.bag
DST=data/interim/Outdoor01_ros2
OUT=outputs/conversion

# gnss_comm types (raw u-blox measurements) are not built in ROS 2: no goal
# uses them, and gnss_comm is GPL-3.0 (docs/data.md, "ROS 2 copy").
GNSS_COMM_TYPES=(
    gnss_comm/msg/GnssPVTSolnMsg gnss_comm/msg/GnssMeasMsg gnss_comm/msg/GnssEphemMsg
    gnss_comm/msg/GnssGloEphemMsg gnss_comm/msg/StampedFloat64Array
)

if [[ -e "${DST}" ]]; then
    echo "${DST} exists; remove it first to reconvert" >&2
    exit 1
fi
mkdir -p "${OUT}"

echo "== 1/5 convert"
uv run rosbags-convert --src "${RAW}" --dst "${DST}" --dst-storage mcap

echo "== 2/5 build Livox message packages"
docker compose run --rm -T ros bash -c "cd ros2_ws && colcon build --event-handlers console_cohesion-"

echo "== 3/5 decode with ROS 2"
docker compose run --rm -T ros bash -c \
    "source ros2_ws/install/setup.bash && python3 scripts/ros2_dump_messages.py ${DST} --count 2" \
    > "${OUT}/ros2_dump.json"

echo "== 4/5 verify"
uv run python scripts/verify_conversion.py "${RAW}" "${DST}" "${OUT}/verify.json" \
    --ros2-dump "${OUT}/ros2_dump.json" --allow-uninstalled "${GNSS_COMM_TYPES[@]}"

echo "== 5/5 provenance"
uv run python - "${RAW}" "${DST}" <<'EOF'
import json, subprocess, sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

raw, dst = sys.argv[1], Path(sys.argv[2])
sums = dict(reversed(line.split(" *", 1)) for line in Path("data/SHA256SUMS").read_text().splitlines())
record = {
    "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "source": raw,
    "source_sha256": sums[raw.removeprefix("data/")],
    "tool": f"rosbags-convert {version('rosbags')}",
    "command": f"rosbags-convert --src {raw} --dst {dst.as_posix()} --dst-storage mcap",
    "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()),
    "verification": "outputs/conversion/verify.json (passed)",
}
(dst / "PROVENANCE.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
EOF
echo "conversion done and verified"
