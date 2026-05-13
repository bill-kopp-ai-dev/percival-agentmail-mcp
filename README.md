# 🤖 Percival AgentMail - percival.OS MCP

**Version 0.0.2**

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
The server exposes 21 tools optimized for LLM comprehension, divided into:

- **Inbox:** `mail_get_inbox_info`, `mail_update_inbox`, `mail_list_inbox_events`
- **Messages:** `mail_send_email`, `mail_list_messages`, `mail_read_message`, `mail_reply_to_message`, `mail_reply_all_message`, `mail_forward_message`, `mail_update_message`, `mail_delete_message`
- **Threads:** `mail_list_threads`, `mail_get_thread`, `mail_update_thread`, `mail_delete_thread`
- **Drafts:** `mail_create_draft`, `mail_list_drafts`, `mail_get_draft`, `mail_update_draft`, `mail_send_draft`
- **Utility:** `mail_get_status`

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
uv sync

# Run locally
uv run percival-agentmail-mcp
```

---

## 📚 About the Project
This server is an integral module of the **percival.OS** project. It provides a secure way for Nanobot to manage external communications autonomously.

- **Main Repository**: [https://github.com/bill-kopp-ai-dev/percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS)
- **License**: MIT

---
*Developed with ❤️ by the percival.OS Team*
