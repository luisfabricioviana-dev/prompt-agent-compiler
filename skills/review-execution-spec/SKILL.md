---
name: review-execution-spec
description: Independently review an ExecutionSpecV2 and its produced artifacts against quality gates, artifact contracts, regression targets, constraints, and evidence before approval.
---

# Review Execution Spec

Use this skill when an execution plan or completed run needs independent verification before it can be approved.

The reviewer must not treat the executor's own success claim as sufficient evidence.

## Inputs

- `ExecutionSpecV2`;
- produced artifacts governed by each `ArtifactContract`;
- execution trace and node outcomes;
- quality gates;
- verification evidence;
- regression targets;
- original constraints and assumptions.

## Review procedure

1. Confirm the objective and success definition still match the original request.
2. Check every blocking quality gate using its required evidence.
3. Validate each produced artifact against its `ArtifactContract`.
4. Confirm prerequisites, stop conditions, and failure routes were respected.
5. Re-run or inspect the specified verification plan when practical.
6. Check that constraints, preservation requirements, and evidence boundaries were not weakened.
7. For high-risk, subjective, externally published, security, legal, regulatory, or weakly verifiable work, require independent review rather than self-approval.
8. Record unsupported assumptions, regressions, missing evidence, and downstream contamination explicitly.

## Decision

Return exactly one review state:

- `PASS` — every blocking gate passes and required evidence is present;
- `FAIL` — at least one blocking gate fails, required evidence is missing, or a material artifact contract is violated.

A FAIL result must identify failed gates, supporting evidence, likely root cause, required repairs, and the targeted reverification scope.

Do not approve merely because the executor completed all nodes.
