"""Tests for the SDK support detection guard in mail_update_inbox.

These simulate the case where the installed ``agentmail`` SDK is an
older wheel that does NOT accept ``metadata`` on ``inboxes.update``.
The handler must surface a clear, actionable error instead of letting
the unexpected TypeError reach the LLM.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
import respx


def _make_fake_lifespan_context():
    """Build a LifespanContext with a wrapper whose SDK client is real."""
    from percival_agentmail_mcp.client import AgentMailClientWrapper
    from percival_agentmail_mcp.config import ServerConfig
    from percival_agentmail_mcp.lifespan import LifespanContext

    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    config = ServerConfig(api_key="am_test_12345678", inbox_id="agent@agentmail.to")
    ctx = LifespanContext(client=wrapper, config=config)
    return ctx


class _FakeMCPContext:
    def __init__(self, lifespan_ctx):
        self._lifespan = lifespan_ctx

    @property
    def request_context(self):
        class R:
            lifespan_context = self._lifespan

        return R()


@pytest.mark.asyncio
async def test_metadata_rejected_clear_error_when_sdk_lacks_support(monkeypatch) -> None:
    """When the installed SDK lacks metadata, the handler must not raise TypeError."""
    from mcp.server.fastmcp import FastMCP

    from percival_agentmail_mcp.tools import register_tools
    from tests.conftest import _FakeMCPContext  # type: ignore

    monkeypatch.setattr(
        "percival_agentmail_mcp.tools.inbox._sdk_supports_metadata",
        lambda: False,
    )

    wrapper = _make_fake_lifespan_context()
    # The SDK client must NOT be invoked; replace the underlying SDK
    # client attribute with a MagicMock since LifespanContext is frozen
    # (we cannot reassign ``wrapper = ...`` either, the same wrapper
    # object the tool already holds via @with_agentmail).
    wrapper.client.client = MagicMock()  # type: ignore[attr-defined]
    wrapper.client.client.inboxes.update = AsyncMock()  # type: ignore[attr-defined]

    mock_ctx = _FakeMCPContext(wrapper)

    server = FastMCP("test-old-sdk")
    register_tools(server)

    tool = server._tool_manager._tools["mail_update_inbox"].fn

    result = await tool(mock_ctx, metadata={"team": "ops"})
    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert "agentmail" in parsed["message"].lower()
    assert "metadata" in parsed["message"].lower()
    # And the SDK must NOT have been called with metadata.
    wrapper.client.client.inboxes.update.assert_not_called()  # type: ignore[attr-defined]  # noqa: E501


@pytest.mark.asyncio
async def test_metadata_passthrough_when_sdk_supports_it(monkeypatch) -> None:
    """When the installed SDK does support metadata, the handler forwards it."""
    from mcp.server.fastmcp import FastMCP

    from percival_agentmail_mcp.tools import register_tools
    from percival_agentmail_mcp.tools.inbox import _sdk_supports_metadata
    from tests.conftest import _FakeMCPContext  # type: ignore

    monkeypatch.setattr(
        "percival_agentmail_mcp.tools.inbox._sdk_supports_metadata",
        lambda: True,
    )

    wrapper = _make_fake_lifespan_context()
    mock_ctx = _FakeMCPContext(wrapper)

    with respx.mock(base_url="https://api.agentmail.to", assert_all_called=False) as rmock:
        route = rmock.patch(url__regex=r"/v0/inboxes/[^/]+$").respond(200, json={"inbox_id": "agent@agentmail.to"})

        server = FastMCP("test-new-sdk")
        register_tools(server)

        tool = server._tool_manager._tools["mail_update_inbox"].fn

        result = await tool(mock_ctx, metadata={"team": "ops"})

    parsed = json.loads(result)
    assert "inbox_id" in parsed
    assert route.called
    body = json.loads(route.calls[0].request.content.decode())
    assert body == {"metadata": {"team": "ops"}}


@pytest.mark.asyncio
async def test_metadata_typeerror_at_runtime_is_translated(monkeypatch) -> None:
    """Even when static inspection says 'supported', the SDK runtime call
    may still raise ``TypeError: unexpected keyword 'metadata'`` (this
    is exactly what happened in the 0.5.0 CI run on 2026-07-22 — local
    static probes were lying because the SDK was stubbed for tests).
    The handler must catch that TypeError and translate it into the
    same actionable error path.
    """
    from mcp.server.fastmcp import FastMCP

    from percival_agentmail_mcp.tools import register_tools
    from tests.conftest import _FakeMCPContext  # type: ignore

    # Pretend the static probe said 'supported', so we skip the early guard.
    monkeypatch.setattr(
        "percival_agentmail_mcp.tools.inbox._sdk_supports_metadata",
        lambda: True,
    )

    wrapper = _make_fake_lifespan_context()
    # Replace the underlying SDK chain with mocks that simulate the
    # exact observed runtime failure: TypeError with the expected string.
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
    # The translated ValueError must surface what to do next.
    assert "agentmail" in parsed["message"].lower()
    assert "metadata" in parsed["message"].lower()
