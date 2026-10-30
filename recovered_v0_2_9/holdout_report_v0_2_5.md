# Blind Holdout v0.2.5 — Router v0.2.4

> Frozen before the first evaluation. Do not tune Router v0.2.4 against this suite.

## Metrics

- **routing_precision**: 0.8
- **routing_recall**: 0.3333
- **overengineering_rate**: 0.04
- **gate_recall**: 0.1351
- **complexity_accuracy**: 0.3
- **case_pass_rate**: 0.2
- **cases**: 50

## Failures (40)

### U03 — build_paraphrase
- Input: Escreva um validador de CPF reutilizável e inclua exemplos de uso.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P01']
- Error: complexity N0 not in ['N1', 'N2']

### U04 — debug_paraphrase
- Input: Depois da última alteração o importador parou de funcionar e encerra antes de ler a segunda linha. Encontre a causa.
- Selected: none
- Complexity: N2 (2)
- Error: missing required patterns: ['P03']

### U05 — ui_error_semantic_role
- Input: Monte uma tela de login que mostre mensagem de erro abaixo do campo e permita navegação completa pelo teclado.
- Selected: P03
- Complexity: N1 (1)
- Error: missing required patterns: ['P01', 'P08']
- Error: forbidden patterns selected: ['P03']
- Error: missing gates: ['ACCESSIBILITY_GATE']
- Error: unexpected selected patterns: ['P03']

### U06 — refactor_paraphrase
- Input: Simplifique este módulo mantendo as mesmas entradas, saídas e exceções públicas.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P02']
- Error: missing gates: ['REGRESSION_GATE']
- Error: complexity N0 not in ['N1', 'N2']

### U07 — clean_architecture
- Input: Separe domínio, persistência e transporte deste serviço sem modificar o contrato externo.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P02', 'P06']
- Error: missing gates: ['REGRESSION_GATE']
- Error: complexity N0 not in ['N2', 'N3']

### U08 — throughput_optimization
- Input: Aumente o throughput deste consumidor em 40% sem elevar o uso de memória.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P05']
- Error: missing gates: ['BASELINE_GATE', 'REGRESSION_GATE']
- Error: complexity N0 not in ['N2', 'N3']

### U09 — cost_optimization
- Input: Corte o custo computacional deste pipeline preservando a qualidade das previsões.
- Selected: none
- Complexity: N1 (2)
- Error: missing required patterns: ['P05']
- Error: missing gates: ['BASELINE_GATE']
- Error: complexity N1 not in ['N2', 'N3']

### U10 — profiling_only
- Input: Faça profiling deste serviço para saber onde está o gargalo; por enquanto não altere nada.
- Selected: none
- Complexity: N1 (2)
- Error: missing gates: ['BASELINE_GATE']

### U11 — production_ui_paraphrase
- Input: Monte uma tela de cadastro adaptável a celular e desktop, com foco visível, labels e leitura correta por leitor de tela.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P01', 'P08']
- Error: missing gates: ['ACCESSIBILITY_GATE', 'RESPONSIVE_GATE']
- Error: complexity N0 not in ['N1', 'N2']

### U13 — system_design_paraphrase
- Input: Defina componentes, contratos e fluxo de dados para um serviço de ingestão em tempo real antes de começar a codificar.
- Selected: P08
- Complexity: N0 (0)
- Error: missing required patterns: ['P04']
- Error: complexity N0 not in ['N2', 'N3']
- Error: unexpected selected patterns: ['P08']

### U14 — architecture_comparison
- Input: Compare event sourcing, CRUD tradicional e CQRS para este cenário; não desenhe nem altere a arquitetura ainda.
- Selected: none
- Complexity: N0 (0)
- Error: complexity N0 not in ['N1', 'N2']

### U15 — independent_review
- Input: Quero uma proposta de arquitetura para um sistema financeiro e uma segunda revisão independente focada em segurança e falhas.
- Selected: P07
- Complexity: N3 (7)
- Error: missing required patterns: ['P04']

