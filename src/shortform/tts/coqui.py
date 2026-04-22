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

    def __init__(self, model: str, speaker_wav: str, language: str = "en", speaker: str = "") -> None:
        self._model = model
        self._speaker_wav = speaker_wav
        self._speaker = speaker  # built-in speaker name; takes priority over speaker_wav
        self._language = language
        self._tts = None  # deferred

    def _init(self) -> None:
        if self._tts is not None:
            return
        os.environ["COQUI_TOS_AGREED"] = "1"
        import functools  # noqa: PLC0415

        import torch  # noqa: PLC0415
        from TTS.api import TTS  # noqa: PLC0415

        gpu = torch.cuda.is_available()
        log.info("GPU available: %s", gpu)

        # PyTorch ≥2.6 defaults weights_only=True which blocks TTS's pickle-based
        # checkpoint loading. Patch torch.load for the duration of model init only.
        _orig_load = torch.load

        @functools.wraps(_orig_load)
        def _permissive_load(f, *args, **kwargs):
            kwargs.setdefault("weights_only", False)
            return _orig_load(f, *args, **kwargs)

        torch.load = _permissive_load
        try:
            log.info("Loading Coqui model %s (gpu=%s)", self._model, gpu)
            self._tts = TTS(model_name=self._model, progress_bar=True, gpu=gpu)
        finally:
            torch.load = _orig_load

    def synthesize(self, text: str, out_path: Path) -> None:
        self._init()
        kwargs: dict = dict(text=text, language=self._language, file_path=str(out_path))
        if self._speaker:
            kwargs["speaker"] = self._speaker
        else:
            kwargs["speaker_wav"] = self._speaker_wav
        self._tts.tts_to_file(**kwargs)
        log.debug("Synthesized → %s", out_path)
