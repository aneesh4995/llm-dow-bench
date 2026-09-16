"""
Defense-evaluation trial runner (CLAUDE.md S5 step 6 / S11, 2026-09-14).

Runs BOTH the attack and baseline condition of a scenario WITH an active
defense (defenses/*.py), n trials each, for a chosen (entry, model, defense)
triple. Two things this measures that the plain run_trials.py/run_trials_b.py
runners don't:

  attack-resistance: with the defense active, does the attack condition's
    cost/call/subagent count still come out amplified relative to what the
    SAME defense does to the baseline condition? (Not relative to the
    no-defense attack numbers already in experiments/trials_*.json -- a
    defense that blocks calls changes the trajectory, so its own
    attack-vs-baseline-under-defense comparison is the fair one.)

  utility cost (false positives): does the defense block anything at all
    during the BASELINE (legitimate) condition? Any block during baseline
    is a false positive by construction -- the baseline task is, by this
    project's own corpus design, never illegitimate.

This is deliberately the SCOPED-DOWN version of CLAUDE.md's full four-defense
evaluation plan (see defenses/ARCHITECTURE.md S6): two defenses only --
HardBudgetDefense (thresholds pulled from analysis/calibration_report.json,
NOT hardcoded -- see that file's own disclosed limitation) and
IntentConsistencyJudge (this paper's actual hypothesis test -- Section
"Hypothesis motivating the defense evaluation" in main.tex). Extend to
CapabilityBroker / CostAwareCircuitBreaker once these two are in and there
is still runway before Sept 29.

Requires OPENROUTER_API_KEY in the environment (.env). Run this from your
own terminal -- the Claude session that wrote this script cannot reach
OpenRouter itself (network allowlist).

Usage:
    python -m benchmark.run_defense_trials --trials 5
    python -m benchmark.run_defense_trials --trials 5 --entries A1 A2 A3 B1 B2 --defenses hard_budget intent_judge
    python -m benchmark.run_defense_trials --trials 3 --models anthropic/claude-sonnet-5 --defenses hard_budget

Writes one JSON per (entry, model, defense) to experiments/defense_trials_*.json.
No number here is pre-baked -- every figure comes from an actual model run
under an actual defense, per CLAUDE.md S9/S10.2.
"""

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from benchmark.cost_meter import run_and_meter
from benchmark.pricing import dollar_cost, safe_model_slug
from defenses.budget import HardBudgetDefense
from defenses.intent_judge import IntentConsistencyJudge

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"
CALIBRATION_PATH = Path(__file__).resolve().parent.parent / "analysis" / "calibration_report.json"

DOMAIN_A_ENTRIES = {"A1", "A2", "A3"}  # A4 (metric_type: absolute) excluded -- no baseline twin to compare against
DOMAIN_B_ENTRIES = {"B1", "B2"}
ALL_ENTRIES = sorted(DOMAIN_A_ENTRIES | DOMAIN_B_ENTRIES)

DEFAULT_MODELS = [
    "anthropic/claude-sonnet-5",
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-opus-5",
    "openai/gpt-5.5",
    "openai/gpt-5.6-luna",
    "openai/gpt-5.6-terra",
]

DEFAULT_DEFENSES = ["hard_budget", "intent_judge"]


def _load_calibration() -> dict:
    if not CALIBRATION_PATH.exists():
        print(
            f"WARNING: {CALIBRATION_PATH} not found -- run "
            "`python -m analysis.calibrate_defenses` first. HardBudgetDefense "
            "will fall back to no caps (effectively disabled) rather than a "
            "fabricated threshold.",
            file=sys.stderr,
        )
        return {}
    return json.loads(CALIBRATION_PATH.read_text())


def _build_defense(defense_name: str, entry: str, model: str, calibration: dict):
    if defense_name == "hard_budget":
        domain = "domain_a" if entry in DOMAIN_A_ENTRIES else "domain_b"
        cal = calibration.get(domain, {}).get(entry, {})
        kwargs = {}
        if entry in DOMAIN_A_ENTRIES:
            tc = cal.get("tool_call_count", {}).get("recommended_threshold")
            dc = cal.get("dollar_cost_usd", {}).get("recommended_threshold")
            if tc is not None:
                kwargs["max_tool_calls"] = tc
            if dc is not None:
                kwargs["max_dollar_cost_usd"] = dc
        else:
            sc = cal.get("subagent_call_count", {}).get("recommended_threshold")
            dc = cal.get("dollar_cost_usd", {}).get("recommended_threshold")
            if sc is not None:
                kwargs["max_subagent_calls"] = sc
            if dc is not None:
                kwargs["max_dollar_cost_usd"] = dc
        return HardBudgetDefense(**kwargs)
    if defense_name == "intent_judge":
        return IntentConsistencyJudge(model=model)
    raise ValueError(f"unknown defense: {defense_name!r}")


def run_domain_a_scenario(scenario_id: str, model: str, defense) -> dict:
    from benchmark.domain_a.agent import build_agent, initial_state
    from benchmark.domain_a.scenarios import SCENARIOS

    scenario = SCENARIOS[scenario_id]
    graph, ledger, state = build_agent(scenario, model=model, defense=defense)
    final_state, cost = run_and_meter(graph, initial_state(scenario), model=model)
    result = cost.to_dict()
    result["scenario_id"] = scenario_id
    result["corpus_entry"] = scenario.corpus_entry
    result["simulated_expensive_tool_cost_usd"] = round(ledger.total_usd, 6)
    result["total_cost_usd"] = round(cost.dollar_cost + ledger.total_usd, 6)
    result["final_message_count"] = len(final_state["messages"])
    result["blocked_call_count"] = len(state.blocked_calls)
    result["blocked_calls"] = state.blocked_calls
    return result


