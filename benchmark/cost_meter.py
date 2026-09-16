"""
Cost-metering instrumentation for the LLM-DoW-Bench harness.

Rather than a LangChain callback handler (version-fragile across LangChain
releases), this measures cost post-hoc from the final LangGraph message-list
state: every AIMessage carries `usage_metadata` (input_tokens, output_tokens)
per LLM call, and every ToolMessage marks one tool invocation. This gives an
exact per-run reconstruction of token count, tool-call count, and (via
pricing.py) dollar cost, plus wall-clock time measured around the invoke.

Sub-agent fan-out depth/breadth (needed for Domain B, threat-model.md §8.2)
is not implemented here — Domain A (this module's target) is single-agent
per CLAUDE.md §4/§8. Extend this module when Domain B's harness is built.
"""

import time
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from benchmark.pricing import DEFAULT_MODEL, dollar_cost


@dataclass
class RunCost:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    llm_call_count: int = 0
    tool_call_count: int = 0
    tool_calls_by_name: dict[str, int] = field(default_factory=dict)
    wall_clock_seconds: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def dollar_cost(self) -> float:
        return dollar_cost(self.model, self.input_tokens, self.output_tokens)

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "llm_call_count": self.llm_call_count,
            "tool_call_count": self.tool_call_count,
            "tool_calls_by_name": self.tool_calls_by_name,
            "wall_clock_seconds": round(self.wall_clock_seconds, 3),
            "dollar_cost_usd": round(self.dollar_cost, 6),
        }


def meter_messages(messages: list[BaseMessage], model: str = DEFAULT_MODEL) -> RunCost:
    cost = RunCost(model=model)
    for msg in messages:
        if isinstance(msg, AIMessage):
            usage = getattr(msg, "usage_metadata", None) or {}
            cost.input_tokens += usage.get("input_tokens", 0)
            cost.output_tokens += usage.get("output_tokens", 0)
            cost.llm_call_count += 1
            for tc in getattr(msg, "tool_calls", None) or []:
                name = tc.get("name", "unknown")
                cost.tool_calls_by_name[name] = cost.tool_calls_by_name.get(name, 0) + 1
                cost.tool_call_count += 1
        elif isinstance(msg, ToolMessage):
            pass  # tool_call_count already attributed from the AIMessage's tool_calls
    return cost


class Stopwatch:
    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed = time.perf_counter() - self._start


def run_and_meter(graph, initial_state: dict, model: str = DEFAULT_MODEL) -> tuple[dict, RunCost]:
    """Invoke a compiled LangGraph graph, metering cost from the resulting messages."""
    with Stopwatch() as sw:
        final_state = graph.invoke(initial_state)
    cost = meter_messages(final_state["messages"], model=model)
    cost.wall_clock_seconds = sw.elapsed
    return final_state, cost
