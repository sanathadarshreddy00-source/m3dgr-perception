"""Slow tests on the real data in data/raw. Run with ``uv run pytest -m slow``.

They fail, rather than skip, when the data is missing: asking for the slow
tests means asking for the real data to be checked.
"""

from __future__ import annotations

import hashlib

import pytest
from conftest import REPO

DATA = REPO / "data"


@pytest.mark.slow
def test_raw_files_match_checksums() -> None:
    """data/raw is read-only (conventions rule 1): its files must match SHA256SUMS."""
    lines = (DATA / "SHA256SUMS").read_text().splitlines()
    assert lines, "SHA256SUMS is empty"
    for line in lines:
        expected, name = line.split(" *", 1)
        path = DATA / name
        assert path.is_file(), f"{path} missing"
        digest = hashlib.sha256()
        with path.open("rb") as f:
            while chunk := f.read(1 << 24):
                digest.update(chunk)
        assert digest.hexdigest() == expected, f"{name} changed"
