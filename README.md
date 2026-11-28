# M3DGR Outdoor01: Multi-Sensor Trajectory Estimation and 3D Reconstruction

> **Status:** project charter, pre-implementation. Nothing below has been
> built yet. This document states what the project sets out to do and how
> results will be judged. It will be updated as work lands.

## Purpose

This project uses one recorded robot run, the `Outdoor01` sequence from the
[M3DGR dataset](https://github.com/sjtuyinjie/M3DGR), to work through the core
of a 3D perception stack end to end: estimating where the robot went,
reconstructing what it saw, and running perception as a live system.

## Data

The data is a single ROS 1 bag, `Outdoor01.bag` (6.5 GB, 411.6 s), plus
`Outdoor01.txt`, a reference trajectory. The bag contains:

- RGB and aligned depth from an Intel RealSense D435i, at 30 Hz
- a 360° camera (Insta360 X4), at 15 Hz
- two Livox LiDARs, the Mid-360 and the Avia, each at 10 Hz
- three IMUs (Mid-360, Avia and the camera), each at about 200 Hz
- two GNSS receivers
- wheel odometry (`/odom`), at 20 Hz

`Outdoor01.txt` holds **positions only**; orientation is not provided. It is
derived from the RTK GNSS fix in the bag. Its accuracy is not yet established.

The bag contains no calibration. Calibration comes from the M3DGR
documentation.

Details, measurements and their sources are in [docs/data.md](docs/data.md).
Raw data is never modified and is not stored in this repository.

## Repository layout

```
src/m3dgr/          Python package
  core/             math and domain types; no I/O, no ROS
  io/               bags, trajectory files, calibration
  pipelines/        stages combining core and io
  cli/              one command per stage
ros2_ws/src/        ROS 2 packages
docker/             one Dockerfile per environment
configs/            all parameters, including calibration with its source
experiments/        one record per run: config, commit, metrics, verdict
tests/              pytest; test bags are generated, not stored
scripts/            one-off scripts (e.g. the data inventory)
docs/               data inventory, conventions, decision log
data/, outputs/     not in git; data/raw/ is read-only
```

Most folders are empty until the first stage that needs them. Conventions
for contributing are in [docs/conventions.md](docs/conventions.md).

## Development setup

Python tools run on Windows through [uv](https://docs.astral.sh/uv/); ROS 2
runs in Docker (`compose.yaml`).

```
uv sync                 # install the package and dev tools, as pinned in uv.lock
uv run ruff check .     # lint
uv run ruff format .    # format
uv run mypy             # type check (strict)
uv run pytest           # fast tests, seconds
uv run pytest -m slow   # tests on the real data in data/raw
```

Tool settings are in `pyproject.toml`; the reasons are in
[docs/decisions.md](docs/decisions.md) (D-014).

## Goals

### 1. Trajectory estimation and comparison

Estimate the robot's trajectory with several independent methods and compare
each against the reference trajectory:

- onboard odometry (`/odom`), as provided
- LiDAR(-inertial) SLAM, run separately on the Mid-360 and the Avia
- image-based Structure-from-Motion (COLMAP or similar)

**Success criteria**

- Every method either produces a trajectory over the sequence or has a
  documented, explained failure (for example, SfM failing to initialise on
  low-parallax straight driving).
- Errors reported as absolute trajectory error (ATE) and relative pose error
  (RPE), using an alignment appropriate to each method: rigid alignment for
  metric methods, similarity alignment for scale-ambiguous monocular SfM.
- Results broken down by trajectory segment (for example, straights vs.
  turns), not only as whole-sequence averages.
- The project's own metric implementation agrees with an established tool
  (`evo`) within a stated tolerance.

### 2. 3D reconstruction

Reconstruct the scene from both sensing modalities:

- **LiDAR-based:** a point-cloud map from motion-corrected scans registered
  with estimated poses, and a surface mesh from that map.
- **Image-based:** neural reconstruction (NeRF and 3D Gaussian splatting),
  optionally supervised with depth.

**Success criteria**

- Image metrics (PSNR, SSIM, LPIPS) computed on held-out views that are
  chosen before training and never used for model or checkpoint selection.
- Geometric accuracy reported in metres against a stated reference, with the
  choice of reference and its own limitations made explicit.
- A comparison of how pose quality (reference vs. estimated trajectories)
  affects reconstruction quality.

### 3. Deployment as a live system

Run the perception stack the way it would run on a robot:

- a containerised ROS 2 system that replays the bag at real-time speed
- at least one perception component written as a C++ ROS 2 node

**Success criteria**

- The system runs from a documented single command on a fresh machine with
  Docker installed.
- Latency, throughput (whether it keeps up with real time), CPU and memory
  are measured and reported.
- The C++ node is benchmarked against a Python implementation of the same
  step.

### 4. Engineering practice

- Every environment can be rebuilt from files in this repository.
- Each pipeline stage runs from one command, driven by a saved config.
- Each run records its config, seed and git commit alongside its outputs.
- Automated tests and linting run on every change, using a small fixture
  rather than the full bag.

## Out of scope

- Developing new SLAM or reconstruction methods.
- Running on physical robot hardware (the containers are meant to make that
  possible later, but it is not a goal here).
- Other M3DGR sequences. They may be added later to test generalisation.
- Web serving or production APIs.

## Open questions

- How accurate the reference trajectory is, and which point on the robot it
  refers to. See [docs/data.md](docs/data.md).
- What serves as the reference for geometric accuracy, given that no
  independent ground-truth geometry is known to exist for this sequence.
