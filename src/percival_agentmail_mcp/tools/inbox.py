"""Inbox management tools (3 tools)."""

import re

from mcp.server.fastmcp import Context, FastMCP

from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import ServerConfig
from percival_agentmail_mcp.constants import MAX_RESULTS_CAP
from percival_agentmail_mcp.decorators import retryable, with_agentmail
from percival_agentmail_mcp.helpers import cap_limit

# Bug D residual — discovered live 2026-07-22 against the
# agentmail API: it rejects ``display_name`` with the literal
# characters ``(`` or ``)`` ("Display name contains invalid
# character(s): ( )" — HTTP 400 ValidationError). The handler
# short-circuits here so the LLM gets a clear, actionable error
# instead of a generic Bad-Request echo.
_DISPLAY_NAME_FORBIDDEN_CHARS = re.compile(r"[()]")


def _normalize_display_name(value: str) -> str:
    """Trim and compress whitespace on a display_name before sending.

    The AgentMail upstream rejects ``display_name`` containing
    parentheses ("(" or ")") with HTTP 400. We surface this as a
    clear ValueError BEFORE paying a round-trip to the API.
    """
    trimmed = " ".join(value.split())
    if _DISPLAY_NAME_FORBIDDEN_CHARS.search(trimmed):
        raise ValueError(
            "display_name may not contain '(' or ')'. The AgentMail upstream "
            "rejects these characters with HTTP 400 'Display name contains "
            "invalid character(s): ( )'. Remove the parenthesized suffix — "
            "e.g. 'Nano v2 - MCP Test' instead of 'Nano v2 - MCP Test "
            "(v0.8.0)'."
        )
    return trimmed


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

        kwargs: dict = {"inbox_id": config.inbox_id}
        if norm_name is not None:
            kwargs["display_name"] = norm_name
        if norm_meta is not None:
            kwargs["metadata"] = norm_meta

        # The AgentMail SDK ships wheels with and without the ``metadata``
        # kwarg on ``inboxes.update``. We can't statically tell which build
        # is installed, so the call itself is the source of truth: catch
        # the ``TypeError: got an unexpected keyword argument 'metadata'``
        # surfaced by older 0.5.x wheels and translate it into a clear,
        # actionable ValueError the LLM can act on (upgrade agentmail or
        # call update_inbox with display_name= instead).
        try:
            inbox = await client.client.inboxes.update(**kwargs)
        except TypeError as e:
            msg = str(e)
            if "metadata" in msg and "unexpected keyword argument" in msg:
                # Translate the TypeError into an actionable ValueError
                # WITHOUT leaking the raw SDK error string — that would
                # confuse the LLM into thinking the bug is in *its*
                # input. The chained __cause__ preserves the diagnostic
                # in the traceback for server-side operators.
                raise ValueError(
                    "update_inbox was called with metadata, but the "
                    "installed agentmail SDK does not support the "
                    "``metadata`` kwarg on ``inboxes.update``. "
                    "Upgrade agentmail to a wheel that ships the kwarg, "
                    "or call update_inbox with display_name=... instead."
                ) from None
            raise
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