### U17 — document_only_paraphrase
- Input: Use apenas os anexos desta conversa para determinar fatos confirmados, dúvidas e pendências; não complemente com outras fontes.
- Selected: none
- Complexity: N0 (0)
- Error: missing gates: ['EVIDENCE_GATE', 'TRACEABILITY_GATE']
- Error: complexity N0 not in ['N2', 'N3']

### U18 — high_stakes_evidence
- Input: Revise o parecer e os anexos, ligue cada conclusão ao respectivo documento e destaque qualquer afirmação sem suporte.
- Selected: none
- Complexity: N1 (1)
- Error: missing gates: ['EVIDENCE_GATE', 'TRACEABILITY_GATE']
- Error: complexity N1 not in ['N2', 'N3']

### U19 — data_analysis_paraphrase
- Input: Examine a planilha de clientes, descubra quais variáveis estão mais associadas ao cancelamento e recomende as três ações prioritárias.
- Selected: none
- Complexity: N0 (0)
- Error: complexity N0 not in ['N2', 'N3']

### U20 — data_summary
- Input: Calcule as métricas principais da tabela e explique os dois movimentos mais relevantes.
- Selected: none
- Complexity: N0 (0)
- Error: complexity N0 not in ['N1', 'N2']

### U21 — calendar_state
- Input: Mova a reunião com a equipe para sexta-feira às 14h, mantendo os mesmos convidados.
- Selected: none
- Complexity: N0 (0)
- Error: complexity N0 not in ['N2', 'N3']

### U24 — destructive_paraphrase
- Input: Limpe definitivamente todos os registros de teste do banco, sem possibilidade de restauração.
- Selected: none
- Complexity: N0 (0)
- Error: missing gates: ['DESTRUCTIVE_ACTION_GATE']
- Error: complexity N0 not in ['N3', 'N4']

### U25 — human_approval_paraphrase
- Input: Prepare tudo, mas não aplique a mudança até eu responder explicitamente que está aprovado.
- Selected: none
- Complexity: N0 (0)
- Error: missing gates: ['HUMAN_APPROVAL_GATE']
- Error: complexity N0 not in ['N2', 'N3']

### U26 — current_research_paraphrase
- Input: Levante as soluções mais recentes para observabilidade de agentes e compare preço, maturidade e integrações.
- Selected: none
- Complexity: N0 (0)
- Error: complexity N0 not in ['N2', 'N3']

### U27 — research_build_paraphrase
- Input: Descubra qual biblioteca OAuth atual atende melhor aos requisitos e integre-a no projeto com testes.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P01']
- Error: complexity N0 not in ['N2', 'N3']

### U28 — ambiguous_improvement
- Input: Aprimore o projeto.
- Selected: none
- Complexity: N0 (0)
- Error: complexity N0 not in ['N1', 'N2']

### U29 — preserving_rewrite
- Input: Refaça a implementação do zero, porém mantenha o output byte a byte idêntico para os mesmos inputs.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P02']
- Error: missing gates: ['REGRESSION_GATE']
- Error: complexity N0 not in ['N2', 'N3']

### U30 — large_summary_paraphrase
- Input: Condense um dossiê de 300 folhas em três páginas sem perder datas, números nem divergências entre fontes.
- Selected: none
- Complexity: N0 (0)
- Error: complexity N0 not in ['N2', 'N3']

### U31 — youtube_build_paraphrase
- Input: Produza um Short de 45 segundos com hook, narração, sequência de cenas, prompts visuais e CTA.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P01']
- Error: complexity N0 not in ['N2', 'N3']

### U32 — youtube_review
- Input: Audite o vídeo final antes do upload: cheque retenção, claims, mapa, continuidade, voz e mixagem.
- Selected: none
- Complexity: N1 (1)
- Error: complexity N1 not in ['N2', 'N3']

### U33 — youtube_local_repair
- Input: O mapa da cena 2 está geograficamente incorreto; todo o restante está aprovado. Repare só esse trecho e revalide o resultado.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P03']
- Error: complexity N0 not in ['N1', 'N2']

### U34 — laf_documentary
- Input: Monte o histórico processual a partir das peças do processo, separe constatação documental de juízo técnico e indique lacunas de prova.
- Selected: none
- Complexity: N0 (0)
- Error: missing gates: ['EVIDENCE_GATE', 'TRACEABILITY_GATE']
- Error: complexity N0 not in ['N3', 'N4']

