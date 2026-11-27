#!/usr/bin/env bash
# Smoke test: can Docker containers see and compute on the host's NVIDIA GPU?
#
# 1. nvidia-smi inside a CUDA base image: the driver is passed through.
# 2. The CUDA n-body sample in benchmark mode: kernels actually run on the GPU.
#
# Usage: bash docker/check_gpu.sh
set -euo pipefail

# Pinned by tag and content digest, so the exact image that passed is reused.
CUDA_IMAGE="nvidia/cuda:12.8.1-base-ubuntu24.04@sha256:133c78a0575303be34164d0b90137a042172bdf60696af01a3c424ab402d86e2"
NBODY_IMAGE="nvcr.io/nvidia/k8s/cuda-sample:nbody@sha256:59261e419d6d48a772aad5bb213f9f1588fcdb042b115ceb7166c89a51f03363"

echo "== 1/2 nvidia-smi in ${CUDA_IMAGE}"
docker run --rm --gpus all "${CUDA_IMAGE}" nvidia-smi

echo "== 2/2 n-body benchmark in ${NBODY_IMAGE}"
docker run --rm --gpus all "${NBODY_IMAGE}" nbody -gpu -benchmark

echo "== image digests used"
docker image inspect --format '{{index .RepoDigests 0}}' "${CUDA_IMAGE}" "${NBODY_IMAGE}"
echo "GPU check passed"
