# PROMPT & AGENT COMPILER v0.2.6

## Run tests

```bash
python -m unittest test_hybrid_compiler_v0_2_6.py
```

## Run deterministic policy benchmark

```bash
python evaluate_oracle_policy_v0_2_6.py
```

## Core files

- `normalized_task.py` — semantic contract object
- `semantic_contract.py` — semantic consistency validator
- `policy_v0_2_6.py` — text-agnostic deterministic policy
- `interpreter_provider.py` — provider interface
- `structured_output_provider.py` — adapter for model-produced JSON
- `semantic_interpreter_prompt.md` — semantic interpretation prompt
- `normalized_task_schema.json` — structured-output schema
- `SEMANTIC_EVAL_SPEC.md` — interpreter evaluation protocol
- `semantic_oracle_cases_v0_2_6.json` — policy-layer development oracle set
- `evaluate_oracle_policy_v0_2_6.py` — policy benchmark

## Important

The 100% oracle-policy score is intentionally scoped to `NormalizedTask → ExecutionSpec` on the development oracle set. It does not claim that arbitrary natural-language requests are interpreted with 100% accuracy.
