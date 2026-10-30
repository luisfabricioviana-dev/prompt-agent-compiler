# PROMPT & AGENT COMPILER v0.2.8

## Focus

Causal semantic evaluation, reproducible model-output replay, and minimum-scope repair routing.

## Run tests

```bash
python -m unittest discover -v
python -m compileall .
```

## Oracle verification

```bash
python evaluate_oracle_v0_2_8.py
python mutation_suite_v0_2_8.py
```

Oracle runs validate the harness; they do not measure model generalization.

## Live model evaluation

```bash
python run_live_model_eval_v0_2_8.py --model <model>
```

This writes both the evaluation report and a cache of normalized predictions.

## Replay without model calls

```bash
python replay_model_eval_v0_2_8.py --predictions semantic_model_predictions_v0_2_8.json
```

## Experimental rule

Do not tune on the next frozen holdout. Use the semantic development set for repairs, freeze the interpreter/policy, then create a new unseen holdout.
