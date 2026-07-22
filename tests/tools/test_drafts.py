"""Tests for draft tools (5 tools)."""

import json
from unittest.mock import AsyncMock

import pytest
from agentmail.core.api_error import ApiError

from tests.tools._fixtures import *

# --- mail_create_draft ---


@pytest.mark.asyncio
async def test_create_draft_minimal(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.drafts.create = AsyncMock(return_value={"id": "d_1"})
    await get_tool("mail_create_draft")(
        fake_ctx,
        to=["a@example.com"],
        subject="Hi",
        text="Body",
    )
    mock_wrapper.client.inboxes.drafts.create.assert_awaited_once_with(
        inbox_id=mock_config.inbox_id,
        to=["a@example.com"],
        subject="Hi",
        text="Body",
    )


@pytest.mark.asyncio
async def test_create_draft_with_html_and_send_at(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.drafts.create = AsyncMock(return_value={"id": "d_1"})
    await get_tool("mail_create_draft")(
        fake_ctx,
        to=["a@example.com"],
        subject="Hi",
        text="Body",
        html="<p>x</p>",
        send_at="2026-12-01T10:00:00Z",
    )
    _, kwargs = mock_wrapper.client.inboxes.drafts.create.call_args
    assert kwargs["html"] == "<p>x</p>"
    assert kwargs["send_at"] == "2026-12-01T10:00:00Z"


@pytest.mark.asyncio
async def test_create_draft_normalizes_to(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.drafts.create = AsyncMock(return_value={"id": "d_1"})
    await get_tool("mail_create_draft")(
        fake_ctx,
        to="a@example.com, b@example.com",
        subject="Hi",
        text="Body",
    )
    _, kwargs = mock_wrapper.client.inboxes.drafts.create.call_args
    assert kwargs["to"] == ["a@example.com", "b@example.com"]


# --- mail_list_drafts ---


@pytest.mark.asyncio
async def test_list_drafts_default(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.drafts.list = AsyncMock(return_value={"drafts": []})
    await get_tool("mail_list_drafts")(fake_ctx)
    mock_wrapper.client.inboxes.drafts.list.assert_awaited_once_with(
        inbox_id=mock_config.inbox_id,
        limit=mock_config.max_results,
    )


@pytest.mark.asyncio
async def test_list_drafts_with_pagination(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.drafts.list = AsyncMock(return_value={"drafts": []})
    await get_tool("mail_list_drafts")(fake_ctx, limit=5, page_token="tok")
    _, kwargs = mock_wrapper.client.inboxes.drafts.list.call_args
    assert kwargs["page_token"] == "tok"
    assert kwargs["limit"] == 5


@pytest.mark.asyncio
async def test_list_drafts_caps_limit(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.drafts.list = AsyncMock(return_value={"drafts": []})
    await get_tool("mail_list_drafts")(fake_ctx, limit=99999)
    _, kwargs = mock_wrapper.client.inboxes.drafts.list.call_args
    assert kwargs["limit"] == 50


# --- mail_get_draft ---


@pytest.mark.asyncio
async def test_get_draft_success(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.drafts.get = AsyncMock(return_value={"id": "d_1"})
    await get_tool("mail_get_draft")(fake_ctx, draft_id="d_1")
    mock_wrapper.client.inboxes.drafts.get.assert_awaited_once_with(inbox_id=mock_config.inbox_id, draft_id="d_1")


@pytest.mark.asyncio
async def test_get_draft_returns_error(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.drafts.get = AsyncMock(side_effect=ApiError(status_code=404, body="missing"))
    result = await get_tool("mail_get_draft")(fake_ctx, draft_id="d_1")
    parsed = json.loads(result)
    assert parsed["code"] == 404


# --- mail_update_draft ---


@pytest.mark.asyncio
async def test_update_draft_all_fields(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.drafts.update = AsyncMock(return_value={"id": "d_1"})
    await get_tool("mail_update_draft")(
        fake_ctx,
        draft_id="d_1",
        to=["a@example.com"],
        subject="New",
        text="Body",
        html="<p>x</p>",
        send_at="2026-12-01T10:00:00Z",
    )
    _, kwargs = mock_wrapper.client.inboxes.drafts.update.call_args
    assert kwargs["inbox_id"] == mock_config.inbox_id
    assert kwargs["to"] == ["a@example.com"]
    assert kwargs["subject"] == "New"
    assert kwargs["html"] == "<p>x</p>"
    assert kwargs["send_at"] == "2026-12-01T10:00:00Z"


@pytest.mark.asyncio
async def test_update_draft_partial(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.drafts.update = AsyncMock(return_value={"id": "d_1"})
    await get_tool("mail_update_draft")(fake_ctx, draft_id="d_1", subject="Only subject")
    _, kwargs = mock_wrapper.client.inboxes.drafts.update.call_args
    assert kwargs["subject"] == "Only subject"
    assert "to" not in kwargs
    assert "text" not in kwargs


# --- mail_send_draft ---


@pytest.mark.asyncio
async def test_send_draft_success(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.drafts.send = AsyncMock(return_value={"id": "msg_x"})
    await get_tool("mail_send_draft")(fake_ctx, draft_id="d_1")
    mock_wrapper.client.inboxes.drafts.send.assert_awaited_once_with(
        inbox_id=mock_config.inbox_id,
        draft_id="d_1",
        add_labels=["sent"],
    )


@pytest.mark.asyncio
async def test_send_draft_returns_error(get_tool, fake_ctx, mock_wrapper) -> None:
    mock_wrapper.client.inboxes.drafts.send = AsyncMock(side_effect=ApiError(status_code=429, body="slow"))
    result = await get_tool("mail_send_draft")(fake_ctx, draft_id="d_1")
    parsed = json.loads(result)
    assert parsed["code"] == 429


@pytest.mark.asyncio
async def test_send_draft_does_not_retry_on_503(get_tool, fake_ctx, mock_wrapper) -> None:
    """Regression: dispatching a draft must NOT auto-retry on 5xx — the SDK
    has no idempotency key, so a retry after a transient error could
    dispatch the same draft twice."""
    mock_wrapper.client.inboxes.drafts.send = AsyncMock(side_effect=ApiError(status_code=503, body="down"))
    await get_tool("mail_send_draft")(fake_ctx, draft_id="d_1")
    assert mock_wrapper.client.inboxes.drafts.send.await_count == 1


@pytest.mark.asyncio
async def test_create_draft_does_not_retry_on_503(get_tool, fake_ctx, mock_wrapper) -> None:
    """Regression: creating a draft must NOT auto-retry — a retry after a
    transient error could create a duplicate draft."""
    mock_wrapper.client.inboxes.drafts.create = AsyncMock(side_effect=ApiError(status_code=503, body="down"))
    await get_tool("mail_create_draft")(fake_ctx, to=["a@example.com"], subject="Hi", text="Body")
    assert mock_wrapper.client.inboxes.drafts.create.await_count == 1
