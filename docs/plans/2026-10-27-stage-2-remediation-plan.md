# Stage-2 — Remediação do Percival AgentMail MCP

**Data / revisão:** 2026-11-01 / 2.2.
**ID / estado:** S2-AM / revisão 2.2: execução local concluída, com validação manual do owner pendente no agente Percival. A-001–A-005, A-009 e A-010 foram implementadas/verificadas dentro do escopo desta etapa; A-004 tem metadata local válida em estado draft. Migração dos repositórios para a organização GitHub `p-bean-labs`, implantação de imagens na conta Docker Hub `pbeanlabs` e execução/retensão de CI remota estão fora do escopo. A-006–A-008 têm perfil/código/fixtures locais; falta Bill pinar e testar manualmente o servidor MCP pela UI de Percival, incluindo o startup health contra AgentMail real e timeout/readiness do broker. Não registrar a ação como concluída até observar o resultado. R-11–R-27 registram decisões do owner. Bill é o único owner, executor e signatário; aplicar uma verificação proporcional por mudança, sem aceites ou relatórios duplicados.
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
- [x] Registrar o perfil nos contratos/manifests aplicáveis; metadata local e
  contratos compartilhados foram atualizados. Os destinos futuros informados
  por Bill são a organização GitHub `p-bean-labs` e a conta Docker Hub `pbeanlabs`.
  Migração dos repositórios e implantação/publicação de imagem não fazem parte
  desta etapa; não há ação de deploy a executar neste plano.
- [ ] Bill fará manualmente, pela UI do agente Percival, a pinagem e os testes
  do servidor MCP, incluindo startup com egress ao AgentMail real. Confirmar
  readiness do broker após a chamada autenticada de health e timeout suficiente
  para o startup concluir. Registrar identidade fixada, resultado e timeout
  observado antes de fechar A-006–A-008; usar file references e não inserir
  valores de secrets neste plano. A ação ainda não foi executada.

