"""
Reproduce this paper's Table 2 (vector cost-amplification), Table 3 (delegation
counts), and Table 4 (defense evaluation) directly from the raw trial logs in
experiments/.

Why this script exists: experiments/ contains every trial run captured during
development, including pre-bugfix re-runs (see git history, e.g. the
intent_judge fix for B1/B2 delegation trajectories). Naively aggregating every
matching file in experiments/ double-counts stale runs and produces incorrect
statistics -- in particular it inflates the intent_judge false-positive rate on
B1/B2 by roughly 13x. The correct aggregation uses only the latest-timestamped
run per (entry, defense, model) combination for the defense-trial files, and
the single canonical combined file per domain for the vector/delegation tables.
This script encodes that logic so results are reproducible without tribal
knowledge of which files are current.

Usage: python3 analysis/build_paper_tables.py
Run from the repo root, or pass --experiments-dir explicitly.
"""
import argparse
import glob
import json
import math
import os
import re
import statistics


def load_combined(path):
    with open(path) as f:
        return json.load(f)


def table2_and_3(experiments_dir):
    dA = load_combined(os.path.join(experiments_dir, "trials_combined_1789341103.json"))
    dB = load_combined(os.path.join(experiments_dir, "trials_combined_b_1789343694.json"))

    by_entry = {}
    for r in dA["results"] + dB["results"]:
        e = r["entry"]
        by_entry.setdefault(e, [])
        for t in r["per_trial"]:
            af = t.get("amplification_factor")
            if af is None:
                continue
            by_entry[e].append(af["total_cost_usd"])

    print("Table 2 -- cost-amplification factor by vector (n=30 per vector)")
    print(f"{'Entry':6}{'n':4}{'Mean':8}{'SD':8}{'95% CI':20}{'Min':8}{'Max':8}")
    for e in ["A1", "A2", "A3", "B1", "B2"]:
        vals = by_entry.get(e, [])
        n = len(vals)
        mean = statistics.mean(vals)
        sd = statistics.stdev(vals) if n > 1 else 0.0
        se = sd / math.sqrt(n)
        lo, hi = mean - 1.96 * se, mean + 1.96 * se
        print(f"{e:6}{n:<4}{mean:<8.2f}{sd:<8.2f}[{lo:.2f}, {hi:.2f}]{'':4}{min(vals):<8.2f}{max(vals):<8.2f}")

    models = [
        "anthropic/claude-opus-5", "anthropic/claude-sonnet-4.6", "anthropic/claude-sonnet-5",
        "openai/gpt-5.5", "openai/gpt-5.6-luna", "openai/gpt-5.6-terra",
    ]
    table = {}
    for r in dB["results"]:
        e, m = r["entry"], r["model"]
        atk = [t["attack"]["subagent_call_count"] for t in r["per_trial"]]
        base = [t["baseline"]["subagent_call_count"] for t in r["per_trial"]]
        table.setdefault(m, {})[e] = (statistics.mean(atk), statistics.mean(base))

    print("\nTable 3 -- sub-agent delegation count, mean over 5 trials")
    print(f"{'Model':28}{'B1 Atk':8}{'B1 Base':9}{'B2 Atk':8}{'B2 Base':8}")
    for m in models:
        b1a, b1b = table[m]["B1"]
        b2a, b2b = table[m]["B2"]
        print(f"{m:28}{b1a:<8.1f}{b1b:<9.1f}{b2a:<8.1f}{b2b:<8.1f}")


def latest_per_model(experiments_dir, entry, defense):
    """Only the most recent (highest-timestamp) file per model survives --
    this is what filters out pre-bugfix re-runs."""
    pattern = os.path.join(experiments_dir, f"defense_trials_{entry}_{defense}_*.json")
    by_model = {}
    for f in glob.glob(pattern):
        m = re.match(rf".*defense_trials_{entry}_{defense}_(.+)_(\d+)\.json", f)
        model, ts = m.group(1), int(m.group(2))
        if model not in by_model or ts > by_model[model][1]:
            by_model[model] = (f, ts)
    return [f for f, _ts in by_model.values()]


def table4(experiments_dir):
    print("\nTable 4 -- defense evaluation (attack-block rate, false-positive rate, mean amplification)")
    print(f"{'Entry':8}{'Defense':14}{'AtkBlock%':11}{'FPrate%':9}{'MeanAmp':8}{'n':4}")
    pooled = {"hard_budget": [0, 0, 0], "intent_judge": [0, 0, 0]}
    for entry in ["A1", "A2", "A3", "B1", "B2"]:
        for defense in ["hard_budget", "intent_judge"]:
            files = latest_per_model(experiments_dir, entry, defense)
            trials = []
            for f in files:
                trials.extend(load_combined(f)["per_trial"])
            n = len(trials)
            atk_blocked = sum(1 for t in trials if t["attack"]["blocked_call_count"] > 0)
            base_blocked = sum(1 for t in trials if t["baseline"]["blocked_call_count"] > 0)
            amps = [t["amplification_factor_under_defense"] for t in trials]
            mean_amp = statistics.mean(amps) if amps else float("nan")
            print(f"{entry:8}{defense:14}{100*atk_blocked/n:<11.1f}{100*base_blocked/n:<9.1f}{mean_amp:<8.2f}{n:<4}")
            p = pooled[defense]
            p[0] += atk_blocked
            p[1] += base_blocked
            p[2] += n

    print()
    for defense in ["hard_budget", "intent_judge"]:
        a, b, n = pooled[defense]
        print(f"Pooled mean  {defense:14}{100*a/n:<11.1f}{100*b/n:<9.1f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiments-dir", default="experiments")
    args = parser.parse_args()
    table2_and_3(args.experiments_dir)
    table4(args.experiments_dir)
