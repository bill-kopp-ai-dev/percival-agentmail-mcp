# Stage-2 — Remediação do Percival AgentMail MCP

**Data / revisão:** 2026-10-29 / 1.4.
**ID / estado:** S2-AM / execução parcial; A-001/A-002/A-003 verificadas localmente; R-11 e decisões R-12–R-15 registradas; A-005 continua aberta, sem scan do candidato; implementação/provas do broker e dependências externas abertas.
**Checkout executor:** `/home/bill/Projects/percival-agentmail-mcp`.  
**Owner e autoridade final:** Bill Kopp (`bill.kopp.dev@gmail.com`), único owner e decisor do servidor MCP e da infraestrutura IaC da Positronic Bean Labs. `labs.positronicbean.com` está em desenvolvimento, não é endpoint operacional.
**Execução técnica:** executor `<positronic>` pode implementar e validar localmente; decisões de produto/infra e aprovação final de VEX/promoção permanecem com Bill.

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

Plano emitido documentalmente em 1.0; execução local parcial registrada nesta revisão 1.4.
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
- [x] Decisões anteriores do owner: `R-10` (2026-10-29) supersede `R-02` quanto ao default
  do broker Percival, que permanece amplo conforme B14/B22/B23–B25; AgentMail é
  stateless e seu perfil deve configurar explicitamente `mounts=[]`, sem depender
  do default amplo. Transição de perfil mais restrito para Full exige confirmação
  e auditoria; `R-03` remove a exigência de estimar esforço, custo ou
  prazo; `R-05` centraliza o tracker F3 em `pblabs-mcp-index`, por imagem
  publicada, com checkouts por link; `R-06` adota o schema externo de
  `server.json`, `pblabs.app.yaml` como extensão operacional versionada e o
  índice PBLabs como destino, sem dependência do Docker MCP Catalog; `R-07`
  exige VEX por CVE associado ao image ID e assinado pelo owner, com CVEs da
  imagem base tratados por herança; `R-09` fixa a matriz de cancelamento/deadline
  por transporte, método e deadline, permitindo declarar limitações sem exigir
  implementação geral de cancelamento.
- [x] `R-11` (2026-10-29): Trivy é o scanner padrão e está instalado; o agente
  pode executar scans locais autonomamente quando necessários, cobrindo todas
  as severidades, atualizando a DB e registrando versão, DB, SHA e image ID.
  Preferir TAR do candidato sem Docker socket. Isto não substitui CI nem autoriza
  VEX, release ou promoção; VEX segue ligado ao image ID e assinado pelo owner
  conforme `R-07`.
- [x] Bill aprovou para AgentMail o uso dos templates S2-C01/S2-C03 e do perfil
  operacional de referência no índice. As decisões específicas, seus efeitos e
  referências estão registradas abaixo; aprovação documental não significa
  adoção pelo broker, promoção ou autorização de operação real.
- [ ] Registrar o perfil aprovado nos contratos/manifests aplicáveis e provar
  entrega de secret, mounts e lifecycle no broker/consumidor. A-001/A-003/A-009
  podem avançar sem aguardar essa prova.

### Decisões explícitas do owner — 2026-10-29

Bill declarou: “Eu (Bill) sou único o "owner" do servidor MCP e também o único
"owner" e responsável pela infraestrtura IaC. Eu estou criando esses servidores
MCP e infraestrutura adjacente para minha empresa a "Positronic Bean Labs".
Dessa forma eu sou a única pessoa responsável pode decidir qualquer aspecto da
aplicação e da infraestrutura, logo minhas decisões são absolutas.”

Identidade registrada: **Bill Kopp**, `bill.kopp.dev@gmail.com`; **Positronic Bean
Labs**; `labs.positronicbean.com` (em desenvolvimento, não operacional).

