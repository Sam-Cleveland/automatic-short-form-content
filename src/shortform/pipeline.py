"""Pipeline orchestrator.

`run(url, config)` is the single entry point for producing one video.
It wires all adapters together and keeps all intermediate files inside
a temporary directory that is cleaned up on exit.
"""

from __future__ import annotations

import logging
import random
import re
from pathlib import Path

from .config import Config
from .utils.fs import temp_workdir

log = logging.getLogger(__name__)


def _build_tts(cfg: Config):
    backend = cfg.backends.tts
    if backend == "coqui":
        from .tts.coqui import CoquiTTS  # noqa: PLC0415

        c = cfg.tts_coqui
        return CoquiTTS(model=c.model, speaker_wav=c.speaker_wav, language=c.language, speaker=c.speaker, speed=c.speed)
    if backend == "kokoro":
        from .tts.kokoro import KokoroTTS  # noqa: PLC0415

        c = cfg.tts_kokoro
        return KokoroTTS(voice=c.voice, speed=c.speed, lang=c.lang, model_repo=c.model_repo)
    if backend == "edge_tts":
        from .tts.edge_tts_adapter import EdgeTTS  # noqa: PLC0415

        return EdgeTTS(voice=cfg.tts_edge.voice, speed=cfg.tts_edge.speed)
    if backend == "elevenlabs":
        from .tts.elevenlabs import ElevenLabsTTS  # noqa: PLC0415

        c = cfg.tts_elevenlabs
        return ElevenLabsTTS(
            voice_id=c.voice_id,
            model=c.model,
            stability=c.stability,
            similarity_boost=c.similarity_boost,
            speed=c.speed,
        )
    raise ValueError(f"Unknown TTS backend: {backend!r}. Choose 'kokoro', 'edge_tts', 'coqui', or 'elevenlabs'.")


def _build_source(cfg: Config):
    backend = cfg.backends.source
    if backend == "reddit":
        from .sources.reddit import RedditSource  # noqa: PLC0415

        return RedditSource()
    if backend == "llm_story":
        from .sources.llm_story import LLMStorySource  # noqa: PLC0415

        return LLMStorySource(cfg.source_llm_story)
    raise ValueError(f"Unknown source backend: {backend!r}. Choose 'reddit' or 'llm_story'.")


def _build_transcriber(cfg: Config):
    backend = cfg.backends.transcribe
    if backend == "whisper_local":
        from .transcribe.whisper_local import WhisperLocal  # noqa: PLC0415

        c = cfg.transcribe_whisper_local
        return WhisperLocal(
            model_id=c.model_id,
            chunk_length_s=c.chunk_length_s,
            batch_size=c.batch_size,
        )
    if backend == "whisper_api":
        from .transcribe.whisper_api import WhisperAPI  # noqa: PLC0415

        return WhisperAPI(model=cfg.transcribe_whisper_api.model)
    raise ValueError(
        f"Unknown transcribe backend: {backend!r}. Choose 'whisper_local' or 'whisper_api'."
    )


def _pick_stock(stock_dir: Path) -> Path:
    clips = list(stock_dir.glob("*.mp4"))
    if not clips:
        raise FileNotFoundError(f"No .mp4 files found in {stock_dir}")
    return random.choice(clips)


