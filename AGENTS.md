# Instruções permanentes do Codex — compiler

Este arquivo orienta o comportamento do Codex **quando carregado no checkout**. Não implanta runtime, credenciais, PEP, subagentes ou conexões externas.

## Orquestração

- Examine automaticamente cada tarefa. Delegue a subagentes **apenas se** a versão instalada do Codex tiver suporte comprovado e houver frentes independentes, revisões de risco ou pesquisa somente leitura realmente úteis. O usuário não precisa repetir o pedido de delegação.
- Prefira scouts somente leitura, com objetivo delimitado, escopo, tempo, permissão, formato de resultado e prova de origem. Não delegue tarefas curtas ou estritamente sequenciais.
- Não conceda a agente filho ferramentas, dados ou privilégios que o executor principal não possua. Escritas devem ter proprietário exclusivo de arquivo e passar por revisão independente.
- Se a ferramenta de delegação não existir, não simule uma execução multiagente; informe `AUTO_DELEGATION_NOT_PROVEN`.

## Proteção e governança

- `PUBLICATION=BLOCKED` e `DISTRIBUTED_RUNTIME_ENABLED=false` por padrão. **Não** fazer merge, deploy, publicação, chamada paga, gestão de tokens ou mudança de ACL sem autorização explícita.
- É obrigatório autenticar executor e impor permissões de filesystem, rede, ferramentas, MCP e recursos por mecanismos reais de execução. Texto em `AGENTS.md` não é um mecanismo de enforcement.
- Não presumir acesso ao REA canônico, ao AVIA ou aos demais repositórios. Contratos versionados só podem ser usados depois de reconciliar hashes, commits e autorização cross-repo.
- Registre resultados separados como `DOCUMENTED`, `MOCK_TESTED`, `REAL_RUNTIME_TESTED`, `DEPLOYED` e `BLOCKED`. Logs sem provenance verificável não comprovam execução real.
- Regras específicas deste agente: compilação/validação de prompts; proíba elevar permissões via prompt compilado.
- Mantenha memória e dados específicos de domínio isolados; compartilhe somente contratos e evidência mínima sanitizada.
- Escalar somente após testes negativos de auth/authz, isolamento, delegação e E2E do consumidor; preservar rollback e revisão independente.

## Dependência de integração (ainda pendente)

REA candidato: `luisfabricioviana-dev/Apredizagem-e-Inova-o` PR #156; AVIA candidato: `luisfabricioviana-dev/agente-youtube` PR #549. Instruções persistentes propostas: REA PR #157 e AVIA PR #550. Nenhuma dessas PRs deve ser presumida mesclada ou operacional. Consulte o Space “Integração de Subagentes — Runtime Codex | Ecossistema REA/AVIA” para critérios de promoção.

Até provas de runtime, identidade e E2E: `PUBLICATION=BLOCKED`.
