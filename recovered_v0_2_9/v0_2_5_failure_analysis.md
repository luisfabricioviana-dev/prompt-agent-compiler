# v0.2.5 Holdout Failure Analysis

Router v0.2.4 was frozen before the 50-case v0.2.5 evaluation.

## Result

- Routing precision: 0.80
- Routing recall: 0.3333
- Overengineering rate: 0.04
- Gate recall: 0.1351
- Complexity accuracy: 0.30
- Case pass rate: 0.20

## Error counts

- Complexity misclassification: 35
- Missing quality gates: 23
- Pattern false negatives: 17
- Unexpected selected patterns: 3
- Forbidden-pattern false positives: 2

## Diagnosis

The lexical interpreter failed on semantic paraphrases such as:

- build verbs not in the hand-maintained lexicon;
- UI described as `tela` rather than `dashboard/formulário/interface`;
- debugging described as `parou de funcionar` rather than `erro/bug`;
- preservation expressed as byte-identical output, F1 invariance, or unchanged exceptions;
- optimization expressed as throughput/cost changes with verbs other than `reduza/otimize`;
- evidence constraints expressed with `anexos`, `peças`, `parecer`, or `base normativa`;
- external state expressed through meeting/posting/rollback language rather than a small set of exact verbs;
- destructive or approval semantics expressed without the exact words used by the heuristic.

The repeated pattern shows that adding synonyms would continue the same failure mode. The required repair is a model-capable semantic interpretation boundary plus a deterministic policy behind a validated normalized contract.
