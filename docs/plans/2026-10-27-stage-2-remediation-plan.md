# Stage-2 — Remediação do Percival AgentMail MCP

**Data / revisão:** 2026-10-31 / 2.0.
**ID / estado:** S2-AM / execução parcial. A-001 e A-003 implementadas e verificadas localmente; A-002 e A-010 preservadas/verificadas. A-004 tem metadata local válida em estado draft, sem release/digest ou namespace verificado. A-005 encontrou uma vulnerabilidade High no primeiro candidato, corrigida via dnspython 2.9.1; candidato final local reportou zero findings e CI ganhou scan/artifact com gate Critical/High, ainda sem execução remota do workflow. A-006 declara só mounts read-only de secret, sem binds de dados/workspace. A-007 foi incorporada ao draft S2-C01. A-008 tem suporte `*_FILE` no produto e nos managers; fixtures isoladas do manager Positronic e do service/profile + mount policy Percival passaram, mas o E2E do processo broker Percival e verificação de permissões operacionais continuam pendentes; instalação gerenciada segue desabilitada. A-009 reconcilia README/CHANGELOG/mypy, sem commit. R-11–R-24 registradas. Bill é o único owner, executor e signatário; aplicar uma verificação proporcional por mudança, sem aceites ou relatórios duplicados.
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

Plano emitido documentalmente em 1.0; execução local parcial registrada nesta revisão 2.0.
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

