"""Kokoro-ONNX TTS backend — fast, CPU-based, no PyTorch/ROCm dependency."""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


class KokoroTTS:
    """Lazy-initialised Kokoro TTS via ONNX Runtime.

    Model files are auto-downloaded from HuggingFace Hub on first use and
    cached in the HF cache directory (~/.cache/huggingface/hub).
    """

    def __init__(
        self,
        voice: str = "bm_george",
        speed: float = 1.0,
        lang: str = "en-us",
        model_repo: str = "hexgrad/Kokoro-82M-ONNX",
    ) -> None:
        self._voice = voice
        self._speed = speed
        self._lang = lang
        self._model_repo = model_repo
        self._kokoro = None  # deferred

    def _init(self) -> None:
        if self._kokoro is not None:
            return
        from huggingface_hub import hf_hub_download  # noqa: PLC0415
        from kokoro_onnx import Kokoro  # noqa: PLC0415

        log.info("Downloading/loading Kokoro model from %s", self._model_repo)
        model_path = hf_hub_download(repo_id=self._model_repo, filename="kokoro-v1.0.onnx")
        voices_path = hf_hub_download(repo_id=self._model_repo, filename="voices-v1.0.bin")
        self._kokoro = Kokoro(model_path, voices_path)
        log.info("Kokoro model loaded (voice=%s)", self._voice)

    def synthesize(self, text: str, out_path: Path) -> None:
        self._init()
        import soundfile as sf  # noqa: PLC0415

        samples, sample_rate = self._kokoro.create(
            text,
            voice=self._voice,
            speed=self._speed,
            lang=self._lang,
        )
        sf.write(str(out_path), samples, sample_rate)
        log.debug("Synthesized → %s", out_path)