### Decisões explícitas do owner — 2026-10-29 a 2026-11-01

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
| R-13 | “Qual é o contrato de mounts e secrets do AgentMail? R - Nos temos um template de contrato definido, veja em </home/bill/Projects/positronic-bean-IaC> e em </home/bill/Projects/pblabs-mcp-index>. Use esse template.” | Aplicar [Agent runtime contract](../../../positronic-bean-IaC/docs/agent-runtime-contract.md), [MCP application contract](../../../positronic-bean-IaC/docs/mcp-app-contract.md), o [perfil AgentMail de referência](../../../pblabs-mcp-index/servers/agentmail/pblabs.app.yaml) e as [propostas de perfil](../../../pblabs-mcp-index/docs/profile-proposals.md). Para AgentMail, não há binds de dados/host/workspace nem dados graváveis; egress é necessário; metadata declara requisitos, não concede privilégios. Segredos usam referências para arquivos read-only estreitos. O app suporta ambos `*_FILE`; a versão 2026-10-31 do perfil Index permanece draft, declara os dois secrets/mounts, sem fonte host ou entrada no catálogo. R-18/R-23 registram a entrega por arquivo; a decisão posterior R-27 limita a próxima validação manual à UI do agente Percival. Positronic não será configurado nem declarado compatível nesta etapa. |
| R-14 | “Como registrar lifecycle e startup no S2-C01? R - Vamos seguir com a sua sugestão: "documentar esses valores como perfil específico do AgentMail e exigir um teste do broker com timeout compatível, sem transformá-los em regra universal para todos os MCPs"” | S2-C01 registra AgentMail como perfil específico: startup depende de egress ao provider; shutdown usa grace de 2 s e fechamento do pool limitado a 5 s. Exigir teste do broker com timeout compatível; não generalizar esses números para outros MCPs. |
| R-15 | “Que tratamento dar a cada CVE do candidato? R - Vamos seguir com sua sugestão: "Sugiro decidir achado a achado, com evidência: corrigir ou justificar a disposição no VEX. Evitaria uma aprovação genérica que cubra candidatos ou image IDs futuros"” | Após cada scan, Bill decide cada achado com evidência, por candidato/image ID; corrigir ou justificar sua disposição no VEX. Não há waiver genérico para outros candidatos/image IDs. |
| R-16 | “Eu, Bill Kopp, sou o único "owner" dessa aplicação e também o "owner" da infraestrutura IaC, também sou o único a trabalhar nesses projetos. Logo, sou o único a decidir e assinar.” | Bill é o único owner, executor, decisor e signatário. Não criar papéis de aprovador/revisor separados nem condicionar trabalho local a aceites de terceiros. |
| R-17 | “Estamos perdendo muito tempo com validações cruzadas, provas desnecessárias e múltiplos aceites para a mesma coisa. Como eu sou o único dono e a única pessoa a trabalhar nessas aplicações isso não faz sentido.” | Usar uma verificação relevante por mudança/artefato e registrar a evidência uma vez. Repetir somente após mudança do artefato, falha ou novo risco concreto. Consolidar as decisões e resultados num registro canônico; não duplicar relatórios ou aceites entre repositórios. |
| R-18 | Bill aprovou a recomendação de tratar API key e inbox ID como segredos, favorecer arquivos read-only nos dois agentes, manter a metadata neutra quanto ao mecanismo privilegiado, implementar o suporte por arquivo em cada manager conforme sua arquitetura e não habilitar instalação gerenciada enquanto esses fluxos não existirem. | Declarar ambos como requisitos secretos no perfil. O contrato define requisitos e não concede mounts nem impõe mecanismo privilegiado; cada manager resolve referências para arquivos read-only, sem valores literais em `env`. O produto e os dois managers agora têm suporte local por arquivo e fixtures isoladas. A orientação inicial de não habilitar instalação permanece até verificação operacional. A decisão posterior R-27 especifica pinagem/teste manual apenas no agente Percival via UI; não configurar nem declarar Positronic compatível nesta etapa. O wrapper Compose foi somente fixture local, não caminho aprovado de instalação. |
| R-19 | Bill aprovou remover o campo `inbox` de `mail_get_version` e `mail_get_status`, sem mudar nomes ou schemas; manter `mail_get_inbox_info`, omitindo/mascarando identificadores e outros campos sensíveis desnecessários ao diagnóstico. | Implementação e testes concluídos em A-001. A mudança de valores foi registrada; consumidores podem depender do valor removido. O payload de info da inbox foi minimizado. |
| R-20 | Bill aprovou o primeiro scan com Trivy sobre candidato escolhido e identificado por source SHA e image ID; relatório e eventual VEX devem apontar para essa identidade. A decisão inicial deixou automação/retensão para depois do primeiro scan. | Scan local do candidato exato concluído em A-005. R-26 posteriormente excluiu execução/retensão de CI remota desta etapa. VEX aplica-se somente se um candidato avaliado tiver CVEs e nunca transfere disposições a outro image ID/digest. |
| R-21 | Bill decidiu usar os padrões e exemplos existentes em Nanobot, PBLabs MCP Index e Percival Weather para os metadados locais AgentMail. | Usar `server.json` validado contra o schema MCP externo `2025-12-11` e `pblabs.app.yaml` schema `0.2`, conforme os exemplos Weather/índice e o padrão Nanobot. Declarar API key e inbox ID como segredos sem valores; o perfil descreve requisitos sem conceder mounts/mecanismo. Metadata local validada em A-004 e permanece draft. A compatibilidade Positronic não é declarada nem será implantada nesta etapa; a validação manual planejada é somente no agente Percival conforme R-27. |
| R-22 | Bill decidiu manter `mypy` sem configuração até existir demanda concreta, seguindo a orientação atual do projeto. | Não adicionar mypy nem ampliar os gates desta remediação. Registrar a decisão em A-009; retomar apenas se surgir requisito concreto. |
| R-23 | Bill escolheu referências a arquivos de segredo já existentes no host: managers persistem apenas os paths privados, montam os arquivos read-only e não leem nem copiam os valores. | O produto lê ambos `*_FILE`; o perfil declara targets `kind: secret`; Percival deriva os nomes `_FILE` e Positronic oferece `--secret-file`. Paths não entram no export de inventário; owner/ACL permanecem responsabilidade do operador. Fixtures isoladas passaram sem alterar estado real. A fixture não exercitou a UI/estado ativo; R-27 registra a validação manual que Bill fará em Percival. |
| R-24 | Após o scan inicial, Bill escolheu automatizar Trivy na CI, reter o relatório completo como artifact associado ao build manifest/SBOM e falhar builds com findings Critical/High. | Decisão histórica implementada no workflow. A execução remota foi posteriormente excluída desta etapa por R-26; não é ação nem gate atual. O scan local do candidato exato foi concluído em A-005. |
| R-25 | Bill informou que os repositórios da Positronic Bean Labs serão implantados futuramente na organização GitHub [`p-bean-labs`](https://github.com/p-bean-labs), e as imagens na conta Docker Hub [`pbeanlabs`](https://hub.docker.com/repositories/pbeanlabs). A migração e o deploy não serão feitos nesta etapa. | Esses endereços são contexto de destino futuro, não autorização nem tarefa atual. Excluir deste plano qualquer ação/gate para migrar repositórios, reivindicar namespace, publicar ou implantar imagem no Docker Hub. Manter a metadata local em draft; não alegar namespace, tag ou digest verificados. |
| R-26 | Bill decidiu que a execução da CI remota está fora do escopo desta etapa. | A-005 fecha-se nesta etapa pela evidência do scan local do candidato exato (`b89a97f`) com zero findings. Não manter execução remota da CI ou retenção de artifact como pendência/gate desta etapa. O workflow já implementado permanece código; eventual execução automática não amplia o escopo nem requer acompanhamento como aceite. |
| R-27 | Bill fará manualmente pela UI do agente Percival a pinagem e os testes do servidor MCP, incluindo A-007. | Uma única validação operacional fecha A-006–A-008: identidade fixada, readiness MCP pelo broker, startup health autenticado contra AgentMail real e timeout do broker suficiente para concluir o startup. Registrar status/resultado e timeout, sem valores de secrets. Fixtures e mocks não comprovam egress nem saúde do provider real. Nenhuma pinagem/teste pela UI foi declarado concluído nesta revisão. |

## 3. Backlog e critérios de conclusão

Estado inicial em 2026-10-27: **não iniciada** para todas as ações. Na revisão
2.2, A-001/A-003 foram implementadas/verificadas localmente e A-007 incorporada
ao draft S2-C01. A-004 (metadata) e A-005 (scan local) estão concluídas para o
escopo desta etapa. Migração de repositórios, publicação/deploy de imagem no
Docker Hub e execução remota de CI foram excluídos por R-25/R-26. A-006–A-008
têm perfil e código local de file secrets com fixtures isoladas aprovadas. A
única ação operacional restante é Bill pinar e testar manualmente pela UI de
Percival, incluindo A-007: startup health autenticado contra AgentMail real e
timeout/readiness do broker, conforme R-27. As prioridades abaixo são as da ação de origem. Cada
ação precisa apenas da implementação e verificação pertinentes; não há etapa
adicional de aceite por outra pessoa.

| Ação | Achados / P | Trabalho e áreas previstas | Dependência / interface | Critério de verificação |
|---|---|---|---|---|
| A-001 | F-001, F-012, F-013 / P2 | Omitir/mascarar inbox no startup; sanitizar erro de transporte sem traceback público; remover ou tornar explícita leitura `.env` em config/server; não expor o inbox ID em representações de config nem em respostas de metadados/diagnóstico | Fix local; preservar nomes e schemas MCP | **Implementada localmente:** `ServerConfig.__repr__`/`__str__`/`model_dump` mascaram API key e inbox ID; `mail_get_version`/`mail_get_status` omitem `inbox` sem mudar nomes ou schemas; `mail_get_inbox_info` usa allowlist (`display_name`, `created_at`, `updated_at`) e exclui email/id/client/pod e metadata arbitrária. Um MCP conformance smoke com o inbox ID como canary detectou `httpx` INFO logando a URL do health check; `httpx`/`httpcore` agora ficam em WARNING e o smoke CI cobre ambos os canaries, fazendo `initialize`/`tools/list` e chamada segura `mail_get_status` com secrets em arquivos. `format_error` registra apenas status/tipo, redige API key/inbox ID de mensagens e metadados e a saída debug não emite traceback. Erro de config sanitizado; dotenv só explícito; file readers rejeitam symlink. Testes atualizados e suíte completa passou. Consumidores ainda podem depender do valor removido, conforme R-19. |
| A-002 | F-002 / P2 | Tratar SIGTERM/SIGINT com cancelamento do lifespan e fechamento do pool; declarar a limitação e o deadline do serviço | Contrato do broker Percival (`S2-NB-X01`/`S2-C01`) se/quando alterado | **Implementada/verificada localmente:** grace de 2 s, seguida de cancelamento do trabalho remanescente e fechamento protegido do pool até 5 s; Compose local dá 10 s. Testes locais cobrem tool lenta e close protegido. Se o perfil do broker mudar, uma verificação ponta a ponta deve confirmar timeout compatível; não exigir matriz ou aceite duplicado para a mesma alteração. |
| A-003 | F-003 / P3 | Repassar argumentos no entrypoint Compose ou recusar forma não suportada explicitamente | Receita local, sem iniciar serviço real | **Verificada em 2026-10-31:** `docker compose config --quiet` passou; a imagem da receita atual foi construída e `docker compose run --rm --no-deps server --version` retornou 0.4.0. Os dois paths de secret foram apontados a `/etc/hostname` somente como fixtures de montagem; `--version` não inicializa o runtime, não leu seus conteúdos e não fez upstream. Nenhuma inbox/credencial real foi usada. |
| A-004 | F-004 / P2 | Preparar e validar localmente `server.json` e `pblabs.app.yaml`/labels conforme `R-06`/`R-18`/R-21/R-23; declarar secrets e targets read-only sem conceder privilégios; distinguir índice PBLabs e Docker MCP Catalog opcional | Schemas externos 2025-12-11 e PBLabs 0.2; checkout do índice PBLabs | **Concluída para o escopo local desta etapa:** `docs/mcp/percival-agentmail-mcp/{server.json,pblabs.app.yaml}` passam os schemas; o perfil no índice local também passa 0.2 e declara os dois secrets/targets. Permanece `draft`, sem compatibilidade Positronic declarada. Destinos futuros informados: GitHub `p-bean-labs` e Docker Hub `pbeanlabs`; migração de repositórios e publicação/deploy de imagem estão fora do escopo. Não verificar ou reivindicar namespace, tag ou digest agora; catálogo do Index permanece vazio. |
| A-005 | F-005 / P2 | Escanear o candidato local exato com Trivy (`R-11`/R-20); registrar source Git tree SHA + image ID e relatório; corrigir/triagem por CVE conforme `R-07`/R-15 e referenciar tracker F3 canônico | Trivy/DB local | **Concluída para esta etapa:** o primeiro candidato tinha 1 High `CVE-2026-114605` em dnspython 2.8.0; `uv.lock` foi atualizado para 2.9.1. Candidato final `0.4.0-stage2-b89a97f`, source tree `b89a97f866714878d328abdc0bdc9111f9d79858`, image ID `sha256:ccf56dbe83f91efb1411f381b0b66fdc4b17f0f7a865703c337c01b52ee9c2ce`, Trivy 0.76.1, DB de 2026-10-31: 0 findings. Evidência local: [scan Trivy](../security/2026-10-31-trivy-stage2-local-candidates.md). Nenhum VEX é necessário para esse candidato sem findings. Execução remota de CI/retensão de artifacts não é pendência desta etapa (`R-26`). |
| A-006 | F-011 / P1 | Declarar perfil stateless sem binds de dados/host/workspace nem dados graváveis; limitar secret mounts a referências read-only estreitas conforme `R-18`/R-23 | Configuração do broker Nanobot (`S2-NB-X01`/S2-C01) | **Perfil/código local verificados; validação operacional pendente:** Compose mantém rootfs read-only, tmpfs restrito, capabilities removidas e secret files read-only. O perfil declara apenas dois mounts `kind: secret` read-only sob `/app/.secrets/`, sem binds de dados/workspace ou dados graváveis. Fixtures verificaram resolução e leitura pelo UID 1000. Bill fará a pinagem/teste manual via UI de Percival (`R-27`); não habilitar como validado até registrar o resultado dessa ação. |
| A-007 | F-007 / P1 | Registrar no perfil AgentMail a decisão de startup/egress; não criar endpoint/override no runtime | Contrato S2-C01; mesma validação manual R-27 de A-006/A-008 | **Decisão registrada; verificação operacional pendente:** o startup faz health request autenticado ao AgentMail e depende de egress. Não haverá fixture/override de endpoint no runtime. A fixture local prova somente o comportamento contra mock, não a rede do broker nem a saúde do provider real. Bill verificará pela UI de Percival que o broker permite a chamada real e aguarda sua conclusão dentro do timeout configurado; registrar readiness/status e timeout observado. D-01 exclui AgentMail do piloto. |
| A-008 | F-008 / P2 | Conforme `R-18`/R-23, tratar API key e inbox ID como secrets via arquivo read-only; implementar suporte nativo a ambos `*_FILE`; alinhar manager/configuração/docs/profile | UI do agente Percival; teste manual do owner (`R-27`) | **Implementada em código; fixtures isoladas passaram; validação manual pendente:** app lê ambos `*_FILE`, valida arquivos regulares e rejeita symlinks. Percival e Positronic resolveram secret mounts/read-only file refs em fixtures locais; ambos chamaram `mail_get_status` contra mock sem expor os canários. Bill fará manualmente a pinagem e os testes via UI do agente Percival. Ação ainda não executada; registrar identidade fixada e resultado da UI antes de fechar A-008. Não incluir valores de secrets no registro. Adoção Positronic não foi solicitada nem declarada. Evidência das fixtures: `docs/security/2026-10-31-secret-file-manager-fixtures.md`. |
| A-009 | F-009, F-010 / P3 | Reconciliar docs de estado/changelog/segurança; registrar decisão mypy (`R-22`); verificar licença apontada no §6 | Nenhuma decisão externa pendente para mypy; documentação local | **Concluída localmente:** `LICENSE` MIT existe; CHANGELOG/README/docs registram redaction, paths `*_FILE`, scan local e `mypy` ausente conforme R-22. README recomenda paths de arquivos read-only, e o wrapper transitório foi removido. Workflow Trivy/gate já consta no código; sua execução remota não integra o escopo desta etapa (`R-26`). A nota F3 antiga permanece excluída; tracker canônico decidido por `R-05`: `pblabs-mcp-index`. |
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
  `LICENSE` MIT. A direção inicial de evidência CI foi refinada por R-20 para
  executar primeiro um scan local do candidato; R-26 depois excluiu a execução
  remota de CI e sua retenção como ações/gates desta etapa.
  - Para o perfil normal AgentMail, egress ao provider no startup é ratificado pelo
    owner do produto; nenhuma fixture/override de endpoint será adicionada ao runtime.
    A decisão não homologa o provider nem altera a exclusão do piloto D-01; sua
    incorporação no contrato S2-C01 segue pendente.
  - Bill aprovou o uso de S2-C01/S2-C03 e as decisões específicas. A validação
    operacional corrente é a ação manual de pinagem/teste via UI de Percival
    registrada em R-27; não criar E2E/aceite separado para os mesmos resultados.
  - `R-07` define o tratamento VEX; Bill confirmou em `R-12` que será seu
    signatário. O scan local da primeira imagem está registrado por source
    SHA/image ID; não há findings nem VEX necessário. Execução remota/retensão CI
    saiu do escopo atual em R-26.
    `R-05` centraliza F3 por image ID em `pblabs-mcp-index`. A exclusão local da
    nota antiga permanece intacta e não deve ser substituída por cópia concorrente.

## 4. Ordem prática e interfaces

Os lotes abaixo servem apenas para organizar a execução; não são gates de aprovação.

1. **AM-1:** A-001/A-002, A-003 e A-009. Implementação, regressões e contrato
   wire-level verificados com fixtures locais.
2. **AM-2:** A-006/A-007/A-008. Perfil registrado em S2-C01. Ação restante:
   Bill fará pinagem e testes manuais via UI de Percival, incluindo startup
   health contra AgentMail real e timeout/readiness do broker. Usar file refs,
   sem registrar valores de secrets; anotar identidade e resultado observados.
3. **AM-3:** A-004/A-005 e A-010. Metadata validada localmente e scan local do
   candidato registrado. Migração/publicação de imagem e execução remota de CI
   estão fora do escopo atual por R-25/R-26; não são tarefas/gates deste plano.

Bill trabalha nos repositórios e sistemas envolvidos. Não exigir retornos ou
aceites intermediários entre lotes. Registrar compatibilidade apenas quando uma
mudança tocar lifespan, configuração, prompts ou schema. `R-03` remove estimativas
de esforço, custo e prazo.

## 5. Qualificação futura no checkout

- [x] Regressões dos casos observados e suíte `uv run pytest --cov`; `uv run ruff
  check .` e `uv run ruff format --check .` passaram. Em 2026-10-31: 246 passed,
  1 skipped, cobertura 91,48%.
- [x] Qualificação offline da imagem `0.4.0-stage2-b89a97f`: versão/configuração,
  MCP `initialize`, `tools/list` e chamada segura `mail_get_status` com fixture
  mock e secrets sintéticos file-backed. Conformance repetido após o último
  ajuste e passou; não usar imagem diferente sem nova qualificação proporcional.
- [x] Mudanças locais de sinais, secrets, configuração e conteúdo de email têm
  cobertura na suíte; foram adicionados testes para comportamentos novos.

Ação manual do owner: pinagem e testes pela UI de Percival, incluindo startup
health real e timeout/readiness do broker, estão registrados uma única vez na
seção 2 (`R-27`). Publicação/deploy de imagem e execução remota da CI não são
critérios desta etapa (`R-25`/`R-26`).

Fixtures locais não homologam o provider real nem enviam email. Chamada real,
publicação ou mudança de produção só ocorre quando estiver explicitamente incluída
na instrução de Bill; não se pede nova aprovação para repetir o mesmo escopo.

## 6. Penúltima etapa — documentar execução neste plano

- [x] Ao concluir um lote, registrar uma única vez o resultado, commit/source SHA,
  verificações executadas e pendências neste plano. Referenciar CI/artefatos
  existentes; não copiar a mesma evidência para vários relatórios.
- [x] Atualizar o plano coordenador somente quando uma mudança alterar contrato
  compartilhado ou bloquear outra ação; apontar para este registro em vez de
  repetir o relatório. Contratos compartilhados e encaminhamento foram
  atualizados; preservar a coleta histórica.

| Data / owner | Ações / achados | SHA inicial → final | Mudanças / evidências locais | Resultado / V-* / pendências |
|---|---|---|---|---|
| 2026-10-27 / executor Positronic | A-001/A-002/A-003 verificadas localmente; A-007 ratificada; A-009 parcial; A-010 limitação aceita; A-004/A-005/A-006/A-008 abertas | `68751b696b62b53fdcf893c3add9cf9e648e4391` → SHA final após commit | `pytest --cov`: 244 passed/1 skipped, 91,51%; Ruff/format; Compose config/build/version smoke; subprocess MCP `initialize` + tool lenta + SIGTERM demonstrou grace/hook/exit 0; imagem local `sha256:3549964cf53c12e3df730b9fab23967af53f40768300a31a8200caec957e7975`, linux/amd64, OCI revision=`local`. Scanner ausente; sem scan. | Parcial; sem inbox real, publicação ou alteração broker; S2-C01/C03 em draft; A-005 aguarda CI/scanner, A-006/A-008 broker; owner release/índice pendente; sem commit |
| 2026-10-29 / executor Positronic | R-11 e R-12–R-15 registradas; A-005 permanece aberta, sem scan do candidato | Checkout observado: `1da902a77a86a853a1140376a666718648597e0d`; SHA/image ID do candidato a registrar junto com o scan | `trivy --version`: 0.76.1; DB local baixada em 2026-10-28, a atualizar antes do scan conforme R-11. Apenas verificação de versão, sem scan. CI gera `docker-build-manifest.json` e SBOM CycloneDX e os publica como artefatos; não há scan de vulnerabilidades no workflow atual. | Bill assina VEX e promoção e decide achados por CVE/candidato conforme R-12/R-15. A-005 segue aberta: produzir scan local com DB atualizada e identidade do candidato; scan automatizado/retenção no CI e referência ao tracker F3 pendentes. Sem autorização implícita para publicação, promoção ou mudança de runtime |
| 2026-10-30 / Bill Kopp | Auditoria do plano contra checkout; A-001 requalificada; A-003 smoke atual pendente; A-004/A-006/A-008/A-009 reconciliadas; R-16/R-17 registram owner único e redução de burocracia | Código: `cfc7ccc8a9376db9af3eb95e1040258bfb8a4b20` (nenhuma alteração de código) | Worktree estava limpo no início. `uv run pytest --cov`: 244 passed/1 skipped, 91,51%; `uv run ruff check .`, `uv run ruff format --check .` e `git diff --check` passaram. CI contém conformidade MCP offline via `docker run`, validação de configuração Compose, manifesto e SBOM, sem Trivy. OCI labels presentes; metadata `server.json`/`pblabs.app.yaml` ausente. Compose local usa secrets por arquivo; wrapper exporta inbox ID como env. README ainda orienta env-file/ambiente, divergindo do perfil de arquivo no Compose. `mail_get_version`, `mail_get_status` e `ServerConfig.__repr__` incluem inbox ID; logs INFO de startup não o incluem. Nenhum acesso a AgentMail real, build Docker, scan Trivy ou mudança em broker. | Revisão 1.6 consolida resultados sem alterar código. Pendentes: smoke Compose atual com secrets sintéticos, revisão da exposição do inbox ID e interfaces A-004/A-005/A-006/A-008. Sem publicação, promoção, alteração de runtime ou acesso a inbox real |
| 2026-10-31 / Bill Kopp | Auditoria do plano contra o código atual; A-001 requalificada como exposição a corrigir; A-008/A-009 atualizadas; R-18 aprovada: file-secrets nos dois managers e bloqueio de instalação gerenciada até validação | Código observado: `097eb291462faffd95a796b63d9783f626eb5188`; plano já tinha alterações locais antes desta revisão | Confirmado por leitura: `config.py` inclui inbox ID em `__repr__`; `tools/version.py` e `tools/status.py` retornam `inbox`; `mail_get_inbox_info` fornece dados da inbox. README ainda recomenda credenciais via env/`--env-file`; Compose usa arquivos, mas wrapper exporta inbox ID ao processo. A implementação atual dos managers foi comparada: entrega por arquivo ainda pendente. Nenhum código, testes, Compose, chamadas upstream ou Docker foram executados nesta revisão. | Revisão documental 1.8 registra R-18 e atualiza A-006/A-008. Instalação gerenciada AgentMail permanece desabilitada nos dois agentes até entrega por arquivo e teste E2E por manager. Nenhuma implementação ocorreu nesta revisão; pendências preservadas. Alterações locais anteriores no plano mantidas |
| 2026-10-31 / Bill Kopp | R-19–R-22 aprovadas: redaction de respostas MCP, scan Trivy por candidato, padrões metadata e manter mypy ausente | Código observado: `097eb291462faffd95a796b63d9783f626eb5188`; nenhuma imagem candidata selecionada nesta decisão | Padrões inspecionados: Nanobot Stage-2 usa schema MCP externo `server.json` e extensão `pblabs.app.yaml`; Index fixa schema PBLabs 0.2; Weather usa MCP schema `2025-12-11`, extensão 0.2 e associa relatório Trivy a source SHA/image ID. `pyproject.toml` não configura mypy. Nenhuma alteração de runtime, scan, build ou chamada externa realizada. | Revisão documental 1.9 registra decisões e atualiza A-001/A-004/A-005/A-009. Pendências: implementar redaction; criar metadata sem declarar compatibilidade Positronic antes de validar; selecionar candidato e executar scan; decidir retenção/automação após resultado. Nenhum teste de runtime executado; `git diff --check` verificado após a edição |
| 2026-10-31 / Bill Kopp | Execução local R-19–R-24; A-001/A-003 implementadas; A-004/A-005/A-006/A-008/A-009 avançadas | Base commit `097eb291462faffd95a796b63d9783f626eb5188`; candidato final source Git tree ID `ebdd933ec4b37dff7a67455fcf3e42571f4ccbba`, image `percival-agentmail-mcp:0.4.0-stage2-ebdd933`, ID `sha256:bfa3fb1f3147867d9d5fc269b0b66fdc4b17f0f7a865703c337c01b52ee9c2ce`, linux/amd64 | `uv run pytest --cov`: 246 passed/1 skipped, 91.40%; Ruff check/format passaram. Schemas MCP/PBLabs passaram; Index catalog check validou 0 entries e perfil AgentMail está draft. Docker/Compose `--version`, MCP conformance initialize/tools/list/status (24 tools) e bind read-only dos dois arquivos sintéticos passaram. Canary detectou ID em log `httpx` INFO; logger foi limitado a WARNING e conformance final (com ambos os segredos como files) passou sem leak. Trivy 0.76.1/DB 2026-10-31: primeiro candidato 1 High `CVE-2026-114605` em dnspython 2.8.0; lock 2.9.1; final zero findings. Evidência: `docs/security/2026-10-31-trivy-stage2-local-candidates.md`; JSON/manifests em runtime tmp. Nanobot: 14 testes MCP, Ruff e basedpyright dirigido (0 errors); WebUI 19 testes/lint. Positronic: 31 testes managed/typecheck. Fixtures E2E isoladas passaram: Positronic `ManagedServers` + `ManagedStdioTransport`; Percival `DockerMcpService` + `MountPolicy` com broker fixture, cada uma iniciou a imagem e chamou `mail_get_status` contra mock. |

| 2026-10-31 / Bill Kopp | Finding adicional A-001: inbox ID em URL INFO de httpx; redação de texto de erro/logs e conformance safe-call | Source tree `b89a97f866714878d328abdc0bdc9111f9d79858`; candidato final `0.4.0-stage2-b89a97f`, image ID `sha256:ccf56dbe83f91efb1411f381b0b66fdc4b17f0f7a865703c337c01b52ee9c2ce` | `pytest --cov`: 246 passed/1 skipped, 91.48%; Ruff/format e YAML CI limpos. O conformance helper iniciou com dois `--secret-file`, fez `initialize`, `tools/list`, chamou `mail_get_status` contra mock e confirmou canários de API key/inbox ID ausentes no output. Trivy 0.76.1: 0 findings. Relatórios e diagnóstico redigido em `docs/security/2026-10-31-trivy-stage2-local-candidates.md`. | Sem chamadas reais, commit/push, CI remoto ou instalação ativa. Manager E2E fixture continua separado; o broker Percival real ainda exige validação. |

**Limite registrado em 2026-10-31:** fixtures e testes de código não equivalem a configurar o MCP pela UI/manager ativo, nem comprovam o egress do broker ou a saúde do AgentMail real. A atualização de escopo de 2026-11-01 (R-25–R-27) retirou migração/deploy e CI remota desta etapa; a única validação operacional ainda aberta é a pinagem/teste manual de Bill pela UI do agente Percival, incluindo startup health real e timeout/readiness. Nenhum estado real de manager foi alterado até executar essa ação.

| 2026-10-31 / Bill Kopp | Handoff de execução local / revisão 2.0 | Source tree do candidato `ebdd933ec4b37dff7a67455fcf3e42571f4ccbba`; imagem `sha256:bfa3fb1f3147867d9d5fc269b0b66fdc4b17f0f7a865703c337c01b52ee9c2ce` | Findings locais limpos após fix dnspython; canary do inbox ID detectou URL de `httpx` e a regressão foi corrigida/retessada. E2E Positronic pelo `ManagedServers` temporário e fixture Percival service+mount-policy passaram com mock e arquivos sintéticos. Contratos/schema/CI atualizados. | **Snapshot histórico de 2026-10-31, supersedido por R-25–R-27:** naquela data ainda eram listados E2E por broker Percival, CI remota e identidade de release/Registry como pendências. R-25/R-26 retiraram migração/deploy e CI remota do escopo atual; R-27 define a validação manual via UI de Percival. Nenhum manager ativo ou inbox real havia sido alterado neste handoff. |

| 2026-11-01 / Bill Kopp | R-25–R-27: destinos futuros e exclusões de escopo confirmados; A-004/A-005 reconciliadas; A-006–A-008 encaminhadas à validação manual pela UI de Percival | Código Stage-2 commit `34def43`; candidato qualificado `b89a97f` | GitHub alvo futuro: `https://github.com/p-bean-labs`; Docker Hub alvo futuro: `https://hub.docker.com/repositories/pbeanlabs`. Migração e publicação/deploy excluídos desta etapa. CI remota excluída como gate; scan local concluído com zero findings. Fixtures file-secret não concluem ação manual nem comprovam health/egress real. | **Próxima ação:** Bill fixa e testa o servidor MCP manualmente pela UI do agente Percival, incluindo startup health real e timeout/readiness do broker; registrar identidade e resultado quando executado. |

### 6.1. Harmonização com IaC — 2026-11-01

- A convenção de ownership `R-12` do coordenador IaC confirma Bill como owner;
  a decisão local de signatário único permanece registrada neste plano. Não há
  aceite duplicado. Migração e deploy de imagem foram excluídos desta etapa por
  R-25; a pinagem/teste manual da configuração Percival permanece em R-27.
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
  específica ao bootstrap Percival. A-005 foi satisfeita pelo scan local do
  candidato atual; execução remota de CI está fora do escopo por R-26. Não há
  VEX para o candidato sem findings. Se surgir futuramente um candidato com
  CVEs, qualquer decisão VEX deve identificar seu source tree/image ID, sem
  transferência de disposição entre imagens.

## 7. Última etapa — atualizar o plano coordenador

- [x] Contratos compartilhados atualizados uma vez: [S2-C01](../../../positronic-bean-IaC/docs/agent-runtime-contract.md), [S2-C03](../../../positronic-bean-IaC/docs/mcp-app-contract.md) e encaminhamento AgentMail no [plano geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md). CI remota e deploy não são gates desta etapa; resta pinagem/teste manual pela UI de Percival com startup health real e timeout/readiness (`R-27`).
