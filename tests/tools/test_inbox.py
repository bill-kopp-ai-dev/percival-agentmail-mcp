"""Tests for inbox tools (3 tools)."""

import json
from unittest.mock import AsyncMock

import pytest
from agentmail.core.api_error import ApiError

from tests.conftest import _FakeMCPContext


@pytest.fixture
def mcp_server():
    from mcp.server.fastmcp import FastMCP

    from percival_agentmail_mcp.tools import register_tools

    server = FastMCP("percival-agentmail-test")
    register_tools(server)
    return server


@pytest.fixture
def get_tool(mcp_server):
    """Return a callable for a specific get_tool by name."""

    def _factory(name: str):
        return mcp_server._tool_manager._tools[name].fn

    return _factory


@pytest.fixture
def fake_ctx(mock_context):
    return _FakeMCPContext(mock_context)


# --- mail_get_inbox_info ---


@pytest.mark.asyncio
async def test_get_inbox_info_returns_inbox_data(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    expected = {"id": mock_config.inbox_id, "display_name": "agent"}
    mock_wrapper.client.inboxes.get = AsyncMock(return_value=expected)

    result = await get_tool("mail_get_inbox_info")(fake_ctx)

    parsed = json.loads(result)
    assert parsed["id"] == mock_config.inbox_id
    mock_wrapper.client.inboxes.get.assert_awaited_once_with(inbox_id=mock_config.inbox_id)


@pytest.mark.asyncio
async def test_get_inbox_info_returns_error_on_exception(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.get = AsyncMock(side_effect=ApiError(status_code=404, body="missing"))
    result = await get_tool("mail_get_inbox_info")(fake_ctx)
    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert parsed["code"] == 404


# --- mail_update_inbox ---


@pytest.mark.asyncio
async def test_update_inbox_with_display_name(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.update = AsyncMock(return_value={"id": mock_config.inbox_id})
    result = await get_tool("mail_update_inbox")(fake_ctx, display_name="Agent Bot")
    mock_wrapper.client.inboxes.update.assert_awaited_once_with(inbox_id=mock_config.inbox_id, display_name="Agent Bot")
    assert "id" in result


@pytest.mark.asyncio
async def test_update_inbox_without_display_name(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.update = AsyncMock(return_value={"id": mock_config.inbox_id})
    await get_tool("mail_update_inbox")(fake_ctx)
    mock_wrapper.client.inboxes.update.assert_awaited_once_with(inbox_id=mock_config.inbox_id, display_name=None)


# --- mail_list_inbox_events ---


@pytest.mark.asyncio
async def test_list_inbox_events_default_limit(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.events.list = AsyncMock(return_value={"events": []})
    await get_tool("mail_list_inbox_events")(fake_ctx)
    mock_wrapper.client.inboxes.events.list.assert_awaited_once_with(
        inbox_id=mock_config.inbox_id,
        limit=mock_config.max_results,
    )


@pytest.mark.asyncio
async def test_list_inbox_events_caps_limit(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.events.list = AsyncMock(return_value={"events": []})
    await get_tool("mail_list_inbox_events")(fake_ctx, limit=99999)
    _, kwargs = mock_wrapper.client.inboxes.events.list.call_args
    assert kwargs["limit"] == 50  # MAX_RESULTS_CAP


@pytest.mark.asyncio
async def test_list_inbox_events_returns_error(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.events.list = AsyncMock(side_effect=ApiError(status_code=429, body="slow"))
    result = await get_tool("mail_list_inbox_events")(fake_ctx)
    parsed = json.loads(result)
    assert parsed["status"] == "error"
