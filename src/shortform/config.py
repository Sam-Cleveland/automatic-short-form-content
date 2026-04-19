"""Pydantic config models and YAML loader.

Usage:
    cfg = load()                          # uses configs/default.yaml
    cfg = load("configs/my_config.yaml")  # custom override
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class BackendsConfig(BaseModel):
    source: str = "reddit"
    tts: str = "coqui"
    transcribe: str = "whisper_local"


class PathsConfig(BaseModel):
    stock_dir: str = "stock"
    output_dir: str = "output"
    resources_dir: str = "."


class AssetsConfig(BaseModel):
    title_font: str = "/Library/Fonts/SF-Pro-Rounded-Semibold.otf"
    caption_font: str = "Bangers-Regular.ttf"
    user_overlay: str = "user.png"
    likes_comments_overlay: str = "likes_comments.png"


class CoquiConfig(BaseModel):
    model: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    speaker_wav: str = "en_uk_003.mp3"
    language: str = "en"


class ElevenLabsConfig(BaseModel):
    voice_id: str = ""
    model: str = "eleven_multilingual_v2"
    stability: float = 0.5
    similarity_boost: float = 0.75


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
    tts_elevenlabs: ElevenLabsConfig = ElevenLabsConfig()
    transcribe_whisper_local: WhisperLocalConfig = WhisperLocalConfig()
    transcribe_whisper_api: WhisperAPIConfig = WhisperAPIConfig()
    video: VideoConfig = VideoConfig()
    batch: BatchConfig = BatchConfig()


def load(path: str | Path = "configs/default.yaml") -> Config:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return Config.model_validate(data)
