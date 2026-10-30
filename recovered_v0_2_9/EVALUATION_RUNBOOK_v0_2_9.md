# Evaluation Runbook v0.2.9

## 1. Verify the frozen state

```bash
python freeze_integrity_v0_2_9.py
```

Proceed only if `valid: true`.

## 2. Generate model interpretations

For every case in `blind_holdout_v0_2_9.json`, run the frozen Semantic Interpreter and save the resulting normalized JSON under the case ID.

Expected file shape:

```json
{
  "H001": {
    "raw_request": "...",
    "actions": ["CREATE"],
    "preservation": [],
    "performance_dimensions": [],
    "evidence_policy": [],
    "ui_requirements": ["UI"],
    "architecture": [],
    "external_state": [],
    "execution": [],
    "capabilities": [],
    "risks": {},
    "feature_evidence": {},
    "unknowns": [],
    "contradictions": []
  }
}
```

Do not edit outputs after looking at benchmark labels.

## 3. Evaluate once

```bash
python holdout_evaluator_v0_2_9.py model_predictions.json \
  --out holdout_eval_result_v0_2_9.json
```

If any case is missing, the status is `INCOMPLETE` and no benchmark score is produced.

## 4. Read causal failures

Inspect:

- semantic interpreter errors;
- provider/grounding errors;
- contract errors;
- policy errors only when semantics are exact;
- promotion-gate failures.

## 5. Retire the holdout

After the first complete model-backed observation, mark the suite as observed/retired for tuning. Do not rerun a repaired interpreter and describe the result as blind generalization.

## 6. Repair correctly

```text
Interpreter error → new DEVELOPMENT cases → repair Interpreter
Boundary error    → repair Provider / Contract
Policy error      → new DEVELOPMENT cases → repair Policy
```

Then freeze the repaired compiler and create a completely new holdout.
