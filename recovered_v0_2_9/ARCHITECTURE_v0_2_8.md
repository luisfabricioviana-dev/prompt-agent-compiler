# PROMPT & AGENT COMPILER v0.2.8 — Causal Evaluation & Repair Architecture

## Goal

v0.2.8 does not add new Patterns. It adds experimental control around the Semantic Interpreter.

```text
REQUEST
  ↓
MODEL SEMANTIC INTERPRETER
  ↓
PROVIDER / GROUNDING BOUNDARY
  ↓
SEMANTIC CONTRACT VALIDATOR
  ↓
NormalizedTask
  ↓
DETERMINISTIC POLICY ROUTER
  ↓
ExecutionSpec
```

Evaluation is decomposed into four attribution layers:

```text
PROVIDER ERROR
CONTRACT ERROR
INTERPRETER ERROR
POLICY ERROR
```

A policy error is causal only if the normalized semantics are correct. This prevents compensating for semantic mistakes by distorting deterministic policy rules.

## New modules

- `semantic_error_taxonomy_v0_2_8.py`
- `end_to_end_decomposition_v0_2_8.py`
- `repair_router_v0_2_8.py`
- `recorded_semantic_provider_v0_2_8.py`
- `model_eval_runner_v0_2_8.py`
- `mutation_suite_v0_2_8.py`
- `run_live_model_eval_v0_2_8.py`
- `replay_model_eval_v0_2_8.py`
- `build_error_report_v0_2_8.py`

## Reproducibility

Every live model evaluation may persist the resulting `NormalizedTask` predictions. Those predictions can then be replayed against later policy versions without spending another model call or changing the semantic evidence.

This supports three controlled experiments:

1. Same model outputs, new policy.
2. New model/prompt, same policy.
3. Full end-to-end comparison.

## Repair locality

```text
wrong model output       → semantic_interpreter
invalid/ungrounded output→ provider_boundary / semantic_contract
correct semantics + bad route → policy_router
```

The Repair Router returns the minimum causally justified component set.
