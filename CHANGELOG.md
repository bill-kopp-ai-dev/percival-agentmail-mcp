# Changelog — Percival AgentMail MCP

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/),
versioning follows [SemVer](https://semver.org/).

## [0.4.0] — unreleased

### Added — attachment surface (v0.4.0)

- **`mail_send_email` attachments** now accept three new optional fields,
  exposed through the MCP layer and propagated verbatim to the upstream
  `SendAttachment`:
  - **`content_disposition`** (`"inline"` | `"attachment"`) — controls
    whether the attachment is rendered inline (e.g. embedded image in
    HTML via `<img src="cid:...">`) or as a downloadable file. Default
    upstream behavior (omitted) is attachment. Validated client-side
    against the SDK enum; typos fail fast before the round-trip.
  - **`content_id`** (`str`) — sets the Content-ID header so the
    attachment can be referenced inline via `<img src="cid:logo">` etc.
    Pair with `content_disposition="inline"` for embedded HTML images.
  - **`url`** (`str`) — public URL the AgentMail upstream fetches
    server-side. **Mutually exclusive with `content_base64`**. Bypasses
    the 6 MB request-body cap on the upstream side (up to ~30 MB total
    per message). Useful for large PDFs / datasets / MinIO-signed-URL
    flows; makes the `MinIO self-hosted` workaround proposed in the
    2026-08-21 issue unnecessary as a primary strategy.
- **`ALLOWED_CONTENT_DISPOSITIONS`** constant in `constants.py`
  (single source of truth for the enum + audit trail).

### Changed — `_to_sdk_attachments` (v0.4.0)

- Now **omits `content`** entirely when only `url` is set, so the wire
  body is clean (`{"url": "..."}`) instead of `{"url": "...",
  "content": null}`.
- Docstring updated to cover the new fields and to document the
  `content_base64` → `content` rename.

### Changed — cap and validation (v0.3.6, shipped with v0.4.0)

- **`MAX_ATTACHMENT_BINARY_BYTES` shrunk from 20 MB to 6 MB**
  (`constants.py`), aligned with the AgentMail upstream total-request
  limit documented on `SendAttachment.content`. Drift between the
  client-side cap and the upstream constraint is closed.
- `_validate_attachments` now rejects attachments with **both**
  `content_base64` and `url` set (mutual exclusion enforced by upstream
  `SendAttachment`), and rejects attachments with **neither** (would be
  silently sent as empty by the upstream — same failure mode as the
  2026-08-21 bug, just via a different code path).
- Error message on size violation now mentions the `url` field as the
  escape hatch for files larger than 6 MB.

### Added — regression coverage (v0.3.6 wire-level, v0.4.0 fields)

- **Wire-level** tests in `tests/test_mcp_transport_contract.py` (mock
  HTTP via `respx`, no network) covering the actual JSON shape sent to
  `POST /v0/inboxes/{id}/messages/send`:
  - `content_base64` must be renamed to `content` on the wire
    (regression guard for the 2026-08-21 fix).
  - Oversized attachments are rejected before the round-trip.
  - 5 MB attachments reach the wire (just under the new cap).
  - `content_disposition` and `content_id` propagate verbatim.
  - `url`-backed attachments omit `content`.
- **Handler-level** tests in `tests/tools/test_messages.py` covering
  the new validation:
  - `content_disposition` enum validation (rejects `"inlined"` etc.).
  - `content_base64` / `url` mutual exclusion.
  - Neither-content-nor-url rejection.
- **Live integration** tests in `tests/integration/` (opt-in via
  `AGENTMAIL_LIVE_TEST=1`) confirm the v0.3.5 fix end-to-end against
  the real AgentMail API: a `.md` and a `.pdf` attachment both
  round-trip and appear in `mail_read_message` of the recipient inbox.

### Added — Docker packaging (v0.4.0)

- **Multi-stage `Dockerfile`** that produces a self-contained stdio
  MCP image:
  - **Builder stage** uses `ghcr.io/astral-sh/uv:0.5.11-python3.12-bookworm-slim`
    and installs the package in non-editable mode into `/app/.venv`,
    with a BuildKit cache mount on `/root/.cache/uv` so CI warm runs
    skip the dependency-resolution layer.
  - **Runtime stage** is `python:3.12-slim` running as a fixed
    non-root user (`app`, UID 1000) with `ENTRYPOINT ["percival-agentmail-mcp"]`
    and `CMD []`. No TCP ports are exposed — stdio MCP only.
  - **Build args** `VERSION` (SemVer from `pyproject.toml`) and
    `GIT_SHA` (short commit) flow into OCI image labels
    (`org.opencontainers.image.version` / `.revision`) so registries,
    scanners and `docker inspect` stay truthful across local dev and
    CI builds.
  - The builder stage is pinned to `/app` as its WORKDIR so the venv
    is produced at its eventual runtime path — the absolute shebangs
    inside console_scripts stay valid after `COPY --from=builder`.
- **`.dockerignore`** that mirrors the repository's `.gitignore` plus
  `tests/`, `*.egg-info`, IDE noise and Docker artefacts themselves;
  prevents accidental secret/`.env` embedding and keeps the build
  context small.
- **`docker-compose.yml`** local recipe: build + env_file + stdio
  (`stdin_open: true`, `tty: false`); ready for Nanobot, opencode,
  Claude Desktop, VS Code or any MCP-aware client.
- **CI job `docker`** (`.github/workflows/ci.yml`):
  - Resolves `VERSION` from `pyproject.toml` and `GIT_SHA` from
    `GITHUB_SHA`, then builds with BuildKit + GHA layer cache.
  - **Smoke `--version`** asserts the package version reported by
    the running container equals the SemVer from `pyproject.toml`.
  - **Smoke no-env** asserts the lifespan raises the sanitized
    `ValueError("Missing or invalid AgentMail configuration...")`
    without dumping a raw traceback to the MCP client.
  - **Inspect** dumps image size, user, entrypoint and OCI labels
    for audit.

### Changed — README (v0.4.0)

- Header version bumped `0.3.4` → `0.4.0`.
- New `## Docker` section with three recipes (direct `docker run`,
  `docker compose`, integration with Nanobot and opencode) and an
  explicit note that no `server.yaml` / `tools.json` is shipped yet —
  that work is deferred until a Docker MCP Registry PR is opened.

### Tests

- 220 → **228 passed** (+8 net: 3 wire-level v0.3.6, 2 wire-level
  v0.4.0, 5 handler-level v0.4.0, 2 live integration opt-in).
  Coverage 92.01% → **92.14%** (target ≥80%).
- 2 pre-existing failures in `tests/test_config.py` are unrelated to
  this release — they are caused by `ServerConfig` reading the local
  `.env` file (a Pydantic-Settings default) and so leaking env values
  into unit tests that try to simulate "missing env". Reproducible
  in CI by deleting `.env`. Tracked separately; fix is to add
  `_env_file=None` to test fixtures or pass an explicit `_env_file`
  path under `tests/`.
- Lint: `uv run ruff check .` clean. `uv run ruff format --check .`
  clean.

## [0.3.5] — 2026-09-25

### Changed

- **Bumped `agentmail` SDK to `>=2.0.4`** (was `>=0.5.8`). The upstream
  Python SDK jumped the major version from 0.6.0 to 2.0.1 on
  2026-09-18 and released 2.0.4 on 2026-09-25 (today). The latest
  stable AgentMail API path remains `https://api.agentmail.to/v0/`
  (only version publicly exposed on <https://docs.agentmail.to/api-reference>),
  so no public contract change. The SDK 2.x line tracks the
  September 2026 API additions documented in
  <https://docs.agentmail.to/changelog.md> (signed CDN download
  disposition, account enable/disable, inbox metadata, full-text
  search, AgentID public-key auth, scoped webhooks, usage metrics).
- **`uv.lock` regenerated**: `agentmail` 0.5.8 → 2.0.4, with the
  expected transitive updates (`httpx`, `pydantic`, `pydantic-core`,
  `typing-inspection`, `websockets`, `idna`).

### Fixed (full code-review pass)

Discovered during a thorough code-review of the 0.3.4 → 0.3.5 line.
None of these are visible at the MCP tool contract layer (the 24
tools + 3 prompts are preserved); all changes are defense-in-depth
or hardening that turn client-side errors that would otherwise
round-trip to the API into clear, immediate LLM-actionable messages.

- **`RateLimiter.acquire` no longer blocks the asyncio event loop**
  (`client.py`). The previous implementation called `time.sleep`
  under a `threading.Lock`, which froze the entire FastMCP server
  for up to a full window when the local rate limit was reached —
  turning a defensive throttle into a denial-of-service against the
  server itself. `acquire` is now `async`, uses
  `asyncio.Lock` + `await asyncio.sleep(...)`, and `format_response`
  / `format_fenced` were made `async` accordingly. All tool handlers
  already used `await` on those methods, so the public-tool surface
  is unchanged.
- **System-label blocklist enforced client-side** (`helpers.py`,
  `tools/{drafts,messages,threads}.py`). Caller-supplied
  `add_labels` / `remove_labels` containing any of `"sent"`,
  `"received"`, `"unread"`, `"draft"`, `"read"` now raises a clear
  `ValueError` *before* hitting the upstream (which would otherwise
  return HTTP 400 "Cannot use system label"). The blocklist is
  centralized in `constants.SYSTEM_LABELS` and the helper
  `helpers.assert_no_system_labels` emits the tool name and field
  name in the error message so the LLM can attribute and correct it
  on the first try. Applied uniformly to `mail_send_draft`,
  `mail_update_draft`, `mail_update_message`, and
  `mail_update_thread`.
- **`mail_update_inbox.metadata` is now type-checked client-side**
  (`tools/inbox.py`). Non-dict input (string, list, scalar) used to
  produce an opaque Pydantic `ValidationError` from the SDK; the
  handler now emits an actionable `ValueError` explaining that
  `metadata` must be a JSON object (`dict`).
- **Recipient lists must be non-empty for `mail_send_email`,
  `mail_send_draft`, `mail_create_draft`, `mail_forward_message`**
  (`helpers.assert_non_empty`). Empty lists, empty strings, and
  whitespace-only strings are rejected up front with a clear
  message instead of being passed to the SDK (which may accept
  them and dispatch to nobody).
- **`cap_limit` accepts non-int input gracefully** (`helpers.py`). A
  string or other non-int limit previously raised `TypeError` from
  the `limit < 1` comparison; it now falls back to the default
  silently.
- **`format_error` truncation now appends "…"** (`client.py`). When
  the joined upstream body string exceeds the 600-char safety cap
  on the inline `message` field, the LLM now sees `Upstream: …` so
  it knows the message was cut. Under the cap, behaviour is
  unchanged.

### Internal

- `format_response`, `format_fenced` are now `async`. The decorators
  and lifecycle are unaffected; this is a pure async refactor
  driven by the rate-limiter fix.
- New shared helpers in `helpers.py`: `assert_no_system_labels`,
  `assert_non_empty`, plus a defensive `isinstance(limit, int)` guard
  in `cap_limit`.
- New constant `SYSTEM_LABELS` in `constants.py` documenting which
  labels the upstream rejects.
- New regression file `tests/test_hardening_fixes.py` (31 tests)
  exercising every fix above.

### Tests

- 173 → **220 passed**; coverage 91.33% → 92.01% (target ≥80%).
- `uv run ruff check .` and `uv run ruff format --check .` green.

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