def run(url: str, cfg: Config) -> Path:
    """Run the full pipeline for a single Reddit URL.

    Returns the path to the rendered MP4.
    Raises on any unrecoverable error — caller is responsible for catching
    and logging in batch mode.
    """
    from .text.cleaner import censor, prepare_body, prepare_title_for_display, prepare_title_for_tts
    from .render import captions as captions_mod
    from .render import compositor
    from .render import title_card
    from .config import resolve_font

    # ── 1. Fetch post ──────────────────────────────────────────────────────
    post = _build_source(cfg).fetch(url)
    log.info("Fetched: %r", post.title)

    # ── 2. Text processing ─────────────────────────────────────────────────
    title_tts = prepare_title_for_tts(post.title)
    title_display = prepare_title_for_display(post.title)
    sentences = prepare_body(post.body)
    log.info("%d sentences after cleaning", len(sentences))

    # ── 3. Idempotency check ───────────────────────────────────────────────
    output_dir = Path(cfg.paths.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-zA-Z0-9_.-]", "", title_display)[:120]
    out_path = output_dir / f"{slug}.mp4"

    if cfg.batch.skip_if_exists and out_path.exists():
        log.info("Skipping %s — already exists (use --force to re-render)", out_path)
        return out_path

    # ── 4. Stock clip ──────────────────────────────────────────────────────
    stock_path = _pick_stock(Path(cfg.paths.stock_dir))
    log.info("Stock: %s", stock_path)

    # ── 5. Initialise backends (lazy — no heavy imports until here) ────────
    tts = _build_tts(cfg)
    transcriber = _build_transcriber(cfg)

    # ── 6. All ephemeral work happens inside a temp directory ──────────────
    resources = Path(cfg.paths.resources_dir)

    with temp_workdir() as tmp:
        # TTS
        title_wav = tmp / "title.wav"
        log.info("Synthesising title audio…")
        tts.synthesize(title_tts, title_wav)

        sentence_wavs: list[Path] = []
        for i, sentence in enumerate(sentences):
            wav = tmp / f"sentence_{i:04d}.wav"
            log.info("Synthesising sentence %d/%d…", i + 1, len(sentences))
            tts.synthesize(sentence, wav)
            sentence_wavs.append(wav)

        # Transcription (per sentence, then accumulate with offset)
        from .transcribe.base import WordTimestamp

        words: list[WordTimestamp] = []
        offset = 0.0
        for i, wav in enumerate(sentence_wavs):
            log.info("Transcribing sentence %d/%d…", i + 1, len(sentence_wavs))
            chunk = transcriber.transcribe(wav)
            dur = compositor._audio_duration(wav)
            for w in chunk:
                words.append(WordTimestamp(text=censor(w.text), start=w.start + offset, end=w.end + offset))
            offset += dur

        # Title card
        title_card_path = tmp / "title_card.png"
        title_card.render(
            title_display,
            title_card_path,
            font_path=resolve_font(cfg.assets.title_font, resources),
            user_overlay=str(resources / cfg.assets.user_overlay),
            likes_comments_overlay=str(resources / cfg.assets.likes_comments_overlay),
            width=cfg.video.width,
        )

        # Concatenate audio
        audio_path = tmp / "audio.wav"
        log.info("Concatenating audio…")
        duration = compositor.concat_audio([title_wav] + sentence_wavs, audio_path)
        title_dur = compositor._audio_duration(title_wav)

        # Copy caption font into temp dir so FFmpeg's fontsdir has no spaces
        import shutil  # noqa: PLC0415

        caption_font_src = Path(resolve_font(cfg.assets.caption_font, resources))
        caption_font_tmp = tmp / caption_font_src.name
        shutil.copy2(caption_font_src, caption_font_tmp)

        # Captions ASS file
        captions_path = tmp / "captions.ass"
        captions_mod.write(
            words,
            captions_path,
            title_offset=title_dur,
            caption_font=caption_font_tmp.stem,  # font name without extension
            width=cfg.video.width,
            height=cfg.video.height,
        )

        # Compose final video
        compositor.compose(
            stock_path=stock_path,
            audio_path=audio_path,
            title_card=title_card_path,
            captions=captions_path,
            title_dur=title_dur,
            duration=duration,
            out_path=out_path,
            width=cfg.video.width,
            height=cfg.video.height,
            fps=cfg.video.fps,
            video_codec=cfg.video.video_codec,
            audio_codec=cfg.video.audio_codec,
            caption_font_dir=str(tmp),  # font was copied here — no spaces in path
        )

    return out_path
