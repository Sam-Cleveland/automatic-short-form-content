from __future__ import annotations

from pathlib import Path
from typing import Protocol


class TTSBackend(Protocol):
    """Synthesize text to a WAV file at `out_path`."""

    def synthesize(self, text: str, out_path: Path) -> None: ...
