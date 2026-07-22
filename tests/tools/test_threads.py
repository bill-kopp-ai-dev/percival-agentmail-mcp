"""Tests for thread tools (4 tools)."""

import json
from unittest.mock import AsyncMock

import pytest
from agentmail.core.api_error import ApiError

from tests.tools._fixtures import *

# --- mail_list_threads ---


@pytest.mark.asyncio
async def test_list_threads_default(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.threads.list = AsyncMock(return_value={"threads": []})
    await get_tool("mail_list_threads")(fake_ctx)
    mock_wrapper.client.inboxes.threads.list.assert_awaited_once_with(
        inbox_id=mock_config.inbox_id,
        limit=mock_config.max_results,
    )


@pytest.mark.asyncio
async def test_list_threads_with_labels_and_pagination(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.threads.list = AsyncMock(return_value={"threads": []})
    await get_tool("mail_list_threads")(fake_ctx, labels=["unread"], limit=5, page_token="tok")
    _, kwargs = mock_wrapper.client.inboxes.threads.list.call_args
    assert kwargs["labels"] == ["unread"]
    assert kwargs["limit"] == 5
    assert kwargs["page_token"] == "tok"


@pytest.mark.asyncio
async def test_list_threads_caps_limit(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.threads.list = AsyncMock(return_value={"threads": []})
    await get_tool("mail_list_threads")(fake_ctx, limit=99999)
    _, kwargs = mock_wrapper.client.inboxes.threads.list.call_args
    assert kwargs["limit"] == 50


# --- mail_get_thread ---


@pytest.mark.asyncio
async def test_get_thread_fences_all_messages(get_tool, fake_ctx, mock_wrapper) -> None:
    payload = {
        "id": "t_1",
        "subject": "Hello thread",
        "messages": [
            {"text": "msg1", "subject": "s1"},
            {"text": "msg2", "html": "<p>x</p>"},
        ],
    }
    mock_wrapper.client.inboxes.threads.get = AsyncMock(return_value=payload)
    result = await get_tool("mail_get_thread")(fake_ctx, thread_id="t_1")
    parsed = json.loads(result)
    assert "EMAIL BODY START" in parsed["subject"]
    for m in parsed["messages"]:
        assert "EMAIL BODY START" in m["text"]


@pytest.mark.asyncio
async def test_get_thread_returns_error(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.threads.get = AsyncMock(side_effect=ApiError(status_code=404, body="missing"))
    result = await get_tool("mail_get_thread")(fake_ctx, thread_id="t_1")
    parsed = json.loads(result)
    assert parsed["code"] == 404


# --- mail_update_thread ---


@pytest.mark.asyncio
async def test_update_thread_add_and_remove_labels(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.threads.update = AsyncMock(return_value={"id": "t_1"})
    await get_tool("mail_update_thread")(
        fake_ctx,
        thread_id="t_1",
        add_labels=["archived"],
        remove_labels=["inbox"],
    )
    _, kwargs = mock_wrapper.client.inboxes.threads.update.call_args
    assert kwargs["inbox_id"] == mock_config.inbox_id
    assert kwargs["add_labels"] == ["archived"]
    assert kwargs["remove_labels"] == ["inbox"]


@pytest.mark.asyncio
async def test_update_thread_normalizes_labels(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.threads.update = AsyncMock(return_value={"id": "t_1"})
    await get_tool("mail_update_thread")(fake_ctx, thread_id="t_1", add_labels="a, b, c")
    _, kwargs = mock_wrapper.client.inboxes.threads.update.call_args
    assert kwargs["add_labels"] == ["a", "b", "c"]


# --- mail_delete_thread ---


@pytest.mark.asyncio
async def test_delete_thread_success(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.threads.delete = AsyncMock(return_value=None)
    result = await get_tool("mail_delete_thread")(fake_ctx, thread_id="t_1")
    parsed = json.loads(result)
    assert parsed["status"] == "success"
    mock_wrapper.client.inboxes.threads.delete.assert_awaited_once_with(inbox_id=mock_config.inbox_id, thread_id="t_1")


@pytest.mark.asyncio
async def test_delete_thread_returns_error(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.threads.delete = AsyncMock(side_effect=ApiError(status_code=403, body="denied"))
    result = await get_tool("mail_delete_thread")(fake_ctx, thread_id="t_1")
    parsed = json.loads(result)
    assert parsed["code"] == 403


# --- Fase 6: mail_mark_thread_read ---


@pytest.mark.asyncio
async def test_mark_thread_read_default_adds_label(get_tool, fake_ctx, mock_wrapper) -> None:
    """Default: adds the custom 'mcp-read' sentinel label. The system
    'read' label is reserved and would be rejected by the upstream.
    """
    mock_wrapper.client.inboxes.threads.update = AsyncMock(return_value={"id": "t_1"})
    await get_tool("mail_mark_thread_read")(fake_ctx, thread_id="t_1")
    _, kwargs = mock_wrapper.client.inboxes.threads.update.call_args
    assert kwargs["add_labels"] == ["mcp-read"]
    assert "remove_labels" not in kwargs


@pytest.mark.asyncio
async def test_mark_thread_read_false_removes_label(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.threads.update = AsyncMock(return_value={"id": "t_1"})
    await get_tool("mail_mark_thread_read")(fake_ctx, thread_id="t_1", read=False)
    _, kwargs = mock_wrapper.client.inboxes.threads.update.call_args
    assert kwargs["remove_labels"] == ["mcp-read"]
    assert "add_labels" not in kwargs
