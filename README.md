# Percival AgentMail MCP Server

A Model Context Protocol (MCP) server that provides AI agents with their **own autonomous email inbox** using the [AgentMail](https://agentmail.to) API. 

While developed as a core component of the [percival.OS ecosystem](https://github.com/bill-kopp-ai-dev/percival.OS) to power the **Nanobot** agent, **this server is fully standard-compliant and can be utilized by ANY AI agent that supports the MCP protocol** (e.g., Claude Desktop, Cursor, or custom architectures).

## What is AgentMail?

AgentMail is an API-first email provider specifically designed for AI agents. Instead of attempting to connect an AI to a human's existing email account (which is fraught with security risks and authentication hurdles like OAuth), AgentMail provisions dedicated, programmable email addresses (e.g., `agent@agentmail.to`). 

This project provides a complete, robust, and secure implementation of the official AgentMail Python SDK, exposing its capabilities as standard MCP tools so your agent can programmatically read, search, draft, and send emails completely independently.

## 🛡️ Philosophy & Security

> [!IMPORTANT]
> **Philosophy: Autonomous but Secure**
> 
> Unlike our sister project `percival-imap-mcp` (which gives the agent controlled, restricted access to the *human user's* email account like Gmail/Outlook), this server operates on the premise that the email address **belongs to the agent itself**. 
> 
> Because the agent owns the inbox, it has **free and unrestricted operational access** to manage it (no protected senders, no blocked operations). However, we implement **strict security guardrails against external threats**:
> 
> 1. **Prompt Injection Fencing**: Incoming emails are untrusted external data. The server automatically fences email bodies (using markers like `--- EMAIL BODY START ---`) before passing them to the LLM, preventing malicious actors from hijacking the agent via emailed instructions.
> 2. **Error Sanitization**: API errors are intercepted and sanitized. Raw stack traces and internal API details are logged internally but never exposed to the LLM, preventing information leakage.
> 3. **Resource Exhaustion Caps**: All listing operations enforce a hard cap (`MAX_RESULTS_CAP = 50`), overriding the agent's requests to prevent token exhaustion and API rate limiting.
> 4. **Automatic Context Injection**: The agent operates from a fixed, pre-configured inbox. It does not need to know or manage its own UUID, reducing context window usage and preventing accidental manipulation of other inboxes.

## Features

- **Full Inbox Management**: Read, send, reply, forward, delete.
- **Thread Context**: Intelligent handling of email threads.
- **Drafts & Scheduling**: Ability to create drafts and schedule emails for future delivery.
- **Universal Compatibility**: Works with any MCP client via `stdio`.

## Installation

This project uses `uv` for dependency management.

1. Ensure you have `uv` installed:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Clone the repository and install dependencies:
   ```bash
   git clone https://github.com/bill-kopp-ai-dev/percival-agentmail-mcp.git
   cd percival-agentmail-mcp
   uv sync
   ```

## Configuration

The server requires environment variables to connect to your AgentMail account.

| Variable | Required | Default | Description |
|---|---|---|---|
| `AGENTMAIL_API_KEY` | Yes | - | Your AgentMail API key from the console. |
| `AGENTMAIL_INBOX_ID` | Yes | - | The identifier of the agent's inbox (e.g., `your_agent@agentmail.to`). |
| `AGENTMAIL_MAX_RESULTS` | No | `25` | Default limit for listing operations (max 50). |
| `AGENTMAIL_TIMEOUT` | No | `30` | Request timeout in seconds. |

### Example `.env`

```env
AGENTMAIL_API_KEY=am_live_xxxxxxxxxxxxxxxxxxxxxxxx
AGENTMAIL_INBOX_ID=your_agent@agentmail.to
```

## Integrating with Nanobot (or other MCP Clients)

To inject this MCP server into your runtime, add the following block to your configuration:

```json
{
  "mcpServers": {
    "percival_agentmail": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/percival-agentmail-mcp",
        "run",
        "percival-agentmail-mcp"
      ],
      "env": {
        "AGENTMAIL_API_KEY": "am_live_xxxxxxxxxxxxxxxxxxxxxxxx",
        "AGENTMAIL_INBOX_ID": "your_agent@agentmail.to"
      }
    }
  }
}
```

## Available Tools (Phase 1)

This server provides 21 tools covering all essential email operations, with highly descriptive docstrings optimized for LLM comprehension:

**Inbox:** `get_inbox_info`, `update_inbox`, `list_inbox_events`
**Messages:** `send_email`, `list_messages`, `read_message`, `reply_to_message`, `reply_all_message`, `forward_message`, `update_message`, `delete_message`
**Threads:** `list_threads`, `get_thread`, `update_thread`, `delete_thread`
**Drafts:** `create_draft`, `list_drafts`, `get_draft`, `update_draft`, `send_draft`
**Utility:** `server_status`

## License

This project is licensed under the MIT License.
