# Changelog — Percival AgentMail MCP

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/),
versioning follows [SemVer](https://semver.org/).

## [0.3.2] — 2026-07-22

### Fixed (review of the 0.3.0/0.3.1 incident response)

- **`AgentMailClientWrapper.aclose()` closed the wrong object (Bug R4
  was only half-fixed).** The 0.3.1 fix stopped at
  `wrapper.client._client_wrapper.httpx_client`, but that object is
  agentmail's own `AsyncHttpClient` wrapper, which has no `aclose()` —
  the code's defensive `getattr(..., None)` made this fail silently
  instead of raising, so the original crash was gone but the real
  `httpx.AsyncClient` (one level deeper, at
  `...httpx_client.httpx_client`) was never actually closed. Verified
  against the live agentmail-sdk 0.5.x object graph. Added a mock-free
  regression test (`test_wrapper_aclose_closes_the_real_sdk_httpx_client`)
  that exercises the real SDK object instead of a hand-built mock,
  since mock/reality drift is exactly what caused both the original
  bug and this incomplete fix.
- **Missing `respx` dev dependency.** `tests/test_mcp_transport_contract.py`
  (S1) imports `respx`, but it was only ever declared in the parent
  monorepo workspace's `pyproject.toml`, not in this package's own
  `[dependency-groups.dev]`. Running `percival-agentmail-mcp`
  standalone (as its own README's `uv sync --all-extras --dev`
  instructions describe) would fail to collect that test file.
  Added `respx` here.

### Internal

- Corrected stale tool-count references (README, `tests/conftest.py`)
  from 23 to 24 after `mail_get_version` was added.
- Removed `tools/version.py`'s duplicate version-resolution helper
  (`_resolve_package_version`, with a redundant
  `except (PackageNotFoundError, Exception)`) in favor of the
  `percival_agentmail_mcp.__version__` single source of truth.

### Verified

- Re-confirmed Bugs A–D (`mail_send_draft`, `mail_forward_message`,
  `mail_update_message`, `mail_update_inbox`) are fixed at the wire
  level via `tests/test_mcp_transport_contract.py`, which asserts on
  the actual HTTP request body sent to a mocked AgentMail endpoint
  (not just handler-level mocks).

## [0.3.1] — 2026-07-21

### Fixed (discovered live-testing on 2026-07-22; complements the 0.3.0
incident response)

- **`mail_send_draft` — `sent` is a system label.** The 0.3.0 fix used
  ``add_labels=["sent"]`` to avoid an empty body. The AgentMail upstream
  rejects system labels ("sent", "received", "unread", "draft", "read")
  with HTTP 400 "Cannot use system label". The handler now sends the
  custom sentinel ``add_labels=["mcp-sent"]`` (overridable by the
  caller) and surfaces a clearer error message to the LLM.
- **`mail_mark_thread_read` — same system-label issue.** Reading /
  unreading a thread now adds/removes the custom sentinel
  ``mcp-read`` instead of the system ``read`` label.
- **`mail_update_thread` (Bug R1).** Same empty-body issue as Bug C
  (2026-07-21). The handler now requires at least one of
  ``add_labels`` / ``remove_labels`` and rejects the call locally with a
  clear error message before hitting the API.
- **`mail_update_draft` (Bug R2).** The handler accepted 0 mutable
  fields and silently sent ``{}`` to the upstream, which rejected with
  HTTP 400. The handler now requires at least one of
  ``to / subject / text / html / send_at / add_labels / remove_labels``.
  Removed `@retryable` from `create_draft` / `send_draft` because the
  SDK has no idempotency key and retrying could produce duplicate drafts
  or duplicate dispatches.
- **Server shutdown — `AsyncAgentMail' object has no attribute 'aclose'`
  (Bug R4).** Discovered during integration: the SDK does NOT expose
  ``aclose()`` on the top-level instance. The httpx client lives at
  ``wrapper.client._client_wrapper.httpx_client``. Added
  ``AgentMailClientWrapper.aclose()`` which closes the underlying httpx
  client safely; the lifespan now uses it instead of crashing.

### Internal

- Migration of `threads.update(messages)` to `mail_mark_thread_read`'s
  custom sentinel (`mcp-read` instead of `read`) — test updated.
- Migration of `mail_send_draft` test fixtures to expect `mcp-sent`.
- Coverage threshold --cov-fail-under=80 preserved (now 91.74%).

## [0.3.0] — 2026-07-21

### Fixed (reported by nanobot live-testing on 2026-07-21, see
[MCP_Docs/Issues/2026-07-21-percival-agentmail-mcp-4-bugs.md](../../MCP_Docs/Issues/2026-07-21-percival-agentmail-mcp-4-bugs.md))

- **Bug A (`mail_send_draft`)** — handler was posting an empty body
  (``{}``), which the AgentMail upstream rejects with HTTP 400 because
  ``drafts.send`` requires at least one of ``add_labels`` /
  ``remove_labels``. The handler now always sends
  ``add_labels=["sent"]`` (label consistent with draft → sent
  lifecycle).
- **Bug B (`mail_forward_message`)** — same root cause: the upstream
  rejected forward calls without a body. The handler now always passes
  ``labels=["forwarded"]``.
- **Bug C (`mail_update_message`)** — calls with both `add_labels=None`
  and `remove_labels=None` were silently sending an empty body. The
  handler now raises a clear `ValueError` *before* hitting the API,
  letting the LLM know which field is missing.
- **Bug D (`mail_update_inbox`)** — the same empty-body problem on
  `inboxes.update`. The handler now requires at least one of
  ``display_name`` or ``metadata``, accepts a new ``metadata`` argument
  on the tool signature (S3 suggestion), and pre-normalises
  ``display_name`` by trimming and compressing internal whitespace.

### Added

- **Tool `mail_get_version`** (S7) — returns ``package_version``,
  ``server_name``, ``python_version``, ``platform``, ``inbox`` without
  calling the AgentMail API. Useful for troubleshooting "am I talking
  to the right server?".
- **S1 — End-to-end MCP-transport contract tests**
  (`tests/test_mcp_transport_contract.py`). These exercise the full
  chain — handler → SDK → httpx — by mocking the AgentMail HTTP API
  with `respx`. They catch the empty-body 400s that slipped past the
  previous handler-level mocks.
- **S5 — Actionable error responses.** `format_error` now accepts
  ``tool_name`` and ``affected`` and embeds both into the JSON
  payload. ``@with_agentmail`` populates them automatically. The
  message additionally surfaces the upstream body string when
  non-empty.

### Internal

- `--cov-fail-under=80` and `--cov` configured.
- `helpers.py` now exports both `build_kwargs` and `cap_limit`.

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
