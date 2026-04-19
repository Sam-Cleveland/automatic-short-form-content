"""ElevenLabs cloud TTS backend (requires `[cloud]` extra + ELEVENLABS_API_KEY)."""

from __future__ import annotations

import logging
import os
import wave
from pathlib import Path

log = logging.getLogger(__name__)

# ElevenLabs PCM format: 44 100 Hz, 16-bit, mono
_SAMPLE_RATE = 44_100
_SAMPLE_WIDTH = 2  # bytes (16-bit)
_CHANNELS = 1


class ElevenLabsTTS:
    """Lazy-initialised wrapper around the ElevenLabs SDK.

    Streams PCM audio from the API and wraps it in a WAV container so the
    rest of the pipeline can treat it identically to Coqui output.
    """

    def __init__(
        self,
        voice_id: str,
        model: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
    ) -> None:
        self._voice_id = voice_id
        self._model = model
        self._stability = stability
        self._similarity_boost = similarity_boost
        self._client = None  # deferred

    def _init(self) -> None:
        if self._client is not None:
            return
        from elevenlabs.client import ElevenLabs  # noqa: PLC0415

        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        self._client = ElevenLabs(api_key=api_key)
        log.info("ElevenLabs client initialised (voice=%s)", self._voice_id)

    def synthesize(self, text: str, out_path: Path) -> None:
        self._init()
        audio_iter = self._client.text_to_speech.convert(
            voice_id=self._voice_id,
            text=text,
            model_id=self._model,
            output_format="pcm_44100",
            voice_settings={
                "stability": self._stability,
                "similarity_boost": self._similarity_boost,
            },
        )
        pcm = b"".join(audio_iter)

        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(_CHANNELS)
            wf.setsampwidth(_SAMPLE_WIDTH)
            wf.setframerate(_SAMPLE_RATE)
            wf.writeframes(pcm)

        log.debug("Synthesized → %s (%d bytes PCM)", out_path, len(pcm))