### Decisões explícitas do owner — 2026-10-29 a 2026-10-31

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
| R-13 | “Qual é o contrato de mounts e secrets do AgentMail? R - Nos temos um template de contrato definido, veja em </home/bill/Projects/positronic-bean-IaC> e em </home/bill/Projects/pblabs-mcp-index>. Use esse template.” | Aplicar [Agent runtime contract](../../../positronic-bean-IaC/docs/agent-runtime-contract.md), [MCP application contract](../../../positronic-bean-IaC/docs/mcp-app-contract.md), o [perfil AgentMail de referência](../../../pblabs-mcp-index/servers/agentmail/pblabs.app.yaml) e as [propostas de perfil](../../../pblabs-mcp-index/docs/profile-proposals.md). Para AgentMail, não há binds de dados/host/workspace nem dados graváveis; egress é necessário; metadata declara requisitos, não concede privilégios. Segredos usam referências para arquivos read-only estreitos, sem ampliar os binds de dados da aplicação. O app suporta `AGENTMAIL_API_KEY_FILE` e `AGENTMAIL_INBOX_ID_FILE`; ambos os valores são secrets conforme `AGENTS.md`. A versão 2026-10-31 do perfil Index permanece draft, declara ambos e os mounts secretos, sem fonte host; não existe server.json de release ou entrada no catálogo. R-18/R-23 registram que manager code local resolve paths de arquivos, mas instalação gerenciada aguarda E2E em Percival e Positronic. |
| R-14 | “Como registrar lifecycle e startup no S2-C01? R - Vamos seguir com a sua sugestão: "documentar esses valores como perfil específico do AgentMail e exigir um teste do broker com timeout compatível, sem transformá-los em regra universal para todos os MCPs"” | S2-C01 registra AgentMail como perfil específico: startup depende de egress ao provider; shutdown usa grace de 2 s e fechamento do pool limitado a 5 s. Exigir teste do broker com timeout compatível; não generalizar esses números para outros MCPs. |
| R-15 | “Que tratamento dar a cada CVE do candidato? R - Vamos seguir com sua sugestão: "Sugiro decidir achado a achado, com evidência: corrigir ou justificar a disposição no VEX. Evitaria uma aprovação genérica que cubra candidatos ou image IDs futuros"” | Após cada scan, Bill decide cada achado com evidência, por candidato/image ID; corrigir ou justificar sua disposição no VEX. Não há waiver genérico para outros candidatos/image IDs. |
| R-16 | “Eu, Bill Kopp, sou o único "owner" dessa aplicação e também o "owner" da infraestrutura IaC, também sou o único a trabalhar nesses projetos. Logo, sou o único a decidir e assinar.” | Bill é o único owner, executor, decisor e signatário. Não criar papéis de aprovador/revisor separados nem condicionar trabalho local a aceites de terceiros. |
| R-17 | “Estamos perdendo muito tempo com validações cruzadas, provas desnecessárias e múltiplos aceites para a mesma coisa. Como eu sou o único dono e a única pessoa a trabalhar nessas aplicações isso não faz sentido.” | Usar uma verificação relevante por mudança/artefato e registrar a evidência uma vez. Repetir somente após mudança do artefato, falha ou novo risco concreto. Consolidar as decisões e resultados num registro canônico; não duplicar relatórios ou aceites entre repositórios. |
| R-18 | Bill aprovou a recomendação de tratar API key e inbox ID como segredos, favorecer arquivos read-only nos dois agentes, manter a metadata neutra quanto ao mecanismo privilegiado, implementar o suporte por arquivo em cada manager conforme sua arquitetura e não habilitar instalação gerenciada enquanto esses fluxos não existirem. | Declarar `AGENTMAIL_API_KEY` e `AGENTMAIL_INBOX_ID` como requisitos secretos no perfil do índice. Não declarar compatibilidade com Positronic até validar esse consumidor. O contrato compartilhado define requisitos e referências de segredo, mas não concede mounts nem impõe mecanismo privilegiado. Cada manager resolve referências para arquivos read-only estreitos conforme sua arquitetura; não usar valor literal de segredo em `env` como padrão. A aplicação adicionará suporte nativo a `AGENTMAIL_INBOX_ID_FILE`. Até a entrega por arquivo ser implementada e verificada ponta a ponta em Percival e Positronic, não habilitar instalação gerenciada do AgentMail em nenhum dos dois. O wrapper/fluxo híbrido Compose é, no máximo, fixture local transitória documentada, não evidência de suporte dos managers nem caminho de instalação aprovado. |
| R-19 | Bill aprovou remover o campo `inbox` de `mail_get_version` e `mail_get_status`, sem mudar nomes ou schemas; manter `mail_get_inbox_info`, omitindo/mascarando identificadores e outros campos sensíveis desnecessários ao diagnóstico. | Implementar a redaction mantendo a forma do contrato quando possível; registrar a mudança de valores porque consumidores podem depender deles. Preservar a função de info da inbox com payload minimizado. A decisão está tomada; implementação/testes e avaliação dos campos concretos retornados ainda pendem em A-001. |
| R-20 | Bill aprovou o primeiro scan com Trivy sobre candidato escolhido e identificado por source SHA e image ID; relatório e eventual VEX devem apontar para essa identidade. A decisão sobre automatização e retenção do scan em CI versus processo local documentado será tomada após o scan inicial. | Selecionar/buildar um candidato exato, atualizar a DB e registrar versão do scanner, identidade e referência ao relatório; aplicar VEX somente se houver CVEs e nunca transferir disposições a outro image ID/digest. Não há candidato selecionado nem scan executado por esta decisão; A-005 permanece aberta. |
| R-21 | Bill decidiu usar os padrões e exemplos existentes em Nanobot, PBLabs MCP Index e Percival Weather para os metadados de publicação AgentMail. | Usar `server.json` validado contra o schema MCP externo `2025-12-11` e `pblabs.app.yaml` schema `0.2`, conforme os exemplos Weather/índice e o padrão registrado no plano Nanobot. Usar os campos/metadados OCI compatíveis com esses exemplos, sem copiar tags, digests, identidade ou estado de release de outros servidores. `server.json` declara nomes de variáveis e classificação secreta, sem valores; o perfil PBLabs declara os requisitos, sem conceder mounts/mecanismo de entrega. Declarar API key e inbox ID como segredos; compatibilidade Positronic continua condicionada à validação de A-004/A-008. |
| R-22 | Bill decidiu manter `mypy` sem configuração até existir demanda concreta, seguindo a orientação atual do projeto. | Não adicionar mypy nem ampliar os gates desta remediação. Registrar a decisão em A-009; retomar apenas se surgir requisito concreto. |
| R-23 | Bill escolheu referências a arquivos de segredo já existentes no host: managers persistem apenas os paths privados, montam os arquivos read-only e não leem nem copiam os valores. | O produto lê `AGENTMAIL_API_KEY_FILE` e `AGENTMAIL_INBOX_ID_FILE`. O perfil AgentMail declara targets `kind: secret` sob `/app/.secrets/`; Percival deriva os nomes `_FILE` dos mounts. Positronic oferece `--secret-file NAME=/absolute/path`. Paths de conteúdo não entram em export de inventário; owner/ACL permanecem responsabilidade do operador. Fixtures isoladas Positronic e Percival service/mount-policy passaram sem alterar estado real; o broker Percival continua sem E2E por RPC. |
| R-24 | Após o scan inicial, Bill escolheu automatizar Trivy na CI, reter o relatório completo como artifact associado ao build manifest/SBOM e falhar builds com findings Critical/High. | Escanear o image ID candidato após build; registrar source SHA e image ID no manifest e no nome do artifact; reportar todos os níveis no JSON e aplicar o gate Critical/High. VEX continua individual por CVE/candidato; scan local não substitui o run remoto da CI. |

