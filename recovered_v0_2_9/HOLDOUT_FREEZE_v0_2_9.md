# HOLDOUT FREEZE — v0.2.9

`blind_holdout_v0_2_9.json` is frozen before any model-backed evaluation.

Rules:

1. Do not modify interpreter prompts, semantic policy, validator, router, thresholds, or benchmark labels after observing model predictions on this suite and continue calling it blind.
2. A single model-backed observation retires the suite for tuning purposes.
3. If repairs are made using its failures, create a new unseen holdout for the next generalization claim.
4. Missing predictions produce `INCOMPLETE`, never imputed or oracle-filled scores.
5. Promotion requires every critical gate in `promotion_gate_v0_2_9.py` to pass.
