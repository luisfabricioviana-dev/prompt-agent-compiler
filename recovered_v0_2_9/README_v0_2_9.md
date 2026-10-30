# PROMPT & AGENT COMPILER v0.2.9

## Status

**Frozen generalization protocol prepared. Model-backed blind evaluation has not been run.**

v0.2.9 builds on the causal evaluation architecture from v0.2.8 and adds:

- 60-case unseen holdout;
- immutable freeze manifest with SHA-256 hashes;
- prediction exchange format;
- incomplete-prediction protection;
- conjunctive promotion gate;
- one-shot blind evaluation runbook.

## Key files

- `blind_holdout_v0_2_9.json`
- `HOLDOUT_FREEZE_v0_2_9.md`
- `FREEZE_MANIFEST_v0_2_9.json`
- `freeze_integrity_v0_2_9.py`
- `prediction_exchange_v0_2_9.py`
- `prediction_exchange_schema_v0_2_9.json`
- `holdout_evaluator_v0_2_9.py`
- `promotion_gate_v0_2_9.py`
- `EVALUATION_PROTOCOL_v0_2_9.md`
- `EVALUATION_RUNBOOK_v0_2_9.md`
- `ARCHITECTURE_v0_2_9.md`

## Verification at package time

- 83 automated tests passed;
- Python compileall passed;
- 27 JSON artifacts parsed successfully;
- freeze integrity: 12/12 tracked files matched SHA-256;
- zero-prediction smoke test returned `INCOMPLETE`, missing 60/60 as intended.

## Scientific constraint

No claim about Semantic Interpreter generalization should be made until a complete model-backed run is recorded against the frozen holdout.
