# Semantic Interpreter Evaluation Spec v0.2.6

## Purpose

Evaluate the semantic layer independently from the deterministic Router.

## Required metrics

### 1. Action micro-F1

Multi-label F1 over:

`CREATE`, `MODIFY`, `DIAGNOSE`, `REVIEW`, `RESEARCH`, `ANALYZE_EVIDENCE`, `ANALYZE_DATA`, `DESIGN`, `OPTIMIZE`, `OPERATE`.

### 2. Preservation F1

Multi-label F1 over:

`BEHAVIOR`, `API`, `OUTPUT`, `MEANING`, `QUALITY`, `COMPATIBILITY`.

### 3. Performance-dimension F1

Must distinguish latency, throughput, memory, compute/cost and quality preservation instead of collapsing them into one performance token.

### 4. Evidence-policy accuracy

Evaluate:

- supplied-only grounding;
- current external evidence requirement;
- traceability requirement.

### 5. Semantic-role accuracy

Adversarial pairs should include:

- UI error state vs software failure;
- compare architecture vs change architecture;
- review performance vs optimize performance;
- current research vs static explanation;
- file/anexo grounding without exact keyword `documentos`.

### 6. External-state classification

Measure state-domain and required capability classes for email, calendar, publishing, database and file workflows.

### 7. Risk error

For 0–4 risk dimensions, report:

- exact bucket accuracy;
- mean absolute error;
- critical-risk recall for values 3–4.

### 8. Evidence-span grounding

For explicit classifications, verify that `evidence_span` is an exact substring of the user request.

### 9. Confidence calibration

Measure whether confidence correlates with correctness. Use calibration bins rather than treating confidence as decoration.

### 10. Contradiction recall

Evaluate whether materially conflicting constraints are surfaced rather than silently resolved.

## End-to-end decomposition

For every failed request, report one primary failure class:

```text
INTERPRETER_FALSE_NEGATIVE
INTERPRETER_FALSE_POSITIVE
INTERPRETER_ROLE_CONFUSION
INTERPRETER_RISK_ERROR
INTERPRETER_EVIDENCE_ERROR
CONTRACT_VALIDATION_ERROR
POLICY_PATTERN_ERROR
POLICY_GATE_ERROR
POLICY_COMPLEXITY_ERROR
CAPABILITY_MAPPING_ERROR
```

This taxonomy is mandatory for future regression reports.

## Acceptance order

Do not optimize overall end-to-end score first.

Priority:

1. critical risk recall;
2. explicit constraint preservation;
3. evidence-policy correctness;
4. action recall;
5. gate recall;
6. pattern precision/recall;
7. complexity calibration;
8. latency/cost.
