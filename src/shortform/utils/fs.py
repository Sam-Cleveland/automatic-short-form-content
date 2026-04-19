"""Filesystem helpers."""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def temp_workdir():
    """Context manager yielding a temporary directory as a Path.

    The directory and all its contents are deleted on exit, so all
    intermediate pipeline artifacts (WAV files, PNGs, ASS files) stay
    off the repo root.
    """
    with tempfile.TemporaryDirectory(prefix="shortform_") as tmpdir:
        yield Path(tmpdir)
