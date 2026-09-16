"""
Pinned Claude API token pricing, for computing real-dollar cost figures
(CLAUDE.md §4 cost dimensions: token count, tool-call count, dollar cost,
wall-clock time, sub-agent fan-out).

Source: https://platform.claude.com/docs/en/about-claude/pricing
Verified live: 2026-08-30. Base input / output rates only (no prompt-caching
or batch discount applied — the harness issues standard synchronous calls).
Per CLAUDE.md §10.2, do not extend/round these numbers; re-fetch and update
this file (with a new dated comment) if pricing changes before experiments
are run.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_per_mtok: float   # USD per 1,000,000 input tokens
    output_per_mtok: float  # USD per 1,000,000 output tokens


# USD per million tokens, base (non-cached) rates.
# Sources verified live from platform.claude.com/docs/en/models/<model>/overview
# claude-sonnet-4-6: verified 2026-08-30 https://platform.claude.com/docs/en/models/sonnet-4-6/overview
PRICING: dict[str, ModelPricing] = {
    "claude-sonnet-5": ModelPricing(input_per_mtok=2.0, output_per_mtok=10.0),
    "claude-sonnet-4-6": ModelPricing(input_per_mtok=3.0, output_per_mtok=15.0),
    # claude-opus-4-8: verified 2026-08-30 https://platform.claude.com/docs/en/models/opus-4-8/overview
    "claude-opus-4-8": ModelPricing(input_per_mtok=5.0, output_per_mtok=25.0),
    "claude-haiku-4-5-20251001": ModelPricing(input_per_mtok=1.0, output_per_mtok=5.0),
    "claude-opus-5": ModelPricing(input_per_mtok=5.0, output_per_mtok=25.0),

    # OpenRouter-routed models (benchmark/llm_provider.py: any model string
    # containing "/" goes through OpenRouter's OpenAI-compatible endpoint).
    # Verified live from openrouter.ai/<slug> 2026-08-30 -- confirmed identical
    # passthrough pricing to the underlying provider's direct API for the
    # Claude models (no OpenRouter markup observed at verification time).
    "anthropic/claude-sonnet-5": ModelPricing(input_per_mtok=2.0, output_per_mtok=10.0),
    "anthropic/claude-opus-4.8": ModelPricing(input_per_mtok=5.0, output_per_mtok=25.0),
    # Verified live from openrouter.ai/<slug> 2026-08-30 (2nd verification pass).
    "anthropic/claude-opus-5": ModelPricing(input_per_mtok=5.0, output_per_mtok=25.0),
    "anthropic/claude-sonnet-4.6": ModelPricing(input_per_mtok=3.0, output_per_mtok=15.0),
    "openai/gpt-5.6-terra": ModelPricing(input_per_mtok=2.0, output_per_mtok=12.0),
    "openai/gpt-5.6-luna": ModelPricing(input_per_mtok=0.20, output_per_mtok=1.20),
    "openai/gpt-5.5": ModelPricing(input_per_mtok=5.0, output_per_mtok=30.0),
}

DEFAULT_MODEL = "anthropic/claude-sonnet-5"  # OpenRouter slug -- see CLAUDE.md S11 "use OpenRouter for all trials"


def safe_model_slug(model: str) -> str:
    """Filesystem-safe form of a model string for experiment filenames --
    OpenRouter slugs contain '/' (e.g. anthropic/claude-sonnet-5), which is
    a path separator, not a valid character in a single filename component."""
    return model.replace("/", "--")


def dollar_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in PRICING:
        raise ValueError(
            f"No pinned pricing for model {model!r}. Add it to benchmark/pricing.py "
            f"with a live-verified source before running cost-metered experiments."
        )
    p = PRICING[model]
    return (input_tokens / 1_000_000) * p.input_per_mtok + (
        output_tokens / 1_000_000
    ) * p.output_per_mtok
