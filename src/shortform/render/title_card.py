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
) -> Path:
    """Render a Reddit-style title card PNG and write it to `out_path`.

    Returns `out_path` for chaining.
    """
    W = 720
    RW = W * 0.73
    RO = (W - RW) / 2
    SW = W * 0.75
    SO = (W - SW) / 2

    font = ImageFont.truetype(font_path, 55)
    shadow_color = (0, 0, 0, 128)
    rectangle_color = (255, 255, 255, 255)
    radius = 80

    image = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    p_height = 51.2 * len(_wrap_text(title, font, draw, RW * 0.85))

    # Shadow
    draw.rounded_rectangle(
        [(SO, SO), (SO + SW, SO + p_height + 190 + SW - RW)],
        fill=shadow_color,
        radius=radius,
    )
    image = image.filter(ImageFilter.GaussianBlur(5))
    draw = ImageDraw.Draw(image)

    # Card background
    draw.rounded_rectangle(
        [(RO, RO), (RO + RW, RO + p_height + 190)],
        fill=rectangle_color,
        radius=radius,
    )

    # Title text
    wrapped = _wrap_text(title, font, draw, RW * 0.85)
    y_text = W * 0.3
    x_text = W * 0.2
    for line in wrapped:
        height = draw.textbbox((0, 0), line, font=font)[3]
        draw.text((x_text, y_text), line, font=font, fill=(0, 0, 0, 255))
        y_text += height * 0.8

    # User icon overlay
    user_img = Image.open(user_overlay)
    user_img = user_img.resize(
        (int(user_img.size[0] * W * 0.00115), int(user_img.size[1] * W * 0.00115))
    )
    image.paste(user_img, (int(W * 0.16), int(W * 0.17)), user_img)

    # Likes/comments overlay
    comments_img = Image.open(likes_comments_overlay)
    comments_img = comments_img.resize(
        (int(comments_img.size[0] * W * 0.001), int(comments_img.size[1] * W * 0.001))
    )
    image.paste(comments_img, (int(W * 0.2), int(p_height + 230)), comments_img)

    # Crop to content
    image = image.crop(
        (SO - 10, SO - 10, SO + SW + 10, SO + p_height + 190 + SW - RW + 10)
    )
    image.save(str(out_path))
    log.debug("Title card → %s", out_path)
    return out_path
