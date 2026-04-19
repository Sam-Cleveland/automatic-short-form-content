from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class WordTimestamp:
    text: str
    start: float  # seconds from audio start
    end: float    # seconds from audio start


class Transcriber(Protocol):
    """Transcribe an audio file, returning word-level timestamps."""

    def transcribe(self, audio_path: Path) -> list[WordTimestamp]: ...
