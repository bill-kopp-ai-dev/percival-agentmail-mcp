# Changelog — Percival AgentMail MCP

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/),
versioning follows [SemVer](https://semver.org/).

## [0.3.4] — 2026-07-22

### Fixed (post-incident follow-up from Nanobot's 10:41 UTC report)

- **`mail_update_inbox` client-side validation**: the AgentMail upstream
  rejects `display_name` containing `(`, `)` (HTTP 400 "Display name
  contains invalid character(s): ( )"). We now raise a `ValueError`
  with an actionable message **before** paying a round-trip to the
  API, so the LLM gets a clear hint instead of a generic 400 echo.
- **`format_error` upstream surfacing**: when an `ApiError` body is a
  Pydantic `ValidationErrorResponse` (rich per-field structure), we now
  parse `errors[i].message + errors[i].path` and surface the most
  actionable messages to the LLM both inline (`"Upstream: Display
  name contains invalid character(s): ( ) at display_name"`) and as a
  structured `upstream_details` list (capped at 3). Also keeps the
  plain-string-body fallback path so older endpoints still surface
  actionable text. Falls back to no `upstream_details` when the
  response is empty.

### Verified via live smoke against `billkopp@agentmail.to`

| Tool | Pre-fix report | Post-0.3.4 |
|---|---|---|
| `mail_send_email` | REGRESSED (400) | ✅ 200 + message_id |
| `mail_send_draft` | REGRESSED (400) | ✅ 200 + message_id |
| `mail_create_draft(to=...)` | REGRESSED (400) | ✅ works |
| `mail_update_inbox(display_name="X (v0.8.0)")` | 400 (Bug D residual) | ✅ actionable error envelope (no round-trip) |
| `mail_get_status` | online | ✅ online, `api_latency_ms~100` |
| `mail_list_messages` | 1+ msgs | ✅ (envia + lista normalmente) |

### Tests

- 6 novos tests em `tests/test_format_error_validation.py`
- 167 → **173 passed**; cobertura 91.33% (target ≥80%).

## [0.3.3] — 2026-07-22

### Changed

- **Pinned `agentmail>=0.5.8`** (was `>=0.5.0`). Version 0.5.0 shipped
  wheels that did NOT accept the `metadata` kwarg on
  `inboxes.update`, which surfaced in CI 2026-07-22 as a
  `TypeError: unexpected keyword argument 'metadata'`. We had already
  fixed the runtime guard (0.3.2) but the cleanest fix is to track an
  SDK that actually knows about the kwarg.
- **Sub-projeto `uv.lock` regenerated.** Many transitive deps were
  out of date (e.g. `certifi 2026.6.17` → `2026.7.22`,
  `soupsieve 2.9` → `2.9.1`, `protobuf 6.33.6` → `7.35.1`).
  Re-resolved against fresh `pyproject.toml` in a clean
  `/tmp/probe-percival` directory (the in-tree `uv lock` was a
  workspace no-op because `uv` was routing the resolution to the
  root `uv.lock`).
- **Verified aligned with workspace root**: `uv lock --check` passes
  from `/home/bill/Codes/mcp-servers-percival` after the regen.

### Verified

- `uv run pytest --cov` → 167 passed, 91.81% coverage.
- `uv lock --check` (workspace root) → aligned.
- Lint + format clean.

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
