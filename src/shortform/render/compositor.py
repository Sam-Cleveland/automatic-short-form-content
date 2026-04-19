"""FFmpeg-based video compositor.

Replaces the MoviePy pipeline from main.py with direct FFmpeg calls via
ffmpeg-python. Produces identical output (720×720, 60fps, AAC audio) without
the Pillow ANTIALIAS compatibility patch or MoviePy's slow Python-level
frame iteration.

Pipeline:
  1. Concat all audio files (title WAV + sentence WAVs) → temp combined.wav
  2. Trim stock video to audio duration
  3. Scale/crop to target resolution
  4. Overlay title card PNG (centered) for the first `title_dur` seconds
  5. Burn in ASS captions
  6. Encode → output MP4
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def _audio_duration(path: Path) -> float:
    """Return duration in seconds using ffprobe."""
    import ffmpeg  # noqa: PLC0415

    probe = ffmpeg.probe(str(path))
    for stream in probe["streams"]:
        if stream.get("codec_type") == "audio":
            return float(stream["duration"])
    return float(probe["format"]["duration"])


def concat_audio(inputs: list[Path], out_path: Path) -> float:
    """Concatenate WAV files into a single WAV; return duration in seconds."""
    # Build a concat list file for FFmpeg's concat demuxer
    list_path = out_path.parent / "audio_list.txt"
    with list_path.open("w") as f:
        for p in inputs:
            f.write(f"file '{p.absolute()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return _audio_duration(out_path)


def compose(
    *,
    stock_path: Path,
    audio_path: Path,
    title_card: Path,
    captions: Path,
    title_dur: float,
    duration: float,
    out_path: Path,
    width: int = 720,
    height: int = 720,
    fps: int = 60,
    video_codec: str = "libx264",
    audio_codec: str = "aac",
    caption_font_dir: str | None = None,
) -> None:
    """Compose the final MP4 from pre-built assets.

    Args:
        stock_path:       Pre-processed stock video clip.
        audio_path:       Combined audio (title + body), already concatenated.
        title_card:       Title card PNG (natural size, will be centred).
        captions:         ASS subtitle file with pop-in animation.
        title_dur:        Duration of the title card display (seconds).
        duration:         Total output duration (= audio duration).
        out_path:         Destination MP4 path.
        caption_font_dir: Directory containing caption fonts (e.g. repo root).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ass_filter = f"ass={captions.absolute()}"
    if caption_font_dir:
        ass_filter += f":fontsdir={caption_font_dir}"

    # fmt: off
    filter_complex = (
        # Scale stock to target resolution
        f"[0:v]scale={width}:{height},setsar=1,trim=duration={duration}[base];"
        # Overlay title card centred for the first title_dur seconds
        f"[base][2:v]overlay=(W-w)/2:(H-h)/2:enable='lt(t,{title_dur:.4f})'[titled];"
        # Burn in ASS captions
        f"[titled]{ass_filter}[out]"
    )
    # fmt: on

    cmd = [
        "ffmpeg", "-y",
        "-i", str(stock_path),            # [0] stock video
        "-i", str(audio_path),            # [1] audio
        "-loop", "1", "-i", str(title_card),  # [2] title card PNG
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "1:a",
        "-t", str(duration),
        "-r", str(fps),
        "-c:v", video_codec,
        "-c:a", audio_codec,
        str(out_path),
    ]
    log.info("Compositing → %s", out_path)
    log.debug("ffmpeg cmd: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)
    log.info("Done: %s", out_path)
