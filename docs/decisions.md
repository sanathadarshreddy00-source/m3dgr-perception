# Decision log

Each entry records a decision that would be costly to reverse, or that someone
would later ask about. Entries are not edited after the fact. A changed
decision gets a new entry that supersedes the old one.

Format: context, decision, alternatives considered, consequences.

---

## D-001: Use ROS 2, converting the ROS 1 bag

**Date:** 2026-11-27 · **Status:** accepted (the ROS 2 distribution is still open)

**Context.** `Outdoor01.bag` is a ROS 1 bag. The deployment goal needs a live
ROS system, and the C++ perception node needs a ROS framework to run in.

**Decision.** Use ROS 2. Convert the bag to ROS 2 format once, and run all
ROS tooling on the converted bag.

**Alternatives.**
- *ROS 1 Noetic:* reads the bag natively, and several SLAM packages were
  written for it. But Noetic reached end of life in May 2025, and ROS 2 is
  what current robotics teams use.

**Consequences.**
- The Livox custom message types (`livox_ros_driver/CustomMsg`) must survive
  conversion. This is checked in the data inventory.
- SLAM packages need a working ROS 2 port, or a containerised alternative.
- The distribution (Humble or Jazzy) is chosen with the rest of the tool
  stack.

---

## D-002: Git workflow

**Date:** 2026-11-27 · **Status:** accepted

**Context.** The project is developed solo with an AI agent, but is meant to
follow the same practice a team would.

**Decision.**
- One branch per task. Changes reach `main` only through a pull request.
- Pull requests are squash-merged, so each one becomes one commit on `main`.
- Commit messages follow Conventional Commits.

**Alternatives.**
- *Committing directly to `main`:* simpler, but CI would not gate changes.
- *Rebase-merge:* keeps every commit of a branch. Work-in-progress commits
  would then end up in `main`.
- *Merge commits:* history is no longer linear and is harder to read.

**Consequences.** Branch protection on `main` (pull request required, CI must
pass, no force-push) is configured once CI exists.

---

## D-003: Public repository under the MIT license

**Date:** 2026-11-27 · **Status:** accepted

**Context.** The repository is meant to be read by others, and CI runs on
GitHub.

**Decision.** Host the repository publicly on GitHub, under the MIT license.

**Alternatives.**
- *Apache-2.0:* the same freedoms plus an explicit patent grant. That grant
  matters little for a project like this, and the license is much longer.
- *No license:* the code would be visible, but legally nobody could reuse it.

**Consequences.**
- The dataset is not redistributed. `data/` is gitignored.
- Third-party code under copyleft licenses (for example GPL) is run as an
  external tool, not copied into this repository. Each tool's license is
  recorded when the tool is chosen.

---

## D-004: Rule placement and enforcement

**Date:** 2026-11-27 · **Status:** accepted

**Context.** Written rules drift, especially when an agent starts each session
with no memory of the last one.

**Decision.**
- Rules that a tool can check are enforced by that tool (linter, pre-commit
  hook or CI) rather than by a written rule alone.
- Agent-specific rules live in `CLAUDE.md`, kept short because it is loaded
  into every agent session.
- Conventions shared by every contributor live in `docs/conventions.md`.

**Consequences.** Until the tooling phase, the rules marked **[tool]** in
`docs/conventions.md` are followed by hand.

---

## D-005: Transform naming and time representation

**Date:** 2026-11-27 · **Status:** accepted

**Context.** This project combines many coordinate frames: world, body, two
LiDARs, several cameras and IMUs. Frame mix-ups and time-matching errors are
easy to make and often fail silently.

**Decision.**
- A transform is named `T_a_b` and maps points from frame `b` into frame `a`.
- Timestamps are stored as integer nanoseconds.

**Alternatives.**
- *`T_b_a` or `T_from_to` ordering:* equally valid. One convention is needed,
  and `T_a_b` makes chained products easy to check, because the inner frames
  match.
- *Timestamps as float seconds:* convenient, but a `float64` holding
  nanosecond-scale epoch times loses precision, and comparing floats for
  equality is unreliable.

**Consequences.** Every module that handles poses or time depends on this.
Changing it later would touch the whole codebase.

---

## D-006: ROS 2 Jazzy

**Date:** 2026-11-27 · **Status:** accepted. This settles the open part of D-001.

**Context.** The ROS 2 releases with long-term support are Humble (Ubuntu
22.04), Jazzy (Ubuntu 24.04, supported until May 2029) and Lyrical (Ubuntu
26.04, released May 2026, supported until May 2031). The Livox driver
(`livox_ros_driver2`) and the community ROS 2 ports of FAST-LIO2 document
Humble and Jazzy.

