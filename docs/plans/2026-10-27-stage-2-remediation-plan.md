# Stage-2 — Remediação do Percival AgentMail MCP

**Data / revisão:** 2026-10-27 / 1.2.
**ID / estado:** S2-AM / execução parcial; A-001/A-002/A-003 verificadas localmente; dependências externas abertas.
**Checkout executor:** `/home/bill/Projects/percival-agentmail-mcp`.  
**Responsável:** executor técnico `<positronic>`; bill confirmado como owner do produto AgentMail e do broker Nanobot; owner de release/índice ainda a designar.

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

Plano emitido documentalmente em 1.0; execução local parcial registrada nesta revisão 1.2.
Preservar 24 tools, envelopes de conteúdo não confiável, erros sanitizados e rate
limit. Preservar 3 prompts por padrão até decisão de compatibilidade: o fato de o
Percival não consumi-los não torna inválida a capacidade MCP do servidor.
Não é o par piloto D-01. Nenhum acesso a inbox real, envio/exclusão de mensagem,
publicação ou mutação de runtime é autorizado pela escrita do plano.

## 2. Preparação e decisões

- [ ] Ler `AGENTS.md`, README, `.env.example` e documentação disponível; registrar
  SHA/worktree e dependências/CI. `R-05` já define o destino F3 como
  `pblabs-mcp-index`; preservar a exclusão local da nota, sem criar espelho.
- [ ] Reproduzir os achados com credencial/inbox sintéticos e upstream fixture;
  tratar `inbox_id` como segredo, inclusive em logs/resultados de teste.
- [ ] Decisões do operador de 2026-10-28 aplicáveis: `R-02` fixa `mounts=[]`
  como default do broker, com mounts explícitos e `null` sujeito a confirmação
  e auditoria separadas; `R-03` remove a exigência de estimar esforço, custo ou
  prazo; `R-05` centraliza o tracker F3 em `pblabs-mcp-index`, por imagem
  publicada, com checkouts por link; `R-06` adota o schema externo de
  `server.json`, `pblabs.app.yaml` como extensão operacional versionada e o
  índice PBLabs como destino, sem dependência do Docker MCP Catalog; `R-07`
  exige VEX por CVE associado ao image ID e assinado pelo owner, com CVEs da
  imagem base tratados por herança; `R-09` fixa a matriz de cancelamento/deadline
  por transporte, método e deadline, permitindo declarar limitações sem exigir
  implementação geral de cancelamento.
- [ ] Solicitar revisão mínima S2-C01 para segredo/mounts/lifecycle e S2-C03 para
  materializar os formatos já decididos. A-001/A-003/A-009 podem avançar sem
  aguardar contrato inteiro. A prova de mounts do broker continua pendente; a
  política não está mais em aberto. Não há operação real implícita.

## 3. Backlog integral e aceite

Estado inicial: **não iniciada** para todas as ações; A-006/A-007 têm dependência
externa ainda não resolvida. As prioridades abaixo são as da ação de origem.