### U35 — laf_normative
- Input: Confronte a demanda administrativa com a documentação e a base normativa fornecida e mostre a consequência técnica de cada pendência.
- Selected: none
- Complexity: N0 (0)
- Error: missing gates: ['EVIDENCE_GATE', 'TRACEABILITY_GATE']
- Error: complexity N0 not in ['N3', 'N4']

### U36 — security_review_paraphrase
- Input: Faça um threat model do fluxo de login e procure caminhos de abuso; não implemente correções nesta etapa.
- Selected: P01
- Complexity: N1 (1)
- Error: forbidden patterns selected: ['P01']
- Error: complexity N1 not in ['N2', 'N3']
- Error: unexpected selected patterns: ['P01']

### U37 — security_build
- Input: Implemente login com segundo fator, expiração de sessão e recuperação segura de conta, incluindo revisão antes do release.
- Selected: P01
- Complexity: N1 (3)
- Error: missing gates: ['INDEPENDENT_REVIEW_GATE']
- Error: complexity N1 not in ['N3', 'N4']

### U38 — rollback_state
- Input: Faça rollback da última implantação e confirme que a versão anterior voltou a atender o tráfego.
- Selected: none
- Complexity: N0 (0)
- Error: missing gates: ['REGRESSION_GATE']
- Error: complexity N0 not in ['N2', 'N3']

### U39 — quality_preserving_perf
- Input: Aumente a vazão do modelo sem reduzir o F1 e sem ultrapassar o orçamento atual de GPU.
- Selected: none
- Complexity: N0 (0)
- Error: missing required patterns: ['P05']
- Error: missing gates: ['BASELINE_GATE', 'REGRESSION_GATE']
- Error: complexity N0 not in ['N2', 'N3']

### U40 — mixed_debug_perf
- Input: Resolva a exceção atual e depois confira se o tempo de resposta continua dentro do valor anterior.
- Selected: none
- Complexity: N2 (2)
- Error: missing required patterns: ['P03']
- Error: missing gates: ['BASELINE_GATE', 'REGRESSION_GATE']

### U41 — file_dependency
- Input: Use os arquivos anexados para gerar uma síntese e cite de qual arquivo veio cada afirmação material.
- Selected: none
- Complexity: N0 (0)
- Error: missing gates: ['EVIDENCE_GATE', 'TRACEABILITY_GATE']
- Error: complexity N0 not in ['N2', 'N3']

### U44 — design_ui
- Input: Projete a arquitetura do painel administrativo e depois implemente a interface responsiva e acessível.
- Selected: P01, P04, P08
- Complexity: N2 (6)
- Error: complexity N2 not in ['N3', 'N4']

### U45 — refactor_boundaries
- Input: Reorganize o serviço em módulos de domínio, aplicação e infraestrutura mantendo a API atual intacta.
- Selected: P02, P06
- Complexity: N1 (0)
- Error: missing gates: ['REGRESSION_GATE']
- Error: complexity N1 not in ['N2', 'N3']

### U46 — destructive_data
- Input: Remova permanentemente todas as contas de demonstração e seus dados associados.
- Selected: none
- Complexity: N0 (0)
- Error: missing gates: ['DESTRUCTIVE_ACTION_GATE']
- Error: complexity N0 not in ['N3', 'N4']

### U48 — parallel_review
- Input: Peça três avaliações independentes da mesma proposta e produza uma síntese final apontando concordâncias e conflitos.
- Selected: none
- Complexity: N0 (0)
- Error: missing gates: ['INDEPENDENT_REVIEW_GATE']
- Error: complexity N0 not in ['N2', 'N3']

### U49 — critical_migration
- Input: Migre o núcleo de pagamentos por etapas, sem quebrar compatibilidade, com checagem independente de segurança e desempenho antes do corte final.
- Selected: P02
- Complexity: N1 (4)
- Error: missing required patterns: ['P04']
- Error: missing gates: ['INDEPENDENT_REVIEW_GATE']
- Error: complexity N1 not in ['N3', 'N4']
