"""Microsoft Edge TTS backend — cloud, free, no GPU, production-quality voices."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg  # noqa: PLC0415
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


class EdgeTTS:
    """Thin wrapper around the `edge-tts` package.

    No model loading or initialisation required — each call streams audio
    from Microsoft's neural TTS API. Output is converted to WAV so it's
    compatible with the pipeline's concat_audio step.
    """

    def __init__(self, voice: str = "en-GB-RyanNeural", speed: float = 1.0) -> None:
        self._voice = voice
        # edge-tts uses a percentage rate string e.g. "+15%" or "-10%"
        pct = int(round((speed - 1.0) * 100))
        self._rate = f"{pct:+d}%"

    def synthesize(self, text: str, out_path: Path) -> None:
        import edge_tts  # noqa: PLC0415

        log.debug("Edge TTS synthesizing (voice=%s, rate=%s)", self._voice, self._rate)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            asyncio.run(
                edge_tts.Communicate(text, voice=self._voice, rate=self._rate).save(str(tmp_path))
            )
            # Convert MP3 → WAV for pipeline compatibility
            subprocess.run(
                [_ffmpeg(), "-y", "-i", str(tmp_path), str(out_path)],
                check=True, capture_output=True,
            )
        finally:
            tmp_path.unlink(missing_ok=True)
        log.debug("Synthesized → %s", out_path)