## 3. Backlog e critérios de conclusão

Estado inicial em 2026-10-27: **não iniciada** para todas as ações. Nesta revisão
2.0, A-001/A-003 foram implementadas/verificadas localmente e a decisão de A-007
foi incorporada ao draft S2-C01. A-006/A-008 têm perfil e código local de file
secrets com fixtures E2E isoladas; falta o E2E pelo processo broker Percival. As
prioridades abaixo são as da ação de origem. Cada ação precisa apenas da
implementação e verificação pertinentes; não há etapa adicional de aceite por
outra pessoa.

| Ação | Achados / P | Trabalho e áreas previstas | Dependência / interface | Critério de verificação |
|---|---|---|---|---|
| A-001 | F-001, F-012, F-013 / P2 | Omitir/mascarar inbox no startup; sanitizar erro de transporte sem traceback público; remover ou tornar explícita leitura `.env` em config/server; não expor o inbox ID em representações de config nem em respostas de metadados/diagnóstico | Fix local; preservar nomes e schemas MCP | **Implementada localmente:** `ServerConfig.__repr__`/`__str__`/`model_dump` mascaram API key e inbox ID; `mail_get_version`/`mail_get_status` omitem `inbox` sem mudar nomes ou schemas; `mail_get_inbox_info` usa allowlist (`display_name`, `created_at`, `updated_at`) e exclui email/id/client/pod e metadata arbitrária. Um MCP conformance smoke com o inbox ID como canary detectou `httpx` INFO logando a URL do health check; `httpx`/`httpcore` agora ficam em WARNING e o smoke CI cobre ambos os canaries, fazendo `initialize`/`tools/list` e chamada segura `mail_get_status` com secrets em arquivos. `format_error` registra apenas status/tipo, redige API key/inbox ID de mensagens e metadados e a saída debug não emite traceback. Erro de config sanitizado; dotenv só explícito; file readers rejeitam symlink. Testes atualizados e suíte completa passou. Consumidores ainda podem depender do valor removido, conforme R-19. |
| A-002 | F-002 / P2 | Tratar SIGTERM/SIGINT com cancelamento do lifespan e fechamento do pool; declarar a limitação e o deadline do serviço | Contrato do broker Percival (`S2-NB-X01`/`S2-C01`) se/quando alterado | **Implementada/verificada localmente:** grace de 2 s, seguida de cancelamento do trabalho remanescente e fechamento protegido do pool até 5 s; Compose local dá 10 s. Testes locais cobrem tool lenta e close protegido. Se o perfil do broker mudar, uma verificação ponta a ponta deve confirmar timeout compatível; não exigir matriz ou aceite duplicado para a mesma alteração. |
| A-003 | F-003 / P3 | Repassar argumentos no entrypoint Compose ou recusar forma não suportada explicitamente | Receita local, sem iniciar serviço real | **Verificada em 2026-10-31:** `docker compose config --quiet` passou; a imagem da receita atual foi construída e `docker compose run --rm --no-deps server --version` retornou 0.4.0. Os dois paths de secret foram apontados a `/etc/hostname` somente como fixtures de montagem; `--version` não inicializa o runtime, não leu seus conteúdos e não fez upstream. Nenhuma inbox/credencial real foi usada. |
| A-004 | F-004 / P2 | Preparar `server.json` e `pblabs.app.yaml`/labels conforme `R-06`/`R-18`/R-21/R-23; declarar secrets e targets read-only sem conceder privilégios; distinguir índice PBLabs e Docker MCP Catalog opcional | Schemas externos 2025-12-11 e PBLabs 0.2; checkout do índice PBLabs | **Parcial; metadata local validada em estado draft:** `docs/mcp/percival-agentmail-mcp/{server.json,pblabs.app.yaml}` passam os dois schemas; o perfil local em `pblabs-mcp-index/servers/agentmail` também passa 0.2, foi atualizado para ambos os secrets/targets e voltou a `draft`. O pacote aponta para a localização Docker Hub pretendida, mas não há tag publicada/digest; namespace MCP e Docker Hub não foram verificados. Sem claim de release ou compatibilidade Positronic. A policy não concede host paths. O Index não contém server.json/catálogo do AgentMail e `catalog.yaml` continua vazio até existir identidade OCI publicada e gate separado. |
| A-005 | F-005 / P2 | Escanear o candidato exato com Trivy (`R-11`/R-20/R-24), registrar source Git tree SHA + image ID e relatório; fix/triagem por CVE conforme `R-07`/R-15 e referenciar tracker F3 canônico | Trivy/DB local e CI | **Parcial, com achado resolvido no candidato final:** o primeiro candidato tinha 1 High `CVE-2026-114605` em dnspython 2.8.0. Atualizei o lock para 2.9.1; a nota do projeto upstream descreve o limite de 16 pointers na 2.9.0 (fix aplicável). Candidato final `0.4.0-stage2-b89a97f`, source tree `b89a97f866714878d328abdc0bdc9111f9d79858`, image ID `sha256:ccf56dbe83f91efb1411f381b0b66fdc4b17f0f7a865703c337c01b52ee9c2ce`, Trivy 0.76.1, DB atualizada em 2026-10-31 13:09 UTC: 0 findings. Resumo durável: [evidência local de Trivy](../security/2026-10-31-trivy-stage2-local-candidates.md); JSON bruto e build manifest vinculados por tree SHA/image ID em `/home/bill/.positronic/runtime/tmp/opencode/`. Nenhum VEX foi emitido: o candidato final não tem CVEs e os anteriores não são candidatos a release. A CI agora grava JSON completo/SBOM/manifest e falha em Critical/High (`R-24`); remote CI ainda não executado. |
| A-006 | F-011 / P1 | Declarar perfil stateless sem binds de dados/host/workspace nem dados graváveis; limitar secret mounts a referências read-only estreitas conforme `R-18`/R-23 | Configuração do broker Nanobot (`S2-NB-X01`/S2-C01) | A fixture Compose mantém rootfs read-only, tmpfs restrito, capabilities removidas e arquivos de segredo read-only. O perfil local PBLabs agora declara somente dois mounts `kind: secret` read-only sob `/app/.secrets/`; nenhum bind de dados/workspace nem escrita de dados. `mounts=[]` continua significando nenhum host bind. Testes do broker/managers e fixtures containerizadas verificam resolução e leitura pelo UID 1000. E2E pelo processo broker Percival ainda não executado; instalação gerenciada permanece desabilitada até essa prova. |
| A-007 | F-007 / P1 | Registrar no perfil AgentMail a decisão de startup/egress e sua fixture offline; não criar endpoint/override no runtime | Contrato S2-C01 e fixture CI | **Incorporada ao draft S2-C01 em 2026-10-31:** o perfil normal exige egress para o health request AgentMail no startup; não haverá fixture/override de endpoint no runtime. Fixtures CI não homologam o provider. D-01 mantém AgentMail fora do piloto e a adoção operacional do contrato segue pendente. |
| A-008 | F-008 / P2 | Conforme `R-18`/R-23, tratar API key e inbox ID como secrets via arquivo read-only; implementar suporte nativo a ambos `*_FILE`; configurar referências host-file nos dois managers; alinhar docs/profile | S2-C01/S2-C03; brokers Percival/Positronic; compatibilidade MCP | **Implementada em código; fixtures E2E isoladas parciais:** app lê ambos `*_FILE`, valida arquivos regulares e rejeita symlinks; Compose remove o wrapper. Percival mapeia secret mounts e `_FILE` no catálogo; fixture `DockerMcpService.install_catalog_app` + `MountPolicy` iniciou o container via conformance helper e executou `mail_get_status` contra mock. Positronic `ManagedServers` em HOME temporário iniciou o container via `ManagedStdioTransport` e executou o mesmo tool contra mock. Positronic remove um valor literal previamente salvo para o secret convertido em referência, preservando outras env vars. Ambos os fixtures leram arquivos read-only sintéticos sem expor valores; nenhum estado ativo foi alterado. O fixture Percival usou broker fake: falta validar o processo broker/RPC real e permissões no host de instalação. E2E de release/catalog não é possível enquanto Index estiver vazio/draft. Manter instalação gerenciada desabilitada até os gates reais passarem; compatibilidade Positronic permanece não declarada. Evidência: `docs/security/2026-10-31-secret-file-manager-fixtures.md`. |
| A-009 | F-009, F-010 / P3 | Reconciliar docs de estado/changelog/segurança com SHA; registrar decisão mypy (`R-22`); verificar ausência de arquivo de licença apontada no §6 | Nenhuma decisão externa pendente para mypy; documentação local | **Parcial:** `LICENSE` MIT existe; CHANGELOG/README/docs registram redaction, paths `*_FILE`, scan/artefatos CI e `mypy` ausente conforme R-22. O README não recomenda mais `--env-file` com valores de credenciais; a fixture Compose usa dois paths de arquivos read-only, e o wrapper transitório foi removido. O workflow agora contém scan Trivy e gate Critical/High; a execução remota da CI ainda não foi observada. A nota F3 antiga permanece excluída, mas seu destino canônico foi decidido por `R-05`: `pblabs-mcp-index`, sem espelho de conteúdo neste checkout |
| A-010 | F-006 / P3 | Preservar suporte aos 3 prompts e registrar a limitação atual do consumidor | Compatibilidade do consumidor Nanobot | **Decisão de Bill ratificada em 2026-10-27:** manter os 3 prompts por padrão. Nanobot não os consome atualmente; isso é limitação do consumidor, não defeito do servidor. Suporte MCP coberto pela suíte local; só repetir compatibilidade se o contrato ou consumidor mudar. |

