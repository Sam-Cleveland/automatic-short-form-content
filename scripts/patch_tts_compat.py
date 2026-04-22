"""
Patches Coqui TTS 0.22.0 for compatibility with transformers 5.x.

Run once after `uv sync` or whenever the venv is rebuilt:
    uv run python scripts/patch_tts_compat.py

Two breakages fixed:
  1. BeamSearchScorer and friends removed from transformers public API.
  2. GenerationMixin dropped from GPT2PreTrainedModel's MRO, so .generate()
     no longer exists on GPT2InferenceModel.
"""

import importlib.util
import sys
from pathlib import Path


def _site_packages() -> Path:
    spec = importlib.util.find_spec("TTS")
    if spec is None or spec.origin is None:
        print("TTS not found in venv — skipping patches")
        sys.exit(0)
    return Path(spec.origin).parent.parent


def patch_stream_generator(tts_root: Path) -> None:
    path = tts_root / "TTS/tts/layers/xtts/stream_generator.py"
    src = path.read_text()

    old = (
        "from transformers import (\n"
        "    BeamSearchScorer,\n"
        "    ConstrainedBeamSearchScorer,\n"
        "    DisjunctiveConstraint,\n"
        "    GenerationConfig,\n"
        "    GenerationMixin,\n"
        "    LogitsProcessorList,\n"
        "    PhrasalConstraint,\n"
        "    PreTrainedModel,\n"
        "    StoppingCriteriaList,\n"
        ")\n"
        "from transformers.generation.utils import GenerateOutput, SampleOutput, logger"
    )
    new = (
        "from transformers import (\n"
        "    GenerationConfig,\n"
        "    GenerationMixin,\n"
        "    LogitsProcessorList,\n"
        "    PreTrainedModel,\n"
        "    StoppingCriteriaList,\n"
        ")\n"
        "from transformers.generation.utils import GenerateOutput, logger\n"
        "\n"
        "# Removed in transformers 5.x — stub for import compatibility (not used in tts_to_file path)\n"
        "try:\n"
        "    from transformers import BeamSearchScorer, ConstrainedBeamSearchScorer, DisjunctiveConstraint, PhrasalConstraint\n"
        "except ImportError:\n"
        "    class BeamSearchScorer:  # type: ignore[no-redef]\n"
        "        pass\n"
        "    class ConstrainedBeamSearchScorer:  # type: ignore[no-redef]\n"
        "        pass\n"
        "    class DisjunctiveConstraint:  # type: ignore[no-redef]\n"
        "        pass\n"
        "    class PhrasalConstraint:  # type: ignore[no-redef]\n"
        "        pass\n"
        "\n"
        "try:\n"
        "    from transformers.generation.utils import SampleOutput\n"
        "except ImportError:\n"
        "    SampleOutput = GenerateOutput  # type: ignore[misc,assignment]"
    )

    if old not in src:
        print(f"stream_generator.py: already patched or unexpected content, skipping")
        return
    path.write_text(src.replace(old, new))
    print(f"Patched: {path}")


def patch_gpt_inference(tts_root: Path) -> None:
    path = tts_root / "TTS/tts/layers/xtts/gpt_inference.py"
    src = path.read_text()

    old = (
        "from transformers import GPT2PreTrainedModel\n"
        "from transformers.modeling_outputs import CausalLMOutputWithCrossAttentions\n"
        "\n"
        "\n"
        "class GPT2InferenceModel(GPT2PreTrainedModel):"
    )
    new = (
        "from transformers import GPT2PreTrainedModel\n"
        "from transformers.generation import GenerationMixin\n"
        "from transformers.modeling_outputs import CausalLMOutputWithCrossAttentions\n"
        "\n"
        "\n"
        "class GPT2InferenceModel(GenerationMixin, GPT2PreTrainedModel):"
    )

    if old not in src:
        print(f"gpt_inference.py: already patched or unexpected content, skipping")
        return
    path.write_text(src.replace(old, new))
    print(f"Patched: {path}")


if __name__ == "__main__":
    tts_root = _site_packages()
    patch_stream_generator(tts_root)
    patch_gpt_inference(tts_root)
    print("Done.")
