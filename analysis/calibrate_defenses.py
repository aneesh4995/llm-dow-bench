"""
Defense threshold calibration -- CLAUDE.md S5 step 6 / S11 (defenses/
scaffold, 2026-09-14).

This is NOT a held-out calibration protocol in the strict train/test sense:
it computes threshold candidates from the same baseline (legitimate-task)
trial data already reported as the "baseline" condition in the paper's
Evaluation section (experiments/trials_*.json, 5 trials per scenario per
model, collected 2026-09-13/14). That data was NOT collected specifically
for calibration and is reused here rather than a freshly-collected,
independent legitimate-task set. This is a real limitation, disclosed
explicitly rather than glossed over -- see the "LIMITATION" note at the
bottom of this file's output. It is still a materially better source than
either of the two rejected options in defenses/budget.py's docstring
(attack-condition data, or a single arbitrary run): it uses n=5 real trials
per scenario per model, actual legitimate-task behavior, not a guess.

Usage:
    python -m analysis.calibrate_defenses

Writes analysis/calibration_report.json (full numbers) and prints a summary
table. No number here is fabricated -- every value is computed directly
from experiments/trials_*.json.
"""

import json
import math
import statistics
from pathlib import Path

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"
OUT_PATH = Path(__file__).resolve().parent / "calibration_report.json"

DOMAIN_A_ENTRIES = ["A1", "A2", "A3"]  # A4 has no baseline twin (metric_type: absolute) -- excluded
DOMAIN_B_ENTRIES = ["B1", "B2"]


def _load_all_trials(prefix: str) -> list[dict]:
    # IMPORTANT: experiments/ contains stale pre-fix trial batches from
    # 2026-08-30 (before the 2026-09-03 Domain B delegation-instrumentation
    # fix, and before the switch to OpenRouter model slugs) alongside the
    # current, valid 5-trial batches from 2026-09-13/14. The pre-fix batches
    # use bare model names (no "/") and, for Domain B specifically, carry
    # the known 0-delegation bug -- including them here silently corrupts
    # calibration (confirmed: an unfiltered first pass showed a B1 baseline
    # subagent_call_count minimum of 0, which is impossible post-fix given
    # the top-level agent cannot read a source without delegating). Filter
    # to OpenRouter-slug models (model string contains "/") only -- this is
    # a reliable proxy for "collected after both fixes" since the switch to
    # OpenRouter slugs happened at the same time as the Domain B fix
    # (CLAUDE.md S11, 2026-09-03).
    out = []
    for f in sorted(EXPERIMENTS_DIR.glob(f"trials_{prefix}_*.json")):
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        if "per_trial" not in d:
            continue
        if "/" not in d.get("model", ""):
            continue  # stale pre-fix / pre-OpenRouter batch, excluded
        out.append(d)
    return out


def calibrate_domain_a(entry: str) -> dict:
    runs = _load_all_trials(entry)
    tool_calls = []
    dollar_costs = []
    for run in runs:
        for t in run.get("per_trial", []):
            b = t.get("baseline")
            if b is None:
                continue
            tool_calls.append(b["tool_call_count"])
            dollar_costs.append(b["total_cost_usd"])
    if not tool_calls:
        return {"entry": entry, "n": 0, "note": "no baseline trial data found"}
    return {
        "entry": entry,
        "n": len(tool_calls),
        "n_models": len({r["model"] for r in runs}),
        "tool_call_count": _stats_and_threshold(tool_calls, is_count=True),
        "dollar_cost_usd": _stats_and_threshold(dollar_costs, is_count=False),
    }


def calibrate_domain_b(entry: str) -> dict:
    runs = _load_all_trials(entry)
    subagent_calls = []
    dollar_costs = []
    for run in runs:
        for t in run.get("per_trial", []):
            b = t.get("baseline")
            if b is None:
                continue
            subagent_calls.append(b["subagent_call_count"])
            dollar_costs.append(b["total_cost_usd"])
    if not subagent_calls:
        return {"entry": entry, "n": 0, "note": "no baseline trial data found"}
    return {
        "entry": entry,
        "n": len(subagent_calls),
        "n_models": len({r["model"] for r in runs}),
        "subagent_call_count": _stats_and_threshold(subagent_calls, is_count=True),
        "dollar_cost_usd": _stats_and_threshold(dollar_costs, is_count=False),
    }


def _stats_and_threshold(values: list[float], is_count: bool = True) -> dict:
    mean = statistics.mean(values)
    std = statistics.pstdev(values) if len(values) > 1 else 0.0
    vmax = max(values)
    vmin = min(values)
    # Two threshold candidates, both computed directly from real data --
    # neither is a guess:
    #   mean_plus_3std: standard "well outside normal legitimate variance"
    #     rule; degenerates to just above vmax when std is small/zero
    #     (as it is for perfectly stable metrics like B1/B2 subagent counts).
    #   max_times_1_5: a simpler, more conservative multiplicative margin
    #     over the single worst observed legitimate run, useful when the
    #     legitimate-condition distribution is small-n / low-variance and
    #     mean+3std would sit implausibly close to vmax.
    # is_count controls rounding only: integer-valued metrics (tool_call_count,
    # subagent_call_count) round UP to the next whole call via math.ceil, since
    # a defense can only allow a whole number of calls. Dollar-cost thresholds
    # are NOT integer-rounded -- every observed dollar_cost_usd value here is
    # well under .00 (simulated-tool-cost-free trials), so math.ceil would
    # collapse every dollar threshold to a uselessly loose "" regardless of
    # the real underlying spread. Round to 6 decimal places instead, matching
    # the precision cost_meter.py already uses for dollar figures.
    raw_mean_plus_3std = mean + 3 * std
    raw_max_times_1_5 = vmax * 1.5
    if is_count:
        threshold_mean_plus_3std = math.ceil(raw_mean_plus_3std)
        threshold_max_times_1_5 = math.ceil(raw_max_times_1_5)
    else:
        threshold_mean_plus_3std = round(raw_mean_plus_3std, 6)
        threshold_max_times_1_5 = round(raw_max_times_1_5, 6)
    return {
        "mean": round(mean, 6),
        "std": round(std, 6),
        "min": round(vmin, 6),
        "max": round(vmax, 6),
        "threshold_mean_plus_3std": threshold_mean_plus_3std,
        "threshold_max_times_1_5": threshold_max_times_1_5,
        "recommended_threshold": max(threshold_mean_plus_3std, threshold_max_times_1_5),
    }


def main():
    report = {
        "generated_from": "experiments/trials_*.json baseline condition, all models, n=5 trials each",
        "limitation": (
            "This is the SAME baseline data already reported as the legitimate "
            "condition in the paper's Evaluation section, not an independently "
            "collected held-out calibration set. Thresholds calibrated here are "
            "therefore not free of look-ahead relative to what the paper already "
            "reports as baseline cost -- a genuinely independent legitimate-task "
            "set (new scenarios, or the same scenarios re-run separately) would "
            "be the methodologically cleaner version of this step. Documented "
            "here rather than glossed over -- see CLAUDE.md S11 (2026-09-14)."
        ),
        "domain_a": {e: calibrate_domain_a(e) for e in DOMAIN_A_ENTRIES},
        "domain_b": {e: calibrate_domain_b(e) for e in DOMAIN_B_ENTRIES},
    }
    OUT_PATH.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"\nWritten to {OUT_PATH}")


if __name__ == "__main__":
    main()
