# PROMPT & AGENT COMPILER v0.2.8 — Verification Report

## Fresh verification

- Unit/regression tests: **75/75 PASS**
- `compileall`: **PASS**
- JSON artifacts validated: **20 files**
- Oracle semantic development set: **31/31 end-to-end PASS**
- Mutation taxonomy suite: **9/9 PASS**

## Live model evaluation

Status: **BLOCKED**

The artifact runtime used for this package has neither the `openai` SDK available in its project Python environment nor `OPENAI_API_KEY` configured. Therefore no model-backed semantic generalization result is claimed for v0.2.8.

## Scientific interpretation

The verified claims are limited to:

1. causal error attribution behaves as tested;
2. recorded semantic outputs can be replayed deterministically;
3. the policy remains correct on the current oracle development set;
4. the mutation suite distinguishes representative interpreter/boundary failure families;
5. live model quality remains unevaluated.
