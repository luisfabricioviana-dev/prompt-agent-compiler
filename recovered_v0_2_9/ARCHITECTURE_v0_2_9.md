# PROMPT & AGENT COMPILER v0.2.9 — Frozen Generalization Protocol

## Purpose

v0.2.9 does not add new routing intelligence. It adds a scientific boundary around the existing compiler so that future model-backed evaluation can support a defensible generalization claim.

```text
UNSEEN REQUEST
    ↓
SEMANTIC INTERPRETER MODEL
    ↓
STRUCTURED OUTPUT / PROVIDER BOUNDARY
    ↓
GROUNDING + CONTRACT VALIDATION
    ↓
NormalizedTask
    ↓
FROZEN DETERMINISTIC POLICY
    ↓
ExecutionSpec
    ↓
CAUSAL ERROR DECOMPOSITION
    ↓
PROMOTION GATE
```

## Design rule

The holdout is an observation instrument, not a development set.

After the first model-backed observation:

- the holdout is retired for tuning;
- its failures may seed a new development set;
- any repaired compiler must be evaluated on a new unseen holdout.

## New components

### `blind_holdout_v0_2_9.json`
60 unseen cases spanning semantic paraphrase, role confusion, performance dimensions, evidence policy, external state, capabilities, approval, destructive operations, risk, LAF, YouTube, analytics, UI, architecture, migration, and ambiguity.

### `prediction_exchange_v0_2_9.py`
Accepts normalized model predictions keyed by case ID and refuses unknown IDs.

### `holdout_evaluator_v0_2_9.py`
Scores a complete prediction file through the existing semantic metrics and causal decomposer. Missing cases produce `INCOMPLETE`; no oracle filling is allowed.

### `promotion_gate_v0_2_9.py`
Promotion is conjunctive. Strong averages cannot compensate for critical grounding or risk failures.

### `freeze_integrity_v0_2_9.py`
SHA-256 snapshot of the holdout and the compiler/evaluation components that materially affect the result.

## Promotion thresholds

- provider success = 1.00
- contract valid = 1.00
- semantic exact ≥ 0.85
- end-to-end pass ≥ 0.90
- critical-risk recall = 1.00
- explicit evidence grounding = 1.00
- minimum semantic-group F1 ≥ 0.90
- feature-evidence coverage ≥ 0.90
- contradiction accuracy ≥ 0.95

These are pre-registered before model-backed observation.

## What v0.2.9 deliberately does not do

- it does not tune the interpreter against the blind set;
- it does not run policy-oracle evaluation on the blind set;
- it does not impute missing model predictions;
- it does not average away critical failures;
- it does not claim generalization before an authenticated model run.
