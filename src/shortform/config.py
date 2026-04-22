"""Pydantic config models and YAML loader.

Usage:
    cfg = load()                          # uses configs/default.yaml
    cfg = load("configs/my_config.yaml")  # custom override
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

# Fonts bundled with the package (OFL licensed, redistributable)
_BUNDLED_FONTS = Path(__file__).parent / "resources" / "fonts"


def resolve_font(font_spec: str, resources_dir: str | Path = ".") -> str:
    """Resolve a font specifier to an absolute path.

    Resolution order:
    1. Absolute path — returned as-is (user-supplied system font)
    2. Relative path under resources_dir — explicit project-local font
    3. Bundled font in the package's resources/fonts/ directory
    """
    p = Path(font_spec)
    if p.is_absolute():
        return str(p)
    candidate = Path(resources_dir) / font_spec
    if candidate.exists():
        return str(candidate)
    bundled = _BUNDLED_FONTS / font_spec
    if bundled.exists():
        return str(bundled)
    raise FileNotFoundError(
        f"Font {font_spec!r} not found in resources_dir={resources_dir!r} "
        f"or bundled fonts ({_BUNDLED_FONTS})"
    )


def _llm_system_prompt_default() -> str:
    from .sources.llm_story import DEFAULT_SYSTEM_PROMPT  # noqa: PLC0415
    return DEFAULT_SYSTEM_PROMPT


def _llm_story_prompt_default() -> str:
    from .sources.llm_story import DEFAULT_STORY_PROMPT  # noqa: PLC0415
    return DEFAULT_STORY_PROMPT


class LLMStoryConfig(BaseModel):
    api_type: str = "openai"   # "openai" (also covers Ollama/vLLM/Together) or "anthropic"
    api_url: str = ""          # base URL override; empty = SDK default
    api_key: str = ""          # falls back to OPENAI_API_KEY / ANTHROPIC_API_KEY env vars
    model: str = "gpt-4o-mini" # for anthropic use e.g. claude-haiku-4-5-20251001
    system_prompt: str = Field(default_factory=_llm_system_prompt_default)
    story_prompt: str = Field(default_factory=_llm_story_prompt_default)
    max_tokens: int = 1024
    temperature: float = 0.9


class BackendsConfig(BaseModel):
    source: str = "reddit"
    tts: str = "coqui"
    transcribe: str = "whisper_local"


class PathsConfig(BaseModel):
    stock_dir: str = "stock"
    output_dir: str = "output"
    resources_dir: str = "."


class AssetsConfig(BaseModel):
    title_font: str = "Nunito-Bold.ttf"
    caption_font: str = "Anton-Regular.ttf"
    user_overlay: str = "user.png"
    likes_comments_overlay: str = "likes_comments.png"


class CoquiConfig(BaseModel):
    model: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    speaker_wav: str = "en_uk_003.mp3"
    speaker: str = ""  # built-in XTTS speaker name; takes priority over speaker_wav when set
    language: str = "en"
    speed: float = 1.0


class KokoroConfig(BaseModel):
    voice: str = "bm_george"  # bm_george (British male), am_michael (US male), af_bella (US female)
    speed: float = 1.0
    lang: str = "en-us"
    model_repo: str = "fastrtc/kokoro-onnx"


class EdgeTTSConfig(BaseModel):
    voice: str = "en-GB-RyanNeural"  # en-US-GuyNeural, en-GB-RyanNeural, en-US-AriaNeural
    speed: float = 1.0


class ElevenLabsConfig(BaseModel):
    voice_id: str = ""
    model: str = "eleven_multilingual_v2"
    stability: float = 0.5
    similarity_boost: float = 0.75
    speed: float = 1.0


class WhisperLocalConfig(BaseModel):
    model_id: str = "openai/whisper-small"
    chunk_length_s: int = 30
    batch_size: int = 16


class WhisperAPIConfig(BaseModel):
    model: str = "whisper-1"


class VideoConfig(BaseModel):
    width: int = 720
    height: int = 720
    fps: int = 60
    audio_codec: str = "aac"
    video_codec: str = "libx264"


class BatchConfig(BaseModel):
    skip_if_exists: bool = True
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0


class Config(BaseModel):
    backends: BackendsConfig = BackendsConfig()
    paths: PathsConfig = PathsConfig()
    assets: AssetsConfig = AssetsConfig()
    tts_coqui: CoquiConfig = CoquiConfig()
    tts_kokoro: KokoroConfig = KokoroConfig()
    tts_edge: EdgeTTSConfig = EdgeTTSConfig()
    tts_elevenlabs: ElevenLabsConfig = ElevenLabsConfig()
    transcribe_whisper_local: WhisperLocalConfig = WhisperLocalConfig()
    transcribe_whisper_api: WhisperAPIConfig = WhisperAPIConfig()
    source_llm_story: LLMStoryConfig = Field(default_factory=LLMStoryConfig)
    video: VideoConfig = VideoConfig()
    batch: BatchConfig = BatchConfig()


def load(path: str | Path = "configs/default.yaml") -> Config:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return Config.model_validate(data)
