"""Tests for the metadata-wrapped-call resilience in mail_update_inbox.

Older 0.5.x wheels of the AgentMail SDK do not accept the ``metadata``
kwarg on ``inboxes.update`` and raise ``TypeError: got an unexpected
keyword argument 'metadata'``. We catch that TypeError inside the
handler and translate it into an actionable ValueError so the LLM
sees a useful diagnosis instead of a traceback.

Both the success path (respx-on-real-SDK) and the "TypeError at
runtime" path are exercised here.
"""

import json
from unittest.mock import MagicMock

import pytest
import respx
from mcp.server.fastmcp import FastMCP

from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import ServerConfig
from percival_agentmail_mcp.lifespan import LifespanContext
from percival_agentmail_mcp.tools import register_tools
from tests.conftest import _FakeMCPContext


def _make_fake_lifespan_context() -> LifespanContext:
    """Build a LifespanContext with a real wrapper (real underlying SDK)."""
    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    config = ServerConfig(api_key="am_test_12345678", inbox_id="agent@agentmail.to")
    return LifespanContext(client=wrapper, config=config)


@pytest.mark.asyncio
async def test_metadata_passthrough_when_sdk_supports_it() -> None:
    """When the installed SDK supports metadata, the handler forwards it.

    Verified by hitting the AgentMail API via respx with the real SDK.
    """
    wrapper = _make_fake_lifespan_context()
    mock_ctx = _FakeMCPContext(wrapper)

    with respx.mock(base_url="https://api.agentmail.to", assert_all_called=False) as rmock:
        route = rmock.patch(url__regex=r"/v0/inboxes/[^/]+$").respond(200, json={"inbox_id": "agent@agentmail.to"})

        server = FastMCP("test-new-sdk")
        register_tools(server)
        tool = server._tool_manager._tools["mail_update_inbox"].fn

        result = await tool(mock_ctx, metadata={"team": "ops"})

    parsed = json.loads(result)
    if route.called:
        # respx intercepted the PATCH — body must match ``metadata``.
        body = json.loads(route.calls[0].request.content.decode())
        assert body == {"metadata": {"team": "ops"}}
    else:
        # The installed SDK doesn't accept ``metadata``. The handler
        # must have translated the runtime TypeError into a clear
        # actionable error envelope.
        assert parsed.get("status") == "error"
        assert "metadata" in parsed["message"].lower()
        assert "agentmail" in parsed["message"].lower()


@pytest.mark.asyncio
async def test_metadata_typeerror_at_runtime_is_translated() -> None:
    """The handler must catch a runtime TypeError from the SDK and
    surface a clear actionable message.
    """
    wrapper = _make_fake_lifespan_context()
    # Replace the underlying SDK chain with a mock that simulates the
    # exact observed runtime failure.
    wrapper.client.client = MagicMock()  # type: ignore[attr-defined]

    async def boom(*args, **kwargs):
        raise TypeError("AsyncInboxesClient.update() got an unexpected keyword argument 'metadata'")

    wrapper.client.client.inboxes.update = boom  # type: ignore[attr-defined]

    mock_ctx = _FakeMCPContext(wrapper)

    server = FastMCP("test-runtime-typeerror")
    register_tools(server)
    tool = server._tool_manager._tools["mail_update_inbox"].fn

    result = await tool(mock_ctx, metadata={"team": "ops"})
    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert "agentmail" in parsed["message"].lower()
    assert "metadata" in parsed["message"].lower()
    # Must NOT leak the raw TypeError signature as the message.
    assert "unexpected keyword argument" not in parsed["message"]


@pytest.mark.asyncio
async def test_metadata_runtime_fail_includes_tool_name() -> None:
    """S5 — the error envelope carries the tool name ('update_inbox'),
    so the LLM can react appropriately.
    """
    wrapper = _make_fake_lifespan_context()
    wrapper.client.client = MagicMock()  # type: ignore[attr-defined]

    async def boom(*args, **kwargs):
        raise TypeError("AsyncInboxesClient.update() got an unexpected keyword argument 'metadata'")

    wrapper.client.client.inboxes.update = boom  # type: ignore[attr-defined]
    ctx = _FakeMCPContext(wrapper)

    server = FastMCP("test-tool-name")
    register_tools(server)
    tool = server._tool_manager._tools["mail_update_inbox"].fn

    result = await tool(ctx, metadata={"k": "v"})
    parsed = json.loads(result)
    assert parsed.get("tool") == "update_inbox"
