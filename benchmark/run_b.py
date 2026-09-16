"""
CLI entry point for Domain B (sub-agent delegation): run one scenario
(attack + baseline twin), meter cost INCLUDING every sub-agent spawned via
delegate_subagent, and compute the cost-amplification factor. Both B1 (V2
fan-out) and B2 (V6 delegation loop) are metric_type: ratio per their corpus
entries, so both always have a baseline twin.

Total cost = top-level agent's own messages + every sub-agent's metered cost
(DelegationLedger, tools.py), summed. Fan-out metrics (subagent_call_count,
max_depth_reached, depth_cap_hit) are reported alongside token/dollar/time
cost -- these are Domain B's distinguishing metrics per CLAUDE.md §4, not
measurable at all in Domain A.

Usage:
    python -m benchmark.run_b --entry B1
    python -m benchmark.run_b --entry B2 --model claude-opus-4-8
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from benchmark.cost_meter import run_and_meter
from benchmark.domain_b.agent import build_agent, initial_state
from benchmark.domain_b.scenarios import SCENARIOS
from benchmark.pricing import DEFAULT_MODEL, dollar_cost, safe_model_slug

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"

ENTRY_TO_VARIANTS = {
    "B1": ("B1-attack", "B1-baseline"),
    "B2": ("B2-attack", "B2-baseline"),
}

RATIO_METRICS = ("total_tokens", "tool_call_count", "wall_clock_seconds", "total_cost_usd")


def run_scenario(scenario_id: str, model: str) -> dict:
    scenario = SCENARIOS[scenario_id]
    graph, ledger, _state = build_agent(scenario, model=model)  # _state: defenses/ RunningState, unused without a defense passed
    final_state, top_cost = run_and_meter(graph, initial_state(scenario), model=model)

    total_input_tokens = top_cost.input_tokens + ledger.aggregate_input_tokens
    total_output_tokens = top_cost.output_tokens + ledger.aggregate_output_tokens
    total_tool_calls = top_cost.tool_call_count + ledger.aggregate_tool_call_count
    total_llm_calls = top_cost.llm_call_count + ledger.aggregate_llm_call_count
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
        "llm_call_count": total_llm_calls,
        "wall_clock_seconds": round(total_wall_clock, 3),
        "total_cost_usd": round(total_cost, 6),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry", required=True, choices=sorted(ENTRY_TO_VARIANTS))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set (checked .env and environment). Set it and retry.", file=sys.stderr)
        sys.exit(1)

    attack_id, baseline_id = ENTRY_TO_VARIANTS[args.entry]
    attack_result = run_scenario(attack_id, args.model)
    baseline_result = run_scenario(baseline_id, args.model)

    output = {
        "entry": args.entry,
        "model": args.model,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "attack": attack_result,
        "baseline": baseline_result,
        "amplification_factor": {
            m: (attack_result[m] / baseline_result[m] if baseline_result[m] else None)
            for m in RATIO_METRICS
        },
        "fanout": {
            "attack_subagent_calls": attack_result["subagent_call_count"],
            "baseline_subagent_calls": baseline_result["subagent_call_count"],
            "attack_max_depth": attack_result["max_depth_reached"],
            "baseline_max_depth": baseline_result["max_depth_reached"],
            "attack_depth_cap_hit": attack_result["depth_cap_hit"],
        },
    }

    EXPERIMENTS_DIR.mkdir(exist_ok=True)
    out_path = EXPERIMENTS_DIR / f"{args.entry}_{safe_model_slug(args.model)}_{int(datetime.now().timestamp())}.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))
    print(f"\nWritten to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
