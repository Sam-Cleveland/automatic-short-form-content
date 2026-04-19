"""Coqui XTTS v2 TTS backend (local, requires torch + TTS package)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)


class CoquiTTS:
    """Lazy-initialised wrapper around Coqui XTTS v2.

    Heavy imports (torch, TTS) happen on first call to `synthesize`, so
    importing this module is safe even when the `[local]` extra is absent.
    """

    def __init__(self, model: str, speaker_wav: str, language: str = "en") -> None:
        self._model = model
        self._speaker_wav = speaker_wav
        self._language = language
        self._tts = None  # deferred

    def _init(self) -> None:
        if self._tts is not None:
            return
        os.environ["COQUI_TOS_AGREED"] = "1"
        from TTS.api import TTS  # noqa: PLC0415

        log.info("Loading Coqui model %s", self._model)
        self._tts = TTS(model_name=self._model, progress_bar=True)

    def synthesize(self, text: str, out_path: Path) -> None:
        self._init()
        self._tts.tts_to_file(
            text=text,
            speaker_wav=self._speaker_wav,
            language=self._language,
            file_path=str(out_path),
        )
        log.debug("Synthesized → %s", out_path)
