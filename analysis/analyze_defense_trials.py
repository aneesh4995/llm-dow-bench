"""
Analysis of the defense-evaluation trial batch (CLAUDE.md S5 step 6 / S11,
2026-09-14/15). Reads experiments/defense_trials_*.json, keeps only the n=5
full-batch file per (entry, model, defense) combo -- discarding the n=2
sanity-check duplicates -- and reports, per CLAUDE.md's own requirement,
BOTH attack-resistance and utility cost (false positives) together, never
attack-resistance alone.

Usage:
    python -m analysis.analyze_defense_trials
"""

import json
import statistics
from collections import defaultdict
from pathlib import Path

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"
OUT_PATH = Path(__file__).resolve().parent / "defense_trials_report.json"


def load_deduped():
    by_key = {}
    for f in sorted(EXPERIMENTS_DIR.glob("defense_trials_*.json")):
        d = json.loads(f.read_text())
        key = (d["entry"], d["model"], d["defense"])
        # Prefer the n=5 (real) batch over the n=2 sanity-check batch; if
        # somehow two n=5 files exist, prefer the later run_at.
        if key not in by_key or (d["trials"], d["run_at"]) > (by_key[key]["trials"], by_key[key]["run_at"]):
            by_key[key] = d
    return by_key


def main():
    by_key = load_deduped()
    print(f"{len(by_key)} unique (entry, model, defense) combos after dedup\n")

    rows = []
    for (entry, model, defense), d in sorted(by_key.items()):
        if d["trials"] != 5:
            print(f"SKIPPING {entry}/{model}/{defense}: only {d['trials']} trials (not the full n=5 batch)")
            continue

        attack_blocked = [t["attack"]["blocked_call_count"] for t in d["per_trial"]]
        baseline_blocked = [t["baseline"]["blocked_call_count"] for t in d["per_trial"]]
        amps = [t["amplification_factor_under_defense"] for t in d["per_trial"] if t["amplification_factor_under_defense"] is not None]

        n_trials_with_attack_block = sum(1 for b in attack_blocked if b > 0)
        n_trials_with_baseline_block = sum(1 for b in baseline_blocked if b > 0)

        row = {
            "entry": entry,
            "model": model,
            "defense": defense,
            "n_trials": d["trials"],
            "attack_cost_mean": d["attack_cost_usd_stats"]["mean"],
            "baseline_cost_mean": d["baseline_cost_usd_stats"]["mean"],
            "amplification_under_defense_mean": statistics.mean(amps) if amps else None,
            "attack_blocked_any_rate": n_trials_with_attack_block / d["trials"],
            "baseline_blocked_any_rate": n_trials_with_baseline_block / d["trials"],  # false-positive rate
            "attack_blocked_total_calls": sum(attack_blocked),
            "baseline_blocked_total_calls": sum(baseline_blocked),
        }
        rows.append(row)

    OUT_PATH.write_text(json.dumps(rows, indent=2))

    # Print a compact table, defense by defense.
    for defense in ["hard_budget", "intent_judge"]:
        print(f"\n=== {defense} ===")
        print(f"{'entry':6}{'model':32}{'amp_w/def':11}{'atk_block%':12}{'FALSE-POS%':12}")
        for row in rows:
            if row["defense"] != defense:
                continue
            amp = row["amplification_under_defense_mean"]
            amp_s = f"{amp:.2f}" if amp is not None else "n/a"
            print(
                f"{row['entry']:6}{row['model']:32}{amp_s:11}"
                f"{row['attack_blocked_any_rate']*100:11.0f}%"
                f"{row['baseline_blocked_any_rate']*100:11.0f}%"
            )

    # Aggregate false-positive rate per defense, across everything -- the
    # single most important number for whether either defense is usable.
    for defense in ["hard_budget", "intent_judge"]:
        d_rows = [r for r in rows if r["defense"] == defense]
        fp_rate = statistics.mean(r["baseline_blocked_any_rate"] for r in d_rows)
        atk_block_rate = statistics.mean(r["attack_blocked_any_rate"] for r in d_rows)
        print(f"\n{defense}: mean false-positive rate (baseline trials with >=1 block) = {fp_rate*100:.1f}%")
        print(f"{defense}: mean attack-trial block rate (attack trials with >=1 block) = {atk_block_rate*100:.1f}%")

    print(f"\nWritten to {OUT_PATH}")


if __name__ == "__main__":
    main()
