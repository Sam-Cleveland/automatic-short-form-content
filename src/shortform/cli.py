"""CLI entry point.

Commands:
    shortform generate <url>      — render one Reddit post
    shortform batch [urls_file]   — render a list of URLs from a file
"""

from __future__ import annotations

import json
import logging
import traceback
from pathlib import Path
from typing import Optional

import typer

from .config import load as load_config
from .utils.logging import setup as setup_logging

app = typer.Typer(help="Reddit-to-short-form-video pipeline.", no_args_is_help=True)

_CONFIG_OPT = typer.Option(Path("configs/default.yaml"), "--config", "-c", help="Config YAML path.")
_FORCE_OPT = typer.Option(False, "--force", help="Re-render even if output already exists.")
_VERBOSE_OPT = typer.Option(False, "--verbose", "-v", help="Enable debug logging.")


@app.command()
def generate(
    url: str = typer.Argument(..., help="Reddit post URL."),
    config: Path = _CONFIG_OPT,
    tts: Optional[str] = typer.Option(None, "--tts", help="TTS backend override (coqui|elevenlabs)."),
    transcribe: Optional[str] = typer.Option(None, "--transcribe", help="Transcription backend override (whisper_local|whisper_api)."),
    force: bool = _FORCE_OPT,
    verbose: bool = _VERBOSE_OPT,
) -> None:
    """Render a single Reddit post to MP4."""
    setup_logging(logging.DEBUG if verbose else logging.INFO)
    cfg = load_config(config)
    if tts:
        cfg.backends.tts = tts
    if transcribe:
        cfg.backends.transcribe = transcribe
    if force:
        cfg.batch.skip_if_exists = False

    from .pipeline import run

    out = run(url.strip(), cfg)
    typer.echo(f"Output: {out}")


@app.command()
def story(
    topic: str = typer.Argument("", help="Optional topic/theme hint (e.g. 'AITA coworker stole my lunch')."),
    config: Path = _CONFIG_OPT,
    tts: Optional[str] = typer.Option(None, "--tts", help="TTS backend override (kokoro|edge_tts|coqui|elevenlabs)."),
    transcribe: Optional[str] = typer.Option(None, "--transcribe", help="Transcription backend override (whisper_local|whisper_api)."),
    force: bool = _FORCE_OPT,
    verbose: bool = _VERBOSE_OPT,
) -> None:
    """Generate an AI-written Reddit-style story and render to MP4."""
    setup_logging(logging.DEBUG if verbose else logging.INFO)
    cfg = load_config(config)
    cfg.backends.source = "llm_story"
    if tts:
        cfg.backends.tts = tts
    if transcribe:
        cfg.backends.transcribe = transcribe
    if force:
        cfg.batch.skip_if_exists = False

    from .pipeline import run

    out = run(topic, cfg)
    typer.echo(f"Output: {out}")


@app.command()
def batch(
    urls_file: Path = typer.Argument(Path("urls.txt"), help="File with one URL per line."),
    config: Path = _CONFIG_OPT,
    force: bool = _FORCE_OPT,
    verbose: bool = _VERBOSE_OPT,
) -> None:
    """Render every URL in a file, continuing on per-URL failures.

    Failures are appended to `failures.jsonl` in the current directory.
    """
    setup_logging(logging.DEBUG if verbose else logging.INFO)
    cfg = load_config(config)
    if force:
        cfg.batch.skip_if_exists = False

    from .pipeline import run

    urls = [u.strip() for u in urls_file.read_text().splitlines() if u.strip()]
    log = logging.getLogger("shortform.batch")
    log.info("Processing %d URL(s) from %s", len(urls), urls_file)

    failures: list[dict] = []
    successes = 0

    for i, url in enumerate(urls, 1):
        log.info("[%d/%d] %s", i, len(urls), url)
        try:
            out = run(url, cfg)
            log.info("OK → %s", out)
            successes += 1
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            log.error("FAIL: %s", exc)
            failures.append({"url": url, "error": str(exc), "traceback": tb})

    log.info("Finished: %d succeeded, %d failed", successes, len(failures))

    if failures:
        failures_path = Path("failures.jsonl")
        with failures_path.open("a") as f:
            for entry in failures:
                f.write(json.dumps(entry) + "\n")
        typer.echo(
            f"{len(failures)} failure(s) written to {failures_path}",
            err=True,
        )
        raise typer.Exit(code=1)
