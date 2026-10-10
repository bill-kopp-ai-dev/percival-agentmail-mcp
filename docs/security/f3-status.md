# F3 — pendências do `percival-agentmail-mcp` no gate do gateway

- **Data:** 2026-10-10 UTC.
- **Fonte canônica:** [`docs/reports/2026-10-10-f3-remediation-triage.md`](../../../../nanobot/docs/reports/2026-10-10-f3-remediation-triage.md)
  no repositório do gateway (`~/Projects/nanobot`) e o plano compartilhado
  [`docs/plans/2026-10-09-docker-standardization-refactor-plan.md`](../../../../nanobot/docs/plans/2026-10-09-docker-standardization-refactor-plan.md).
  Esta nota é um espelho por servidor; toda decisão de F3 vive no relatório
  canônico. (O AgentMail tem `docs/issues/` no `.gitignore` como rascunho
  local, então a nota F3 vive em `docs/security/`. Em outros MCPs
  Percival, a nota equivalente está em `docs/issues/2026-10-10-f3-status.md`.)
- **Imagem atual:** `percival-agentmail-mcp:0.4.0-34312b9-f3-91a24f005774`
  (SHA base `34312b9966efb946a7fb16ea53c205bf4abb71c9`,
  image ID `sha256:1fa2ca61c3685e8f0a7a33993d5e4d8b4ba8546c75ccec817fe5d010616d9fb4`).
  Trivy 0.67.2: **0 Critical / 44 High**.
- **Política:** `nanobot/docs/Decisions/2026-10-09-docker-image-posture-policy.md`.
  Findings Critical/High bloqueiam o gate F3; cada waiver precisa de
  aplicabilidade/mitigação/owner/expiração individuais.

## Findings remanescentes e estado

| CVE / pacote | Evidência local | Estado / decisão necessária |
|---|---|---|
| `CVE-2026-76642`, `CVE-2026-78408/09/10` / util-linux | Os advisories descrevem fluxos privilegiados de `mount`/`nsenter`/`fstab`/cgroups. O Dockerfile atual remove o setuid de `/usr/bin/mount` e apaga `/usr/bin/nsenter` e `/usr/bin/infocmp`; o container roda como UID 1000 com `CapEff=0000000000000000`. | Hardening reduz os caminhos, mas as libs e binários base permanecem presentes. Requer VEX por CVE com revisão de reachability e confirmação equivalente no builder CI. |
| `CVE-2026-54369` / libacl | Symlink traversal em `acl_*_file` com caller privilegiado. Container é non-root e não chama o helper de ACL com privilégio elevado no fluxo conhecido. | Triage de alcance ainda pendente; continua scanner High. |
| `CVE-2025-69720` / ncurses | Debian descreve overflow em `infocmp`. O binário foi removido no rebuild atual; libs ncurses permanecem. | Forte candidato a `vulnerable_code_not_present` para `infocmp`; revisar e formalizar VEX. |
| `CVE-2026-16742` / libsystemd/libudev | LPE em `systemd-homed` (Debian `<no-dsa> (Minor issue)`). `systemd-homed` não está instalado no runtime. | Candidato a `vulnerable_code_not_present`; formalizar VEX e revalidar no builder CI. |
| `CVE-2026-9538` / Perl Archive::Tar | Trixie lista como `postponed (Minor issue)`. `Archive::Tar` não é usado pelo servidor (somente cliente AgentMail via SDK oficial). | Candidatos a `vulnerable_code_not_present`; revisar e formalizar VEX. |
| CVEs de curl/GnuTLS no base | O MCP não depende de curl CLI. | Acompanhar novas CVEs no update cycle. |

## O que ainda falta neste repositório

1. **Triagem VEX formal por CVE** para o image ID do candidato atual
   (`sha256:1fa2ca61c368…`), em arquivo OpenVEX próprio sob
   `docs/security/`, com `justification`, `impact_statement` e
   `action_statement`. Este MCP ainda não tem um OpenVEX
   próprio; o gateway já tem
   [`2026-10-10-f3-openvex.json`](../../../../nanobot/docs/reports/2026-10-10-f3-openvex.json)
   para o seu image ID. Cada MCP precisa de um arquivo restrito ao seu
   digest, com a mesma checagem runtime + comparação CycloneDX.
2. **Build limpo e rescan no builder CI** do gateway (`ci.yml`,
   `linux/amd64`, Arch container pinado) no SHA
   `34312b9966efb946a7fb16ea53c205bf4abb71c9` (ou em um SHA que substitua
   o hardening local). Sem esse passo, F3 não fecha para este MCP.
3. **Acompanhamento de upstream Trixie**: se o pacote corrigido de
   `util-linux` ou `ncurses` aparecer em Trixie/Debian-security, regenerar
   o lock/snapshot, rebuildar, resscanear e remover o `chmod`/`rm` se
   tornarem desnecessários.
4. **Não fazer commit/push** deste diff até o operador autorizar; F3 não
   autoriza cutover, alteração de consumidores ou release.

## Evidência reproduzível

- Trivy JSON: `/home/bill/.positronic/runtime/tmp/opencode/trivy-reports/agentmail-f3-remediated.json`
  (SHA-256 `baa14352099c0348e79e4175ca590f6a53c30fa6bc5e5e0aea170b765ba4b3bd`).
- CycloneDX SBOM: `…/agentmail-f3-remediated.cdx.json`
  (SHA-256 `dbc60ed1aa438edd04885c9463be9db28d3a572b100b3a867f4c66c892b7b787`).
- Pin da base Python runtime: `python:3.12-slim@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe`.
- Pin da base UV (builder): `ghcr.io/astral-sh/uv:0.5.11-python3.12-bookworm-slim@sha256:cc9311ae7d42ccb51f6ac10c8ab8526de8a3f484b36349fd87af8e5ced7079c0`.
- Snapshot apt: `DEBIAN_SNAPSHOT=20261009T000000Z`.
