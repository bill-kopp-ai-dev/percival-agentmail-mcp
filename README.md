# 🤖 Percival AgentMail - percival.OS MCP

**Version 0.4.0**

[![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)]()
[![MCP](https://img.shields.io/badge/mcp-server-blue.svg)]()
[![percival.OS](https://img.shields.io/badge/percival.OS-ecosystem-orange.svg)](https://github.com/bill-kopp-ai-dev/percival.OS)

## 📋 Description
**Percival AgentMail** is an MCP server that provides AI agents with their own **autonomous email inbox** using the [AgentMail](https://agentmail.to) API. 

This server is part of the **percival.OS** ecosystem, a Personal Agentic Operating System designed for autonomy, security, and absolute privacy.

---

## 🛡️ percival.OS Principles
Like all components of `percival.OS`, this MCP server strictly follows our core principles:

- **Privacy First**: Unlike other services, AgentMail allows the agent to have a dedicated address, separating AI communications from your personal accounts.
- **Data Sovereignty**: The agent manages its own email interactions under your supervision and governance.
- **Hardened Security**: We implement *Prompt Injection Fencing* for incoming emails and error sanitization to prevent information leakage.
- **Transparency**: Open-source and auditable to ensure full governance of your data.

---

## 🚀 Features & Tools
The server exposes 24 tools optimized for LLM comprehension, divided into:

- **Inbox:** `mail_get_inbox_info`, `mail_update_inbox`, `mail_list_inbox_events`
- **Messages:** `mail_send_email` (supports attachments), `mail_list_messages`, `mail_read_message`, `mail_reply_to_message`, `mail_reply_all_message`, `mail_forward_message`, `mail_update_message`, `mail_delete_message`, `mail_get_attachment`
- **Threads:** `mail_list_threads`, `mail_get_thread`, `mail_update_thread`, `mail_delete_thread`, `mail_mark_thread_read`
- **Drafts:** `mail_create_draft`, `mail_list_drafts`, `mail_get_draft`, `mail_update_draft`, `mail_send_draft`
- **Utility:** `mail_get_status` (pings API, reports latency), `mail_get_version`

### 🎯 MCP Prompts
The server also exposes 3 prompts that guide the LLM through recurring
workflows safely:

- **`summarize_email`** — read an email and produce a structured
  3-bullet summary (topic / actions / sentiment).
- **`draft_reply`** — draft a reply (never sends; saves via
  `mail_create_draft`) in `professional` / `friendly` / `concise` /
  `apologetic` tones.
- **`classify_message`** — classify into one of `ACTION_REQUIRED`,
  `FYI`, `SPAM`, `NEWSLETTER`, `PERSONAL`.

Every prompt reinforces the **untrusted-email-body** model: the email
body returned by `mail_read_message` is enclosed between
`--- EMAIL BODY START ---` and `--- EMAIL BODY END ---` markers and must
be treated as data, never as instructions.

---

## 🐳 Docker

A multi-stage `Dockerfile` is shipped from v0.4.0 onward. The resulting
image is a self-contained stdio MCP server (~260 MB, non-root, no
exposed ports) that can plug into any MCP-aware client.

> **Scope note.** This cycle ships a **local-first** image only: no
> `server.yaml` / `tools.json`, no submission to the official
> [Docker MCP Registry](https://hub.docker.com/mcp) yet. The image
> runs against Nanobot, opencode and the Docker MCP Toolkit gateway
> (as a plain Docker image, not as a catalog entry).

### Quick start

```bash
# 1. Build the image locally (VERSION is read from pyproject.toml).
docker build --build-arg VERSION=0.4.0 --build-arg GIT_SHA=local \
  -t percival-agentmail-mcp:dev .

# 2. Smoke (offline, no network):
docker run --rm percival-agentmail-mcp:dev --version
# → Percival AgentMail MCP Server version 0.4.0

# 3. Run against your real inbox (stdio over the container's
#    stdin/stdout — the MCP client attaches via `docker run -i`):
docker run --rm -i --env-file .env percival-agentmail-mcp:dev
```

### With `docker compose`

The shipped `docker-compose.yml` optionally reads `.env`, exposes nothing, and
spawns the server in stdio mode (`stdin_open: true`, `tty: false`):

```bash
docker compose build
docker compose run --rm -T server --version
docker compose run --rm -T server
```

### With Nanobot (`~/.nanobot/config.json`)

```json
{
  "tools": {
    "mcpServers": {
      "percival-agentmail-mcp": {
        "command": "docker",
        "args": [
          "compose", "-f",
          "/path/to/percival-agentmail-mcp/docker-compose.yml",
          "run", "--rm", "-T", "server"
        ],
        "env": {
          "AGENTMAIL_API_KEY": "YOUR_API_KEY",
          "AGENTMAIL_INBOX_ID": "your_agent@agentmail.to"
        }
      }
    }
  }
}
```

Or without compose, pointing straight at the image:

```json
{
  "tools": {
    "mcpServers": {
      "percival-agentmail-mcp": {
        "command": "docker",
        "args": ["run", "--rm", "-i", "--env-file",
                 "/path/to/percival-agentmail-mcp/.env",
                 "percival-agentmail-mcp:dev"],
        "env": {}
      }
    }
  }
}
```

### With opencode (`.opencode/opencode.json` or `opencode.json`)

```json
{
  "mcp": {
    "percival-agentmail-mcp": {
      "type": "local",
      "command": [
        "docker", "compose", "-f",
        "/path/to/percival-agentmail-mcp/docker-compose.yml",
        "run", "--rm", "-T", "server"
      ],
      "environment": {
        "AGENTMAIL_API_KEY": "YOUR_API_KEY",
        "AGENTMAIL_INBOX_ID": "your_agent@agentmail.to"
      }
    }
  }
}
```

### Configuration

The runtime reads the same environment variables the local install
does — see `.env.example`. `AGENTMAIL_API_KEY` and `AGENTMAIL_INBOX_ID`
are mandatory; `AGENTMAIL_TIMEOUT` and `AGENTMAIL_MAX_RESULTS` have
safe defaults.

Pass them via `--env-file .env`, `docker run -e KEY=VALUE …`, or
the `environment:` / `env_file:` keys in `docker-compose.yml`. Secrets
never end up baked into the image: the `.dockerignore` blocks `.env*`
from the build context.

### CI

`.github/workflows/ci.yml` runs a dedicated `docker` job that builds
the image with BuildKit + GHA layer cache, then runs three smoke
checks: `--version` exits 0 with the SemVer from `pyproject.toml`,
a missing-env run raises the sanitized `ValueError` (no raw
traceback), and `docker inspect` confirms the non-root user, the
stdio entrypoint and the OCI labels.

---

## ⚙️ Local development (via uv)

For development or when you prefer a process-per-host tool instead of
a container, run the server straight from a source checkout using
[`uv`](https://docs.astral.sh/uv/). Wire the resulting process into
the same MCP clients:

```json
{
  "tools": {
    "mcpServers": {
      "percival-agentmail-mcp": {
        "command": "uv",
        "args": [
          "run",
          "--directory",
          "/path/to/percival-agentmail-mcp",
          "percival-agentmail-mcp"
        ],
        "env": {
          "AGENTMAIL_API_KEY": "YOUR_API_KEY",
          "AGENTMAIL_INBOX_ID": "your_agent@agentmail.to"
        }
      }
    }
  }
}
```

---

## 🛠️ Development & Testing
This project uses `uv` for dependency management.

```bash
# Sync environment
uv sync --all-extras --dev

# Run locally
uv run percival-agentmail-mcp

# Run tests with coverage
uv run pytest --cov

# Lint
uv run ruff check .
uv run ruff format --check .
```

## 🩺 Troubleshooting

### "Cannot reach AgentMail API at startup"
The server performs a health check on boot. Common causes:
- **Invalid `AGENTMAIL_API_KEY`** (HTTP 401) — verify at https://agentmail.to
- **Network/firewall** blocking `api.agentmail.to`
- **Wrong `AGENTMAIL_INBOX_ID`** (HTTP 404)

### "Validation error — Invalid input fields: inbox_id"
`AGENTMAIL_INBOX_ID` must be a valid email address (Pydantic `EmailStr`).

### "Rate limit exceeded"
The AgentMail API limits bursts. The server retries automatically with
exponential backoff. If persistent 429s occur, reduce concurrent usage
in the LLM client.

### "Internal error occurred. Check server logs"
All exceptions are sanitized; details live in the server stderr output.
Run with `--debug` for verbose logging.

### Error response shape (0.3.4+)
When a mutational tool hits an upstream validation error, the JSON
envelope surfaces the actionable message in three places so the LLM
can react without guesswork:

```json
{
  "status": "error",
  "code": 400,
  "tool": "mail_update_inbox",
  "affected": {"inbox_id": "billkopp@agentmail.to"},
  "message": "Bad request — check the parameters provided. Upstream: Display name contains invalid character(s): ( ) at display_name",
  "upstream_details": [
    "Display name contains invalid character(s): ( ) at display_name"
  ]
}
```

| Field | Meaning |
|---|---|
| `code` | HTTP status from upstream (or a tool-local code like `VALIDATION`). |
| `tool` | The MCP tool that raised (S5 — was added in 0.3.1). |
| `affected` | Dict of IDs relevant to the failure (e.g. `{inbox_id}`, `{draft_id}`). |
| `upstream_details` | Structured list, max 3 messages; each is the human-readable upstream message + the field path it refers to. New in 0.3.4. |
| `message` | Human-friendly wrapper that may also embed `Upstream: …` snippets for legacy string-only endpoints. |

Two intentional safeguards also fire **before** the API is called:

- `mail_update_inbox(display_name)` rejects any input containing `(`
  or `)` locally with an actionable `ValueError`. The AgentMail
  upstream silently rejects those characters with a 400 most agents
  cannot decipher — this short-circuit avoids the round-trip and
  tells the LLM exactly which character to remove.
- `mail_send_draft`, `mail_update_thread`, `mail_update_message`,
  `mail_mark_thread_read` all reject empty-body requests locally
  (Bugs A, R1, R3). Don't worry — the handler will tell you.

## 🔁 Migration from 0.3.x

| Change | Action |
|---|---|
| `mail_send_email` attachment cap reduced from 20 MB to **6 MB binary** (aligned with the upstream `SendAttachment.content` 6 MB total-request limit). | Adjust payloads; use the new `url` field for larger files (see below). |
| `mail_send_email` attachments now accept three new optional fields: **`content_disposition`** (`"inline"` / `"attachment"`), **`content_id`** (sets `Content-ID` for inline `<img src="cid:...">` references), and **`url`** (public URL the AgentMail upstream fetches server-side; **mutually exclusive** with `content_base64`). | Optional / additive. The `url` field unlocks payloads up to ~30 MB and replaces the MinIO-self-hosted workaround for > 6 MB files. |
| New **local-first Docker image** (multi-stage `Dockerfile`, ~262 MB, non-root UID 1000, stdio MCP via `docker run -i` or `docker compose`). | Optional. See the `## 🐳 Docker` section for recipes; no registry push and no `docker/mcp-registry` PR yet. |
| `agentmail` Python SDK bumped to **2.0.4** (was 0.5.8) in 0.3.5. | No action — public contract is on the stable AgentMail API path `https://api.agentmail.to/v0/`. |
| `__version__` derived from package metadata (single source of truth: `pyproject.toml`). | No action. |
| `scratch_test.py` removed. | No action. |

---

## 🛠️ Recent Maintenance (0.4.0)

The 0.4.0 line is an **attachment surface** expansion plus first-class
**Docker packaging**. Tool names, schema and contract semantics are
unchanged — it is a non-breaking release.

1. **Attachment surface (v0.4.0)**
   - `mail_send_email` accepts three new optional fields:
     `content_disposition`, `content_id`, and `url`. They propagate
     to the upstream `SendAttachment` and are validated client-side
     (e.g. `content_disposition` enum, mutual exclusion of
     `content_base64` / `url`, neither-present rejection) so typos
     fail fast before the round-trip.
   - **Cap aligned to 6 MB binary** (was 20 MB) so the client-side
     guard matches the upstream 6 MB total-request limit. Drift
     closed in v0.3.6, shipped with 0.4.0.
   - Wire-level coverage in `tests/test_mcp_transport_contract.py`
     and handler-level coverage in `tests/tools/test_messages.py`
     guard the regression; live integration (opt-in via
     `AGENTMAIL_LIVE_TEST=1`) confirms `.md` and `.pdf` round-trip
     against the real AgentMail API.
2. **Local-first Docker image** — see `## 🐳 Docker` above.
3. **228 → 230 tests passing**, coverage 92.14 % → 92.47 %
   (target ≥ 80 %).

### Recent Maintenance (0.3.x)

The 0.3.x line tightened the contract with the upstream AgentMail API
and stamped out three categories of bugs:

1. **Wire-level contract** (Bugs A–D, 2026-07-21 incident, fixed in
   0.3.1 + 0.3.2): four MCP tools were silently posting empty bodies
   or using labels that the upstream rejects. Fixed at the handler
   layer and end-to-end (`tests/test_mcp_transport_contract.py`). No
   action required.
2. **Connection lifecycle** (0.3.2): the lifespan's `aclose()` now
   closes the real `httpx.AsyncClient` two levels below
   `AsyncAgentMail`, draining connection pools cleanly instead of
   leaking them silently. No action required.
3. **Upstream error surfacing + client-side validation** (0.3.4): the
   server used to echo generic 400 ("Bad request — check the
   parameters provided") without telling the LLM what failed. It now
   parses the upstream Pydantic `ValidationErrorResponse` and
   surfaces per-field messages (`upstream_details` list, max 3)
   alongside the human-friendly wrapper. In addition, the
   `mail_update_inbox` handler rejects `display_name` containing `(`
   or `)` locally with a clear, actionable `ValueError` before
   paying a round-trip — the upstream rejects those characters with
   the cryptic message "Display name contains invalid character(s):
   ( )", which the average LLM cannot derive on its own. The Bug D
   residual from the Nanobot 2026-07-22 10:41 UTC report is now fully
   resolved.

See `CHANGELOG.md` for the full history.

---

## 📚 About the Project

This server is an integral module of the **percival.OS** project. It
provides a secure way for Nanobot to manage external communications
autonomously.

- **Main Repository**: [https://github.com/bill-kopp-ai-dev/percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS)
- **License**: MIT

---
*Developed with ❤️ by the percival.OS Team*
