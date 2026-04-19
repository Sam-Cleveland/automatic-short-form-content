"""Local OpenAI Whisper transcription via HuggingFace Transformers."""

from __future__ import annotations

import logging
from pathlib import Path

from .base import WordTimestamp

log = logging.getLogger(__name__)


class WhisperLocal:
    """Lazy-initialised Whisper pipeline.

    Model and processor are downloaded from HuggingFace on first use and
    cached by the `transformers` library. GPU (CUDA > MPS) is used if
    available, otherwise falls back to CPU.
    """

    def __init__(
        self,
        model_id: str = "openai/whisper-small",
        chunk_length_s: int = 30,
        batch_size: int = 16,
    ) -> None:
        self._model_id = model_id
        self._chunk_length_s = chunk_length_s
        self._batch_size = batch_size
        self._pipe = None  # deferred

    def _init(self) -> None:
        if self._pipe is not None:
            return
        import torch  # noqa: PLC0415
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline  # noqa: PLC0415

        if torch.cuda.is_available():
            device, dtype = "cuda:0", torch.float16
        elif torch.backends.mps.is_available():
            device, dtype = "mps", torch.float32
        else:
            device, dtype = "cpu", torch.float32

        log.info("Loading Whisper model %s on %s", self._model_id, device)
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            self._model_id,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
        )
        model.to(device)
        processor = AutoProcessor.from_pretrained(self._model_id)
        self._pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            max_new_tokens=128,
            chunk_length_s=self._chunk_length_s,
            batch_size=self._batch_size,
            return_timestamps=True,
            torch_dtype=dtype,
            device=device,
        )

    def transcribe(self, audio_path: Path) -> list[WordTimestamp]:
        self._init()
        result = self._pipe(str(audio_path), return_timestamps="word")
        words = []
        for chunk in result["chunks"]:
            ts = chunk["timestamp"]
            if ts[0] is None or ts[1] is None:
                continue
            words.append(WordTimestamp(text=chunk["text"], start=ts[0], end=ts[1]))
        return words
