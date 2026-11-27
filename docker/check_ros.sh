#!/usr/bin/env bash
# Smoke test for the ROS 2 image: builds it, then inside a container checks
# that ROS 2 runs (a message is published and received), that the build and
# bag tools are present, and that data/raw is read-only.
#
# Usage: bash docker/check_ros.sh
set -euo pipefail

docker compose build ros

docker compose run --rm ros bash -c '
set -euo pipefail
echo "ROS_DISTRO=${ROS_DISTRO}"

ros2 topic pub --rate 5 /smoke std_msgs/msg/String "{data: hello}" >/dev/null &
PUB_PID=$!
timeout 30 ros2 topic echo --once /smoke std_msgs/msg/String
kill "${PUB_PID}"
echo "pub/sub ok"

colcon --log-base /tmp/colcon_log version-check >/dev/null && echo "colcon ok"
ros2 pkg prefix rosbag2_storage_mcap >/dev/null && echo "mcap storage ok"

if touch data/raw/.write_test 2>/dev/null; then
    rm -f data/raw/.write_test
    echo "FAIL: data/raw is writable" >&2
    exit 1
fi
echo "data/raw is read-only"
'
echo "ROS check passed"
