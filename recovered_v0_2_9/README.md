
# PROMPT & AGENT COMPILER — Router Harness v0.2.2

Primeiro harness executável do núcleo de roteamento.

## Componentes

- `models.py` — contratos mínimos (`FeatureValue`, `PatternDecision`, `ExecutionSpec`, `QualityGate`)
- `patterns.py` — biblioteca P01–P08
- `router.py` — feature extraction, constraints, contradictions, complexity, scoring e gates
- `benchmark_cases.json` — 20 casos golden
- `evaluate.py` — avaliação automática
- `test_harness.py` — testes unitários mínimos
- `benchmark_report.json` — saída estruturada
- `benchmark_report.md` — relatório humano

## Executar

```bash
python evaluate.py
python -m unittest test_harness.py
```

## Métricas

- Routing Precision
- Routing Recall
- Overengineering Rate
- Gate Recall
- Complexity Accuracy
- Case Pass Rate

## Importante

Esta versão é propositalmente determinística e baseada em regras.
Ela serve para produzir erros observáveis antes de qualquer tentativa de ML, autoajuste ou roteamento opaco.