**Decision.** Use ROS 2 Jazzy, in Docker on an Ubuntu 24.04 base image.

**Alternatives.**
- *Humble:* the most tested with LiDAR packages, but its support ends during
  this project.
- *Lyrical:* the longest support, but too new; the packages this project
  needs do not document it yet.

**Consequences.** Every ROS package that is used must build on Jazzy. That is
checked for each one when it is added.

---

## D-007: LiDAR SLAM: KISS-ICP first, then FAST-LIO2

**Date:** 2026-11-27 · **Status:** accepted

**Context.** Goal 1 needs a LiDAR trajectory from each of the Mid-360 and the
Avia. The bag also contains each LiDAR's own IMU.

**Decision.**
- KISS-ICP first. It uses LiDAR only, is installed with pip, runs from Python
  without ROS, and has few parameters.
- Then FAST-LIO2, which fuses LiDAR and IMU, run in the ROS 2 container from a
  community ROS 2 port.
- Both run on both LiDARs, so the results compare LiDAR-only with
  LiDAR-inertial methods.

**Alternatives.**
- *FAST-LIO2 only:* there would be nothing simpler to compare it against, and
  no trajectory until the ROS 2 environment works.
- *LIO-SAM:* needs an IMU that reports its own orientation (9-axis). None of
  the IMUs in the bag does: their orientation fields are all zero (see
  docs/data.md).

**Consequences.**
- FAST-LIO2 is GPL-2.0. It is run as an external tool; its code is not copied
  into this repository (D-003).
- One port documents per-point timestamps only for the `livox_ros_driver2`
  message. The Avia uses `livox_ros_driver`, whose fields are identical (see
  docs/data.md). Relabelling its message type during conversion must be
  tested.
- Point times come from `header.stamp + offset_time`, never `timebase`,
  because the Avia's `timebase` is on its own clock.

---

## D-008: Structure-from-Motion with COLMAP 4

**Date:** 2026-11-27 · **Status:** accepted

**Context.** Goal 1 needs an image-based trajectory. COLMAP 4.0 now includes
GLOMAP as its global mapper, so a single tool offers both incremental and
global reconstruction.

**Decision.** Use COLMAP 4 and compare its incremental and global mappers.

**Consequences.**
- The 12 338 RGB frames (30 Hz) must be subsampled. How is decided when this
  stage is designed.
- The camera is rolling shutter. This is a known source of error for fast
  motion.
- The intrinsics come from M3DGR's `calibration.md`. Whether to fix them or
  refine them is decided at this stage.
- Monocular SfM has no scale, so it is aligned with a similarity transform.
  The charter already requires this.

---

## D-009: Reconstruction with nerfstudio and Open3D

**Date:** 2026-11-27 · **Status:** accepted for the frameworks. The specific
models are still open.

**Context.** Goal 2 covers reconstruction from both images and LiDAR.

**Decision.**
- From images: nerfstudio, with gsplat for Gaussian splatting.
- From LiDAR: Open3D, for building the point-cloud map and meshing it.

**Open.** Which neural models to train (for example nerfacto, depth-nerfacto
or splatfacto, or alternatives) is explored and decided when this stage is
reached.

**Consequences.**
- The GPU is an RTX 3060 Laptop with 6 GB of memory. This limits scene size
  and batch size, especially for Gaussian splatting.
- torch, CUDA, gsplat and any compiled extensions are pinned together as one
  set (see D-010).

**Update, 2026-11-28: GPU image postponed.** On PyPI and GitHub that day:
- nerfstudio's latest release was 1.1.5, from November 2024. The last commit
  on its main branch was in July 2025. The repository is not archived.
- nerfstudio pins `gsplat==1.4.0`, while gsplat's latest release is 1.5.3.
  Its development setup pins `torch==2.7.1`; the current torch is 2.15.

An image built for nerfstudio would therefore freeze an older torch, CUDA and
gsplat combination. The model choice is still open, and nerfstudio's
inactivity is a reason to look at alternatives, so the GPU image is built at
the start of the reconstruction stage, once the models are chosen. GPU access
from containers is already verified (D-010).

---

## D-010: Environments: Docker for Linux and GPU, uv on Windows

**Date:** 2026-11-27 · **Status:** accepted, pending the GPU check below

**Context.** The development machine runs Windows 11. ROS 2 Jazzy supports
only Ubuntu as a main platform. CUDA extensions are each compiled for one
torch and CUDA version, and building them on Windows was unreliable in the
past.

