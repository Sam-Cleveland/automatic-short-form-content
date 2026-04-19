"""OpenAI Whisper API transcription backend (requires `[cloud]` extra + OPENAI_API_KEY)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .base import WordTimestamp

log = logging.getLogger(__name__)


class WhisperAPI:
    """Thin wrapper around openai.audio.transcriptions with word timestamps."""

    def __init__(self, model: str = "whisper-1") -> None:
        self._model = model
        self._client = None  # deferred

    def _init(self) -> None:
        if self._client is not None:
            return
        from openai import OpenAI  # noqa: PLC0415

        self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        log.info("OpenAI Whisper API client initialised")

    def transcribe(self, audio_path: Path) -> list[WordTimestamp]:
        self._init()
        with open(audio_path, "rb") as f:
            result = self._client.audio.transcriptions.create(
                model=self._model,
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )
        return [
            WordTimestamp(text=w.word, start=w.start, end=w.end)
            for w in (result.words or [])
            if w.start is not None and w.end is not None
        ]
