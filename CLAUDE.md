# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated pipeline that converts Reddit posts into short-form videos (TikTok/Instagram Reels style). Flow: scrape Reddit → generate TTS audio → transcribe with Whisper → burn captions on stock footage → render MP4.

## Commands

```bash
# Install (Python 3.11.7 required)
pip install -e ".[local,dev]"    # Coqui TTS + local Whisper
pip install -e ".[cloud,dev]"    # ElevenLabs + OpenAI Whisper API

# Run
shortform generate "https://www.reddit.com/r/..."
shortform batch urls.txt
shortform generate <url> --tts elevenlabs --transcribe whisper_api --force

# Test and lint
pytest
ruff check src tests

# Preprocess raw stock footage into 300-second clips
python scripts/process_stock.py /path/to/raw/
```

## Architecture

```
src/shortform/
├── cli.py           # Typer entry point: `generate` and `batch` commands
├── pipeline.py      # Orchestrator — wires all adapters end-to-end
├── config.py        # Pydantic config models + YAML loader
├── sources/         # Reddit scraper (Source Protocol)
├── text/            # Pure-function cleaners: censor, slang-expand, sentence-split
├── tts/             # TTS adapters: CoquiTTS (local), ElevenLabsTTS (cloud)
├── transcribe/      # Transcription adapters: WhisperLocal, WhisperAPI
├── render/
│   ├── title_card.py   # PIL-based Reddit-style title card generator
│   ├── captions.py     # ASS subtitle writer with pop-in animation
│   └── compositor.py   # FFmpeg composition (stock + audio + title + captions)
└── utils/           # temp_workdir, logging setup
```

**End-to-end flow in `pipeline.run(url, cfg)`:**
1. `sources/reddit.py` — fetches post JSON from Reddit's `.json` API
2. `text/cleaner.py` — HTML-unescape, censor profanity, expand acronyms (AITA → "Am I the A-hole"), split into sentences
3. TTS backend — generates per-sentence `.wav` files + title `.wav`
4. Transcription backend — word-level timestamps per sentence (accumulated with offset)
5. `render/title_card.py` — PIL draws the Reddit-style card to a PNG
6. `render/captions.py` — writes an ASS subtitle file with 25ms pop-in scale animation
7. `render/compositor.py` — single FFmpeg call: stock video + audio concat + title overlay + ASS burn-in → MP4
8. All intermediate files live in a `tempfile.TemporaryDirectory()` — nothing left in the repo root after a run

**Adapter pattern:** each stage (TTS, transcription, source) has a `Protocol` in `base.py`. Swap backends by changing `backends.tts` / `backends.transcribe` in `configs/default.yaml` or via `--tts` / `--transcribe` CLI flags. Heavy deps (torch, TTS, openai) are lazy-imported inside each adapter so the wrong extras don't error on import.

**Batch mode:** `shortform batch urls.txt` continues on per-URL failure; appends errors to `failures.jsonl`.

## Hard Dependencies

- **Font**: `assets.title_font` in config — default `/Library/Fonts/SF-Pro-Rounded-Semibold.otf` (macOS system font)
- **Stock footage**: `stock/` must contain pre-processed 300-second clips (run `scripts/process_stock.py` first)
- **Speaker reference** (Coqui): `en_uk_003.mp3` at project root; controls the cloned voice
- **Overlay assets**: `user.png`, `likes_comments.png` — used in title card rendering; paths resolved relative to `paths.resources_dir` in config
