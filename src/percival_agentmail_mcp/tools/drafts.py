"""Draft tools (5 tools)."""

from mcp.server.fastmcp import Context, FastMCP

from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import ServerConfig
from percival_agentmail_mcp.constants import MAX_RESULTS_CAP
from percival_agentmail_mcp.decorators import retryable, with_agentmail
from percival_agentmail_mcp.helpers import build_kwargs, cap_limit, normalize_list

# Sentinel labels (prefixed with "mcp-") that the upstream AgentMail
# labels endpoints accept. System labels ("sent", "received", "unread",
# "draft", "read") are reserved and any attempt to add/remove them via
# the SDK is rejected with HTTP 400 "Cannot use system label".
_SENT_VIA_MCP_LABEL = "mcp-sent"


def register(mcp: FastMCP) -> None:
    # No @retryable on create_draft/send_draft: retrying after a
    # timeout/5xx could create a duplicate draft or dispatch the same
    # draft twice — the SDK has no idempotency key to make that safe.
    @mcp.tool("mail_create_draft")
    @with_agentmail
    async def create_draft(
        ctx: Context,
        client: AgentMailClientWrapper,
        config: ServerConfig,
        to: list[str] | str,
        subject: str,
        text: str,
        html: str | None = None,
        send_at: str | None = None,
    ) -> str:
        """Saves a new email draft without sending it.
        You can optionally schedule the email to be sent automatically at a future date by providing a 'send_at' timestamp in ISO 8601 format.
        """
        kwargs = build_kwargs(
            {
                "inbox_id": config.inbox_id,
                "to": normalize_list(to),
                "subject": subject,
                "text": text,
            },
            {"html": html, "send_at": send_at},
        )
        return client.format_response(await client.client.inboxes.drafts.create(**kwargs))

    @mcp.tool("mail_list_drafts")
    @with_agentmail
    @retryable
    async def list_drafts(
        ctx: Context,
        client: AgentMailClientWrapper,
        config: ServerConfig,
        limit: int | None = None,
        page_token: str | None = None,
    ) -> str:
        """Retrieves a paginated list of unsent email drafts currently stored in the agent's inbox."""
        kwargs = build_kwargs(
            {
                "inbox_id": config.inbox_id,
                "limit": cap_limit(limit, config.max_results, MAX_RESULTS_CAP),
            },
            {"page_token": page_token},
        )
        return client.format_response(await client.client.inboxes.drafts.list(**kwargs))

    @mcp.tool("mail_get_draft")
    @with_agentmail
    @retryable
    async def get_draft(
        ctx: Context,
        client: AgentMailClientWrapper,
        config: ServerConfig,
        draft_id: str,
    ) -> str:
        """Fetches the complete content and configuration of a specific, unsent email draft."""
        result = await client.client.inboxes.drafts.get(
            inbox_id=config.inbox_id,
            draft_id=draft_id,
        )
        return client.format_response(result)

    @mcp.tool("mail_update_draft")
    @with_agentmail
    @retryable
    async def update_draft(
        ctx: Context,
        client: AgentMailClientWrapper,
        config: ServerConfig,
        draft_id: str,
        to: list[str] | str | None = None,
        subject: str | None = None,
        text: str | None = None,
        html: str | None = None,
        send_at: str | None = None,
        add_labels: list[str] | str | None = None,
        remove_labels: list[str] | str | None = None,
    ) -> str:
        """Modifies the contents, recipients, or scheduling parameters of an existing email draft.

        At least one of the optional fields MUST be provided; the
        AgentMail upstream rejects empty-body PATCH with HTTP 400
        (residual bug found live on 2026-07-22).
        """
        norm_to = normalize_list(to)
        norm_add = normalize_list(add_labels)
        norm_rem = normalize_list(remove_labels)
        if all(v is None for v in (norm_to, subject, text, html, send_at, norm_add, norm_rem)):
            raise ValueError(
                "update_draft requires at least one field to update. "
                "Got all of (to, subject, text, html, send_at, "
                "add_labels, remove_labels) as None/empty."
            )
        kwargs = build_kwargs(
            {"inbox_id": config.inbox_id, "draft_id": draft_id},
            {
                "to": norm_to,
                "subject": subject,
                "text": text,
                "html": html,
                "send_at": send_at,
                "add_labels": norm_add,
                "remove_labels": norm_rem,
            },
        )
        return client.format_response(await client.client.inboxes.drafts.update(**kwargs))

    @mcp.tool("mail_send_draft")
    @with_agentmail
    async def send_draft(
        ctx: Context,
        client: AgentMailClientWrapper,
        config: ServerConfig,
        draft_id: str,
        add_labels: list[str] | str | None = None,
        remove_labels: list[str] | str | None = None,
    ) -> str:
        """Immediately dispatches a previously saved email draft.

        The AgentMail upstream requires at least one of ``add_labels`` /
        ``remove_labels`` AND rejects system labels ("sent", "received",
        "unread", "draft", "read") — using one returns HTTP 400
        "Cannot use system label". To work around both constraints we
        always pass a sentinel custom label ``mcp-sent`` unless the
        caller overrides via ``add_labels``/``remove_labels``. The label
        appears on the resulting message thread and is safe to filter
        later.
        """
        norm_add = normalize_list(add_labels)
        norm_rem = normalize_list(remove_labels)
        # Always include our custom sentinel if neither list was provided,
        # so the call always sends a non-empty labels payload.
        if not norm_add and not norm_rem:
            norm_add = [_SENT_VIA_MCP_LABEL]
        kwargs = build_kwargs(
            {"inbox_id": config.inbox_id, "draft_id": draft_id},
            {"add_labels": norm_add, "remove_labels": norm_rem},
        )
        return client.format_response(await client.client.inboxes.drafts.send(**kwargs))
