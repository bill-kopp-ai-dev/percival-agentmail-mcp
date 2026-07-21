"""Tests for the status utility get_tool (1 get_tool)."""

import json
from unittest.mock import AsyncMock

import pytest
from agentmail.core.api_error import ApiError

from tests.tools._fixtures import *


@pytest.mark.asyncio
async def test_status_online_with_latency(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.get = AsyncMock(return_value={"id": mock_config.inbox_id})
    result = await get_tool("mail_get_status")(fake_ctx)
    parsed = json.loads(result)
    assert parsed["status"] == "online"
    assert parsed["api_reachable"] is True
    assert parsed["inbox"] == mock_config.inbox_id
    assert isinstance(parsed["api_latency_ms"], int)
    assert parsed["api_error"] is None


@pytest.mark.asyncio
async def test_status_degraded_on_api_error(get_tool, fake_ctx, mock_wrapper, mock_config) -> None:
    mock_wrapper.client.inboxes.get = AsyncMock(side_effect=ApiError(status_code=500, body="boom"))
    result = await get_tool("mail_get_status")(fake_ctx)
    parsed = json.loads(result)
    assert parsed["status"] == "degraded"
    assert parsed["api_reachable"] is False
    assert parsed["api_error"] == "ApiError"
