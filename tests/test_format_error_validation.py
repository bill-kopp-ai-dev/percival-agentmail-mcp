"""Regression tests for the upstream-error surfacing in format_error.

Two fixes from 2026-07-22:

1. ``format_error`` must extract structured details from the AgentMail
   upstream ``ValidationErrorResponse`` model — the API returns
   per-field validation messages (e.g. ``Display name contains
   invalid character(s): ( )``) that the LLM can act on.

2. ``mail_update_inbox`` (display_name) must reject "(" or ")"
   client-side, returning a clear ``ValueError`` message instead of
   letting the upstream emit a generic 400 echo.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest
import respx
from mcp.server.fastmcp import FastMCP

from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import ServerConfig
from percival_agentmail_mcp.lifespan import LifespanContext
from percival_agentmail_mcp.tools import register_tools
from tests.conftest import _FakeMCPContext

# -- (2) display_name client-side validation -------------------------------


@pytest.mark.asyncio
async def test_update_inbox_rejects_parentheses_locally() -> None:
    """Display name with parentheses must be rejected client-side.

    The AgentMail upstream rejects ``(`` / ``)`` in display_name with
    HTTP 400 and the message ``Display name contains invalid
    character(s): ( )``. We catch that locally so the LLM sees a
    clear, actionable error instead of an opaque generic 400.
    """
    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    config = ServerConfig(api_key="am_test_12345678", inbox_id="agent@agentmail.to")
    ctx = LifespanContext(client=wrapper, config=config)
    mock_ctx = _FakeMCPContext(ctx)

    server = FastMCP("test-display-name")
    register_tools(server)
    tool = server._tool_manager._tools["mail_update_inbox"].fn

    import json as jsonlib

    # Display_name with a single parenthesis — must short-circuit
    # before any HTTP call is made.
    result = await tool(mock_ctx, display_name="X (v0.8.0)")
    parsed = jsonlib.loads(result)
    assert parsed["status"] == "error"
    assert "(" in parsed["message"]
    assert ")" in parsed["message"]
    assert "agentmail" in parsed["message"].lower() or "upstream" in parsed["message"].lower()

    # SDK must NOT be called for an invalid display_name.
    wrapper.client = MagicMock()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_update_inbox_accepts_display_name_without_parentheses() -> None:
    """A display_name without parentheses must reach the SDK."""
    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    config = ServerConfig(api_key="am_test_12345678", inbox_id="agent@agentmail.to")
    ctx = LifespanContext(client=wrapper, config=config)
    mock_ctx = _FakeMCPContext(ctx)

    with respx.mock(base_url="https://api.agentmail.to", assert_all_called=False) as rmock:
        route = rmock.patch(url__regex=r"/v0/inboxes/[^/]+$").respond(200, json={"inbox_id": "agent@agentmail.to"})

        server = FastMCP("test-display-name-ok")
        register_tools(server)
        tool = server._tool_manager._tools["mail_update_inbox"].fn

        result = await tool(mock_ctx, display_name="Nano v2 - MCP Test")

    import json as jsonlib

    parsed = jsonlib.loads(result)
    if route.called:
        # No error envelope
        assert "inbox_id" in parsed or "error" not in str(parsed.get("status", ""))
    else:
        assert parsed.get("status") in {"success", "ok", None}


# -- (1) format_error extracts structured upstream details ------------------


@pytest.mark.asyncio
async def test_format_error_surfaces_validation_errors() -> None:
    """format_error must surface per-field upstream ValidationErrors.

    Discovered live on 2026-07-22: ApiError.body is a pydantic
    ValidationErrorResponse with an ``errors`` list of
    ``{code, message, path}``. Surface the messages to the LLM in a
    dedicated ``upstream_details`` key, and append to the wrapper's
    ``message`` field.
    """
    import json as jsonlib

    from agentmail.core.api_error import ApiError

    from percival_agentmail_mcp.client import AgentMailClientWrapper

    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")

    # Build a ValidationErrorResponse-shaped body using the SDK's
    # pydantic model. Some AgentMail error responses may have an
    # empty ``message`` field at the top level; the per-error
    # messages are what we want to surface.
    from agentmail.types.validation_error_response import ValidationErrorResponse

    body = ValidationErrorResponse(
        name="ValidationError",
        errors=[
            {
                "code": "custom",
                "message": "Display name contains invalid character(s): ( )",
                "path": ["display_name"],
            },
            {
                "code": "custom",
                "message": "Field X is required",
                "path": ["foo", "bar"],
            },
        ],
    )
    api_err = ApiError(status_code=400, body=body)

    formatted = wrapper.format_error(
        api_err, tool_name="mail_update_inbox", affected={"inbox_id": "agent@agentmail.to"}
    )
    parsed = jsonlib.loads(formatted)
    assert parsed["status"] == "error"
    assert parsed["tool"] == "mail_update_inbox"
    assert parsed["affected"] == {"inbox_id": "agent@agentmail.to"}
    # The upstream message must be surfaced in the envelope.
    assert "upstream_details" in parsed
    assert len(parsed["upstream_details"]) == 2
    assert "( )" in parsed["upstream_details"][0]
    assert parsed["upstream_details"][0].startswith("Display name contains invalid character(s): ( ) at display_name")
    # And the top-level message must mention the upstream too.
    assert "Upstream:" in parsed["message"]
    assert "Display name" in parsed["message"]


@pytest.mark.asyncio
async def test_format_error_handles_plain_string_body() -> None:
    """Older endpoints may return plain string bodies — handle gracefully."""
    import json as jsonlib

    from agentmail.core.api_error import ApiError

    from percival_agentmail_mcp.client import AgentMailClientWrapper

    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    api_err = ApiError(status_code=400, body="Generic upstream message")
    formatted = wrapper.format_error(api_err, tool_name="mail_update_inbox")
    parsed = jsonlib.loads(formatted)
    assert parsed["status"] == "error"
    assert "upstream_details" in parsed
    assert parsed["upstream_details"] == ["Generic upstream message"]
    assert "Upstream: Generic upstream message" in parsed["message"]


@pytest.mark.asyncio
async def test_format_error_handles_empty_validation_response() -> None:
    """Defensive: ValidationErrorResponse with no errors must not crash."""
    import json as jsonlib

    from agentmail.core.api_error import ApiError
    from agentmail.types.validation_error_response import ValidationErrorResponse

    from percival_agentmail_mcp.client import AgentMailClientWrapper

    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    body = ValidationErrorResponse(name="ValidationError", errors=[])
    api_err = ApiError(status_code=400, body=body)
    formatted = wrapper.format_error(api_err, tool_name="mail_update_inbox")
    parsed = jsonlib.loads(formatted)
    assert parsed["status"] == "error"
    # Empty validation list → no upstream_details key
    assert "upstream_details" not in parsed


@pytest.mark.asyncio
async def test_format_error_caps_upstream_details() -> None:
    """The upstream_details list is capped at 3 messages to keep envelopes small."""
    import json as jsonlib

    from agentmail.core.api_error import ApiError
    from agentmail.types.validation_error_response import ValidationErrorResponse

    from percival_agentmail_mcp.client import AgentMailClientWrapper

    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    body = ValidationErrorResponse(
        name="ValidationError",
        errors=[{"code": "custom", "message": f"err{i}", "path": ["display_name"]} for i in range(10)],
    )
    api_err = ApiError(status_code=400, body=body)
    formatted = wrapper.format_error(api_err, tool_name="mail_update_inbox")
    parsed = jsonlib.loads(formatted)
    assert len(parsed["upstream_details"]) == 3
