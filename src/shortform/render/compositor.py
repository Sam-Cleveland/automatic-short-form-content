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
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

def _ffmpeg_candidates() -> list[str]:
    candidates = [
        "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
        "/usr/local/opt/ffmpeg-full/bin/ffmpeg",
        "ffmpeg",
    ]
    try:
        import imageio_ffmpeg  # noqa: PLC0415
        candidates.insert(0, imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass
    return candidates


@lru_cache(maxsize=1)
def _ffmpeg_bin() -> str:
    """Return a path to an ffmpeg binary that has the `ass` filter (libass)."""
    for candidate in _ffmpeg_candidates():
        try:
            result = subprocess.run(
                [candidate, "-filters"],
                capture_output=True, text=True, timeout=10,
            )
            if " ass " in result.stdout:
                log.debug("Using ffmpeg binary: %s", candidate)
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    raise RuntimeError(
        "No ffmpeg binary with libass support found. "
        "On macOS: brew install ffmpeg-full. "
        "Otherwise: uv add imageio-ffmpeg"
    )


def _audio_duration(path: Path) -> float:
    """Return duration in seconds using ffmpeg -i (works without a separate ffprobe binary)."""
    import re  # noqa: PLC0415

    result = subprocess.run(
        [_ffmpeg_bin(), "-i", str(path)],
        capture_output=True, text=True,
    )
    # ffmpeg prints duration to stderr even on error (no output file specified)
    match = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", result.stderr)
    if not match:
        raise RuntimeError(f"Could not determine duration of {path}")
    h, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
    return h * 3600 + m * 60 + s


def concat_audio(inputs: list[Path], out_path: Path) -> float:
    """Concatenate WAV files into a single WAV; return duration in seconds."""
    # Build a concat list file for FFmpeg's concat demuxer
    list_path = out_path.parent / "audio_list.txt"
    with list_path.open("w") as f:
        for p in inputs:
            f.write(f"file '{p.absolute()}'\n")

    cmd = [
        _ffmpeg_bin(), "-y",
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
        _ffmpeg_bin(), "-y",
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
