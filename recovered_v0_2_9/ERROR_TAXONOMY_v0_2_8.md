# Semantic Error Taxonomy v0.2.8

The purpose of the taxonomy is causal attribution. A downstream mismatch is not automatically a policy defect.

## Provider / boundary

- `INTERPRETER_PROVIDER_ERROR` — transport/client/model invocation failed.
- `PROVIDER_GROUNDING_ERROR` — an EXPLICIT evidence span is absent from the user request.

## Semantic contract

- `CONTRACT_VALIDATION_ERROR` — output cannot satisfy the normalized semantic contract.

## Semantic Interpreter

- `INTERPRETER_<GROUP>_FALSE_NEGATIVE` — required normalized feature missing.
- `INTERPRETER_<GROUP>_FALSE_POSITIVE` — unsupported normalized feature added.
- `INTERPRETER_ROLE_CONFUSION_UI_ERROR_AS_DEBUG` — a UI error state is misread as a software debugging request.
- `INTERPRETER_RISK_UNDERESTIMATION` / `INTERPRETER_RISK_OVERESTIMATION` — risk magnitude differs.
- `INTERPRETER_CONTRADICTION_MISS` / `INTERPRETER_CONTRADICTION_HALLUCINATION` — contradiction presence differs.
- `INTERPRETER_EVIDENCE_COVERAGE_MISS` — material normalized feature has no evidence record.

## Policy Router

These errors are **causal only when semantic input is exact**.

- `POLICY_PATTERN_ERROR`
- `POLICY_GATE_ERROR`
- `POLICY_COMPLEXITY_ERROR`

If semantics are wrong, policy divergences are retained as observations but marked `causal=false`.

## Repair rule

Repair the earliest causally responsible layer. Do not patch policy rules to compensate for an incorrect `NormalizedTask`.
