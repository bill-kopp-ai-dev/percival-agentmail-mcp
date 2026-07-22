"""Inbox management tools (3 tools)."""

import inspect

from mcp.server.fastmcp import Context, FastMCP

from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import ServerConfig
from percival_agentmail_mcp.constants import MAX_RESULTS_CAP
from percival_agentmail_mcp.decorators import retryable, with_agentmail
from percival_agentmail_mcp.helpers import cap_limit


def _normalize_display_name(value: str) -> str:
    """Trim and compress whitespace on a display_name before sending."""
    return " ".join(value.split())


def _sdk_supports_metadata() -> bool:
    """Return True if the installed AgentMail SDK accepts ``metadata`` on update().

    Different 0.5.x wheels of the AgentMail SDK have shipped with and
    without the ``metadata`` kwarg on ``inboxes.update``. The CI
    workflow on 2026-07-22 pinned ``agentmail==0.5.0``, which lacks the
    parameter — `update(metadata=...)` raised ``TypeError: got an
    unexpected keyword argument 'metadata'``. We probe the live SDK
    once, lazily, and skip passing metadata when it isn't supported.
    """
    try:
        from agentmail import AsyncAgentMail

        params = inspect.signature(AsyncAgentMail(api_key="probe").inboxes.update).parameters
    except Exception:  # pragma: no cover — defensive
        return False
    return "metadata" in params


def register(mcp: FastMCP) -> None:
    @mcp.tool("mail_get_inbox_info")
    @with_agentmail
    async def get_inbox_info(
        ctx: Context,
        client: AgentMailClientWrapper,
        config: ServerConfig,
    ) -> str:
        """Retrieves the current configuration and statistical details of the agent's primary email inbox."""
        inbox = await client.client.inboxes.get(inbox_id=config.inbox_id)
        return client.format_response(inbox)

    @mcp.tool("mail_update_inbox")
    @with_agentmail
    async def update_inbox(
        ctx: Context,
        client: AgentMailClientWrapper,
        config: ServerConfig,
        display_name: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Modifies the agent's primary inbox settings.

        At least one of ``display_name`` or ``metadata`` MUST be provided
        — the AgentMail upstream rejects empty-body updates with HTTP
        400 (Bug D in the 2026-07-21 incident report). The
        ``display_name`` is trimmed and internal whitespace is compressed
        before being sent.

        The ``metadata`` parameter requires a 0.5.x SDK wheel that
        actually exposes the kwarg. Older 0.5.x wheels (such as the
        0.5.0 pinned in CI on 2026-07-22) reject it with ``TypeError``;
        when that's the case the handler surfaces a clear error and
        instructs the caller to upgrade ``agentmail``.
        """
        norm_name = _normalize_display_name(display_name) if display_name else None
        norm_meta = metadata if metadata else None

        if not norm_name and not norm_meta:
            raise ValueError(
                "update_inbox requires at least one of `display_name` or "
                "`metadata` to be provided. "
                f"Got display_name={display_name!r}, metadata={metadata!r}."
            )

        if norm_meta is not None and not _sdk_supports_metadata():
            raise ValueError(
                "update_inbox was called with metadata, but the installed "
                "agentmail SDK does not support updating inbox metadata "
                "(observed against agentmail==0.5.0). Upgrade agentmail to "
                "a wheel that ships the `metadata` kwarg on `inboxes.update`, "
                "or call update_inbox with display_name=... instead."
            )

        kwargs: dict = {"inbox_id": config.inbox_id}
        if norm_name is not None:
            kwargs["display_name"] = norm_name
        if norm_meta is not None:
            kwargs["metadata"] = norm_meta

        inbox = await client.client.inboxes.update(**kwargs)
        return client.format_response(inbox)

    @mcp.tool("mail_list_inbox_events")
    @with_agentmail
    @retryable
    async def list_inbox_events(
        ctx: Context,
        client: AgentMailClientWrapper,
        config: ServerConfig,
        limit: int | None = None,
    ) -> str:
        """Fetches recent event logs for the agent's inbox, useful for tracking automated actions like message delivery or receipt."""
        events = await client.client.inboxes.events.list(
            inbox_id=config.inbox_id,
            limit=cap_limit(limit, config.max_results, MAX_RESULTS_CAP),
        )
        return client.format_response(events)
