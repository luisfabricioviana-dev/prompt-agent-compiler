# PROMPT & AGENT COMPILER

> Status: **v0.2.10 RECONCILIATION CANDIDATE**

The current reconciliation branch validates the authentic recovered v0.2.9 compiler baseline and the Governed Factory + REA candidate line in one fail-closed CI workflow.

See `docs/V0.2.10_RECONCILIATION.md` and `VERSION_MANIFEST_v0_2_10.json`.

This repository reconstructs the previously documented v0.2.8 baseline of the PROMPT & AGENT COMPILER so that future changes can be versioned, tested, and reviewed in GitHub.

The reconstruction is intentionally explicit: historical test counts are treated as **targets**, not as re-verified facts, until the reconstructed suite is executed again.

## v0.2.8 reconstructed architecture

`REQUEST → Semantic Interpreter → provider/grounding boundary → semantic contract validator → NormalizedTask → deterministic Policy Router → ExecutionSpec`

The reconstructed baseline also includes:

- causal failure taxonomy;
- minimal-scope Repair Router;
- RecordedSemanticProvider for deterministic replay;
- Model Eval Runner interfaces;
- mutation-oriented regression helpers.

## Historical verification targets

The following numbers were documented for the lost/original v0.2.8 implementation and are preserved here only as regression targets:

- 75 tests;
- 31 semantic end-to-end cases;
- 9 mutation-taxonomy cases;
- 20 valid JSON artifacts;
- `compileall` PASS.

They must not be reported as passing for this reconstructed repository until freshly executed.

## Governance

- `NEW TUTORIAL ≠ NEW TOP-LEVEL RULE`
- `PRODUCT STATE ≠ ARCHITECTURAL TRUTH`
- `SHARED MECHANISM ≠ SHARED DOMAIN MEMORY`
- `ONE FAILURE → FIXTURE FIRST → RULE ONLY IF GENERALIZABLE`
- `GOOD PROMPT ≠ RELIABLE SYSTEM`


## Reconciliation safety note

The recovered v0.2.9 source is materialized under `recovered_v0_2_9/` without the blind holdout. The v0.2.9 holdout is retired; future generalization evaluation requires a new private unseen set.
