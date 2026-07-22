# 🤖 Percival AgentMail - percival.OS MCP

**Version 0.3.4**

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

## ⚙️ Configuration in percival.OS (Nanobot)
Add the following configuration to your `~/.nanobot/config.json`:

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

## 🔁 Migration from 0.0.x

| Change | Action |
|---|---|
| `AGENTMAIL_INBOX_ID` must be a valid email | Fix `.env` |
| `__version__` now derived from package metadata | No action |
| `scratch_test.py` removed | No action |
| New `mail_get_attachment` and `mail_mark_thread_read` available | No action (additive) |
| `mail_send_email` accepts `attachments` (max 20 MB base64) | Optional |

---

## 🛠️ Recent Maintenance (0.3.x)

The 0.3.x line tightens the contract with the upstream AgentMail API
and stamps out three categories of bugs:

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
   alongside the human-readable wrapper. In addition, the
   `mail_update_inbox` handler rejects `display_name` containing `(`
   or `)` locally with a clear, actionable `ValueError` before
   paying a round-trip — the upstream rejects those characters with
   the cryptic message "Display name contains invalid character(s):
   ( )", which the average LLM cannot derive on its own. The Bug D
   residual from the Nanobot 2026-07-22 10:41 UTC report is now fully
   resolved.

See `CHANGELOG.md` for the full history.

---

## �📚 About the Project
This server is an integral module of the **percival.OS** project. It provides a secure way for Nanobot to manage external communications autonomously.

- **Main Repository**: [https://github.com/bill-kopp-ai-dev/percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS)
- **License**: MIT

---
*Developed with ❤️ by the percival.OS Team*