F-010 é melhoria/decisão consciente, não defeito obrigatório de tipagem. F-011
era hipótese bloqueada no relatório: confirmar no broker antes de afirmar defeito
atual. A-007 não se encerra apenas repetindo que o MCP está fora do piloto: a
política de startup/egress precisa ser explicitada e validada conforme a decisão.

### Decisões anteriores recebidas do owner — 2026-10-27 e 2026-10-28

- Bill confirma ser o owner do produto AgentMail e do broker Nanobot; ratifica
  egress no startup e escolhe shutdown limitado (2 s grace + pool close até 5 s),
  verificado em teste local com tool lenta.
- Bill aceita preservar os três prompts e Positronic Bean Labs como titular do
  `LICENSE` MIT. A direção inicial de evidência CI registrada em 2026-10-27 foi
  refinada por `R-20` para executar primeiro um scan do candidato exato e decidir
  depois se CI ou processo local documentado será o caminho de automação/retenção.
  - Para o perfil normal AgentMail, egress ao provider no startup é ratificado pelo
    owner do produto; nenhuma fixture/override de endpoint será adicionada ao runtime.
    A decisão não homologa o provider nem altera a exclusão do piloto D-01; sua
    incorporação no contrato S2-C01 segue pendente.
  - Bill aprovou o uso de S2-C01/S2-C03 e as decisões específicas. A adoção
    operacional no broker segue pendente; verificar uma vez quando implementada.
  - `R-07` define o gate VEX; Bill confirmou em `R-12` que será seu signatário
    final. Para a primeira execução, `R-20` exige referência do relatório no plano
    e vínculo a source SHA/image ID; a escolha de retenção/automação segue pendente.
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
| 2026-10-31 / Bill Kopp | Auditoria do plano contra o código atual; A-001 requalificada como exposição a corrigir; A-008/A-009 atualizadas; R-18 aprovada: file-secrets nos dois managers e bloqueio de instalação gerenciada até validação | Código observado: `097eb291462faffd95a796b63d9783f626eb5188`; plano já tinha alterações locais antes desta revisão | Confirmado por leitura: `config.py` inclui inbox ID em `__repr__`; `tools/version.py` e `tools/status.py` retornam `inbox`; `mail_get_inbox_info` fornece dados da inbox. README ainda recomenda credenciais via env/`--env-file`; Compose usa arquivos, mas wrapper exporta inbox ID ao processo. A implementação atual dos managers foi comparada: entrega por arquivo ainda pendente. Nenhum código, testes, Compose, chamadas upstream ou Docker foram executados nesta revisão. | Revisão documental 1.8 registra R-18 e atualiza A-006/A-008. Instalação gerenciada AgentMail permanece desabilitada nos dois agentes até entrega por arquivo e teste E2E por manager. Nenhuma implementação ocorreu nesta revisão; pendências preservadas. Alterações locais anteriores no plano mantidas |
| 2026-10-31 / Bill Kopp | R-19–R-22 aprovadas: redaction de respostas MCP, scan Trivy por candidato, padrões metadata e manter mypy ausente | Código observado: `097eb291462faffd95a796b63d9783f626eb5188`; nenhuma imagem candidata selecionada nesta decisão | Padrões inspecionados: Nanobot Stage-2 usa schema MCP externo `server.json` e extensão `pblabs.app.yaml`; Index fixa schema PBLabs 0.2; Weather usa MCP schema `2025-12-11`, extensão 0.2 e associa relatório Trivy a source SHA/image ID. `pyproject.toml` não configura mypy. Nenhuma alteração de runtime, scan, build ou chamada externa realizada. | Revisão documental 1.9 registra decisões e atualiza A-001/A-004/A-005/A-009. Pendências: implementar redaction; criar metadata sem declarar compatibilidade Positronic antes de validar; selecionar candidato e executar scan; decidir retenção/automação após resultado. Nenhum teste de runtime executado; `git diff --check` verificado após a edição |
| 2026-10-31 / Bill Kopp | Execução local R-19–R-24; A-001/A-003 implementadas; A-004/A-005/A-006/A-008/A-009 avançadas | Base commit `097eb291462faffd95a796b63d9783f626eb5188`; candidato final source Git tree ID `ebdd933ec4b37dff7a67455fcf3e42571f4ccbba`, image `percival-agentmail-mcp:0.4.0-stage2-ebdd933`, ID `sha256:bfa3fb1f3147867d9d5fc269b0b66fdc4b17f0f7a865703c337c01b52ee9c2ce`, linux/amd64 | `uv run pytest --cov`: 246 passed/1 skipped, 91.40%; Ruff check/format passaram. Schemas MCP/PBLabs passaram; Index catalog check validou 0 entries e perfil AgentMail está draft. Docker/Compose `--version`, MCP conformance initialize/tools/list/status (24 tools) e bind read-only dos dois arquivos sintéticos passaram. Canary detectou ID em log `httpx` INFO; logger foi limitado a WARNING e conformance final (com ambos os segredos como files) passou sem leak. Trivy 0.76.1/DB 2026-10-31: primeiro candidato 1 High `CVE-2026-114605` em dnspython 2.8.0; lock 2.9.1; final zero findings. Evidência: `docs/security/2026-10-31-trivy-stage2-local-candidates.md`; JSON/manifests em runtime tmp. Nanobot: 14 testes MCP, Ruff e basedpyright dirigido (0 errors); WebUI 19 testes/lint. Positronic: 31 testes managed/typecheck. Fixtures E2E isoladas passaram: Positronic `ManagedServers` + `ManagedStdioTransport`; Percival `DockerMcpService` + `MountPolicy` com broker fixture, cada uma iniciou a imagem e chamou `mail_get_status` contra mock. |

