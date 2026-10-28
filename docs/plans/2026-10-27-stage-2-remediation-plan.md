# Stage-2 — Remediação do Percival AgentMail MCP

**Data / revisão:** 2026-10-27 / 1.0.  
**ID / estado:** S2-AM / planejado; execução não iniciada.  
**Checkout executor:** `/home/bill/Projects/percival-agentmail-mcp`.  
**Responsável:** executor AgentMail a designar por bill; broker e operação com seus donos.

## 1. Objetivo e origem

Resolver ou tratar explicitamente os 13 achados da **seção 6** do
[relatório AgentMail](../../../positronic-bean-IaC/docs/reports/2026-10-26-percival-agentmail-mcp-iac-readiness-report.md#6-achados-issues-e-inconsistências),
com ações/aceites das seções 7 e 9. São 10 ações (2 P1, 5 P2, 3 P3), sem P0.
Baseline e HEAD na emissão: `68751b696b62b53fdcf893c3add9cf9e648e4391`.
Exclusão local preexistente de `docs/security/f3-status.md` preservada.

[Coordenador stage-2](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
— retorno S2-AM, seções 3 e 7. Fontes comuns:
[consolidação](../../../positronic-bean-IaC/docs/reports/2026-10-26-stage-1-consolidated-readiness-report.md)
e [D-01..D-06](../../../positronic-bean-IaC/docs/decisions/2026-10-27-iac-stage-1-scope-and-pilot-decisions.md).

Este plano é documental nesta emissão; execução futura somente no projeto dono.
Preservar 24 tools, envelopes de conteúdo não confiável, erros sanitizados e rate
limit. Preservar 3 prompts por padrão até decisão de compatibilidade: o fato de o
Percival não consumi-los não torna inválida a capacidade MCP do servidor.
Não é o par piloto D-01. Nenhum acesso a inbox real, envio/exclusão de mensagem,
publicação ou mutação de runtime é autorizado pela escrita do plano.

## 2. Preparação e decisões

- [ ] Ler `AGENTS.md`, README, `.env.example` e documentação disponível; registrar
  SHA/worktree, dependências/CI e destino da nota de segurança removida com o owner.
- [ ] Reproduzir os achados com credencial/inbox sintéticos e upstream fixture;
  tratar `inbox_id` como segredo, inclusive em logs/resultados de teste.
- [ ] Solicitar revisão mínima S2-C01 para segredo/mounts/lifecycle e S2-C03 para
  metadados. A-001/A-003/A-009 podem avançar sem aguardar contrato inteiro.
- [ ] Dimensionar lotes com bill (D-06); receita de broker/piloto depende de D-05
  e do P0 `nanobot/A-001` fechado, sem operação real implícita.

## 3. Backlog integral e aceite

Estado inicial: **não iniciada** para todas as ações; A-006/A-007 têm dependência
externa ainda não resolvida. As prioridades abaixo são as da ação de origem.

| Ação | Achados / P | Trabalho e áreas previstas | Dependência / dono externo | Critério de verificação |
|---|---|---|---|---|
| A-001 | F-001, F-012, F-013 / P2 | Omitir/mascarar inbox no startup; sanitizar erro de transporte sem traceback público; remover ou tornar explícita leitura `.env` em config/server | Nenhuma dependência externa para fix local | Canário inbox ausente dos logs INFO; rede indisponível com diagnóstico sanitizado; `.env` arbitrário no cwd não lido sem opt-in; nenhuma regressão de secret file |
| A-002 | F-002 / P2 | Tratar SIGTERM/SIGINT com cancelamento do lifespan e fechamento do pool; se optar por limitação, decisão explícita e contrato | Dono do produto + `nanobot` S2-NB-X01/S2-C01 | Hook e exit code observados em sinal/EOF; drain limitado, ou 143/sem-drain aceito e declarado pelo owner sem alegar shutdown gracioso |
| A-003 | F-003 / P3 | Repassar argumentos no entrypoint Compose ou recusar forma não suportada explicitamente | Receita local, sem iniciar serviço real | `docker compose run --rm -T server --version` imprime versão sem startup/upstream; alternativa de recusa documentada exige decisão de owner |
| A-004 | F-004 / P2 | Preparar `server.json` e metadata/rótulos conforme formato adotado; distinguir índice PBLabs e Docker MCP Catalog opcional | S2-C03; etapas 2/4 IaC, owner do índice | Schema externo válido na revisão adotada; identidade/imagem/transporte/versão coerentes; rótulos aplicáveis e referência de catálogo real quando publicada |
| A-005 | F-005 / P2 | Rescan do artefato atual, triagem/VEX por CVE e atualização da nota de segurança no destino acordado | Pipeline/CI e responsável de distribuição; etapa 2 IaC | DB/data/scanner/SHA/image ID registrados; scan e decisão VEX aplicáveis ao candidato, não à base histórica; CI externo com evidência própria |
| A-006 | F-011 / P1 | Declarar perfil stateless sem bind de host e confirmar a hipótese contra broker vigente; implementação no dono | S2-NB-X01 + S2-C01 | Matriz de mounts versionada; caso AgentMail passa com `mounts=[]`, sem bind `/`; nenhuma reabertura de controle/segredos do host |
| A-007 | F-007 / P1 | Decidir health de startup e fixture offline suportada pelo produto: endpoint de teste ou deferimento explícito; documentar egress | Produto + S2-C01 | Caminho offline reproduzível sem monkeypatch externo oculto, ou dependência de egress/limite formalmente aceita; exclusão do piloto já mantida por D-01 |
| A-008 | F-008 / P2 | Documentar preferência `AGENTMAIL_API_KEY_FILE` e alinhar consumidor/instalador com suporte existente do MCP | S2-NB-X01/S2-C01; instalador etapa 3 IaC | Arquivo RO/referência e restrição de symlink comprovados; broker não precisa guardar literal para esse perfil; decisão de owner e teste do consumidor |
| A-009 | F-009, F-010 / P3 | Reconciliar docs de estado/changelog/segurança com SHA e registrar decisão sobre mypy; verificar ausência de arquivo de licença apontada no §6 | Owner para tipagem/licença/atribuição | Contagens medidas, sem copiar números do diagnóstico; decisão datada de tipagem (não obrigação inferida); licença/atribuição coerentes, sem inventar autoria |
| A-010 | F-006 / P3 | Alinhar apresentação/consumo dos 3 prompts, preferindo documentar suporte por cliente ou flag compatível | Dono do consumidor `nanobot` A-010 | `prompts/list`/capabilities coerentes no perfil adotado; clientes MCP diretos preservados; remoção/breaking change só após decisão conjunta |

F-010 é melhoria/decisão consciente, não defeito obrigatório de tipagem. F-011
era hipótese bloqueada no relatório: confirmar no broker antes de afirmar defeito
atual. A-007 não se encerra apenas repetindo que o MCP está fora do piloto: a
política de startup/egress precisa ser explicitada e validada conforme a decisão.

## 4. Lotes e coordenação externa

1. **AM-1:** A-001/A-002, A-003 e atualização A-009. Logs/config/lifecycle devem
   preservar o contrato wire-level; nenhum inbox/credencial real em fixture.
2. **AM-2:** A-006/A-007/A-008 após revisão mínima de S2-C01, com implementação
   broker em S2-NB-X01. O plano AgentMail recebe evidência; não altera `nanobot`
   nem registries dos gestores diretamente.
3. **AM-3:** A-004/A-005 após contrato do índice/candidato; A-010 com consumidor.
   Publicação/PR remota/catalog import real são passos externos das etapas 2/4/5,
   com autorizações próprias; documento local não equivale a release.

Riscos: mudar lifespan afeta pool/retry; alterar `.env` afeta configuração existente;
alterar prompts/schema quebra clientes. Registrar compatibilidade e decisões,
sem assumir prazos, orçamento ou adesão de usuários a um novo profile.

## 5. Qualificação futura no checkout

- [ ] Regressões dos casos observados e suíte `uv run pytest --cov` com limiar
  vigente; `uv run ruff check .` e `uv run ruff format --check .` conforme CI.
- [ ] Build/smoke offline, `initialize` → `notifications/initialized` → `tools/list`
  → chamada segura com upstream fixture; stdout JSON-RPC, stderr sem segredo.
- [ ] Repetir `V-RUN`/`V-CONFIG`/`V-MCP`/`V-FUNC` e `V-BUILD` se imagem mudar;
  `V-DATA` não aplicável para stateless. `V-PILOT`/`V-REUSE` só mudam com prova.
- [ ] Sinais/EOF com init único do gestor, fechamento do pool e limites de saída;
  preservar testes de secret file/symlink, rede e envelopes de email.
- [ ] Aceite externo de mount/secret no broker recebido; scan/CI/publicação por
  artefato e provedor real, se exigido, em sandbox explicitamente aprovada.

Fixture não homologa AgentMail real nem envio de email. Gate externo pendente
mantém a ação aberta/parcial, mesmo que os testes locais estejam verdes.

## 6. Penúltima etapa — documentar execução neste plano

- [ ] Atualizar cada ação com resultado, data/owner, SHA inicial/final, testes,
  ambiente e links para evidências sanitizadas em `docs/` deste projeto.
- [ ] Registrar decisões de produto/limites e revalidação `V-*`; complementar
  seção 9 do relatório IaC quando autorizado, sem reescrever a coleta histórica.

| Data / owner | Ações / achados | SHA inicial → final | Mudanças / evidências locais | Resultado / V-* / pendências |
|---|---|---|---|---|
| Pendente | A-001–A-010 | A registrar | Nenhuma execução nesta emissão | Não iniciada |

## 7. Última etapa — atualizar o plano coordenador

- [ ] Reler o [stage-2 geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md),
  atualizar **S2-AM na seção 3** e acrescentar resultado na **seção 7**, com
  contagens, SHA/evidência, dependências liberadas e aceites locais/externos.
- [ ] Preservar retornos dos demais e informar reflexo nas etapas 2/4/5. Sem
  acesso à IaC, fornecer retorno e manter **aguardando sincronização**. Só declarar
  concluído com aceites e retorno efetivos; pendência/transferência é estado parcial.
