"""
CLI entry point: run one Domain A scenario through the harness, meter its
cost, and write a raw result to experiments/. Computes cost-amplification
factor (attack / baseline) when a baseline variant exists for the entry
(A1-A3, metric_type: ratio per attacks/corpus/); A4 (metric_type: absolute)
reports its own tool-call count against the corpus entry's reference bound
instead, per attacks/corpus/domain-a-helpdesk/a4-v5-adversarial-task-framing.yaml.

Usage:
    python -m benchmark.run --entry A1
    python -m benchmark.run --entry A4
    python -m benchmark.run --entry A1 --model claude-haiku-4-5-20251001

Requires ANTHROPIC_API_KEY set in the environment. No numbers this script
prints are pre-baked — every figure comes from an actual model run, per
CLAUDE.md §9/§10.2.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from benchmark.domain_a.agent import build_agent, initial_state
from benchmark.domain_a.scenarios import SCENARIOS
from benchmark.cost_meter import run_and_meter
from benchmark.pricing import DEFAULT_MODEL, safe_model_slug

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"

ENTRY_TO_VARIANTS = {
    "A1": ("A1-attack", "A1-baseline"),
    "A2": ("A2-attack", "A2-baseline"),
    "A3": ("A3-attack", "A3-baseline"),
    "A4": ("A4-attack", None),  # absolute metric, no baseline twin
}


def run_scenario(scenario_id: str, model: str) -> dict:
    scenario = SCENARIOS[scenario_id]
    graph, ledger, _state = build_agent(scenario, model=model)  # _state: defenses/ RunningState, unused without a defense passed
    final_state, cost = run_and_meter(graph, initial_state(scenario), model=model)
    result = cost.to_dict()
    result["scenario_id"] = scenario_id
    result["corpus_entry"] = scenario.corpus_entry
    result["simulated_expensive_tool_cost_usd"] = round(ledger.total_usd, 6)
    result["total_cost_usd"] = round(cost.dollar_cost + ledger.total_usd, 6)
    result["final_message_count"] = len(final_state["messages"])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry", required=True, choices=sorted(ENTRY_TO_VARIANTS))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    load_dotenv()  # picks up .env in the repo root if present

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set (checked .env and environment). Set it and retry.", file=sys.stderr)
        sys.exit(1)

    attack_id, baseline_id = ENTRY_TO_VARIANTS[args.entry]
    attack_result = run_scenario(attack_id, args.model)

    output = {
        "entry": args.entry,
        "model": args.model,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "attack": attack_result,
    }

    if baseline_id is not None:
        baseline_result = run_scenario(baseline_id, args.model)
        output["baseline"] = baseline_result
        for metric in ("total_tokens", "tool_call_count", "wall_clock_seconds", "total_cost_usd"):
            b = baseline_result[metric]
            output.setdefault("amplification_factor", {})[metric] = (
                attack_result[metric] / b if b else None
            )
    else:
        output["metric_type"] = "absolute"
        output["note"] = (
            "No baseline twin for this entry (metric_type: absolute). Compare "
            "attack.tool_call_count / search_ticket_history call pattern against "
            "the corpus entry's reference_completion bound by hand."
        )

    EXPERIMENTS_DIR.mkdir(exist_ok=True)
    out_path = EXPERIMENTS_DIR / f"{args.entry}_{safe_model_slug(args.model)}_{int(datetime.now().timestamp())}.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))
    print(f"\nWritten to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
