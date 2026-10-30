---
name: repair-failed-run
description: Convert a failed execution or review into a causal minimum-scope repair plan and targeted reverification without restarting unaffected work.
---

# Repair Failed Run

Use this skill after a gate, artifact, node, or review failure.

## Inputs

- the failed `ExecutionSpecV2`;
- failure evidence;
- reviewer findings when available;
- affected artifacts and downstream consumers;
- the causal error classification when the failure originated in semantic interpretation, provider boundary, policy, runtime capability, or execution.

## Procedure

1. Identify the earliest causal failure. Do not assign a downstream routing symptom to the policy when the normalized semantics were already wrong.
2. Classify the failure source: interpreter, provider/grounding, semantic contract, policy, capability runtime, execution node, integration, artifact, or reviewer gate.
3. Determine the minimum repair scope:
   - `local` for an isolated artifact or node correction;
   - `node` when the complete node must rerun;
   - `downstream_branch` when invalid output contaminated dependent nodes;
   - `full_pipeline` only when the causal defect invalidates the complete execution contract.
4. Preserve approved and unaffected artifacts.
5. Apply only the repair needed to remove the causal defect.
6. Perform targeted reverification of the repaired scope and every contaminated downstream dependency.
7. Escalate scope only when new evidence proves the smaller repair is insufficient.

## Output

Return a repair plan containing the causal failure, repair owner, minimum scope, affected artifacts, exact correction, and targeted reverification steps.

Default to local repair. Never restart the full pipeline merely because one downstream gate failed.
