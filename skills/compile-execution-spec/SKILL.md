---
name: compile-execution-spec
description: Compile a human request into a validated ExecutionSpecV2 using normalized semantics, explicit runtime capabilities, executable graph contracts, and fail-closed readiness.
---

# Compile Execution Spec

Use this skill when a human request must become an executable compiler contract rather than a prose-only prompt.

## Inputs

- the raw request;
- a validated `NormalizedTask` from the semantic interpreter boundary;
- the deterministic policy result from the canonical policy router;
- a runtime `CapabilityRegistry`;
- any explicit constraints, approvals, dependencies, or output requirements already known.

Do not silently infer that a capability is available from task wording, model confidence, or prior successful runs.

## Procedure

1. Validate the `NormalizedTask` before routing.
2. Preserve the policy-selected patterns, quality gates, complexity, constraints, contradictions, and evidence lineage.
3. Resolve required and optional runtime capabilities through `CapabilityRegistry`.
4. Treat an unregistered mandatory capability as `UNKNOWN_CAPABILITY`; do not silently promote it to available.
5. Build an `ExecutionSpecV2` with:
   - objective;
   - measurable success definition;
   - execution nodes and prerequisites;
   - roles;
   - ArtifactContract outputs;
   - quality gates;
   - verification plan;
   - failure routes;
   - stop conditions;
   - output contract;
   - learning trace.
6. Validate the execution graph before returning the spec.
7. Set readiness only from graph validity plus resolved runtime capability state.

## Readiness

Return one of:

- `READY` — graph valid and all mandatory capabilities available;
- `ADAPT_REQUIRED` — graph valid but at least one mandatory capability is constrained;
- `UNKNOWN_CAPABILITY` — graph valid but at least one mandatory capability is unknown;
- `BLOCKED` — a mandatory capability is unavailable;
- `INVALID` — objective, success contract, graph, artifact wiring, or other structural validation failed.

## Output

Return the complete `ExecutionSpecV2` plus a concise explanation of any non-READY state. Never replace missing runtime evidence with an optimistic assumption.
