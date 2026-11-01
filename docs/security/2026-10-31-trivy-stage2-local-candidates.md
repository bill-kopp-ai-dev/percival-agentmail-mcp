# Trivy evidence — AgentMail Stage-2 local candidates

**Scope:** local validation artifacts only. No image was published, promoted or
installed in either manager. The CI scan path is implemented but has not yet
run remotely.

## Scanner and database

- Trivy **0.76.1**, scanner `vuln` (Debian OS and Python packages).
- Vulnerability database updated **2026-10-31 13:09 UTC**; bundle digest
  `sha256:b591e9190cff4aa4e385b1a25bccfd9ecf178d3c77fd194e1410b7ce7e1df058`.
- Exact reports and build manifests are retained outside the checkout under
  `/home/bill/.positronic/runtime/tmp/opencode/` (paths below). No credentials
  or inbox data were used.

## Candidate chain

| Candidate | Source Git tree ID | Local image ID | Result | Evidence |
|---|---|---|---|---|
| `percival-agentmail-mcp:0.4.0-stage2-54395f4` | `54395f4af687d362cc68bfdd65577adea9941dd5` | `sha256:b7e254c2c90bea64b648808a676ae0b9848d73cf95cc4153b1cc3db2162a8b68` | **1 High:** `CVE-2026-114605`, `dnspython 2.8.0`, fixed in 2.9.0+ | `agentmail-trivy-54395f4.json`; initial manifest `agentmail-stage2-build-manifest.json` |
| `percival-agentmail-mcp:0.4.0-stage2-735ba26` | `735ba26893909ea0a5c06065a54eff17e1c9240a` | `sha256:a8623c5c44ad2a74eff687dbd74ad9b45714df83dba9a16f88d7d3e542940cb1` | **0 vulnerabilities** after dependency update | `agentmail-trivy-735ba26.json`; `agentmail-stage2-735ba26-manifest.json` |
| `percival-agentmail-mcp:0.4.0-stage2-ba8da41` | `ba8da41d6f4bab2c8c609b06645cf4a35d11ab32` | `sha256:e14553ac1c4159c50a9effb3060ed18c343088cf5a1c09eaf9f26df13c357619` | **0 vulnerabilities**; later superseded by startup-log fix | `agentmail-trivy-ba8da41.json`; `agentmail-stage2-ba8da41-manifest.json` |
| `percival-agentmail-mcp:0.4.0-stage2-ea5629f` | `ea5629f8c768b66625dc8298b7ea85f85f850bd6` | `sha256:fdd40632ceead6236d7073077429b37ec6894792d1bdd502513cb71476559415` | **0 vulnerabilities**; conformance exposed inbox ID in `httpx` INFO request URL | `agentmail-trivy-ea5629f.json`; `agentmail-stage2-ea5629f-manifest.json` |
| `percival-agentmail-mcp:0.4.0-stage2-ebdd933` | `ebdd933ec4b37dff7a67455fcf3e42571f4ccbba` | `sha256:bfa3fb1f3147867d9d5fc269b0b66fdc4b17f0f7a865703c337c01b52ee9c2ce` | **0 vulnerabilities**; startup URL logging fix and inbox-ID canary pass | `agentmail-trivy-ebdd933.json`; `agentmail-stage2-ebdd933-manifest.json` |
| `percival-agentmail-mcp:0.4.0-stage2-b89a97f` | `b89a97f866714878d328abdc0bdc9111f9d79858` | `sha256:ccf56dbe83f91efb1411f381b0b66fdc4b17f0f7a865703c337c01b52ee9c2ce` | **0 vulnerabilities**; final candidate after API-error log redaction | `agentmail-trivy-b89a97f.json`; `agentmail-stage2-b89a97f-manifest.json` |

All candidates are `linux/amd64`, version label `0.4.0`, user `app` (UID 1000).
The source identifier is a Git **tree** object ID for the uncommitted worktree,
not a commit or release SHA. The corresponding Docker `revision` label and
manifest match that tree ID. Image IDs are local config/manifest-list IDs, not
published repository digests.

## Disposition

The first scan found the vulnerable parser in the transitive `dnspython`
dependency ([Trivy advisory](https://avd.aquasec.com/nvd/cve-2026-114605)).
`uv.lock` now pins **2.9.1**. The upstream dnspython release notes
for [2.9.0](https://dnspython.readthedocs.io/en/stable/whatsnew.html) document
the 16-hop limit on DNS compression-pointer decompression; PyPI lists 2.9.1 as
released on 2026-10-29. The final candidate scan found no CVEs, so no VEX
disposition was created. The earlier candidate remains local
and unpromoted; its finding does not transfer to another image ID.

Separately, the MCP conformance canary exposed that `httpx` INFO logging
included the synthetic inbox ID in the health-check URL on stderr. The final
candidate raises `httpx`/`httpcore` request logging to WARNING; error formatting
also avoids raw upstream bodies, exception strings and tracebacks, and redacts
the configured API key/inbox ID from returned diagnostics. The conformance
harness supplies both secrets from synthetic read-only files, performs
startup/`initialize`/`tools/list` and `mail_get_status` against the mock, and
checks both file contents against protocol and stderr output; all passed.

The CI workflow now uploads the full Trivy JSON report alongside the build
manifest and CycloneDX SBOM and fails on Critical/High findings. The remote CI
run and artifact retention have not yet been observed; release identity and
publication remain separate gates.
