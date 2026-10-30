# Stage-2 — Remediação do Percival AgentMail MCP

**Data / revisão:** 2026-10-30 / 1.6.
**ID / estado:** S2-AM / execução parcial. A-002 verificada localmente; A-003 verificada historicamente, revalidação do Compose atual pendente; A-001/A-009 parciais; A-004/A-005 abertas; A-006/A-008 têm fixture Compose local, mas não prova de broker; A-007 aguarda incorporação no contrato; A-010 preservada e coberta localmente. R-11–R-17 registradas. Bill é o único owner, executor e aprovador; aplicar uma verificação proporcional por mudança, sem aceites ou relatórios duplicados.
**Checkout:** `/home/bill/Projects/percival-agentmail-mcp`.
**Owner, executor e autoridade final:** Bill Kopp (`bill.kopp.dev@gmail.com`), único owner, operador, executor, decisor e signatário do servidor MCP e da infraestrutura IaC da Positronic Bean Labs. Website: `labs.positronicbean.com` (em desenvolvimento, não operacional). Não há aprovador, executor ou aceite humano separado.

## 1. Objetivo e origem

Resolver ou tratar explicitamente os 13 achados da **seção 6** do
[relatório AgentMail](../../../positronic-bean-IaC/docs/reports/2026-10-26-percival-agentmail-mcp-iac-readiness-report.md#6-achados-issues-e-inconsistências),
com ações e critérios das seções 7 e 9. São 10 ações (2 P1, 5 P2, 3 P3), sem P0.
Baseline e HEAD na emissão: `68751b696b62b53fdcf893c3add9cf9e648e4391`.
Exclusão local preexistente de `docs/security/f3-status.md` preservada.

[Coordenador stage-2](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
— retorno S2-AM, seções 3 e 7. Fontes comuns:
[consolidação](../../../positronic-bean-IaC/docs/reports/2026-10-26-stage-1-consolidated-readiness-report.md)
e [D-01..D-06](../../../positronic-bean-IaC/docs/decisions/2026-10-27-iac-stage-1-scope-and-pilot-decisions.md).

Plano emitido documentalmente em 1.0; execução local parcial registrada nesta revisão 1.6.
Preservar 24 tools, envelopes de conteúdo não confiável, erros sanitizados e rate
limit. Preservar 3 prompts por padrão até decisão de compatibilidade: o fato de o
Percival não consumi-los não torna inválida a capacidade MCP do servidor.
Não é o par piloto D-01. Este plano não autoriza, por si só, acesso a inbox real,
envio/exclusão de mensagem, publicação ou mudança de runtime. Uma instrução
explícita de Bill para uma operação delimitada é a única autorização necessária;
não solicitar aprovações ou aceites adicionais para a mesma operação.

## 2. Preparação e decisões

- [x] Ler `AGENTS.md`, README, `.env.example` e documentação disponível; registrar
  SHA/worktree e dependências/CI. Na revisão de 2026-10-30, HEAD era
  `cfc7ccc8a9376db9af3eb95e1040258bfb8a4b20`, worktree inicialmente limpo,
  branch `main` 5 commits à frente de `origin/main`; CI e dependências conferidos.
  `R-05` já define o destino F3 como
  `pblabs-mcp-index`; preservar a exclusão local da nota, sem criar espelho.
- [x] Reproduzir os achados com credencial/inbox sintéticos e upstream fixture;
  tratar `inbox_id` como segredo, inclusive em logs/resultados de teste. A suíte
  local usa fixtures; nenhum smoke contra AgentMail real foi executado. A revisão
  também detectou campos de resposta MCP que devolvem o inbox ID, anotados em A-001.
- [x] Decisões anteriores do owner: `R-10` (2026-10-29) supersede `R-02` quanto ao default
  do broker Percival, que permanece amplo conforme B14/B22/B23–B25; AgentMail é
  stateless e seu perfil deve configurar explicitamente `mounts=[]`, sem depender
  do default amplo. Uma transição para perfil mais amplo exige decisão explícita
  de Bill e registro da alteração, sem aceite separado. `R-03` remove a exigência de estimar esforço, custo ou
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
  operacional de referência no índice. As decisões e seus efeitos estão
  registradas abaixo.
- [ ] Registrar o perfil nos contratos/manifests aplicáveis. Se a mudança for
  implantada no broker, executar uma verificação ponta a ponta do perfil afetado;
  não exigir aceite ou relatório separado para cada componente da mesma mudança.

### Decisões explícitas do owner — 2026-10-29 e 2026-10-30

Bill declarou: “Eu (Bill) sou único o "owner" do servidor MCP e também o único
"owner" e responsável pela infraestrtura IaC. Eu estou criando esses servidores
MCP e infraestrutura adjacente para minha empresa a "Positronic Bean Labs".
Dessa forma eu sou a única pessoa responsável pode decidir qualquer aspecto da
aplicação e da infraestrutura, logo minhas decisões são absolutas.”

Identidade registrada: **Bill Kopp**, `bill.kopp.dev@gmail.com`; **Positronic Bean
Labs**; `labs.positronicbean.com` (em desenvolvimento, não operacional).

| ID | Decisão recebida verbatim | Efeito no plano |
|---|---|---|
| R-12 | “Quem assina a promoção e o VEX? R - Eu, Bill.” | Bill é o único signatário de VEX e promoção. Para um candidato identificado, uma decisão explícita pode abranger o VEX e a promoção; não pedir assinaturas/aceites repetidos para os mesmos artefatos. |
| R-13 | “Qual é o contrato de mounts e secrets do AgentMail? R - Nos temos um template de contrato definido, veja em </home/bill/Projects/positronic-bean-IaC> e em </home/bill/Projects/pblabs-mcp-index>. Use esse template.” | Aplicar [Agent runtime contract](../../../positronic-bean-IaC/docs/agent-runtime-contract.md), [MCP application contract](../../../positronic-bean-IaC/docs/mcp-app-contract.md), o [perfil AgentMail de referência](../../../pblabs-mcp-index/servers/agentmail/pblabs.app.yaml) e as [propostas de perfil](../../../pblabs-mcp-index/docs/profile-proposals.md). Para AgentMail, `mounts=[]` significa sem bind de host/workspace; dados graváveis são falsos; egress é necessário; metadata declara requisitos, não concede privilégios. Segredos usam referência/arquivo read-only estreito gerenciado pelo broker, sem ampliar os binds da aplicação. A aplicação suporta `AGENTMAIL_API_KEY_FILE`; API key e inbox ID permanecem secretos conforme `AGENTS.md`. O manifest do índice é rascunho e hoje lista apenas `AGENTMAIL_API_KEY`; a proposta de perfil ainda indica injeção por env e classifica inbox ID como não secreto, em conflito com o suporte atual a arquivo e a regra deste projeto. Reconciliar esses pontos antes de publicar metadata; Bill registra a decisão uma vez. Isso não afirma que o broker já entrega secrets. |
| R-14 | “Como registrar lifecycle e startup no S2-C01? R - Vamos seguir com a sua sugestão: "documentar esses valores como perfil específico do AgentMail e exigir um teste do broker com timeout compatível, sem transformá-los em regra universal para todos os MCPs"” | S2-C01 registra AgentMail como perfil específico: startup depende de egress ao provider; shutdown usa grace de 2 s e fechamento do pool limitado a 5 s. Exigir teste do broker com timeout compatível; não generalizar esses números para outros MCPs. |
| R-15 | “Que tratamento dar a cada CVE do candidato? R - Vamos seguir com sua sugestão: "Sugiro decidir achado a achado, com evidência: corrigir ou justificar a disposição no VEX. Evitaria uma aprovação genérica que cubra candidatos ou image IDs futuros"” | Após cada scan, Bill decide cada achado com evidência, por candidato/image ID; corrigir ou justificar sua disposição no VEX. Não há waiver genérico para outros candidatos/image IDs. |
| R-16 | “Eu, Bill Kopp, sou o único "owner" dessa aplicação e também o "owner" da infraestrutura IaC, também sou o único a trabalhar nesses projetos. Logo, sou o único a decidir e assinar.” | Bill é o único owner, executor, decisor e signatário. Não criar papéis de aprovador/revisor separados nem condicionar trabalho local a aceites de terceiros. |
| R-17 | “Estamos perdendo muito tempo com validações cruzadas, provas desnecessárias e múltiplos aceites para a mesma coisa. Como eu sou o único dono e a única pessoa a trabalhar nessas aplicações isso não faz sentido.” | Usar uma verificação relevante por mudança/artefato e registrar a evidência uma vez. Repetir somente após mudança do artefato, falha ou novo risco concreto. Consolidar as decisões e resultados num registro canônico; não duplicar relatórios ou aceites entre repositórios. |

## 3. Backlog e critérios de conclusão

Estado inicial em 2026-10-27: **não iniciada** para todas as ações. Nesta revisão,
A-007 tem decisão de produto ratificada e aguarda incorporação/prova no contrato;
A-006 ainda depende de configuração do broker. As prioridades abaixo são as da
ação de origem. Cada ação precisa apenas da implementação e verificação pertinentes;
não há etapa adicional de aceite por outra pessoa.

| Ação | Achados / P | Trabalho e áreas previstas | Dependência / interface | Critério de verificação |
|---|---|---|---|---|
| A-001 | F-001, F-012, F-013 / P2 | Omitir/mascarar inbox no startup; sanitizar erro de transporte sem traceback público; remover ou tornar explícita leitura `.env` em config/server | Nenhuma dependência externa para fix local | **Parcial/requalificada em 2026-10-30:** logs INFO de startup não incluem inbox; erro de config é sanitizado; `.env` do cwd é ignorado salvo `AGENTMAIL_ENV_FILE`; testes de secret-file/symlink passam. A suíte completa passou. Limite importante: `ServerConfig.__repr__` inclui `inbox_id` (coberto como comportamento esperado pelo teste atual) e `mail_get_version`/`mail_get_status` devolvem esse identificador; `mail_get_inbox_info` retorna dados da inbox. Isso não demonstra vazamento nos logs de startup, mas impede afirmar que o ID está oculto de toda saída/configuração. Rever o escopo de exposição com a regra de segredo do projeto; esta revisão não alterou a API. |
| A-002 | F-002 / P2 | Tratar SIGTERM/SIGINT com cancelamento do lifespan e fechamento do pool; declarar a limitação e o deadline do serviço | Contrato do broker Percival (`S2-NB-X01`/`S2-C01`) se/quando alterado | **Implementada/verificada localmente:** grace de 2 s, seguida de cancelamento do trabalho remanescente e fechamento protegido do pool até 5 s; Compose local dá 10 s. Testes locais cobrem tool lenta e close protegido. Se o perfil do broker mudar, uma verificação ponta a ponta deve confirmar timeout compatível; não exigir matriz ou aceite duplicado para a mesma alteração. |
| A-003 | F-003 / P3 | Repassar argumentos no entrypoint Compose ou recusar forma não suportada explicitamente | Receita local, sem iniciar serviço real | **Verificada historicamente; revalidar no Compose atual:** o smoke registrado em 2026-10-27 confirmou repasse de `--version` sem startup/upstream. Desde então, a receita atual exige arquivos externos para os dois secrets; o smoke não foi repetido nesta revisão sem esses arquivos. Os testes atuais verificam contrato estático e o CI verifica configuração Compose, mas seu MCP smoke executa a imagem por `docker run` direto, não via `docker compose run`. Repetir com fixtures sintéticas sem segredos reais. |
| A-004 | F-004 / P2 | Preparar `server.json` e metadata/rótulos conforme `R-06`; distinguir índice PBLabs e Docker MCP Catalog opcional | Schema e checkout do índice PBLabs, administrados por Bill | **Aberta:** a imagem tem labels OCI e o CI valida MCP stdio, mas não há `server.json` nem `pblabs.app.yaml` neste checkout. Criar e validar os metadados uma vez contra o schema adotado; manter identidade/imagem/transporte/versão coerentes e usar `pblabs-mcp-index`. Docker MCP Catalog não é dependência. |
| A-005 | F-005 / P2 | Escanear o artefato atual com Trivy (`R-11`), fazer triagem/VEX por CVE conforme `R-07`/R-15 e referenciar o tracker F3 canônico | Scanner local; CI/publicação apenas quando esse fluxo for alterado | **Aberta:** o candidato local não foi escaneado nesta revisão. O workflow publica manifesto de build e SBOM CycloneDX, sem scan de vulnerabilidades. Fazer um scan do candidato identificado por SHA/image ID e registrar versão da ferramenta/DB e resultado. O VEX do image ID lista a disposição de cada CVE e recebe uma assinatura de Bill por candidato; a assinatura pode também cobrir a promoção desse mesmo artefato quando essa intenção estiver explícita. Sem aprovação genérica para image IDs futuros. |
| A-006 | F-011 / P1 | Declarar perfil stateless sem bind de host e configurar `mounts=[]`, sem dados graváveis | Configuração do broker Nanobot (`S2-NB-X01`/`S2-C01`) | O Compose local declara rootfs read-only, tmpfs restrito, capabilities removidas e secrets por arquivo, sem bind de workspace. Isso é evidência da fixture local, não do broker. Ao aplicar o perfil no broker, executar um único teste ponta a ponta que confirme mounts e escrita esperados; a pendência de configuração/perfil permanece. |
| A-007 | F-007 / P1 | Registrar no perfil AgentMail a decisão de startup/egress e sua fixture offline; não criar endpoint/override no runtime | Contrato S2-C01 e fixture CI | **Decisão de Bill ratificada em 2026-10-27:** aceitar egress ao AgentMail no perfil normal; não introduzir fixture/override de endpoint no runtime. Startup exige conectividade válida; fixture CI não homologa provider. Incorporar a decisão no S2-C01; D-01 mantém AgentMail fora do piloto. Não requer novo aceite. |
| A-008 | F-008 / P2 | Documentar preferência `AGENTMAIL_API_KEY_FILE` e alinhar o perfil do broker/instalador ao suporte do MCP | Configuração do broker/instalador (`S2-NB-X01`/`S2-C01`) | **Parcial local; broker pendente:** o runtime lê `AGENTMAIL_API_KEY_FILE`, valida arquivo regular e rejeita symlink. O Compose local monta arquivos para API key e inbox ID; seu wrapper lê o inbox ID e exporta `AGENTMAIL_INBOX_ID` ao processo. O servidor não tem suporte nativo `AGENTMAIL_INBOX_ID_FILE`. Ao alterar o broker, validar uma vez a entrega dos dois valores por referência/arquivo conforme o perfil; não é necessária uma aprovação adicional após o teste. |
| A-009 | F-009, F-010 / P3 | Reconciliar docs de estado/changelog/segurança com SHA e registrar decisão sobre mypy; verificar ausência de arquivo de licença apontada no §6 | Bill, se uma decisão de licença/tipagem for necessária | **Parcial:** `LICENSE` MIT existe; CHANGELOG/README/docs estão presentes; `mypy` segue não configurado em `pyproject.toml`. O workflow atual executa teste/lint, conformidade MCP offline e gera manifesto/SBOM; scan Trivy no CI e evidência VEX/retenção continuam pendentes. Há divergência documental a resolver: o README ainda exemplifica `--env-file .env` e entrega por ambiente, enquanto o Compose atual documenta arquivos separados para API key e inbox ID conforme R-13. A nota F3 antiga permanece excluída, mas seu destino canônico foi decidido por `R-05`: `pblabs-mcp-index`, sem espelho de conteúdo neste checkout |
| A-010 | F-006 / P3 | Preservar suporte aos 3 prompts e registrar a limitação atual do consumidor | Compatibilidade do consumidor Nanobot | **Decisão de Bill ratificada em 2026-10-27:** manter os 3 prompts por padrão. Nanobot não os consome atualmente; isso é limitação do consumidor, não defeito do servidor. Suporte MCP coberto pela suíte local; só repetir compatibilidade se o contrato ou consumidor mudar. |

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
  - Bill aprovou o uso de S2-C01/S2-C03 e as decisões específicas. A adoção
    operacional no broker segue pendente; verificar uma vez quando implementada.
  - O destino do novo scan será artefato CI com referência no plano. `R-07` define
    o gate VEX; Bill confirmou em `R-12` que será seu signatário final. Produção/
    retenção das evidências segue pendente.
    `R-05` centraliza F3 por image ID em `pblabs-mcp-index`. A exclusão local da
    nota antiga permanece intacta e não deve ser substituída por cópia concorrente.

## 4. Ordem prática e interfaces

Os lotes abaixo servem apenas para organizar a execução; não são gates de aprovação.

1. **AM-1:** A-001/A-002, A-003 e atualização A-009. Preservar contrato wire-level
   e usar somente inbox/credenciais sintéticos em fixtures.
2. **AM-2:** A-006/A-007/A-008. Registrar o perfil AgentMail uma vez em S2-C01;
   se a implementação do broker for alterada, validar o perfil afetado com um
   teste ponta a ponta.
3. **AM-3:** A-004/A-005 e A-010. Validar metadata no schema adotado; associar
   scan/VEX a um candidato; testar o consumidor somente se houver mudança de
   compatibilidade.

Bill trabalha nos repositórios e sistemas envolvidos. Não exigir retornos ou
aceites intermediários entre lotes. Registrar compatibilidade apenas quando uma
mudança tocar lifespan, configuração, prompts ou schema. `R-03` remove estimativas
de esforço, custo e prazo.

## 5. Qualificação futura no checkout

- [x] Regressões dos casos observados e suíte `uv run pytest --cov` com limiar
  vigente; `uv run ruff check .` e `uv run ruff format --check .` conforme CI.
  Verificado em 2026-10-30: 244 passed, 1 skipped (smoke real desabilitado),
  cobertura 91,51%; Ruff check e format passaram.
- [ ] Se mudar imagem, entrypoint ou transporte, executar uma qualificação offline
  da imagem: versão/configuração pertinente e um ciclo MCP com fixture segura
  (`initialize`, `tools/list`, chamada segura). Não repetir testes equivalentes
  como gates separados para a mesma imagem.
- [ ] Para mudanças locais de sinais, secrets, configuração ou conteúdo de email,
  usar a cobertura já incluída na suíte; acrescentar teste específico apenas
  quando a alteração criar um comportamento ainda não coberto.
- [ ] Se mudar a integração com o broker, executar um teste ponta a ponta do
  perfil afetado. Para publicação, escanear uma vez cada image ID; um VEX por
  candidato lista a disposição dos CVEs e pode acompanhar a decisão de promoção.
  Não há aceite adicional após evidência técnica suficiente.

Fixtures locais não homologam o provider real nem enviam email. Chamada real,
publicação ou mudança de produção só ocorre quando estiver explicitamente incluída
na instrução de Bill; não se pede nova aprovação para repetir o mesmo escopo.

## 6. Penúltima etapa — documentar execução neste plano

- [ ] Ao concluir um lote, registrar uma única vez o resultado, commit/source SHA,
  verificações executadas e pendências neste plano. Referenciar CI/artefatos
  existentes; não copiar a mesma evidência para vários relatórios.
- [ ] Atualizar o plano coordenador somente quando uma mudança alterar contrato
  compartilhado ou bloquear outra ação; apontar para este registro em vez de
  repetir o relatório. Preservar a coleta histórica.

| Data / owner | Ações / achados | SHA inicial → final | Mudanças / evidências locais | Resultado / V-* / pendências |
|---|---|---|---|---|
| 2026-10-27 / executor Positronic | A-001/A-002/A-003 verificadas localmente; A-007 ratificada; A-009 parcial; A-010 limitação aceita; A-004/A-005/A-006/A-008 abertas | `68751b696b62b53fdcf893c3add9cf9e648e4391` → SHA final após commit | `pytest --cov`: 244 passed/1 skipped, 91,51%; Ruff/format; Compose config/build/version smoke; subprocess MCP `initialize` + tool lenta + SIGTERM demonstrou grace/hook/exit 0; imagem local `sha256:3549964cf53c12e3df730b9fab23967af53f40768300a31a8200caec957e7975`, linux/amd64, OCI revision=`local`. Scanner ausente; sem scan. | Parcial; sem inbox real, publicação ou alteração broker; S2-C01/C03 em draft; A-005 aguarda CI/scanner, A-006/A-008 broker; owner release/índice pendente; sem commit |
| 2026-10-29 / executor Positronic | R-11 e R-12–R-15 registradas; A-005 permanece aberta, sem scan do candidato | Checkout observado: `1da902a77a86a853a1140376a666718648597e0d`; SHA/image ID do candidato a registrar junto com o scan | `trivy --version`: 0.76.1; DB local baixada em 2026-10-28, a atualizar antes do scan conforme R-11. Apenas verificação de versão, sem scan. CI gera `docker-build-manifest.json` e SBOM CycloneDX e os publica como artefatos; não há scan de vulnerabilidades no workflow atual. | Bill assina VEX e promoção e decide achados por CVE/candidato conforme R-12/R-15. A-005 segue aberta: produzir scan local com DB atualizada e identidade do candidato; scan automatizado/retenção no CI e referência ao tracker F3 pendentes. Sem autorização implícita para publicação, promoção ou mudança de runtime |
| 2026-10-30 / Bill Kopp | Auditoria do plano contra checkout; A-001 requalificada; A-003 smoke atual pendente; A-004/A-006/A-008/A-009 reconciliadas; R-16/R-17 registram owner único e redução de burocracia | Código: `cfc7ccc8a9376db9af3eb95e1040258bfb8a4b20` (nenhuma alteração de código) | Worktree estava limpo no início. `uv run pytest --cov`: 244 passed/1 skipped, 91,51%; `uv run ruff check .`, `uv run ruff format --check .` e `git diff --check` passaram. CI contém conformidade MCP offline via `docker run`, validação de configuração Compose, manifesto e SBOM, sem Trivy. OCI labels presentes; metadata `server.json`/`pblabs.app.yaml` ausente. Compose local usa secrets por arquivo; wrapper exporta inbox ID como env. README ainda orienta env-file/ambiente, divergindo do perfil de arquivo no Compose. `mail_get_version`, `mail_get_status` e `ServerConfig.__repr__` incluem inbox ID; logs INFO de startup não o incluem. Nenhum acesso a AgentMail real, build Docker, scan Trivy ou mudança em broker. | Revisão 1.6 consolida resultados sem alterar código. Pendentes: smoke Compose atual com secrets sintéticos, revisão da exposição do inbox ID e interfaces A-004/A-005/A-006/A-008. Sem publicação, promoção, alteração de runtime ou acesso a inbox real |

## 7. Última etapa — atualizar o plano coordenador

- [ ] Se este trabalho alterar um contrato compartilhado, atualizar uma vez o
  item S2-AM no [plano geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
  e referenciar a evidência local. Não exigir confirmação de outro owner, retorno
  intermediário ou cópia integral do relatório para concluir o trabalho local.
