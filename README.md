# Automatic Short-Form Content

Automated pipeline that converts Reddit posts into short-form videos (TikTok / Instagram Reels style).

**Flow:** scrape Reddit → generate TTS audio → transcribe with Whisper → burn word-by-word captions on stock footage → render MP4.

## Setup

Python 3.11.7 required (see `.python-version`).

```bash
python -m venv venv && source venv/bin/activate

# Local ML models (Coqui TTS + Whisper)
pip install -e ".[local,dev]"

# Cloud APIs only (ElevenLabs + OpenAI Whisper)
pip install -e ".[cloud,dev]"

# Both
pip install -e ".[local,cloud,dev]"
```

Copy `.env.example` to `.env` and fill in any API keys you need:

```bash
cp .env.example .env
```

### Stock footage

Drop raw `.mp4` files into a directory and run the preprocessor to slice them into 300-second clips:

```bash
python scripts/process_stock.py /path/to/raw/footage/
# clips appear in stock/
```

## Usage

```bash
# Single post
shortform generate "https://www.reddit.com/r/tifu/comments/..."

# Batch (one URL per line in urls.txt)
shortform batch urls.txt

# Override backends per-run
shortform generate <url> --tts elevenlabs --transcribe whisper_api

# Re-render even if output already exists
shortform generate <url> --force

# All options
shortform generate --help
shortform batch --help
```

## Configuration

Edit `configs/default.yaml` to change backends, paths, video resolution, or TTS settings. Override per-run with `--config path/to/custom.yaml`.

Key settings:

| Key | Default | Options |
|-----|---------|---------|
| `backends.tts` | `coqui` | `coqui`, `elevenlabs` |
| `backends.transcribe` | `whisper_local` | `whisper_local`, `whisper_api` |
| `assets.title_font` | `/Library/Fonts/SF-Pro-Rounded-Semibold.otf` | any `.otf`/`.ttf` path |
| `video.fps` | `60` | any integer |

## Development

```bash
# Run tests
pytest

# Lint + format check
ruff check src tests
ruff format --check src tests
```

## Hard dependencies

- **SF Pro Rounded font** — `assets.title_font` in config; default is `/Library/Fonts/SF-Pro-Rounded-Semibold.otf` (macOS system font).
- **Stock footage** — `stock/` directory must contain pre-processed clips (see above).
- **Speaker reference** (Coqui only) — `en_uk_003.mp3` in project root; controls the cloned voice.
