"""Reddit-styled title card renderer using Pillow.

Extracted from the original `create_title()` in main.py. Font path and asset
paths are now parameters (fed from config) rather than hardcoded strings.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

log = logging.getLogger(__name__)


def _wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    draw: ImageDraw.ImageDraw,
    max_width: float,
) -> list[str]:
    lines: list[str] = []
    words = text.split(" ")
    current = words[0]
    for word in words[1:]:
        if draw.textlength(" ".join([current, word]), font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = " ".join([current, word])
    lines.append(current)
    return lines


def render(
    title: str,
    out_path: Path,
    *,
    font_path: str,
    user_overlay: str,
    likes_comments_overlay: str,
    width: int = 720,
) -> Path:
    """Render a Reddit-style title card PNG and write it to `out_path`.

    Returns `out_path` for chaining.
    """
    W = width
    RW = int(W * 0.73)
    RO = (W - RW) // 2
    SW = int(W * 0.75)
    SO = (W - SW) // 2

    font_size = int(55 * W / 720)
    font = ImageFont.truetype(font_path, font_size)
    # Thick same-colour stroke inflates each glyph outward — creates the bubbly/heavy look
    stroke_w = max(1, int(2 * W / 720))
    radius = int(80 * W / 720)
    inner_pad = int(20 * W / 720)

    # --- Load overlay images upfront so we know their heights before drawing ---
    user_img_raw = Image.open(user_overlay)
    u_scale = W * 0.00115
    user_img = user_img_raw.resize(
        (int(user_img_raw.size[0] * u_scale), int(user_img_raw.size[1] * u_scale)),
        Image.LANCZOS,
    )

    comments_img_raw = Image.open(likes_comments_overlay)
    c_scale = W * 0.001
    comments_img = comments_img_raw.resize(
        (int(comments_img_raw.size[0] * c_scale), int(comments_img_raw.size[1] * c_scale)),
        Image.LANCZOS,
    )

    # --- Measure text layout on a scratch canvas to find the true text bottom ---
    scratch = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    scratch_draw = ImageDraw.Draw(scratch)
    wrapped = _wrap_text(title, font, scratch_draw, RW * 0.85)

    text_y_start = int(W * 0.3)
    y_cursor = text_y_start
    for line in wrapped:
        # Include stroke in height measurement so spacing accounts for it
        h = scratch_draw.textbbox((0, 0), line, font=font, stroke_width=stroke_w)[3]
        y_cursor += int(h * 0.85)
    text_bottom = y_cursor + inner_pad  # small breathing room after last line

    # Comments go below text — never overlapping
    comments_y = text_bottom + inner_pad
    card_bottom = comments_y + comments_img.size[1] + inner_pad

    # Canvas must be tall enough for the full card (can exceed W for long titles)
    canvas_h = max(W, card_bottom + inner_pad * 2)
    image = Image.new("RGBA", (W, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Shadow (drawn before card so blur stays behind it)
    shadow_extra = (SW - RW) // 2
    draw.rounded_rectangle(
        [(SO, SO), (SO + SW, card_bottom + shadow_extra)],
        fill=(0, 0, 0, 128),
        radius=radius,
    )
    image = image.filter(ImageFilter.GaussianBlur(5))
    draw = ImageDraw.Draw(image)

    # White card background
    draw.rounded_rectangle(
        [(RO, RO), (RO + RW, card_bottom)],
        fill=(255, 255, 255, 255),
        radius=radius,
    )

    # User icon
    image.paste(user_img, (int(W * 0.16), int(W * 0.17)), user_img)

    # Title text — black fill + same-colour stroke = thicker/bubbly glyphs
    y_text = text_y_start
    x_text = int(W * 0.2)
    for line in wrapped:
        h = draw.textbbox((0, 0), line, font=font, stroke_width=stroke_w)[3]
        draw.text(
            (x_text, y_text), line, font=font,
            fill=(0, 0, 0, 255),
            stroke_width=stroke_w,
            stroke_fill=(0, 0, 0, 255),
        )
        y_text += int(h * 0.85)

    # Likes/comments — anchored below text, never overlaps
    image.paste(comments_img, (int(W * 0.2), comments_y), comments_img)

    # Crop to the card's visible bounding box
    image = image.crop((SO - 10, SO - 10, SO + SW + 10, card_bottom + 10))
    image.save(str(out_path))
    log.debug("Title card → %s", out_path)
    return out_path
