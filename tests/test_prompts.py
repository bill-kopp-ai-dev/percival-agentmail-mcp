"""Tests for the MCP prompts (summarize_email, draft_reply, classify_message)."""

import pytest
from mcp.server.fastmcp import FastMCP

from percival_agentmail_mcp.prompts import register_prompts


@pytest.fixture
def mcp_server():
    server = FastMCP("percival-agentmail-test-prompts")
    register_prompts(server)
    return server


def _extract_text(messages: list) -> str:
    """Concatenate text from a list of Message objects."""
    parts: list[str] = []
    for m in messages:
        c = getattr(m, "content", m)
        if hasattr(c, "text"):
            parts.append(c.text)
        else:
            parts.append(str(c))
    return "\n".join(parts)


# --- Registration ---


def test_all_prompts_registered(mcp_server: FastMCP) -> None:
    prompts = mcp_server._prompt_manager.list_prompts()
    names = {p.name for p in prompts}
    assert "summarize_email" in names
    assert "draft_reply" in names
    assert "classify_message" in names


def test_prompts_have_descriptions(mcp_server: FastMCP) -> None:
    prompts = mcp_server._prompt_manager.list_prompts()
    by_name = {p.name: p for p in prompts}
    for name in ("summarize_email", "draft_reply", "classify_message"):
        assert by_name[name].description
        assert len(by_name[name].description) > 10


# --- summarize_email ---


@pytest.mark.asyncio
async def test_summarize_email_renders_message_id(mcp_server: FastMCP) -> None:
    msgs = await mcp_server._prompt_manager.render_prompt("summarize_email", {"message_id": "msg_xyz"})
    text = _extract_text(msgs)
    assert "msg_xyz" in text
    # Must include the tool name we want the LLM to call
    assert "mail_read_message" in text


@pytest.mark.asyncio
async def test_summarize_email_warns_about_untrusted_body(mcp_server: FastMCP) -> None:
    msgs = await mcp_server._prompt_manager.render_prompt("summarize_email", {"message_id": "msg_1"})
    text = _extract_text(msgs)
    # The fence markers must be mentioned so the LLM recognizes them.
    assert "EMAIL BODY START" in text
    assert "EMAIL BODY END" in text
    assert "UNTRUSTED" in text or "external data" in text.lower()


@pytest.mark.asyncio
async def test_summarize_email_ignores_injection_attempts(mcp_server: FastMCP) -> None:
    msgs = await mcp_server._prompt_manager.render_prompt("summarize_email", {"message_id": "msg_1"})
    text = _extract_text(msgs)
    assert "ignore previous instructions" in text.lower()


# --- draft_reply ---


@pytest.mark.asyncio
async def test_draft_reply_default_tone_is_professional(mcp_server: FastMCP) -> None:
    msgs = await mcp_server._prompt_manager.render_prompt("draft_reply", {"message_id": "msg_abc"})
    text = _extract_text(msgs)
    assert "professional" in text.lower()
    # Must reference the draft tool (never send_email)
    assert "mail_create_draft" in text
    assert "mail_send_email" in text  # mentioned as forbidden


@pytest.mark.asyncio
async def test_draft_reply_custom_tone(mcp_server: FastMCP) -> None:
    msgs = await mcp_server._prompt_manager.render_prompt("draft_reply", {"message_id": "msg_1", "tone": "apologetic"})
    text = _extract_text(msgs)
    assert "apologetic" in text.lower()


@pytest.mark.asyncio
async def test_draft_reply_invalid_tone_falls_back_to_professional(
    mcp_server: FastMCP,
) -> None:
    """Bad tone strings should NOT raise; they should fall back to professional."""
    msgs = await mcp_server._prompt_manager.render_prompt(
        "draft_reply", {"message_id": "msg_1", "tone": "yelling-with-megaphone"}
    )
    text = _extract_text(msgs)
    assert "professional" in text.lower()


@pytest.mark.asyncio
async def test_draft_reply_empty_tone_uses_default(mcp_server: FastMCP) -> None:
    msgs = await mcp_server._prompt_manager.render_prompt("draft_reply", {"message_id": "msg_1", "tone": ""})
    text = _extract_text(msgs)
    assert "professional" in text.lower()


# --- classify_message ---


@pytest.mark.asyncio
async def test_classify_message_defines_label_set(mcp_server: FastMCP) -> None:
    msgs = await mcp_server._prompt_manager.render_prompt("classify_message", {"message_id": "msg_1"})
    text = _extract_text(msgs)
    # All 5 labels must be listed
    for label in (
        "ACTION_REQUIRED",
        "FYI",
        "SPAM",
        "NEWSLETTER",
        "PERSONAL",
    ):
        assert label in text


@pytest.mark.asyncio
async def test_classify_message_is_read_only(mcp_server: FastMCP) -> None:
    """The prompt must NOT instruct the LLM to modify the email."""
    msgs = await mcp_server._prompt_manager.render_prompt("classify_message", {"message_id": "msg_1"})
    text = _extract_text(msgs).lower()
    # No mutating tool should appear in the instructions
    assert "mail_update_message" not in text
    assert "mail_delete_message" not in text
    assert "read-only" in text or "do not modify" in text
