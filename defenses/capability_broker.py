"""
Defense #3: capability broker gating specific expensive tools.

Distinct from HardBudgetDefense (which caps aggregate cost/call count
regardless of *which* tool is being called) and CostAwareCircuitBreaker
(which looks at call *pattern*): this defense maintains a per-tool quota
for a named allowlist of "expensive" or "high-leverage" tools -- the ones a
domain's own design already marks as the cost-amplification lever for a
given vector (run_sentiment_deep_analysis for V3 in Domain A;
delegate_subagent for V2/V6 in Domain B) -- and blocks once that specific
tool's quota is exhausted, leaving every other (non-listed) tool
unrestricted.

This is the defense family closest to what the dissertation project (see
CLAUDE.md's "HARD REQUIREMENT: NO OVERLAP" block) calls a Capability Broker
/ Runtime Policy Engine -- and per that same hard requirement, this
implementation must stay narrowly cost/budget-scoped (a per-tool call
quota) rather than reproducing that project's unauthorized-action-gating
architecture. It is cited in Related Work (main.tex, via CaMeL and similar
capability-broker literature) as a pre-existing defense *category* this
project evaluates for cost, not as this project's own architectural
invention.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from defenses.base import Defense, RunningState, Verdict


@dataclass
class CapabilityBroker(Defense):
    name: str = "capability_broker"
    # tool_name -> max number of times it may be called in one top-level run.
    quotas: dict = field(default_factory=dict)

    def check_tool_call(self, tool_name: str, tool_args: dict, state: RunningState) -> Verdict:
        cap = self.quotas.get(tool_name)
        if cap is None:
            return Verdict.allow()
        # state.note_call() already ran for this call before check_tool_call()
        # is invoked (see domain_a/tools.py, domain_b/tools.py), so
        # called_so_far here INCLUDES the call currently being decided --
        # a quota of N must therefore allow called_so_far up to and
        # including N, and only block once called_so_far exceeds N.
        called_so_far = state.tool_calls_by_name.get(tool_name, 0)
        if called_so_far > cap:
            return Verdict.block(
                f"capability_broker: {tool_name!r} quota of {cap} call(s) "
                f"per run exceeded (this is call number {called_so_far})"
            )
        return Verdict.allow()
