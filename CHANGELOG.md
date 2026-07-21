# Changelog — Percival AgentMail MCP

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/),
versioning follows [SemVer](https://semver.org/).

## [Unreleased]

### Fixed
- **Duplicate side-effect risk removed:** `@retryable` no longer wraps
  non-idempotent write operations (`mail_send_email`,
  `mail_reply_to_message`, `mail_reply_all_message`,
  `mail_forward_message`, `mail_create_draft`, `mail_send_draft`). The
  AgentMail SDK has no idempotency key, so auto-retrying these on a
  transient 5xx/timeout could have sent a duplicate email or created a
  duplicate draft. Read/list/get/update/delete operations keep retrying.
- **Attachments now actually reach the API:** `mail_send_email`'s
  `attachments` payload used `content_base64` as the key, but the SDK's
  `SendAttachment` model only recognizes `content` for the base64
  payload — the extra `content_base64` key was silently accepted and
  ignored (`extra="allow"`), so every attachment was sent with empty
  content. The tool now translates `content_base64` → `content` right
  before the SDK call; the LLM-facing parameter name is unchanged.
- **Version drift:** `percival_agentmail_mcp.__version__` was still
  hardcoded to `"0.1.0"` after the 0.2.0 release, even though
  `--version` (which read `importlib.metadata` separately) reported the
  correct value. `__version__` itself now derives from
  `importlib.metadata`, so there is exactly one source of truth again;
  `server.py`'s redundant `_resolve_version()` helper was removed.
- Corrected stale tool-count references (README, `tools/__init__.py`,
  test docstring) from 21/24 to the actual 23.

## [0.2.0] — 2026-07-21

### Added
- `.env.example` template versionável.
- `CHANGELOG.md` (este arquivo).
- `[project.urls]` em `pyproject.toml` linkando repo, issues e changelog.
- **3 MCP prompts** registrados em `src/percival_agentmail_mcp/prompts.py`:
  `summarize_email`, `draft_reply`, `classify_message`. Reforçam o
  modelo de "email body é external data" e guiam o LLM em fluxos
  recorrentes.
- Tool `mail_get_attachment` — download de anexos via SDK.
- Tool `mail_mark_thread_read` — atalho para marcar thread como lida/não-lida.
- `mail_send_email` agora aceita lista de `attachments` (max 20 MB base64).
- `mail_get_status` pinga a API real e retorna `api_latency_ms`.
- Workflow CI em `.github/workflows/ci.yml` (lint + testes em Python 3.11/3.12).
- Pre-commit hooks em `.pre-commit-config.yaml` (ruff + pre-commit-hooks + uv-lock).
- `pyproject.toml` com `[tool.coverage.*]` e `--cov-fail-under=80`.
- `constants.py`, `helpers.py`, `decorators.py` — módulos extraídos.
- Subpacote `tools/` com 1 módulo por domínio (`inbox`, `messages`, `threads`, `drafts`, `status`).
- Decorator `@with_agentmail` (injeta client/config + captura erros) e `@retryable`.

### Changed
- **Segurança:** `inbox_id` agora validado como `EmailStr`; `max_results`/`timeout` com bounds rígidos.
- **Segurança:** API key mascarada em `__repr__` / `__str__` / `model_dump`.
- **Segurança:** `aclose()` chamado explicitamente no shutdown do lifespan.
- **Segurança:** fences aplicados a **todos** os campos externos (subject, from, to, cc, preamble, snippet), não só text/html.
- **Segurança:** erro formatado cobre `ApiError`, `httpx.TimeoutException`, `httpx.ConnectError`, `pydantic.ValidationError` e genéricos (com mapa expandido de status codes).
- **Resiliência:** retry com backoff exponencial para 408/429/500/502/503/504.
- **Resiliência:** rate limiter token-bucket (30 chamadas/60s).
- **Resiliência:** servidor faz health check no startup e aborta com mensagem clara se a API estiver inacessível.
- Versão única da verdade via `importlib.metadata.version(...)`.
- `args.dev` removido (era dead code).
- `tools.py` (511 linhas) dividido em 5 módulos por domínio.

### Removed
- `scratch_test.py` (continha e-mail pessoal hardcoded).

### Security
- `LifespanContext` agora é `dataclass(frozen=True)`, garantindo imutabilidade.
- Fencing preservado em mutação (substituição de string, não alteração in-place).

## [0.1.0] — 2026-07-21

### Security
- Sanitized error messages returned to LLM clients (HIGH-02).
- Masked API key in `ServerConfig.__repr__` / `__str__` (LOW-01).
- Content fences delimit untrusted email bodies (HIGH-01).
