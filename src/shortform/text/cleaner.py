"""Pure-function text cleaning for Reddit post titles and bodies.

Fixes three bugs from the original single-file implementation:
- The censor loop in `main.py` used `title` instead of `title_text` as the
  source each iteration, so only the last-matching censor key survived.
- `script.replace('\\n', ' ')` was called without reassignment, making it a no-op.
- The zero-width-space strip targeted the HTML entity `&#x200B;` but ran
  *after* `html.unescape`, which had already converted it to `\\u200b`.
"""

from __future__ import annotations

import html
import re

from .dicts import CENSOR, SLANG, TTS_FIXES


def expand_slang(text: str) -> str:
    """Replace Reddit-isms like `AITA` with their spoken form.

    Case-insensitive, word-boundary-anchored. Iterates in dict order, so longer
    keys like `AITAH` must come before their prefixes in `SLANG` to win.
    """
    for key, value in SLANG.items():
        text = re.sub(r"\b" + re.escape(key) + r"\b", value, text, flags=re.IGNORECASE)
    return text


def apply_tts_fixes(text: str) -> str:
    """Apply regex fixes that improve TTS prosody (e.g. collapsing ellipses)."""
    for pattern, replacement in TTS_FIXES.items():
        text = re.sub(pattern, replacement, text)
    return text


def censor(text: str) -> str:
    """Replace profanity with censored variants for display.

    Substring match (no word boundary), case-insensitive. `asshole` therefore
    also censors `assholes`, and `suicid` covers both `suicide` and `suicidal`.
    """
    for key, value in CENSOR.items():
        text = re.sub(re.escape(key), value, text, flags=re.IGNORECASE)
    return text


def strip_trailing_sections(text: str) -> str:
    """Cut the body off at a new-line followed by tl;dr / edit / update / info / summary."""
    return re.split(
        r"\n(?:tl[;.\/]?dr|edit|update|info|summary)",
        text,
        flags=re.IGNORECASE,
    )[0]


def split_sentences(text: str) -> list[str]:
    """Split text into sentences on `.?!`.

    Uses a 3-char positive lookbehind `(?<=[^A-Z].[.?!])`. This handles
    `Dr. Smith` correctly (no split: the `D` before `r.` is uppercase) but
    still mid-splits tight acronyms like `U.S.` where a space-U-dot window
    satisfies the pattern. Short leading sentences (e.g. `Hi.`) also don't
    split since they lack 3 preceding chars. These are known limitations of
    the original heuristic, preserved for output parity.
    """
    return [s.strip() for s in re.split(r"(?<=[^A-Z].[.?!])", text) if s.strip()]


def prepare_title_for_tts(title: str) -> str:
    """Title text to feed TTS: slang expanded, TTS fixes applied, NOT censored."""
    return apply_tts_fixes(expand_slang(title))


def prepare_title_for_display(title: str) -> str:
    """Title text to render on the title card: slang expanded, TTS-fixed, then censored."""
    return censor(apply_tts_fixes(expand_slang(title)))


def prepare_body(script: str) -> list[str]:
    """Body script ready for per-sentence TTS synthesis.

    Pipeline: slang-expand → TTS-fix → HTML-unescape → strip zero-width spaces
    → strip trailing tl;dr/edit sections → normalize newlines → split sentences.
    """
    script = expand_slang(script)
    script = apply_tts_fixes(script)
    script = html.unescape(script)
    script = script.replace("\u200b", "")
    script = strip_trailing_sections(script)
    script = script.replace("\n", " ")
    return split_sentences(script)
