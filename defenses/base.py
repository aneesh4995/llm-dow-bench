"""
Base interfaces for LLM-DoW-Bench defense evaluation (RQ3, CLAUDE.md S3 /
S5 step 6).

Every defense here is a pre-tool-call gate: given the running cost/
trajectory state of the current agent run (RunningState) and the tool call
the agent is about to make, it returns a Verdict (allow, or block with a
reason). This mirrors the existing MAX_SUBAGENT_DEPTH safety-valve pattern
already in domain_b/tools.py (a hard cap that returns an explanatory
tool-result string instead of executing) rather than raising an exception --
a blocked call should look, to the agent, like a tool that declined to run,
not a harness crash, so the agent's own behavior after being blocked (give
up? retry differently? complete with what it has?) is itself observable
data, not lost to a stack trace.

No new instrumentation is required: RunningState is populated entirely from
data the harness already computes (SimulatedCostLedger in domain_a/tools.py,
DelegationLedger in domain_b/tools.py, pricing.dollar_cost). See
domain_a/tools.py and domain_b/tools.py for the wiring -- both accept an
optional `defense` argument that defaults to NullDefense, so passing nothing
reproduces this project's existing (pre-defense) baseline/attack trial
behavior exactly.

STATUS (2026-09-14): scaffold only. No defense here has been run against the
attack corpus yet -- see CLAUDE.md S5 step 6 / S10.2 (data-integrity rules).
Do not cite any attack-resistance or false-positive number for these
defenses until a real experiments/ run produces one.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RunningState:
    """Live trajectory state visible to a defense's check_tool_call() call,
    threaded through as one mutable object shared by every tool in a single
    top-level run (and, for Domain B, shared across every sub-agent spawned
    from it -- the same object DelegationLedger already aggregates into).
    Tool wrappers update this immediately before calling the defense, so a
    defense always sees state that includes the call it is about to decide
    on (tool_call_count, tool_calls_by_name), but cost fields
    (dollar_cost_usd, subagent_call_count, max_depth_reached) reflect
    everything *completed* so far, not the pending call -- a defense cannot
    see the cost of the call it hasn't allowed yet, only what led up to it.
    """

    task_prompt: str = ""
    tool_call_count: int = 0
    tool_calls_by_name: dict = field(default_factory=dict)
    dollar_cost_usd: float = 0.0
    subagent_call_count: int = 0
    max_depth_reached: int = 0
    elapsed_seconds: float = 0.0
    blocked_calls: list = field(default_factory=list)

    def note_call(self, tool_name: str) -> None:
        self.tool_call_count += 1
        self.tool_calls_by_name[tool_name] = self.tool_calls_by_name.get(tool_name, 0) + 1

    def note_block(self, tool_name: str, reason: str) -> None:
        self.blocked_calls.append({"tool": tool_name, "reason": reason})


@dataclass
class Verdict:
    allowed: bool
    reason: str = ""

    @classmethod
    def allow(cls) -> "Verdict":
        return cls(allowed=True)

    @classmethod
    def block(cls, reason: str) -> "Verdict":
        return cls(allowed=False, reason=reason)


class Defense:
    """Base class. Subclasses override check_tool_call(); wiring into
    tools.py (calling it, handling the Verdict) is identical across every
    defense, so that part lives once in domain_a/tools.py and
    domain_b/tools.py rather than being reimplemented per defense."""

    name = "base"

    def check_tool_call(self, tool_name: str, tool_args: dict, state: RunningState) -> Verdict:
        return Verdict.allow()


class NullDefense(Defense):
    """No-op defense -- this project's existing (pre-defense-evaluation)
    behavior. This is the default everywhere in domain_a/tools.py and
    domain_b/tools.py, so importing this module and threading `defense`
    through cannot silently change any already-collected baseline/attack
    trial result (CLAUDE.md S10.2)."""

    name = "none"
