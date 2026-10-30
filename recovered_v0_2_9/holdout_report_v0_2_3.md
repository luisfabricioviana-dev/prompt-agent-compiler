# PROMPT & AGENT COMPILER — Blind Holdout Report v0.2.3

> Frozen holdout. This suite was evaluated against the v0.2.2 Router without post-observation rule changes.

## Metrics

- **routing_precision**: 0.8889
- **routing_recall**: 0.7143
- **overengineering_rate**: 0.025
- **gate_recall**: 0.3478
- **complexity_accuracy**: 0.375
- **case_pass_rate**: 0.275
- **cases**: 40

## Failures

### H04 — refactor
- Input: Refatore esta classe para reduzir duplicação sem mudar a API pública.
- Selected: P02
- Complexity: N0 (0)
- Error: missing gates: ['REGRESSION_GATE']
- Error: complexity N0 not in ['N1', 'N2']

### H05 — refactor_optimize
- Input: Refatore este pipeline preservando o resultado e reduza seu tempo de execução em pelo menos 30%.
- Selected: P02
- Complexity: N1 (2)
- Error: missing required patterns: ['P05']
- Error: missing gates: ['BASELINE_GATE']
- Error: complexity N1 not in ['N2', 'N3']

### H08 — optimize
- Input: Reduza o consumo de memória deste job sem alterar o resultado final.
- Selected: none
- Complexity: N1 (2)
- Error: missing required patterns: ['P05']
- Error: missing gates: ['BASELINE_GATE']
- Error: complexity N1 not in ['N2', 'N3']

### H09 — ui
- Input: Crie um dashboard responsivo com estados de loading, empty, erro e navegação por teclado.
- Selected: P01, P03, P08
- Complexity: N1 (1)
- Error: missing gates: ['ACCESSIBILITY_GATE']
- Error: unexpected selected patterns: ['P03']

### H11 — multi_agent_real
- Input: Projete um sistema de pagamentos crítico e faça revisão independente de arquitetura e segurança antes da aprovação.
- Selected: P04, P07
- Complexity: N2 (5)
- Error: complexity N2 not in ['N3', 'N4']

### H12 — multi_agent_fake
- Input: Use cinco agentes para escrever uma função que some dois inteiros.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P01']

### H17 — destructive
- Input: Apague todos os arquivos temporários do projeto e não mantenha backup.
- Selected: none
- Complexity: N0 (0)
- Error: missing gates: ['DESTRUCTIVE_ACTION_GATE']
- Error: complexity N0 not in ['N3', 'N4']

### H18 — ambiguous
- Input: Melhore isso.
- Selected: none
- Complexity: N0 (0)
- Error: complexity N0 not in ['N1', 'N2']

### H19 — ambiguous_debug
- Input: Tem alguma coisa errada nesse código. Veja o que é.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P03']
- Error: complexity N0 not in ['N1', 'N2']

### H20 — contradiction
- Input: Troque toda a arquitetura interna, mas preserve exatamente a API e o comportamento observável.
- Selected: P04
- Complexity: N2 (6)
- Error: missing required patterns: ['P02']

### H21 — evidence_only
- Input: Avalie somente os documentos anexados e identifique o que está comprovado, o que é interpretação e o que permanece pendente.
- Selected: none
- Complexity: N0 (0)
- Error: missing gates: ['EVIDENCE_GATE', 'TRACEABILITY_GATE']
- Error: complexity N0 not in ['N2', 'N3']

### H22 — laf
- Input: Reconstrua a cronologia do processo de licenciamento, diferencie fato documental de avaliação técnica e indique pendências com rastreabilidade.
- Selected: P01
- Complexity: N1 (1)
- Error: forbidden patterns selected: ['P01']
- Error: missing gates: ['EVIDENCE_GATE', 'TRACEABILITY_GATE']
- Error: complexity N1 not in ['N3', 'N4']
- Error: unexpected selected patterns: ['P01']

### H23 — laf_normative
- Input: Analise a demanda atual do processo e confronte cada conclusão com os documentos e normas fornecidos, sem usar fontes externas.
- Selected: none
- Complexity: N1 (3)
- Error: missing gates: ['EVIDENCE_GATE', 'TRACEABILITY_GATE']
- Error: complexity N1 not in ['N3', 'N4']

