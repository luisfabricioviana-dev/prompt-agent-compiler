# PROMPT & AGENT COMPILER — Recovery Audit (2026-09-13)

## Recovered source bundles

- `prompt_agent_compiler_v0_2_8(1).zip`
  - SHA-256: `e67968d6e116e791e85be57d2027db31c5cb11dd55aaeed8d3caf20ccd80fc12`
- `prompt_agent_compiler_v0_2_9(1).zip`
  - SHA-256: `a0986c482309b6de7bf1bf90be3db9cba546f4cd0703813fe8b2161508fede7a`

## Fresh verification of recovered v0.2.8

Executed against the recovered source tree using Python 3.13.5:

- `python -m unittest discover -s . -p 'test_*.py' -v` → **75/75 PASS**
- `python -m compileall -q .` → **PASS**
- all **22** top-level JSON files parse cleanly
- `evaluate_oracle_v0_2_8.py` → provider success 1.0, contract valid 1.0, semantic exact 1.0, causal policy pass 1.0, end-to-end 1.0 across **31** policy cases
- `mutation_suite_v0_2_8.py` → **9/9 PASS**

The historical verification report states that the original packaged verification counted **20 JSON artifacts**; the recovered archive currently contains 22 top-level JSON files because status/version artifacts are also present in the distribution. This is not treated as a regression.

## Fresh verification of recovered v0.2.9

- `python -m unittest discover -s . -p 'test_*.py' -v` → **83/83 PASS**
- `python -m compileall -q .` → **PASS**
- all **27** top-level JSON files parse cleanly
- `freeze_integrity_v0_2_9.py` → **12/12 files valid**, no drift
- `blind_holdout_v0_2_9.json` → **60 frozen cases, 60 unique IDs**
- model-backed blind holdout evaluation remains **NOT RUN**; no generalization claim is authorized

## Lineage comparison

Recovered v0.2.9 is a strict additive superset of recovered v0.2.8 at the top level:

- no v0.2.8 top-level file is missing from v0.2.9;
- every common top-level file is byte-identical;
- v0.2.9 adds exactly 17 files:
  - `ARCHITECTURE_v0_2_9.md`
  - `EVALUATION_PROTOCOL_v0_2_9.md`
  - `EVALUATION_RUNBOOK_v0_2_9.md`
  - `FREEZE_MANIFEST_v0_2_9.json`
  - `HOLDOUT_FREEZE_v0_2_9.md`
  - `README_v0_2_9.md`
  - `VERIFICATION_REPORT_v0_2_9.md`
  - `VERSION_MANIFEST_v0_2_9.json`
  - `blind_holdout_v0_2_9.json`
  - `freeze_integrity_v0_2_9.py`
  - `holdout_evaluator_v0_2_9.py`
  - `holdout_protocol_v0_2_9.py`
  - `prediction_exchange_schema_v0_2_9.json`
  - `prediction_exchange_v0_2_9.py`
  - `predictions_template_v0_2_9.json`
  - `promotion_gate_v0_2_9.py`
  - `test_holdout_protocol_v0_2_9.py`

## Architectural interpretation

Recovered v0.2.9 does **not** introduce new routing intelligence. It adds a frozen scientific generalization protocol around the v0.2.8 compiler:

`UNSEEN REQUEST → SEMANTIC INTERPRETER MODEL → PROVIDER BOUNDARY → GROUNDING + CONTRACT → NormalizedTask → FROZEN DETERMINISTIC POLICY → ExecutionSpec → CAUSAL ERROR DECOMPOSITION → PROMOTION GATE`

Its holdout is explicitly an observation instrument, not a development set.

## Repository governance after recovery

The previously reconstructed branches are preserved as archives:

- `archive/reconstructed-v0.2.8-before-recovery`
- `archive/reconstructed-v0.2.9-before-recovery`

PR #1 was closed as **SUPERSEDED — DO NOT MERGE**.

The tutorial-derived task-spec / prompt-reliability hardening remains valuable, but it must no longer use version `v0.2.9`, because that version already exists in the recovered canonical lineage. Recommended next version: **v0.2.10**.

## Canonical decision

1. Treat recovered v0.2.8 as the authentic baseline.
2. Treat recovered v0.2.9 as the authentic additive successor.
3. Preserve the reconstructed implementation only for archaeological comparison.
4. Rebase the new prompt/task-spec hardening onto recovered v0.2.9 and release it as v0.2.10 after regression.
5. Do not claim model-backed generalization until the frozen v0.2.9 holdout is actually evaluated with an authenticated model-backed semantic provider.
