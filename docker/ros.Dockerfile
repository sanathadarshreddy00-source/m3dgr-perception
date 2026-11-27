# ROS 2 Jazzy environment: SLAM, bag playback and the live system (D-006, D-010).
#
# Build and run through compose.yaml:  docker compose run --rm ros
#
# The base image is pinned by digest. Packages installed with apt are not
# version-pinned: the ROS apt repository keeps only the latest version of each
# package (see D-012).
FROM ros:jazzy-ros-base-noble@sha256:5147d3ae250ce754afd399f6bfec15b33dd4e473ca357e30432a3182031bfad6

# Listed explicitly even where the base image already contains them, so the
# image's dependencies are declared here rather than inherited by accident.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        python3-colcon-common-extensions \
        ros-jazzy-rosbag2-storage-mcap \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ws
