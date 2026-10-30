# PROMPT & AGENT COMPILER v0.2.6 — Hybrid Semantic Architecture

## Why v0.2.6 exists

The v0.2.4 Router reached 100% on 60 development cases, but the frozen unseen v0.2.5 holdout exposed severe end-to-end brittleness:

- routing precision: 0.80
- routing recall: 0.3333
- gate recall: 0.1351
- complexity accuracy: 0.30
- case pass rate: 0.20

The dominant failure was not the deterministic policy itself. It was natural-language interpretation by an expanding lexical/heuristic layer.

## Architectural change

```text
HUMAN REQUEST
      ↓
SEMANTIC INTERPRETER PROVIDER
      ↓
NORMALIZED TASK
      ↓
SEMANTIC CONTRACT VALIDATOR
      ↓
DETERMINISTIC POLICY ROUTER
      ↓
EXECUTION SPEC
```

The policy layer never inspects user wording.

## NormalizedTask

The contract represents:

- actions
- preservation requirements
- performance dimensions
- evidence policy
- UI requirements
- architecture semantics
- external/persistent state
- execution properties
- required capability classes
- risk profile
- feature-level evidence/confidence
- unknowns
- contradictions

## Interpretation and policy are evaluated separately

### Layer A — Interpreter benchmark

```text
request → NormalizedTask
```

Measures whether language was understood correctly.

### Layer B — Policy benchmark

```text
oracle NormalizedTask → ExecutionSpec
```

Measures routing, gates and complexity without language interpretation.

### Layer C — End-to-end benchmark

```text
request → provider → NormalizedTask → policy → ExecutionSpec
```

Measures actual system quality.

This prevents an interpretation failure from being misdiagnosed as a routing-policy failure.

## Provider boundary

`SemanticInterpreterProvider` is an interface. The core does not depend on a specific model vendor or API.

A model-backed provider should produce structured JSON matching `normalized_task_schema.json` and the semantic prompt. The host application is responsible for choosing/calling the model.

The current package intentionally does **not** pretend that the old heuristic interpreter generalizes. It is not the recommended production semantic provider.

## Deterministic policy result

The v0.2.6 oracle-policy benchmark contains 20 normalized tasks spanning build, debug, refactor, optimization, evidence, destructive state, approval, research, design, UI, data analysis, external state, independent review and critical migration.

Result after the development cycle:

- routing precision: 1.00
- routing recall: 1.00
- overengineering rate: 0.00
- gate recall: 1.00
- complexity accuracy: 1.00
- case pass rate: 1.00

This result validates only the **policy layer on the development oracle set**. It is not evidence that natural-language interpretation is solved.

## Scientific discipline

- v0.2.3 holdout: retired after one blind evaluation.
- v0.2.5 holdout: retired after one blind evaluation.
- neither may be reused as a future blind benchmark.
- v0.2.6 may use their failure classes for development.
- the next end-to-end holdout must be newly created after a real semantic provider is connected.
