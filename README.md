# shortform

Converts Reddit posts (or AI-generated stories) into short-form videos — TikTok / Instagram Reels / YouTube Shorts style. Word-by-word captions, Reddit title card, stock footage background.

**Flow:** fetch post → clean text → TTS audio → Whisper transcription → title card → burn captions → render MP4

---

## Prerequisites

- Python 3.11+
- FFmpeg with `libass` (needed for caption burn-in)

```bash
# macOS — Homebrew's default ffmpeg lacks libass
brew install ffmpeg-full

# Ubuntu/Debian
sudo apt install ffmpeg
```

---

## Installation

```bash
git clone https://github.com/Sam-Cleveland/automatic-short-form-content
cd automatic-short-form-content
python -m venv .venv && source .venv/bin/activate
```

Install the extras for the backends you want:

```bash
# Recommended: cloud TTS (edge_tts, free) + local Whisper
pip install -e ".[cloud,dev]"

# Local ONNX TTS (kokoro — no GPU required, ~50 MB model download)
pip install -e ".[kokoro,dev]"

# All cloud + local ML backends
pip install -e ".[cloud,local,kokoro,dev]"
```

Copy `.env.example` to `.env` and fill in any API keys you need:

```bash
cp .env.example .env
```

---

## Stock footage

Drop raw `.mp4` files anywhere, then run the preprocessor to slice them into 300-second clips that the pipeline picks from randomly:

```bash
python scripts/process_stock.py /path/to/raw/footage/
# clips land in stock/
```

---

## User avatar overlay

The title card uses a `user.png` Reddit avatar overlay. Supply your own — it should be a transparent-background PNG (roughly 100×100 px). Place it in the project root:

```bash
cp your-avatar.png user.png
```

---

## Usage

```bash
# Render a single Reddit post
shortform generate "https://www.reddit.com/r/tifu/comments/..."

# Generate an AI-written story (requires OPENAI_API_KEY or ANTHROPIC_API_KEY)
shortform story
shortform story "AITA for telling my sister her fiancé hit on me"

# Batch render — one URL per line
shortform batch urls.txt

# Per-run backend override
shortform generate <url> --tts kokoro --transcribe whisper_api

# Re-render even if output already exists
shortform generate <url> --force

shortform generate --help
shortform story --help
shortform batch --help
```

---

## Backends

| Stage | Backend | Extra | Notes |
|---|---|---|---|
| TTS | `edge_tts` *(default)* | `cloud` | Microsoft neural voices, free, requires internet |
| TTS | `kokoro` | `kokoro` | ONNX, no GPU, downloads ~50 MB model once |
| TTS | `elevenlabs` | `cloud` | High quality, paid API |
| TTS | `coqui` | `local` | XTTS v2, GPU recommended, unmaintained upstream |
| Transcribe | `whisper_local` *(default)* | `local` or `kokoro` | Runs on CPU or GPU |
| Transcribe | `whisper_api` | `cloud` | OpenAI Whisper API |
| Source | `reddit` *(default)* | — | Scrapes Reddit's `.json` API |
| Source | `llm_story` | `cloud` | Generates original AITA/TIFU content via LLM |

Set defaults in `configs/default.yaml` or override per-run with `--tts` / `--transcribe`.

---

## Configuration

Edit `configs/default.yaml` to change backends, voices, video settings, or paths. Override for a single run with `--config path/to/custom.yaml`.

Key settings:

| Key | Default | Description |
|---|---|---|
| `backends.tts` | `edge_tts` | TTS backend |
| `backends.transcribe` | `whisper_local` | Transcription backend |
| `tts_edge.voice` | `en-GB-RyanNeural` | Edge TTS voice name |
| `tts_kokoro.voice` | `bm_george` | Kokoro voice (bm_george, am_michael, af_bella…) |
| `video.width` / `video.height` | `1080` / `1920` | Output resolution (9:16 portrait) |
| `video.fps` | `60` | Output frame rate |
| `source_llm_story.api_type` | `openai` | `openai` or `anthropic` |
| `source_llm_story.model` | `gpt-4o-mini` | LLM model for story generation |
| `source_llm_story.api_url` | `""` | Base URL override (Ollama, LM Studio, etc.) |

### Local LLM

For Ollama or LM Studio, set in `default.yaml`:

```yaml
source_llm_story:
  api_type: openai
  api_url: "http://localhost:11434/v1"
  api_key: "ollama"
  model: llama3
```

---

## Development

```bash
pytest
ruff check src tests
ruff format --check src tests
```

---

## License

MIT