**Decision.**
- A ROS 2 Jazzy Docker image, for SLAM and the live system.
- A GPU Docker image built on an NVIDIA CUDA base image, for reconstruction.
- The existing uv environment on Windows, for analysis: bag reading, evo and
  plots.

**Alternatives.**
- *pixi (conda packages with a lockfile) natively on Windows:* no Docker
  needed, but ROS 2 on Windows is poorly supported, and the CUDA build
  problems would remain.
- *Everything in one image:* torch/CUDA and ROS have conflicting needs, and
  the image would be very large.

**Consequences.**
- Docker Desktop with the WSL2 backend must be installed.
- The first task of the environment phase is a smoke test showing the GPU is
  visible inside a container. If it fails, the GPU environment falls back to
  pixi.

**Update, 2026-11-27: GPU check passed.** `docker/check_gpu.sh` ran
`nvidia-smi` and the CUDA n-body sample in containers, on Docker Desktop
29.9.3 with the WSL2 backend.
- The container sees the RTX 3060 Laptop GPU: 6 GB, compute capability 8.6.
- The n-body benchmark computed on the GPU, at about 3.5 TFLOP/s single
  precision.
- The host driver (621.24) supports CUDA up to 13.5. Container images must not
  need a newer CUDA than that.
- CUDA extensions compiled in the GPU image should target compute capability
  8.6.

The pixi fallback is not needed.

---

## D-011: Bag conversion with rosbags, to MCAP

**Date:** 2026-11-27 · **Status:** accepted

**Context.** D-001 requires a ROS 2 copy of the bag. The two Livox message
types are not standard ROS messages.

**Decision.**
- Convert with `rosbags-convert`, part of the rosbags package already in the
  uv environment.
- Write MCAP, the default bag storage format in Jazzy.
- Register both Livox message types from the definitions stored in the bag.
- The converted bag goes in `data/interim/`. `data/raw/` stays untouched.

**Alternatives.** Converting with the `rosbag2` tools inside a ROS 1 + ROS 2
bridge setup needs a ROS 1 installation, which this project does not use.

**Consequences.** The conversion is a pipeline stage with its own check:
message counts and stamps of the converted bag must match docs/data.md.

---

## D-012: Development container simplifications

**Date:** 2026-11-27 · **Status:** accepted

**Context.** The ROS 2 image (`docker/ros.Dockerfile`) is for development:
SLAM, bag playback and building ROS packages.

**Decision.**
- **apt packages are not version-pinned.** The base image is pinned by
  digest, but `apt-get install` fetches the current version. The ROS apt
  repository keeps only the latest version of each package, so exact pins
  would break as soon as a package is updated.
- **The container runs as root.** That is the usual default for development
  containers, and Docker Desktop bind mounts on Windows are not affected by
  file ownership.

**Alternatives.**
- *ROS snapshot repositories* (dated, frozen copies of the ROS apt
  repository) make apt installs exactly repeatable. This is the fix to adopt
  if package drift ever breaks a build.
- *A non-root user:* the right choice for a deployment image. It is
  reconsidered for the Goal 3 image.

**Consequences.** Rebuilding the image on a later date can produce slightly
different package versions. The smoke test `docker/check_ros.sh` is rerun
after every rebuild.

---

## D-013: Livox message types as definition-only packages

**Date:** 2026-11-27 · **Status:** accepted. It is implemented at the first
step that plays the bag back in ROS 2.

**Context.** ROS 2 can only publish or subscribe to a message type whose
package is built and installed. `ros2 bag play` skips topics with unknown
types, and FAST-LIO2 is compiled against `livox_ros_driver2/msg/CustomMsg`.
The Avia publishes `livox_ros_driver/CustomMsg` and the Mid-360 publishes
`livox_ros_driver2/CustomMsg`. The fields are identical, but the package names
differ, so ROS treats them as two types (docs/data.md). Converting the bag does
not need these packages, because `rosbags-convert` uses the definitions stored
in the bag.

**Decision.** Add two minimal ROS 2 packages to `ros2_ws/src`,
`livox_ros_driver` and `livox_ros_driver2`. Each contains only its message
definitions, taken from the definitions stored in the bag.

**Alternatives.**
- *The official `livox_ros_driver2`:* requires building the Livox-SDK2
  hardware library, which is not needed for recorded data, and covers only the
  Mid-360's type.
- *One package, with the Avia relabelled during conversion:* the converted bag
  would no longer match the raw bag, so its message types could not be checked
  directly against docs/data.md.

**Consequences.**
- The converted bag keeps both original types.
- Whether FAST-LIO2 needs the Avia's messages relabelled is decided at the
  FAST-LIO2 stage (D-007).
- The license of the Livox driver sources is checked before their
  definitions are copied.
