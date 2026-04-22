"""Generate ASS subtitle files with per-word timing and pop() scale animation.

The original pipeline used MoviePy's `TextClip.resize(pop)` where `pop(t)`
returns a scale factor of 0.1 at t=0, growing linearly to 1.0 by t=0.025s.
This is approximated in ASS with `\fscx10\fscy10\t(0,25,\fscx100\fscy100)`:
scale from 10% → 100% over the first 25 ms of each word's display time.
"""

from __future__ import annotations

from pathlib import Path

from ..transcribe.base import WordTimestamp

# ASS timestamp format: H:MM:SS.cc  (centiseconds, not milliseconds)
def _ts(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h = cs // 360000
    cs %= 360000
    m = cs // 6000
    cs %= 6000
    s = cs // 100
    cs %= 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


_HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},120,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,0,5,10,10,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# Pop-in animation: start at 10% scale, reach 100% after 25 ms
_POP = r"{\fscx10\fscy10\t(0,25,\fscx100\fscy100)}"


def write(
    words: list[WordTimestamp],
    out_path: Path,
    *,
    title_offset: float,
    caption_font: str = "Bangers-Regular",
    width: int = 720,
    height: int = 720,
) -> Path:
    """Write an ASS file for `words` and return `out_path`.

    `title_offset` is the duration of the title audio; word timestamps are
    shifted forward by this amount so captions don't appear during the title card.
    """
    # Strip file extension if present so ASS uses the font name, not path
    font_name = Path(caption_font).stem

    lines = [_HEADER.format(width=width, height=height, font_name=font_name)]
    for word in words:
        start = word.start + title_offset
        end = word.end + title_offset
        text = word.text.strip()
        if not text:
            continue
        lines.append(
            f"Dialogue: 0,{_ts(start)},{_ts(end)},Default,,0,0,0,,{_POP}{text}\n"
        )

    out_path.write_text("".join(lines), encoding="utf-8")
    return out_path