| Ação | Achados / P | Trabalho e áreas previstas | Dependência / dono externo | Critério de verificação |
|---|---|---|---|---|
| A-001 | F-001, F-012, F-013 / P2 | Omitir/mascarar inbox no startup; sanitizar erro de transporte sem traceback público; remover ou tornar explícita leitura `.env` em config/server | Nenhuma dependência externa para fix local | **Verificada localmente:** sem inbox em logs INFO; erro de config sem traceback; falha de rede com credenciais/inbox sintéticos em `--network=none` gerou `ConnectError` sanitizado, exit 1 e sem traceback; cwd `.env` ignorado salvo `AGENTMAIL_ENV_FILE`; testes de secret-file/symlink mantidos. |
| A-002 | F-002 / P2 | Tratar SIGTERM/SIGINT com cancelamento do lifespan e fechamento do pool; declarar a limitação e o deadline do serviço | Owner do produto e broker: bill; S2-NB-X01/S2-C01; `R-09` | **Implementada/verificada localmente:** grace de 2 s, seguida de cancelamento do trabalho remanescente e fechamento protegido do pool até 5 s; Compose local dá 10 s. Testes cobrem tool lenta e close protegido. A matriz comum registra suporte/limitação por transporte, método e deadline; isso não torna a grace de container uma exigência de cancelamento MCP end-to-end. O broker precisa adotar timeout compatível e passar teste próprio. |
| A-003 | F-003 / P3 | Repassar argumentos no entrypoint Compose ou recusar forma não suportada explicitamente | Receita local, sem iniciar serviço real | **Verificada localmente:** `docker compose run --rm -T server --version` imprimiu versão e saiu sem startup/upstream; montagens usaram `.env.example` como fixture, sem segredo real. `docker compose config --quiet` passou. |
| A-004 | F-004 / P2 | Preparar `server.json` e metadata/rótulos conforme `R-06`; distinguir índice PBLabs e Docker MCP Catalog opcional | S2-C03; etapas 2/4 IaC, owner do índice | Schema externo adotado materializado/validado; identidade/imagem/transporte/versão coerentes; `pblabs.app.yaml` operacional versionado e destino `pblabs-mcp-index`; Docker MCP Catalog não é dependência |
| A-005 | F-005 / P2 | Rescan do artefato atual, triagem/VEX por CVE conforme `R-07` e referência ao tracker F3 canônico | Pipeline/CI e owner de release/índice; etapa 2 IaC | Build local atual (linux/amd64, tag `dev`, revision label `local`) concluído; Trivy/Grype/Syft ausentes, portanto sem scan/SBOM/VEX nesta execução. Produzir scan/SBOM do candidato e VEX por CVE ligado ao image ID e assinado pelo owner; CVEs herdados da imagem base seguem a postura por herança; imagem local não é candidata publicada |
| A-006 | F-011 / P1 | Declarar perfil stateless sem bind de host e confirmar a hipótese contra broker vigente; implementação no dono | Owner do broker Nanobot: bill; S2-NB-X01 + S2-C01; `R-02` | Perfil decidido: `mounts=[]` para serviço stateless, com mounts explícitos estreitos read-only para secrets quando suportados; `null` somente como operação separada, confirmada e auditada. Implementação e prova no broker ainda pendentes; hipótese F-011 não fechada |
| A-007 | F-007 / P1 | Decidir health de startup e fixture offline suportada pelo produto: endpoint de teste ou deferimento explícito; documentar egress | Produto + S2-C01 | **Decisão ratificada pelos owners AgentMail e broker (bill), 2026-10-27:** aceitar egress ao AgentMail no perfil normal; não introduzir fixture/override de endpoint no runtime de produto. Startup exige conectividade válida; fixture CI é simulada e não homologa provider. Incorporar no S2-C01 continua pendente; D-01 mantém AgentMail fora do piloto. |
| A-008 | F-008 / P2 | Documentar preferência `AGENTMAIL_API_KEY_FILE` e alinhar consumidor/instalador com suporte existente do MCP | Owner do broker Nanobot: bill; S2-NB-X01/S2-C01; instalador etapa 3 IaC | **Preferência aceita para revisão:** chave por arquivo read-only/referência; implementação do broker/instalador e teste do consumidor pendentes. MCP valida arquivo regular e rejeita symlink; isso não prova entrega pelo broker. |
| A-009 | F-009, F-010 / P3 | Reconciliar docs de estado/changelog/segurança com SHA e registrar decisão sobre mypy; verificar ausência de arquivo de licença apontada no §6 | Owner para tipagem/licença/atribuição | **Parcial:** `LICENSE` MIT criado; CHANGELOG/README/docs atualizados; `mypy` segue não configurado conforme PROJECT.md. Evidência de scan será referenciada neste plano; scanner/CI ainda pendentes. A nota F3 antiga permanece excluída, mas seu destino canônico foi decidido por `R-05`: `pblabs-mcp-index`, sem espelho de conteúdo neste checkout |
| A-010 | F-006 / P3 | Alinhar apresentação/consumo dos 3 prompts, preferindo documentar suporte por cliente ou flag compatível | Dono do consumidor `nanobot` A-010 | **Decisão do owner Nanobot (bill), 2026-10-27:** manter os 3 prompts no servidor por padrão; não remover nem ocultar por flag. Nanobot não os consome atualmente; registrar como limitação do consumidor, não defeito do servidor. Suporte MCP direto coberto pela suíte local; mudança futura exige decisão conjunta e teste de compatibilidade. |