def run_domain_b_scenario(scenario_id: str, model: str, defense) -> dict:
    from benchmark.domain_b.agent import build_agent, initial_state
    from benchmark.domain_b.scenarios import SCENARIOS

    scenario = SCENARIOS[scenario_id]
    graph, ledger, state = build_agent(scenario, model=model, defense=defense)
    final_state, top_cost = run_and_meter(graph, initial_state(scenario), model=model)

    total_input_tokens = top_cost.input_tokens + ledger.aggregate_input_tokens
    total_output_tokens = top_cost.output_tokens + ledger.aggregate_output_tokens
    total_tool_calls = top_cost.tool_call_count + ledger.aggregate_tool_call_count
    total_wall_clock = top_cost.wall_clock_seconds + ledger.aggregate_wall_clock_seconds
    total_cost = dollar_cost(model, total_input_tokens, total_output_tokens)

    return {
        "scenario_id": scenario_id,
        "corpus_entry": scenario.corpus_entry,
        "model": model,
        "top_level": top_cost.to_dict(),
        "subagent_call_count": ledger.subagent_call_count,
        "max_depth_reached": ledger.max_depth_reached,
        "depth_cap_hit": ledger.depth_cap_hit,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "tool_call_count": total_tool_calls,
        "wall_clock_seconds": total_wall_clock,
        "total_cost_usd": round(total_cost, 6),
        "blocked_call_count": len(state.blocked_calls),
        "blocked_calls": state.blocked_calls,
    }


def run_scenario(entry: str, variant: str, model: str, defense) -> dict:
    scenario_id = f"{entry}-{variant}"
    if entry in DOMAIN_A_ENTRIES:
        return run_domain_a_scenario(scenario_id, model, defense)
    return run_domain_b_scenario(scenario_id, model, defense)


def _stats(values: list[float]) -> dict:
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "values": values,
    }


def run_entry_model_defense(entry: str, model: str, defense_name: str, trials: int, calibration: dict) -> dict:
    per_trial = []
    attack_costs, baseline_costs = [], []
    attack_blocked_counts, baseline_blocked_counts = [], []
    amplification_factors = []

    for i in range(trials):
        # A fresh defense instance per trial: CostAwareCircuitBreaker (not
        # used by default here, but if added) keeps internal history state
        # that must not leak across trials; HardBudgetDefense/
        # IntentConsistencyJudge are stateless across calls so this is a
        # no-op for them, but the pattern is kept uniform.
        attack_defense = _build_defense(defense_name, entry, model, calibration)
        baseline_defense = _build_defense(defense_name, entry, model, calibration)

        attack_result = run_scenario(entry, "attack", model, attack_defense)
        baseline_result = run_scenario(entry, "baseline", model, baseline_defense)

        attack_costs.append(attack_result["total_cost_usd"])
        baseline_costs.append(baseline_result["total_cost_usd"])
        attack_blocked_counts.append(attack_result["blocked_call_count"])
        baseline_blocked_counts.append(baseline_result["blocked_call_count"])
        amp = attack_result["total_cost_usd"] / baseline_result["total_cost_usd"] if baseline_result["total_cost_usd"] else None
        amplification_factors.append(amp)

        per_trial.append({"trial": i, "attack": attack_result, "baseline": baseline_result, "amplification_factor_under_defense": amp})
        print(
            f"  [{entry}/{model}/{defense_name}] trial {i}: "
            f"attack_cost=${attack_result['total_cost_usd']:.4f} "
            f"(blocked={attack_result['blocked_call_count']}), "
            f"baseline_cost=${baseline_result['total_cost_usd']:.4f} "
            f"(blocked={baseline_result['blocked_call_count']})",
            file=sys.stderr,
        )

    return {
        "entry": entry,
        "model": model,
        "defense": defense_name,
        "trials": trials,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "per_trial": per_trial,
        "attack_cost_usd_stats": _stats(attack_costs),
        "baseline_cost_usd_stats": _stats(baseline_costs),
        "amplification_factor_under_defense_stats": _stats([a for a in amplification_factors if a is not None]),
        "attack_blocked_count_stats": _stats(attack_blocked_counts),
        "baseline_blocked_count_stats": _stats(baseline_blocked_counts),
        "false_positive_note": (
            "baseline_blocked_count_stats > 0 for ANY trial means the defense "
            "blocked a call during the legitimate-task condition -- a false "
            "positive by this project's corpus design (baseline scenarios are "
            "never illegitimate). Report this rate explicitly; do not average "
            "it away."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--entries", nargs="+", default=ALL_ENTRIES, choices=ALL_ENTRIES)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--defenses", nargs="+", default=DEFAULT_DEFENSES, choices=["hard_budget", "intent_judge"])
    args = parser.parse_args()

    load_dotenv()
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY not set (checked .env and environment). Set it and retry.", file=sys.stderr)
        sys.exit(1)

    calibration = _load_calibration()
    EXPERIMENTS_DIR.mkdir(exist_ok=True)

    for entry in args.entries:
        for model in args.models:
            for defense_name in args.defenses:
                print(f"=== Running {entry} / {model} / {defense_name} ({args.trials} trials each condition) ===", file=sys.stderr)
                try:
                    result = run_entry_model_defense(entry, model, defense_name, args.trials, calibration)
                except Exception as exc:  # noqa: BLE001 -- log and continue to the next combo rather than losing the whole batch
                    print(f"  ERROR on {entry}/{model}/{defense_name}: {exc}", file=sys.stderr)
                    continue
                ts = int(datetime.now().timestamp())
                out_path = EXPERIMENTS_DIR / f"defense_trials_{entry}_{defense_name}_{safe_model_slug(model)}_{ts}.json"
                out_path.write_text(json.dumps(result, indent=2))
                print(f"  Written to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
