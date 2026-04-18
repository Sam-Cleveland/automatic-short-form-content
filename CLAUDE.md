# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated pipeline that converts Reddit posts into short-form videos (TikTok/Instagram Reels style). Flow: scrape Reddit → generate TTS audio → transcribe with Whisper → overlay captions on stock footage → render MP4.

## Commands

```bash
# Install dependencies (Python 3.11.7 required)
pip install -r requirements.txt

# Run on a single Reddit URL
python main.py "https://www.reddit.com/r/subreddit/comments/..."

# Batch process URLs from urls.txt
python main.py

# Preprocess raw stock video into 300-second clips for the stock/ directory
python process_stock.py
```

## Architecture

All logic lives in `main.py`. There is no framework or module structure — it's a single-file pipeline.

**End-to-end flow in `create_video()`:**
1. `scrape_reddit_page()` — fetches Reddit post JSON, decodes HTML entities, censors profanity, expands acronyms (AITA → "Am I the A-hole"), splits into sentences
2. Coqui XTTS v2 TTS — generates per-sentence `.wav` files using `Resources/en_uk_003.mp3` as the speaker reference voice
3. `create_title()` — renders a Reddit-styled title card image via PIL (SF Pro Rounded font + overlay PNGs), then generates title audio via TTS
4. OpenAI Whisper (`small` model) — transcribes the concatenated audio with word-level timestamps for caption sync
5. MoviePy — composites stock video + audio + title overlay + word-by-word captions (with `pop()` easing), exports 720×720 MP4 at 60fps

**Key details:**
- Stock videos must be pre-processed into exactly 300-second clips by `process_stock.py` before use
- GPU is used automatically if CUDA or MPS is available; falls back to CPU
- Output files go to `output/{post_title}.mp4`
- `google_tts.py` is a deprecated alternative TTS implementation — not used by `main.py`
- `test.py` is a diff utility for comparing caption outputs, not a test suite

## Hard Dependencies

- **Font**: `/Library/Fonts/SF-Pro-Rounded-Semibold.otf` — hardcoded macOS system font path; must exist on the machine
- **Stock footage**: `stock/` directory must contain pre-processed video clips (run `process_stock.py` first)
- **Speaker reference**: `Resources/en_uk_003.mp3` must be present for Coqui XTTS voice cloning
- **Overlay assets**: `Resources/user.png`, `pfp.png`, `likes_comments.png`, `awards.png` used in title card rendering