| ID | Decisão recebida verbatim | Efeito no plano |
|---|---|---|
| R-12 | “Quem assina a promoção e o VEX? R - Eu, Bill.” | Bill é o único signatário/aprovador final de VEX e promoção. O executor pode preparar evidências e propostas; promoção continua condicionada à identidade do artefato publicado e à aprovação explícita de Bill. |
| R-13 | “Qual é o contrato de mounts e secrets do AgentMail? R - Nos temos um template de contrato definido, veja em </home/bill/Projects/positronic-bean-IaC> e em </home/bill/Projects/pblabs-mcp-index>. Use esse template.” | Aplicar [Agent runtime contract](../../../positronic-bean-IaC/docs/agent-runtime-contract.md), [MCP application contract](../../../positronic-bean-IaC/docs/mcp-app-contract.md), o [perfil AgentMail de referência](../../../pblabs-mcp-index/servers/agentmail/pblabs.app.yaml) e as [propostas de perfil](../../../pblabs-mcp-index/docs/profile-proposals.md). Para AgentMail, `mounts=[]` significa sem bind de host/workspace; dados graváveis são falsos; egress é necessário; metadata declara requisitos, não concede privilégios. Segredos usam referência/arquivo read-only estreito gerenciado pelo broker, sem ampliar os binds da aplicação. A aplicação suporta `AGENTMAIL_API_KEY_FILE`; API key e inbox ID permanecem secretos conforme `AGENTS.md`. O manifest do índice é rascunho e hoje lista apenas `AGENTMAIL_API_KEY`; a proposta de perfil ainda indica injeção por env e classifica inbox ID como não secreto, em conflito com o suporte atual a arquivo e a regra deste projeto. Reconciliar esses pontos antes de aprovar/publicar metadata, sem afirmar que o broker já entrega secrets. |
| R-14 | “Como registrar lifecycle e startup no S2-C01? R - Vamos seguir com a sua sugestão: "documentar esses valores como perfil específico do AgentMail e exigir um teste do broker com timeout compatível, sem transformá-los em regra universal para todos os MCPs"” | S2-C01 registra AgentMail como perfil específico: startup depende de egress ao provider; shutdown usa grace de 2 s e fechamento do pool limitado a 5 s. Exigir teste do broker com timeout compatível; não generalizar esses números para outros MCPs. |
| R-15 | “Que tratamento dar a cada CVE do candidato? R - Vamos seguir com sua sugestão: "Sugiro decidir achado a achado, com evidência: corrigir ou justificar a disposição no VEX. Evitaria uma aprovação genérica que cubra candidatos ou image IDs futuros"” | Após cada scan, Bill decide cada achado com evidência, por candidato/image ID; corrigir ou justificar sua disposição no VEX. Não há waiver genérico para outros candidatos/image IDs. |

## 3. Backlog integral e aceite

Estado inicial em 2026-10-27: **não iniciada** para todas as ações. Nesta revisão,
A-007 tem decisão de produto ratificada e aguarda incorporação/prova no contrato;
A-006 ainda depende de implementação e prova no broker. As prioridades abaixo
são as da ação de origem.