### H25 — youtube_build
- Input: Crie um Short completo sobre o tema, incluindo roteiro, plano de cenas e especificações de geração.
- Selected: P01
- Complexity: N1 (1)
- Error: complexity N1 not in ['N2', 'N3']

### H26 — youtube_qa
- Input: Revise este vídeo pronto e identifique problemas de retenção, factualidade, continuidade visual e áudio antes da publicação.
- Selected: none
- Complexity: N0 (0)
- Error: complexity N0 not in ['N2', 'N3']

### H27 — youtube_repair
- Input: A cena 4 está errada no mapa, mas o restante do vídeo está aprovado. Corrija apenas essa cena e valide novamente.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P03']
- Error: complexity N0 not in ['N1', 'N2']

### H28 — security_review
- Input: Revise este fluxo de autenticação para encontrar falhas de segurança sem implementar mudanças ainda.
- Selected: none
- Complexity: N0 (0)
- Error: complexity N0 not in ['N2', 'N3']

### H29 — security_build
- Input: Projete e implemente autenticação com MFA, rotação de sessão e recuperação de conta, com revisão de segurança.
- Selected: P01, P04
- Complexity: N2 (6)
- Error: complexity N2 not in ['N3', 'N4']

### H30 — stateful_external
- Input: Atualize o evento existente no calendário para amanhã às 15h sem criar um novo evento.
- Selected: none
- Complexity: N0 (0)
- Error: complexity N0 not in ['N2', 'N3']

### H31 — stateful_external
- Input: Responda ao último e-mail do fornecedor mantendo o mesmo assunto e o contexto da conversa.
- Selected: none
- Complexity: N0 (0)
- Error: complexity N0 not in ['N2', 'N3']

### H32 — data_analysis
- Input: Analise este CSV, encontre os principais drivers de churn e produza uma recomendação baseada em evidências.
- Selected: none
- Complexity: N1 (3)
- Error: complexity N1 not in ['N2', 'N3']

### H33 — data_optimize
- Input: Este modelo de previsão está lento. Meça a baseline, identifique o gargalo e reduza a latência sem piorar a acurácia.
- Selected: P05
- Complexity: N1 (2)
- Error: missing gates: ['REGRESSION_GATE']
- Error: complexity N1 not in ['N2', 'N3']

### H34 — docs
- Input: Reescreva esta documentação para ficar mais clara, sem mudar o significado técnico.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P02']
- Error: missing gates: ['REGRESSION_GATE']
- Error: complexity N0 not in ['N1', 'N2']

### H35 — large_summary
- Input: Resuma 400 páginas em uma síntese executiva de duas páginas, preservando fatos, números e divergências.
- Selected: none
- Complexity: N1 (2)
- Error: complexity N1 not in ['N2', 'N3']

### H36 — parallelizable
- Input: Compare quatro arquiteturas independentes para o mesmo problema e depois faça uma síntese crítica única.
- Selected: P04
- Complexity: N2 (4)
- Error: unexpected selected patterns: ['P04']

### H37 — approval
- Input: Prepare a mudança e só execute depois de uma aprovação humana explícita.
- Selected: none
- Complexity: N0 (0)
- Error: complexity N0 not in ['N2', 'N3']

### H38 — performance_without_claim
- Input: Veja se existe algum gargalo relevante neste serviço; não faça otimizações ainda.
- Selected: none
- Complexity: N0 (0)
- Error: missing gates: ['BASELINE_GATE']
- Error: complexity N0 not in ['N1', 'N2']

### H39 — mixed
- Input: Corrija o bug, preserve o comportamento restante, depois meça se a correção piorou a performance.
- Selected: P02, P03, P05
- Complexity: N1 (2)
- Error: complexity N1 not in ['N2', 'N3']

### H40 — critical_mixed
- Input: Projete a nova arquitetura, migre incrementalmente sem quebra de compatibilidade, revise segurança e performance e só então libere para produção.
- Selected: P04, P05
- Complexity: N2 (6)
- Error: missing required patterns: ['P02']
- Error: missing gates: ['REGRESSION_GATE']
- Error: complexity N2 not in ['N3', 'N4']


## Passed cases

- H01 — trivial
- H02 — build
- H03 — debug
- H06 — design
- H07 — design_build
- H10 — ui_simple
- H13 — research
- H14 — research_then_build
- H15 — tool_use
- H16 — auth
- H24 — youtube_research