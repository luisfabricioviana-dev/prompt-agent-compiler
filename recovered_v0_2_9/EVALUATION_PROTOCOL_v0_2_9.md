# Model Evaluation Protocol v0.2.9

## Purpose
Measure generalization without confusing interpreter, contract, grounding, and policy errors.

## Required sequence

```text
FROZEN COMPILER v0.2.8/0.2.9 protocol
→ unseen requests
→ model interpreter
→ save raw structured predictions
→ no edits
→ evaluate_prediction_file
→ causal error decomposition
→ promotion gate
→ retire holdout after first observation
```

## Prediction exchange
Supply one normalized prediction per case ID in `blind_holdout_v0_2_9.json`. No missing cases are scored.

## Promotion policy
Promotion is conjunctive, not an average. A model cannot compensate for poor critical-risk recall or ungrounded explicit evidence with high aggregate F1.

## Interpretation
- `provider_success_rate` and `contract_valid_rate` are boundary reliability.
- semantic group F1 / exact rate are interpreter quality.
- risk and grounding metrics are safety/traceability quality.
- `causal_policy_pass_rate` is evaluated only when semantics are exact.
- `end_to_end_pass_rate` is the user-visible system metric.

## No tuning on holdout
After predictions are observed, failures can inform a new development set, but this holdout cannot be reused for an unbiased generalization claim.
