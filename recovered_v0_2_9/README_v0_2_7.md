# PROMPT & AGENT COMPILER v0.2.7

## What changed

v0.2.7 connects a model-capable Semantic Interpreter boundary to the deterministic compiler core.

### New files

- `openai_responses_semantic_provider.py` — Structured Outputs model adapter
- `semantic_provider_schema_v0_2_7.json` — strict provider boundary schema
- `semantic_interpreter_prompt_v0_2_7.md` — descriptive semantic prompt
- `semantic_eval_v0_2_7.py` — semantic metrics
- `semantic_dev_cases_v0_2_7.json` — 31-case development benchmark
- `evaluate_semantic_provider_v0_2_7.py` — provider evaluation harness
- `run_live_semantic_eval_v0_2_7.py` — live semantic benchmark CLI
- `compile_with_model_v0_2_7.py` — end-to-end compile CLI
- `policy_v0_2_7.py` — canonical deterministic policy
- `LIVE_EVAL_STATUS_v0_2_7.json` — explicit experiment status

## Run tests

```bash
python -m unittest discover -v
```

## Run oracle harness

```bash
python evaluate_semantic_provider_v0_2_7.py
```

The oracle harness proves the evaluation and policy plumbing. It does **not** measure model generalization.

## Run live semantic evaluation

Requires an authenticated OpenAI SDK environment:

```bash
python run_live_semantic_eval_v0_2_7.py --model gpt-5.6-terra
```

The model is configurable via `--model` or `PAC_SEMANTIC_MODEL`.

## Compile one request end-to-end

```bash
python compile_with_model_v0_2_7.py "Reduza a memória sem piorar a acurácia"
```

## Experimental discipline

Do not tune and evaluate on the same holdout.

After a live model is tuned on the v0.2.7 development benchmark, create a new unseen holdout (v0.2.8 or later) and freeze it before the first run.