| 2026-10-31 / Bill Kopp | Finding adicional A-001: inbox ID em URL INFO de httpx; redação de texto de erro/logs e conformance safe-call | Source tree `b89a97f866714878d328abdc0bdc9111f9d79858`; candidato final `0.4.0-stage2-b89a97f`, image ID `sha256:ccf56dbe83f91efb1411f381b0b66fdc4b17f0f7a865703c337c01b52ee9c2ce` | `pytest --cov`: 246 passed/1 skipped, 91.48%; Ruff/format e YAML CI limpos. O conformance helper iniciou com dois `--secret-file`, fez `initialize`, `tools/list`, chamou `mail_get_status` contra mock e confirmou canários de API key/inbox ID ausentes no output. Trivy 0.76.1: 0 findings. Relatórios e diagnóstico redigido em `docs/security/2026-10-31-trivy-stage2-local-candidates.md`. | Sem chamadas reais, commit/push, CI remoto ou instalação ativa. Manager E2E fixture continua separado; o broker Percival real ainda exige validação. |

**Limite de aceite da revisão 2.0:** os fixtures E2E e testes de código não equivalem a instalar o MCP por um broker ativo. A-008 segue parcial até E2E pelo processo broker Percival; CI remoto, digest/release, claim dos namespaces e adoção Positronic também seguem pendentes. Nenhum estado real de manager foi alterado.

