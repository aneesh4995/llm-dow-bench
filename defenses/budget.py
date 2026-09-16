"""
Defense #1: hard per-run token/tool-call/dollar/subagent-count budget cap.

The simplest possible defense, and the one a reader is most likely to reach
for first ("why not just cap it?"). Included as a baseline comparison point
for the other three defenses, not because it is expected to be this paper's
headline result.

CALIBRATION PROBLEM (flagged explicitly in the "how do we build a good
defense model" design discussion, 2026-09-14 -- CLAUDE.md S11 session log,
S5 step 6): a hard cap is only meaningful relative to what a *legitimate*
run of the same task actually costs. Two wrong ways to set it:
  (a) From attack-condition data -- circular, since it would tautologically
      block whatever this project's own corpus happened to measure.
  (b) From a single legitimate run -- noisy, since legitimate per-scenario
      cost varies by model (main.tex's own delegation-split finding: e.g.
      baseline B2 delegation count is stable at 1 across models, but
      baseline B1 varies; see the Evaluation section's per-model tables).
The methodologically correct source is a held-out set of *legitimate* task
completions per scenario (CLAUDE.md S5 step 6: "a held-out legitimate-task
set"), giving a distribution (not a single number) to calibrate against --
e.g. a threshold at some multiple of the legitimate-condition mean or a
high percentile of it, decided and justified before this defense is run
against the attack corpus, not after.

This module does not resolve that calibration problem. It takes already-
calibrated thresholds as constructor arguments. Do not hardcode a threshold
derived from this project's own attack-condition trial data anywhere this
class is instantiated -- that is exactly the circular case above. Sourcing
real thresholds from a held-out legitimate-task calibration run is an open
item, not yet done.
"""

from __future__ import annotations

from dataclasses import dataclass

from defenses.base import Defense, RunningState, Verdict


@dataclass
class HardBudgetDefense(Defense):
    name: str = "hard_budget"
    max_tool_calls: int | None = None
    max_dollar_cost_usd: float | None = None
    max_subagent_calls: int | None = None

    def check_tool_call(self, tool_name: str, tool_args: dict, state: RunningState) -> Verdict:
        if self.max_tool_calls is not None and state.tool_call_count > self.max_tool_calls:
            return Verdict.block(
                f"hard_budget: tool_call_count {state.tool_call_count} exceeds "
                f"cap {self.max_tool_calls}"
            )
        if (
            self.max_dollar_cost_usd is not None
            and state.dollar_cost_usd > self.max_dollar_cost_usd
        ):
            return Verdict.block(
                f"hard_budget: dollar_cost_usd {state.dollar_cost_usd:.4f} exceeds "
                f"cap {self.max_dollar_cost_usd:.4f}"
            )
        if (
            self.max_subagent_calls is not None
            and tool_name == "delegate_subagent"
            and state.subagent_call_count >= self.max_subagent_calls
        ):
            return Verdict.block(
                f"hard_budget: subagent_call_count {state.subagent_call_count} "
                f"has already reached cap {self.max_subagent_calls}"
            )
        return Verdict.allow()
