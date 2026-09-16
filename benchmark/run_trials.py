"""
Repeated-trial runner: run each Domain A entry n times per model, capture
every per-trial cost record, and aggregate mean/std for the primary metrics
so single-run sampling noise (the n=1 caveat in CLAUDE.md's session log) can
be separated from a real effect.

Each entry runs its attack (and baseline twin, for A1-A3) n times. For ratio
entries (A1-A3) the amplification factor is computed per-trial (attack_i /
baseline_i, paired within a trial) and then aggregated. For the absolute
entry (A4) the attack cost itself is aggregated; there is no twin to divide by.

Writes one JSON per (entry, model) to experiments/, plus a combined summary.
No number here is pre-baked; every figure comes from an actual model run
(CLAUDE.md §9/§10.2).

Usage:
    python -m benchmark.run_trials --trials 5
    python -m benchmark.run_trials --trials 5 --models claude-sonnet-5 claude-opus-4-8
    python -m benchmark.run_trials --trials 5 --entries A1 A3
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
from benchmark.run import ENTRY_TO_VARIANTS, run_scenario

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"

DEFAULT_MODELS = [
    "anthropic/claude-sonnet-5",
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-opus-5",
    "openai/gpt-5.5",
    "openai/gpt-5.6-luna",
    "openai/gpt-5.6-terra",
]  # all routed through OpenRouter (llm_provider.py) -- see CLAUDE.md S11
RATIO_METRICS = ("total_tokens", "tool_call_count", "wall_clock_seconds", "total_cost_usd")


def _stats(values: list[float]) -> dict:
    """mean / std / min / max for a list of trial values (std=0 when n<2)."""
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
    is_ratio = baseline_id is not None

    per_trial = []
    for i in range(trials):
        attack = run_scenario(attack_id, model)
        rec = {"trial": i, "attack": attack}
        if is_ratio:
            baseline = run_scenario(baseline_id, model)
            rec["baseline"] = baseline
            rec["amplification_factor"] = {
                m: (attack[m] / baseline[m] if baseline[m] else None)
                for m in RATIO_METRICS
            }
        per_trial.append(rec)

    summary = {
        "entry": entry,
        "model": model,
        "trials": trials,
        "metric_type": "ratio" if is_ratio else "absolute",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "per_trial": per_trial,
    }

    if is_ratio:
        summary["amplification_factor_stats"] = {
            m: _stats([t["amplification_factor"][m] for t in per_trial
                       if t["amplification_factor"][m] is not None])
            for m in RATIO_METRICS
        }
        # Also aggregate raw attack/baseline dollar cost for absolute context.
        summary["attack_cost_usd_stats"] = _stats(
            [t["attack"]["total_cost_usd"] for t in per_trial])
        summary["baseline_cost_usd_stats"] = _stats(
            [t["baseline"]["total_cost_usd"] for t in per_trial])
    else:
        summary["attack_cost_usd_stats"] = _stats(
            [t["attack"]["total_cost_usd"] for t in per_trial])
        summary["attack_input_tokens_stats"] = _stats(
            [t["attack"]["input_tokens"] for t in per_trial])
        summary["attack_tool_call_count_stats"] = _stats(
            [t["attack"]["tool_call_count"] for t in per_trial])

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
            # Terse progress line to stderr.
            if summary["metric_type"] == "ratio":
                s = summary["amplification_factor_stats"]["total_cost_usd"]
                print(f"  {entry}/{model}: cost amp mean={s['mean']:.2f}x "
                      f"stdev={s['stdev']:.2f} (n={s['n']})", file=sys.stderr)
            else:
                s = summary["attack_cost_usd_stats"]
                t = summary["attack_input_tokens_stats"]
                print(f"  {entry}/{model}: attack ${s['mean']:.4f} "
                      f"(stdev ${s['stdev']:.4f}), input_tok mean={t['mean']:.0f}", file=sys.stderr)

    combined_path = EXPERIMENTS_DIR / f"trials_combined_{stamp}.json"
    combined_path.write_text(json.dumps(combined, indent=2))
    print(f"\nCombined summary: {combined_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
