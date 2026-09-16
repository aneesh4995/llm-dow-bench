"""
Chat-model provider selection. LangGraph's model-agnosticism (the reason it
was locked as this project's SDK, threat-model.md §8.3) is only real if the
harness can actually swap providers -- this module is that swap point.

Model-name convention:
  - A slug containing "/" (e.g. "anthropic/claude-sonnet-5",
    "openai/gpt-5.6-terra") is an OpenRouter model ID: routed through
    ChatOpenAI pointed at OpenRouter's OpenAI-compatible endpoint, using
    OPENROUTER_API_KEY. OpenRouter fronts both Claude and GPT (and others)
    behind one API, so this is also how a future non-Anthropic model
    (CLAUDE.md's cross-model RQ2 requirement) gets wired in with no new
    provider-specific code.
  - A bare model name with no "/" (e.g. "claude-sonnet-5") is routed direct
    to Anthropic via ChatAnthropic, using ANTHROPIC_API_KEY. This is the
    legacy/default path used by every experiment already run this session
    (see experiments/) -- kept so those pinned model names keep working
    unchanged.

pricing.py's PRICING dict keys must match whichever of these two strings is
passed as `model` throughout the harness (run.py, run_b.py, cost_meter.py) --
the OpenRouter and direct-Anthropic pricing for the same underlying model
were verified live to be identical passthrough rates (see pricing.py's
OpenRouter entries), so no separate pricing math is needed per route.
"""

import os

from langchain_anthropic import ChatAnthropic


def build_chat_model(model: str):
    if "/" in model:
        from langchain_openai import ChatOpenAI

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY not set (checked environment/.env) but "
                f"model {model!r} is an OpenRouter slug (contains '/'). Add "
                "OPENROUTER_API_KEY to .env."
            )
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
    return ChatAnthropic(model=model)
