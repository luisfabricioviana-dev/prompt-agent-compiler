---
name: evaluate-compiler
description: Evaluate semantic interpretation, policy routing, capabilities, and end-to-end compiler behavior with separated development and blind-holdout evidence and a conjunctive promotion gate.
---

# Evaluate Compiler

Use this skill to measure compiler quality without mixing development tuning with generalization evidence.

## Dataset identity

Every fixture and prediction must carry a stable `case_id`. Do not use request text as the sole replay identity.

Separate:

- development/golden fixtures, which may guide repairs;
- oracle fixtures, which test downstream policy with correct semantics;
- mutation fixtures, which test known failure classes;
- blind holdout fixtures, which are reserved for one unseen evaluation.

Never use a blind holdout for tuning, prompt editing, policy editing, threshold calibration, or fixture-driven repair after its content has been observed.

## Evaluation stages

Measure separately:

1. request → `NormalizedTask` for INTERPRETER quality;
2. provider/grounding and semantic-contract validity;
3. correct `NormalizedTask` → policy route for POLICY quality;
4. capability resolution and runtime readiness;
5. request → final execution contract for end-to-end quality.

When semantics are wrong, downstream pattern/gate/complexity differences may be recorded as observations but must not be attributed causally to POLICY.

## Required metrics

At minimum record provider success, contract validity, semantic exactness or group metrics, critical-risk recall, evidence grounding, capability-resolution errors, causal policy pass rate, end-to-end pass rate, contradiction handling, and feature-evidence coverage.

## Promotion gate

Apply the registered promotion gate conjunctively. A strong average score cannot compensate for a critical-risk miss, grounding failure, invalid contract, or incomplete prediction set.

If any required `case_id` is missing, return INCOMPLETE rather than fabricating a partial benchmark.

After a blind holdout is observed, retire it from future generalization claims and create a new private unseen set for the next promotion attempt.
