# benchmark/ — LLM-DoW-Bench harness

Status: **Domain A (helpdesk) harness implemented, not yet run.** No experiment
in `experiments/` exists yet — nothing here has produced a real cost figure.
Per `CLAUDE.md` §9/§10.2, do not treat anything in this file as measured data.

## What exists

- `pricing.py` — pinned Claude API token pricing (input/output $/MTok), source
  and verification date cited in the file header. Re-verify before relying on
  it if time has passed.
- `cost_meter.py` — post-hoc cost metering from a LangGraph run's final
  message list: token count (in/out), LLM call count, tool-call count (by
  name), wall-clock time, dollar cost.
- `domain_a/` — Domain A (single-agent helpdesk) implementation:
  - `scenarios.py` — mock ticket/KB content instantiating corpus entries
    A1-A4 (`attacks/corpus/domain-a-helpdesk/`), attack + baseline variants
    where a ratio metric applies.
  - `tools.py` — the four sketch tools from `threat-model.md` §8.1
    (`search_kb`, `search_ticket_history`, `draft_reply`,
    `run_sentiment_deep_analysis`). The last is the domain's stand-in for an
    expensive external API call; its simulated per-call cost is a fixed
    harness-design constant, not a real third-party price — see the
    docstring in `tools.py`.
  - `agent.py` — LangGraph `create_react_agent` wrapping the four tools.
- `run.py` — CLI: runs one corpus entry (attack, and baseline if the entry's
  `metric_type` is `ratio`), computes cost-amplification factor, writes a
  JSON result to `experiments/`.

## Not yet implemented

- Domain B (research/analyst agent with sub-agent delegation — corpus
  entries B1/B2, `threat-model.md` §8.2). Needs LangGraph delegation-node /
  fan-out depth-breadth counters, not built here.
- Any defense (`defenses/` is still empty scaffolding) — this harness only
  measures baseline vulnerability so far, per `CLAUDE.md` §5 step 5.

## Running it

```bash
cd ~/llm-dow-bench
source .venv/bin/activate   # or use .venv/bin/python directly
export ANTHROPIC_API_KEY=sk-ant-...
python -m benchmark.run --entry A1
python -m benchmark.run --entry A2
python -m benchmark.run --entry A3
python -m benchmark.run --entry A4   # no baseline twin — absolute metric
```

Each run prints a JSON result and writes it to `experiments/<entry>_<model>_<ts>.json`.
`--model` defaults to `claude-sonnet-5`; pass a different model id (must be
added to `pricing.py` first) to compare across models per RQ2.

A1-A3 report an `amplification_factor` dict (ratio of attack/baseline for
total_tokens, tool_call_count, wall_clock_seconds, total_cost_usd). A4 has no
baseline twin (metric_type: absolute, per `attacks/corpus/domain-a-helpdesk/a4-v5-adversarial-task-framing.yaml`)
— compare its `tool_call_count` / `search_ticket_history` call pattern by
hand against the corpus entry's `reference_completion` bound (top-5 relevant
tickets).

## Requires

`ANTHROPIC_API_KEY` in the environment. No key is stored in this repo or
committed anywhere — set it locally before running.