| Ação | Achados / P | Trabalho e áreas previstas | Dependência / dono externo | Critério de verificação |
|---|---|---|---|---|
| A-001 | F-001, F-012, F-013 / P2 | Omitir/mascarar inbox no startup; sanitizar erro de transporte sem traceback público; remover ou tornar explícita leitura `.env` em config/server | Nenhuma dependência externa para fix local | **Verificada localmente:** sem inbox em logs INFO; erro de config sem traceback; falha de rede com credenciais/inbox sintéticos em `--network=none` gerou `ConnectError` sanitizado, exit 1 e sem traceback; cwd `.env` ignorado salvo `AGENTMAIL_ENV_FILE`; testes de secret-file/symlink mantidos. |
| A-002 | F-002 / P2 | Tratar SIGTERM/SIGINT com cancelamento do lifespan e fechamento do pool; declarar a limitação e o deadline do serviço | Owner do produto e broker: bill; S2-NB-X01/S2-C01; `R-09` | **Implementada/verificada localmente:** grace de 2 s, seguida de cancelamento do trabalho remanescente e fechamento protegido do pool até 5 s; Compose local dá 10 s. Testes cobrem tool lenta e close protegido. A matriz comum registra suporte/limitação por transporte, método e deadline; isso não torna a grace de container uma exigência de cancelamento MCP end-to-end. O broker precisa adotar timeout compatível e passar teste próprio. |
| A-003 | F-003 / P3 | Repassar argumentos no entrypoint Compose ou recusar forma não suportada explicitamente | Receita local, sem iniciar serviço real | **Verificada localmente:** `docker compose run --rm -T server --version` imprimiu versão e saiu sem startup/upstream; montagens usaram `.env.example` como fixture, sem segredo real. `docker compose config --quiet` passou. |
| A-004 | F-004 / P2 | Preparar `server.json` e metadata/rótulos conforme `R-06`; distinguir índice PBLabs e Docker MCP Catalog opcional | S2-C03; etapas 2/4 IaC, owner do índice | Schema externo adotado materializado/validado; identidade/imagem/transporte/versão coerentes; `pblabs.app.yaml` operacional versionado e destino `pblabs-mcp-index`; Docker MCP Catalog não é dependência |
| A-005 | F-005 / P2 | Escanear o artefato atual com Trivy (`R-11`), fazer triagem/VEX por CVE conforme `R-07` e R-15 e referenciar o tracker F3 canônico | Agente pode executar o scan localmente; CI/retenção e promoção exigem seus gates próprios; Bill é o signatário/aprovador final | **Aberta:** o candidato local ainda não foi escaneado. O CI já gera e retém manifesto de build e SBOM CycloneDX como artefatos, mas não executa scan de vulnerabilidades. Identificar candidato por SHA e image ID; atualizar a DB e registrar versão/data da DB, SHA e image ID no resultado. Bill decide cada achado com evidência e assina o VEX referente ao mesmo image ID; CVEs herdados da imagem base seguem a postura por herança. Scan local não equivale a CI, publicação ou promoção |
| A-006 | F-011 / P1 | Declarar perfil stateless sem bind de host e confirmar a hipótese contra broker vigente; implementação no dono | Owner e decisor do broker Nanobot: Bill; S2-NB-X01 + S2-C01; `R-10`, R-13 | Perfil AgentMail declara explicitamente `mounts=[]` (sem bind de host), sem dados graváveis; qualquer secret file usa referência/mount estreito read-only separado, quando suportado. Metadata declara necessidades e não concede acesso. Implementação/prova no broker e teste consumidor pendentes; hipótese F-011 não fechada |
| A-007 | F-007 / P1 | Documentar no perfil AgentMail a decisão de startup/egress e sua fixture offline, sem criar endpoint/override no runtime | Bill + S2-C01 | **Decisão ratificada por Bill, 2026-10-27:** aceitar egress ao AgentMail no perfil normal; não introduzir fixture/override de endpoint no runtime de produto. Startup exige conectividade válida; fixture CI é simulada e não homologa provider. Incorporar no S2-C01 continua pendente; D-01 mantém AgentMail fora do piloto. |
| A-008 | F-008 / P2 | Documentar preferência `AGENTMAIL_API_KEY_FILE` e alinhar consumidor/instalador com suporte existente do MCP | Owner e decisor do broker Nanobot: Bill; S2-NB-X01/S2-C01; instalador etapa 3 IaC; R-13 | **Decisão de perfil registrada:** usar referência a arquivo read-only estreito para API key onde suportado. MCP valida arquivo regular e rejeita symlink; isso não prova entrega pelo broker. Broker/instalador e teste do consumidor seguem pendentes. O inbox ID também é segredo e não pode aparecer em logs, inventário ou evidências. |
| A-009 | F-009, F-010 / P3 | Reconciliar docs de estado/changelog/segurança com SHA e registrar decisão sobre mypy; verificar ausência de arquivo de licença apontada no §6 | Owner para tipagem/licença/atribuição | **Parcial:** `LICENSE` MIT criado; CHANGELOG/README/docs atualizados; `mypy` segue não configurado conforme PROJECT.md. O CI já gera manifesto de build e SBOM CycloneDX; scan Trivy no CI e retenção/referência da evidência continuam pendentes. A nota F3 antiga permanece excluída, mas seu destino canônico foi decidido por `R-05`: `pblabs-mcp-index`, sem espelho de conteúdo neste checkout |
| A-010 | F-006 / P3 | Alinhar apresentação/consumo dos 3 prompts, preferindo documentar suporte por cliente ou flag compatível | Dono do consumidor `nanobot` A-010 | **Decisão do owner Nanobot (bill), 2026-10-27:** manter os 3 prompts no servidor por padrão; não remover nem ocultar por flag. Nanobot não os consome atualmente; registrar como limitação do consumidor, não defeito do servidor. Suporte MCP direto coberto pela suíte local; mudança futura exige decisão conjunta e teste de compatibilidade. |

