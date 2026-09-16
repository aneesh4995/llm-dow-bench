"""
defenses/ -- candidate DoW defense implementations (CLAUDE.md S5 step 6,
S7 directory layout, RQ3). See defenses/base.py for the shared Defense /
RunningState / Verdict interface every defense here implements, and each
submodule's own docstring for that defense's specific design rationale and
open calibration/evaluation items.

STATUS (2026-09-14): scaffold only, wired into benchmark/domain_a/tools.py
and benchmark/domain_b/tools.py via an optional `defense` argument that
defaults to NullDefense (no behavior change to existing trials). None of
these has been run against attacks/corpus/ yet -- see each module's
docstring and CLAUDE.md S10.2 before citing any number from this code.
"""

from defenses.base import Defense, NullDefense, RunningState, Verdict
from defenses.budget import HardBudgetDefense
from defenses.capability_broker import CapabilityBroker
from defenses.circuit_breaker import CostAwareCircuitBreaker
from defenses.intent_judge import IntentConsistencyJudge

__all__ = [
    "Defense",
    "NullDefense",
    "RunningState",
    "Verdict",
    "HardBudgetDefense",
    "CapabilityBroker",
    "CostAwareCircuitBreaker",
    "IntentConsistencyJudge",
]