| 2026-10-31 / Bill Kopp | Handoff de execução local / revisão 2.0 | Source tree do candidato `ebdd933ec4b37dff7a67455fcf3e42571f4ccbba`; imagem `sha256:bfa3fb1f3147867d9d5fc269b0b66fdc4b17f0f7a865703c337c01b52ee9c2ce` | Findings locais limpos após fix dnspython; canary do inbox ID detectou URL de `httpx` e a regressão foi corrigida/retessada. E2E Positronic pelo `ManagedServers` temporário e fixture Percival service+mount-policy passaram com mock e arquivos sintéticos. Contratos/schema/CI atualizados. | Permanecem: E2E pelo processo broker Percival real, execução remota CI, nome/digest/release do Registry/Hub, e decisão de habilitar instalações após esses gates. Nenhum manager ativo, inbox real, publicação, VEX, commit ou push foi alterado. |

### 6.1. Harmonização com IaC — 2026-10-31

- A convenção de ownership `R-12` do coordenador IaC confirma Bill como owner;
  a decisão local de signatário único permanece registrada neste plano. Não há
  aceite duplicado; permanecem os gates técnicos e a autorização explícita para
  publicação ou alteração de runtime.
- O perfil AgentMail permanece próprio: não declara binds de dados/host/workspace
  nem dados graváveis; exige dois mounts `kind: secret` read-only sob
  `/app/.secrets/`. Esses targets não concedem privilégios por si; o source path
  é configuração privada de cada manager. `R-10` não transfere ao AgentMail o
  default amplo específico do broker Percival.