F-010 é melhoria/decisão consciente, não defeito obrigatório de tipagem. F-011
era hipótese bloqueada no relatório: confirmar no broker antes de afirmar defeito
atual. A-007 não se encerra apenas repetindo que o MCP está fora do piloto: a
política de startup/egress precisa ser explicitada e validada conforme a decisão.

### Decisões anteriores recebidas do owner — 2026-10-27 e 2026-10-28

- Bill confirma ser o owner do produto AgentMail e do broker Nanobot; ratifica
  egress no startup e escolhe shutdown limitado (2 s grace + pool close até 5 s),
  verificado em teste local com tool lenta.
- Bill aceita preservar os três prompts, escolhe artefatos CI com referência no
  plano como destino de scan/VEX, e Positronic Bean Labs como titular do `LICENSE` MIT.
  - Para o perfil normal AgentMail, egress ao provider no startup é ratificado pelo
    owner do produto; nenhuma fixture/override de endpoint será adicionada ao runtime.
    A decisão não homologa o provider nem altera a exclusão do piloto D-01; sua
    incorporação no contrato S2-C01 segue pendente.
  - As revisões mínimas S2-C01/S2-C03 foram solicitadas antes da publicação dos
    templates. Bill aprovou seu uso e as decisões específicas nesta revisão; adoção
    operacional e provas do broker/consumidor seguem pendentes.
  - O destino do novo scan será artefato CI com referência no plano. `R-07` define
    o gate VEX; Bill confirmou em `R-12` que será seu signatário final. Produção/
    retenção das evidências segue pendente.
    `R-05` centraliza F3 por image ID em `pblabs-mcp-index`. A exclusão local da
    nota antiga permanece intacta e não deve ser substituída por cópia concorrente.

## 4. Lotes e coordenação externa

1. **AM-1:** A-001/A-002, A-003 e atualização A-009. Logs/config/lifecycle devem
   preservar o contrato wire-level; nenhum inbox/credencial real em fixture.
2. **AM-2:** A-006/A-007/A-008 após registrar em S2-C01 o perfil aprovado por Bill
   (R-13/R-14), com implementação/prova do broker em S2-NB-X01. O plano AgentMail
   recebe evidência; não altera `nanobot` nem registries dos gestores diretamente.
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
- [ ] Prova de entrega de mount/secret no broker e teste do consumidor recebidos;
  scan/CI e publicação continuam gates separados. Smoke de provider real somente
  se exigido, com aprovação específica para a operação e sandbox.

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
| 2026-10-29 / executor Positronic | R-11 e R-12–R-15 registradas; A-005 permanece aberta, sem scan do candidato | Checkout observado: `1da902a77a86a853a1140376a666718648597e0d`; SHA/image ID do candidato a registrar junto com o scan | `trivy --version`: 0.76.1; DB local baixada em 2026-10-28, a atualizar antes do scan conforme R-11. Apenas verificação de versão, sem scan. CI gera `docker-build-manifest.json` e SBOM CycloneDX e os publica como artefatos; não há scan de vulnerabilidades no workflow atual. | Bill assina VEX e promoção e decide achados por CVE/candidato conforme R-12/R-15. A-005 segue aberta: produzir scan local com DB atualizada e identidade do candidato; scan automatizado/retenção no CI e referência ao tracker F3 pendentes. Sem autorização implícita para publicação, promoção ou mudança de runtime |

## 7. Última etapa — atualizar o plano coordenador

- [ ] Reler o [stage-2 geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md),
  atualizar **S2-AM na seção 3** e acrescentar resultado na **seção 7**, com
  contagens, SHA/evidência, dependências liberadas e aceites locais/externos.
- [ ] Preservar retornos dos demais e informar reflexo nas etapas 2/4/5. Sem
  acesso à IaC, fornecer retorno e manter **aguardando sincronização**. Só declarar
  concluído com aceites e retorno efetivos; pendência/transferência é estado parcial.