F-010 é melhoria/decisão consciente, não defeito obrigatório de tipagem. F-011
era hipótese bloqueada no relatório: confirmar no broker antes de afirmar defeito
atual. A-007 não se encerra apenas repetindo que o MCP está fora do piloto: a
política de startup/egress precisa ser explicitada e validada conforme a decisão.

### Decisões recebidas do operador — 2026-10-27 e 2026-10-28

- Bill confirma ser o owner do produto AgentMail e do broker Nanobot; ratifica
  egress no startup e escolhe shutdown limitado (2 s grace + pool close até 5 s),
  verificado em teste local com tool lenta.
- Bill aceita preservar os três prompts, escolhe artefatos CI com referência no
  plano como destino de scan/VEX, e Positronic Bean Labs como titular do `LICENSE` MIT.
- Para o perfil normal AgentMail, egress ao provider no startup é ratificado pelo
  owner do produto; nenhuma fixture/override de endpoint será adicionada ao runtime.
  A decisão não homologa o provider nem altera a exclusão do piloto D-01; sua
  incorporação no contrato S2-C01 ainda aguarda review comum.
- Revisões mínimas S2-C01/S2-C03 foram solicitadas; os contratos ainda não existem
  nesta revisão e seus drafts ficam sujeitos aos owners IaC, produto e release/índice.
- O destino do novo scan será artefato CI com referência no plano. `R-07` define
  o gate VEX e sua assinatura; produção/retenção das evidências segue pendente.
  `R-05` centraliza F3 por image ID em `pblabs-mcp-index`. A exclusão local da
  nota antiga permanece intacta e não deve ser substituída por cópia concorrente.

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
alterar prompts/schema quebra clientes. Registrar compatibilidade; `R-03` remove
a exigência de estimar esforço, custo ou prazo.

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
| 2026-10-27 / executor Positronic | A-001/A-002/A-003 verificadas localmente; A-007 ratificada; A-009 parcial; A-010 limitação aceita; A-004/A-005/A-006/A-008 abertas | `68751b696b62b53fdcf893c3add9cf9e648e4391` → SHA final após commit | `pytest --cov`: 244 passed/1 skipped, 91,51%; Ruff/format; Compose config/build/version smoke; subprocess MCP `initialize` + tool lenta + SIGTERM demonstrou grace/hook/exit 0; imagem local `sha256:3549964cf53c12e3df730b9fab23967af53f40768300a31a8200caec957e7975`, linux/amd64, OCI revision=`local`. Scanner ausente; sem scan. | Parcial; sem inbox real, publicação ou alteração broker; S2-C01/C03 em draft; A-005 aguarda CI/scanner, A-006/A-008 broker; owner release/índice pendente; sem commit |

## 7. Última etapa — atualizar o plano coordenador

- [ ] Reler o [stage-2 geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md),
  atualizar **S2-AM na seção 3** e acrescentar resultado na **seção 7**, com
  contagens, SHA/evidência, dependências liberadas e aceites locais/externos.
- [ ] Preservar retornos dos demais e informar reflexo nas etapas 2/4/5. Sem
  acesso à IaC, fornecer retorno e manter **aguardando sincronização**. Só declarar
  concluído com aceites e retorno efetivos; pendência/transferência é estado parcial.
