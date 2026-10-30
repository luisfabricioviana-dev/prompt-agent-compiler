# PROMPT & AGENT COMPILER — Architecture v0.2.7

## Purpose

v0.2.7 turns the v0.2.6 semantic boundary into an executable model-provider architecture while keeping routing policy deterministic and auditable.

```text
HUMAN REQUEST
      ↓
MODEL SEMANTIC INTERPRETER
      ↓
STRICT STRUCTURED OUTPUT
      ↓
GROUNDING CHECK
      ↓
SEMANTIC CONTRACT VALIDATOR
      ↓
NormalizedTask
      ↓
DETERMINISTIC POLICY v0.2.7
      ↓
ExecutionSpec
```

## Architectural invariant

The model **describes the task**. It never selects P01–P08, complexity levels, or Quality Gates.

The deterministic policy consumes only `NormalizedTask`. Therefore policy behavior can be tested independently of prompt wording and model choice.

## Provider boundary

`OpenAIResponsesSemanticProvider` uses a strict JSON-schema response format. The provider schema differs slightly from the core schema only at the serialization boundary:

- all risk keys are emitted, with `0` meaning absent/irrelevant;
- `feature_evidence` is serialized as an array of fixed-shape items;
- the adapter converts that array back into the core `feature_evidence` mapping;
- zero-valued risks are removed before core validation.

This avoids dynamic-key dependence in the strict provider schema.

## Grounding gate

Every model classification marked `EXPLICIT` must contain an exact `evidence_span` from the human request.

If not, the provider raises `SemanticGroundingError` before policy execution.

This makes explicit-evidence fabrication a blocking semantic-layer failure.

## Policy v0.2.7 changes

Two policy defects were found by the semantic oracle harness and repaired through red-green tests:

1. optimization + preservation now has a minimum complexity floor of N2;
2. a boundary refactor handled by P06 no longer adds P04 merely because architecture changes internally, unless a separate DESIGN signal exists.

## Evaluation decomposition

Three different evaluations are now possible:

```text
A. Request → NormalizedTask
   measures Interpreter quality

B. NormalizedTask → ExecutionSpec
   measures Policy quality

C. Request → ExecutionSpec
   measures end-to-end quality
```

Failures are classified into semantic, contract, pattern, gate, complexity, and capability classes.

## Semantic metrics

v0.2.7 measures:

- multilabel precision/recall/F1 by semantic group;
- risk exact accuracy;
- risk MAE;
- critical-risk recall;
- explicit evidence-span grounding;
- feature-evidence coverage;
- confidence Brier score and ECE;
- contradiction presence accuracy;
- downstream route pass rate.

## Experimental status

The provider integration is implemented and verified with injected fake clients and an oracle semantic provider.

No live model-backed semantic-generalization claim is made in this version because the execution runtime used to build the artifact has no OpenAI SDK/API credential configured.

The next experimental milestone is a live development run followed by a **new unseen holdout**. Retired holdouts v0.2.3 and v0.2.5 must not be reused as blind tests.
