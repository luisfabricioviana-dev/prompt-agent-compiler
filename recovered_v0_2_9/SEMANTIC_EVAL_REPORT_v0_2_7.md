# Semantic Evaluation Report v0.2.7

## Scope

This report distinguishes **harness/policy verification** from **live model evaluation**.

## Development semantic benchmark

31 cases cover:

- UI semantic-role disambiguation;
- debugging paraphrases;
- preservation contracts;
- latency/throughput/memory/cost/quality performance dimensions;
- supplied-only and current-external evidence policies;
- email/calendar/publishing/database state;
- destructive actions and approval;
- anti-overengineering multi-agent cases;
- security/high-consequence review;
- LAF-style evidence analysis;
- YouTube research/build/review/repair;
- large workload;
- ambiguity;
- contradictions.

## Oracle semantic harness result

With benchmark semantics supplied perfectly by `OracleSemanticProvider`:

- contract valid rate: 100%
- all semantic group F1: 100%
- risk exact accuracy: 100%
- risk MAE: 0
- critical-risk recall: 100%
- evidence-span grounding: 100%
- feature-evidence coverage: 100%
- confidence Brier: 0
- confidence ECE: 0
- contradiction accuracy: 100%
- downstream route pass rate: 100%

These numbers validate the **evaluation plumbing and deterministic policy against this development set**. They are not model-performance numbers.

## Policy errors found during oracle run

Before the final policy patch, route pass rate was 86.67% despite perfect semantics. The decomposed harness identified four policy-layer failures:

- three optimization + preservation cases were under-classified as N1;
- one boundary-refactor case unnecessarily selected P04 alongside P06.

Both failure classes received regression tests before the policy repair.

## Live model evaluation

Status: **NOT RUN**.

Reason: the OpenAI SDK and API credential are not configured in the artifact-build runtime.

Therefore v0.2.7 makes no claim about natural-language semantic generalization yet.
