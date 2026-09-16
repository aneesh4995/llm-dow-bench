"""
Repeated-trial runner for Domain B (B1/B2), mirroring run_trials.py's
mean/stdev aggregation for Domain A. Both entries are metric_type: ratio
(always have a baseline twin), so both get per-trial amplification factors.
Also aggregates fan-out metrics (subagent_call_count, max_depth_reached,
depth_cap_hit) across trials -- Domain B's distinguishing metrics.

Usage:
    python -m benchmark.run_trials_b --trials 5
    python -m benchmark.run_trials_b --trials 5 --models claude-opus-4-8
"""

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from benchmark.pricing import safe_model_slug
from benchmark.run_b import ENTRY_TO_VARIANTS, RATIO_METRICS, run_scenario

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"
DEFAULT_MODELS = [
    "anthropic/claude-sonnet-5",
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-opus-5",
    "openai/gpt-5.5",
    "openai/gpt-5.6-luna",
    "openai/gpt-5.6-terra",
]  # all routed through OpenRouter (llm_provider.py) -- see CLAUDE.md S11


def _stats(values: list[float]) -> dict:
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "values": values,
    }


def run_entry_trials(entry: str, model: str, trials: int) -> dict:
    attack_id, baseline_id = ENTRY_TO_VARIANTS[entry]
    per_trial = []
    for i in range(trials):
        attack = run_scenario(attack_id, model)
        baseline = run_scenario(baseline_id, model)
        amp = {m: (attack[m] / baseline[m] if baseline[m] else None) for m in RATIO_METRICS}
        per_trial.append({"trial": i, "attack": attack, "baseline": baseline, "amplification_factor": amp})

    summary = {
        "entry": entry,
        "model": model,
        "trials": trials,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "per_trial": per_trial,
        "amplification_factor_stats": {
            m: _stats([t["amplification_factor"][m] for t in per_trial if t["amplification_factor"][m] is not None])
            for m in RATIO_METRICS
        },
        "attack_subagent_calls_stats": _stats([t["attack"]["subagent_call_count"] for t in per_trial]),
        "baseline_subagent_calls_stats": _stats([t["baseline"]["subagent_call_count"] for t in per_trial]),
        "attack_max_depth_stats": _stats([t["attack"]["max_depth_reached"] for t in per_trial]),
        "attack_depth_cap_hit_count": sum(1 for t in per_trial if t["attack"]["depth_cap_hit"]),
    }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--entries", nargs="+", default=sorted(ENTRY_TO_VARIANTS))
    args = parser.parse_args()

    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set (checked .env and environment). Set it and retry.", file=sys.stderr)
        sys.exit(1)

    EXPERIMENTS_DIR.mkdir(exist_ok=True)
    stamp = int(datetime.now().timestamp())
    combined = {"trials": args.trials, "run_at": datetime.now(timezone.utc).isoformat(), "results": []}

    for model in args.models:
        for entry in args.entries:
            print(f"[running] {entry} x{args.trials} on {model} ...", file=sys.stderr)
            summary = run_entry_trials(entry, model, args.trials)
            out_path = EXPERIMENTS_DIR / f"trials_{entry}_{safe_model_slug(model)}_{stamp}.json"
            out_path.write_text(json.dumps(summary, indent=2))
            combined["results"].append(summary)
            s = summary["amplification_factor_stats"]["total_cost_usd"]
            sc = summary["attack_subagent_calls_stats"]
            bc = summary["baseline_subagent_calls_stats"]
            print(f"  {entry}/{model}: cost amp mean={s['mean']:.2f}x stdev={s['stdev']:.2f} "
                  f"(n={s['n']}) | subagent_calls attack={sc['mean']:.1f} baseline={bc['mean']:.1f} "
                  f"| depth_cap_hit={summary['attack_depth_cap_hit_count']}/{args.trials}", file=sys.stderr)

    combined_path = EXPERIMENTS_DIR / f"trials_combined_b_{stamp}.json"
    combined_path.write_text(json.dumps(combined, indent=2))
    print(f"\nCombined summary: {combined_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
