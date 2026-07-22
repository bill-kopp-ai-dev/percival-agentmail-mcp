"""Tests for the mail_get_version tool (S7 of the 2026-07-21 incident)."""

import json
import re
from unittest.mock import AsyncMock

import pytest

from tests.tools._fixtures import *  # noqa: F401,F403


@pytest.mark.asyncio
async def test_get_version_returns_required_fields(get_tool, fake_ctx) -> None:
    result = await get_tool("mail_get_version")(fake_ctx)
    parsed = json.loads(result)
    assert parsed["server_name"] == "percival-agentmail-mcp"
    assert re.match(r"\d+\.\d+\.\d+", parsed["package_version"])
    assert re.match(r"\d+\.\d+\.\d+", parsed["python_version"])
    assert parsed["inbox"] == "agent@agentmail.to"
    assert "Linux" in parsed["platform"] or "Darwin" in parsed["platform"] or "Windows" in parsed["platform"]


@pytest.mark.asyncio
async def test_get_version_does_not_hit_the_api(get_tool, fake_ctx, mock_wrapper) -> None:
    """mail_get_version is read-only metadata; must not call the AgentMail API."""
    mock_wrapper.client.inboxes.get = AsyncMock()
    result = await get_tool("mail_get_version")(fake_ctx)
    assert result is not None
    mock_wrapper.client.inboxes.get.assert_not_called()
