# Attack Corpus — LLM-DoW-Bench

**Status: design-stage. Nothing in this directory has been executed against a real agent yet.** Every entry is a specification (task, injected content or task framing, and a reference completion for scoring), not a measured result. No file here reports an attack success rate, a cost figure, or an amplification factor — that requires the benchmark harness (`benchmark/`, not yet built) to actually run these. See `CLAUDE.md` §10.2 (data integrity) before adding anything to this directory that looks like a number.

## Structure

```
attacks/corpus/
├── README.md                      (this file)
├── domain-a-helpdesk/              Domain A: single-agent helpdesk/support (threat-model.md §8.1)
│   ├── a1-v1-retry-induction.yaml
│   ├── a2-v3-expensive-tool-bait.yaml
│   ├── a3-v4-context-bloat.yaml
│   └── a4-v5-adversarial-task-framing.yaml
└── domain-b-research/               Domain B: research/analyst agent with sub-agent delegation (threat-model.md §8.2)
    ├── b1-v2-subagent-fanout.yaml
    └── b2-v6-delegation-loop.yaml
```

## Entry schema

Each `.yaml` file follows this shape:

```yaml
id:                   unique corpus entry id
domain:               A | B
primary_vector:       V1-V6 (threat-model.md §3)
secondary_vectors:    [] (other vectors this entry also exercises, if any)
capability:           C1 (tool-result content control) | C2 (task-framing control) | C1+C2
status:               design-draft   # never anything else until the harness has actually run it
task_prompt:          the (legitimate-sounding) instruction given to the agent
injected_content:     the poisoned tool-result content, if capability includes C1 (omit if C2-only)
metric_type:          ratio | absolute   # see threat-model.md §9
baseline_task:        (ratio metric only) the unpoisoned/non-adversarial twin task, for cost-amplification-factor
reference_completion: (absolute metric only, V5 entries) the authored reasonable-effort reference task
tools_involved:       which of the domain's sketch tools (threat-model.md §8.1/8.2) this entry exercises
expected_mechanism:   one or two sentences on why this should induce excess cost, as a design hypothesis
notes:                anything relevant re: dissertation no-overlap boundary, open questions, etc.
```

## Cross-check against the no-overlap hard requirement

Every entry here was checked against `CLAUDE.md`'s hard no-overlap requirement: none require the agent to take an unauthorized, destructive, or exfiltrating action to succeed. If a future entry accidentally also achieves an unauthorized action as a side effect, it must be rewritten or dropped — it belongs to the dissertation project's threat model, not this one (see `threat-model.md` §6).

## Next steps

1. Finalize exact tool interfaces for Domain A and Domain B (currently sketches in `threat-model.md` §8.1/§8.2).
2. Expand this initial 6-entry set once the benchmark harness (`benchmark/`) exists and can actually execute an entry, since implementation details (how a "sub-agent" is invoked, how a tool result is injected) will surface gaps in these specs.
3. Do not mark any entry's `status` as anything other than `design-draft` until the harness has actually run it and logged a real result in `experiments/`.