- O harness comum `pblabs-mcp-stdio/v1` está versionado e passou em Notes e
  Weather, mas AgentMail não foi um desses consumidores. A prova cobre somente
  o subconjunto stdio comum; não substitui a CI, os testes funcionais, o perfil
  broker, nem prova de egress/startup contra o provider. Não declarar
  `V-REUSE` ou `V-PILOT` de AgentMail aprovado por analogia.
- O smoke DinD autorizado foi Percival+Notes; AgentMail continua fora desse
  piloto conforme D-01. A ação A-011 do plano IaC, sobre provenance, é
  específica ao bootstrap Percival, sem alterar os gates locais de
  imagem/release AgentMail. A-005 tem scan local do candidato atual e workflow
  CI definido por `R-24`, ainda sem execução remota. Scan e eventual VEX
  identificam source tree SHA/image ID; VEX é assinado por Bill para cada CVE
  do candidato, sem transferência de decisão entre imagens.

## 7. Última etapa — atualizar o plano coordenador

- [x] Contratos compartilhados atualizados uma vez: [S2-C01](../../../positronic-bean-IaC/docs/agent-runtime-contract.md), [S2-C03](../../../positronic-bean-IaC/docs/mcp-app-contract.md) e encaminhamento AgentMail no [plano geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md). A execução CI remota e os E2E por manager permanecem gates técnicos pendentes.
