# PROMPT & AGENT COMPILER — Holdout Failure Analysis v0.2.3

> The v0.2.3 holdout is retired for future tuning. It remains a historical generalization measurement for Router v0.2.2.

## Frozen result

- **routing_precision**: 0.8889
- **routing_recall**: 0.7143
- **overengineering_rate**: 0.025
- **gate_recall**: 0.3478
- **complexity_accuracy**: 0.375
- **case_pass_rate**: 0.275
- **cases**: 40

## Error taxonomy

- **complexity_under_or_misclassification**: 25
- **missing_quality_gate**: 12
- **pattern_false_negative**: 8
- **pattern_false_positive_unexpected**: 3
- **pattern_false_positive_forbidden**: 1

## Root causes

### 1. Lexical brittleness
Feature and gate extraction still depends too heavily on exact trigger phrases. Paraphrases such as 'sem mudar a API pública', 'somente os documentos anexados', 'apague', 'tem alguma coisa errada' and 'reduza o consumo de memória' are missed.

### 2. Complexity overfitting
Thresholds were calibrated against the 20-case development set, so many novel tasks collapse to N0/N1 even when they have external state, large workload, high consequence, or multi-stage verification.

### 3. Gate coupling to narrow wording
Regression, evidence, baseline and destructive-action gates are triggered by narrow lexical patterns instead of being compiled from underlying features and constraints.

### 4. Intent conflation
The token 'erro' inside UI state descriptions caused P03 DEBUG to be selected for a production UI task; lexical tokens are being interpreted without local semantic role.

### 5. Weak modification model
Requests like 'troque toda a arquitetura', 'reescreva documentação' and 'migre incrementalmente' are not consistently recognized as modification/refactor tasks.

### 6. Weak performance ontology
Performance is modeled mostly as latency/performance keywords, missing memory consumption, accuracy-preserving optimization, profiling-only requests, and performance-regression verification.

### 7. External-state blindness
Calendar, email, publication and approval workflows carry state/auth/irreversibility complexity, but the current complexity model only recognizes a narrow set of verbs.

### 8. Domain-evidence blindness
LAF/documentary tasks need evidence and traceability gates from task semantics, not exact phrases such as 'processo administrativo' or 'documentos fornecidos'.

## Representative failures

### missing_quality_gate
- **H04** — missing gates: ['REGRESSION_GATE']
  - `Refatore esta classe para reduzir duplicação sem mudar a API pública.`
- **H05** — missing gates: ['BASELINE_GATE']
  - `Refatore este pipeline preservando o resultado e reduza seu tempo de execução em pelo menos 30%.`
- **H08** — missing gates: ['BASELINE_GATE']
  - `Reduza o consumo de memória deste job sem alterar o resultado final.`
- **H09** — missing gates: ['ACCESSIBILITY_GATE']
  - `Crie um dashboard responsivo com estados de loading, empty, erro e navegação por teclado.`
- **H17** — missing gates: ['DESTRUCTIVE_ACTION_GATE']
  - `Apague todos os arquivos temporários do projeto e não mantenha backup.`
- **H21** — missing gates: ['EVIDENCE_GATE', 'TRACEABILITY_GATE']
  - `Avalie somente os documentos anexados e identifique o que está comprovado, o que é interpretação e o que permanece pendente.`

### complexity_under_or_misclassification
- **H04** — complexity N0 not in ['N1', 'N2']
  - `Refatore esta classe para reduzir duplicação sem mudar a API pública.`
- **H05** — complexity N1 not in ['N2', 'N3']
  - `Refatore este pipeline preservando o resultado e reduza seu tempo de execução em pelo menos 30%.`
- **H08** — complexity N1 not in ['N2', 'N3']
  - `Reduza o consumo de memória deste job sem alterar o resultado final.`
- **H11** — complexity N2 not in ['N3', 'N4']
  - `Projete um sistema de pagamentos crítico e faça revisão independente de arquitetura e segurança antes da aprovação.`
- **H17** — complexity N0 not in ['N3', 'N4']
  - `Apague todos os arquivos temporários do projeto e não mantenha backup.`
- **H18** — complexity N0 not in ['N1', 'N2']
  - `Melhore isso.`

### pattern_false_negative
- **H05** — missing required patterns: ['P05']
  - `Refatore este pipeline preservando o resultado e reduza seu tempo de execução em pelo menos 30%.`
- **H08** — missing required patterns: ['P05']
  - `Reduza o consumo de memória deste job sem alterar o resultado final.`
- **H12** — missing required patterns: ['P01']
  - `Use cinco agentes para escrever uma função que some dois inteiros.`
- **H19** — missing required patterns: ['P03']
  - `Tem alguma coisa errada nesse código. Veja o que é.`
- **H20** — missing required patterns: ['P02']
  - `Troque toda a arquitetura interna, mas preserve exatamente a API e o comportamento observável.`
- **H27** — missing required patterns: ['P03']
  - `A cena 4 está errada no mapa, mas o restante do vídeo está aprovado. Corrija apenas essa cena e valide novamente.`

### pattern_false_positive_unexpected
- **H09** — unexpected selected patterns: ['P03']
  - `Crie um dashboard responsivo com estados de loading, empty, erro e navegação por teclado.`
- **H22** — unexpected selected patterns: ['P01']
  - `Reconstrua a cronologia do processo de licenciamento, diferencie fato documental de avaliação técnica e indique pendências com rastreabilidade.`
- **H36** — unexpected selected patterns: ['P04']
  - `Compare quatro arquiteturas independentes para o mesmo problema e depois faça uma síntese crítica única.`

### pattern_false_positive_forbidden
- **H22** — forbidden patterns selected: ['P01']
  - `Reconstrua a cronologia do processo de licenciamento, diferencie fato documental de avaliação técnica e indique pendências com rastreabilidade.`

## Architectural consequence

The next version should not add more keyword lists as the primary repair. The failure pattern indicates that the Router needs a two-stage semantic model:

```text
REQUEST
  ↓
SEMANTIC FEATURE INTERPRETER
  ↓
NORMALIZED TASK FEATURES / CONSTRAINTS / RISKS
  ↓
DETERMINISTIC POLICY ROUTER
  ↓
PATTERNS + COMPLEXITY + GATES
```

The semantic layer may use an LLM or structured classifier, but the policy layer should remain explicit and auditable.

## v0.2.4 development target

1. Replace direct keyword→pattern decisions with keyword/semantic evidence→normalized feature decisions.
2. Compile Quality Gates from normalized features and constraints rather than from request wording.
3. Replace single additive complexity score with factorized dimensions: workflow, consequence, external state, uncertainty, verification burden, reversibility, specialization.
4. Add semantic roles so words such as `erro` can mean UI state rather than software failure.
5. Expand performance representation: latency, throughput, memory, cost, accuracy/quality preservation, profiling-only.
6. Add external-state and authorization features explicitly.
7. Add evidence-domain features independent of exact LAF/document wording.
8. Create a new DEVELOPMENT SET from these failure classes.
9. After changes, create a completely new unseen HOLDOUT v0.2.5; never reuse v0.2.3 as a tuning benchmark.

## Scientific status

The 20-case golden suite measured regression consistency after tuning. The 40-case frozen holdout measured generalization and exposed substantial overfitting. Therefore the current Router is a useful prototype, but not yet production-ready.