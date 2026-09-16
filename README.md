# LLM-DoW-Bench

A benchmark, threat model, and defense evaluation for **Denial-of-Wallet (DoW)** attacks against LLM tool-use agents — an attacker inducing an agent to burn far more tokens, tool calls, and dollars than a task requires, without taking any individually unauthorized action.

This repository is an **anonymized artifact release for double-blind peer review** (submitted to IEEE SaTML 2027). It contains no author-identifying information. See `paper/main.tex` for the full manuscript.

## The problem

LLM agents with tool access can be induced — via a poisoned tool result, a page they're asked to summarize, or an adversarially framed task — into doing something entirely *permitted*: searching, calling an API, delegating to a sub-agent, an excessive number of times or in an unnecessarily expensive way. No confidentiality or integrity boundary is crossed. The agent's owner simply pays for work the task never needed. Unlike the usual framing of prompt injection (data exfiltration, unauthorized actions), every action the agent takes is individually reasonable — which is why intent-classifier and permission-scoping defenses don't obviously catch it.

Four widely used agent-security benchmarks (AgentDojo, InjecAgent, ToolEmu, R-Judge) do not measure cost as an outcome at all. This project does.

## What's here

- **`threat-model.md`** — adversary model (tool-result content control / task-framing control) and a six-vector attack-surface taxonomy (V1–V6: retry induction, sub-agent fan-out, expensive-tool bait, context/input bloat, adversarial task framing, delegation-loop induction).
- **`attacks/corpus/`** — concrete attack + baseline task specifications instantiating V1–V6 across two agentic domains: a single-agent helpdesk/support agent (Domain A) and a research/analyst agent with sub-agent delegation (Domain B).
- **`benchmark/`** — a LangGraph-based cost-metering harness. Model-agnostic by design: any model string containing `/` (e.g. `anthropic/claude-sonnet-5`, `openai/gpt-5.6-terra`) routes through OpenRouter, so the same harness code drove every model in the evaluation with no provider-specific branches.
- **`defenses/`** — four candidate defenses as pre-tool-call gates: a hard cumulative-cost/call budget, a cost-aware circuit breaker, a capability broker with per-tool call quotas, and an LLM-based intent-consistency judge. Two (hard budget, intent judge) have been run against the full corpus; results below.
- **`experiments/`** — every raw trial result (JSON) behind every number in the paper. Nothing in the paper is derived from a number that isn't traceable to a file here.
- **`analysis/`** — scripts that turn `experiments/` output into the paper's tables (`build_paper_tables.py`, `analyze_defense_trials.py`, `calibrate_defenses.py`).
- **`paper/`** — the manuscript (`main.tex`), compiled PDF, and bibliography.

## Headline results (n=5 trials/condition, 6 frontier models — 3 Claude, 3 OpenAI, via OpenRouter)

Cost-amplification factor (attack cost ÷ legitimate-task cost) varies sharply by vector and by model, not uniformly:

| Vector | Effect |
|---|---|
| V1 — unbounded retry induction | Weak, model-dependent: mean 1.2–1.3×, range 0.8–1.8× |
| V3 — expensive-tool bait | Weak, model-dependent (same range as V1) |
| V4 — context/input bloat | **Severe and universal**: mean 6.4×, up to 21.5× in a single trial, on *every* model tested |
| V2 / V6 — sub-agent fan-out / delegation-loop induction | **Sharp per-model split**: 4 of 6 models (all three Claude models + one OpenAI model) resist the injected delegation instructions almost perfectly; 2 OpenAI models comply substantially, in one case ranging 6–13 sub-agent calls per trial against a stable legitimate baseline of 3 |

Defense evaluation (2 of 4 candidate defenses run against the full corpus):

| Defense | Attack-trial block rate | False-positive rate | Why |
|---|---|---|---|
| Hard cumulative-cost/call budget | 0.7% | 0% | A pre-tool-call gate cannot intervene on cost that accrues *within* a single already-issued call — exactly V4's mechanism, so it never touches the benchmark's largest effect |
| LLM-based intent-consistency judge | 13.3% | 1.3% | Catches most of what actually works (concentrated almost entirely in the two delegation vectors, on the two models susceptible to them) but at nonzero false-positive cost and its own unmetered per-call LLM overhead |

Full methodology, per-model/per-vector tables, and discussion are in `paper/main.tex`.

## Reproducing a result

```bash
pip install -r benchmark/requirements.txt
```

Set `OPENROUTER_API_KEY` (or `ANTHROPIC_API_KEY` for a bare, non-`/` model name) in a `.env` file at the repo root.

```bash
# One attack+baseline pair, Domain A
python -m benchmark.run --entry A3 --model anthropic/claude-sonnet-5

# One attack+baseline pair, Domain B (sub-agent delegation)
python -m benchmark.run_b --entry B2 --model openai/gpt-5.6-terra

# Full n=5 trial batch across all six models, one domain
python -m benchmark.run_trials --trials 5
python -m benchmark.run_trials_b --trials 5

# Defense evaluation
python -m benchmark.run_defense_trials --trials 5 --entries A1 A2 A3 B1 B2 --defenses hard_budget intent_judge
```

Each run writes a raw JSON result to `experiments/`; `analysis/build_paper_tables.py` regenerates the paper's tables from whatever is in that directory.

## Status

Pre-print / under double-blind review. Baseline and defense evaluation results are real, measured data (see `experiments/`) — nothing in the paper or this README is a projected or illustrative figure. Open items (defense calibration methodology, two remaining unevaluated defenses, wider model coverage) are documented in the paper's Limitations section.
