"""Live end-to-end integration tests for `mail_send_email` attachments.

These tests exercise the **real** AgentMail API to confirm that
attachments survive the wire — i.e., that the fix in v0.3.5
(`_to_sdk_attachments` mapping `content_base64` -> `content`) reaches
the upstream AgentMail API and is persisted on the resulting message.

Opt-in only: skipped unless ``AGENTMAIL_LIVE_TEST=1``. Never runs in
the default CI pipeline. Requires a valid ``AGENTMAIL_API_KEY`` and
``AGENTMAIL_INBOX_ID`` in the environment (loaded from ``.env`` by
the runner, never committed).

Design notes
------------
- **Self-send**: ``to`` is set to the same inbox (``AGENTMAIL_INBOX_ID``)
  so we don't depend on an external recipient, an external SMTP relay,
  or external mail-client round-trip delays. The wire-level contract is
  exercised regardless of where the message is delivered downstream.
- **Unique subject**: prefixed with ``[integration-test-attachments]``
  plus a UUID, so we can identify our test message if cleanup fails.
- **Cleanup**: every test deletes its message via
  ``mail_delete_message`` in a ``finally`` block, even on assertion
  failure, so the inbox does not accumulate debris across runs.
- **Marker**: ``@pytest.mark.integration`` — already declared in
  ``pyproject.toml``.
"""

from __future__ import annotations

import base64
import json
import os
import uuid
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import ServerConfig
from percival_agentmail_mcp.lifespan import LifespanContext
from percival_agentmail_mcp.tools import register_tools
from tests.conftest import _FakeMCPContext

SUBJECT_PREFIX = "[integration-test-attachments]"


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes"}


pytestmark = pytest.mark.integration


# Skip the entire module unless AGENTMAIL_LIVE_TEST is explicitly enabled.
# Fail loudly (not silently) if the flag is set but the credentials are
# missing — that's a misconfiguration the operator must see.
if not _env_flag("AGENTMAIL_LIVE_TEST"):
    pytest.skip(
        "Live integration tests disabled (set AGENTMAIL_LIVE_TEST=1 to enable)",
        allow_module_level=True,
    )


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        pytest.fail(f"{name} is required when AGENTMAIL_LIVE_TEST=1", pytrace=False)
    return value


@pytest.fixture
def live_config() -> ServerConfig:
    api_key = _require("AGENTMAIL_API_KEY")
    inbox_id = _require("AGENTMAIL_INBOX_ID")
    return ServerConfig(
        api_key=api_key,
        inbox_id=inbox_id,
        max_results=10,
        timeout=30,
    )


@pytest.fixture
def live_wrapper(live_config: ServerConfig) -> AgentMailClientWrapper:
    # Function-scoped: each test gets a fresh httpx client bound to its
    # own asyncio event loop. Reusing the wrapper across tests would
    # surface "Event loop is closed" when pytest-asyncio creates a new
    # loop per test (the default).
    return AgentMailClientWrapper(api_key=live_config.api_key, timeout=live_config.timeout)


@pytest.fixture
def live_ctx(live_wrapper: AgentMailClientWrapper, live_config: ServerConfig) -> _FakeMCPContext:
    lifespan = LifespanContext(client=live_wrapper, config=live_config)
    return _FakeMCPContext(lifespan)


@pytest.fixture
def live_server() -> FastMCP:
    server = FastMCP("percival-agentmail-integration-test")
    register_tools(server)
    return server


def _get_tool(server: FastMCP, name: str):
    return server._tool_manager._tools[name].fn


@pytest.fixture
def fresh_subject() -> str:
    return f"{SUBJECT_PREFIX} {uuid.uuid4().hex[:12]}"


@pytest.fixture
def md_attachment() -> dict[str, str]:
    payload = "# Smoke test\n\nThis is the Markdown body that the integration test sends.\n"
    return {
        "filename": "smoke-test.md",
        "content_base64": base64.b64encode(payload.encode("utf-8")).decode("ascii"),
        "content_type": "text/markdown",
    }


@pytest.fixture
def pdf_attachment() -> dict[str, str]:
    # Minimal valid PDF (single blank page). Generated as raw bytes so we
    # do not need to install reportlab/matplotlib in the dev env.
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj\n"
        b"4 0 obj<</Length 44>>stream\n"
        b"BT /F1 12 Tf 100 700 Td (smoke test) Tj ET\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f\n"
        b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    )
    return {
        "filename": "smoke-test.pdf",
        "content_base64": base64.b64encode(pdf_bytes).decode("ascii"),
        "content_type": "application/pdf",
    }


async def _read_message(server, ctx, message_id: str) -> dict[str, Any]:
    """Read a message back as a parsed JSON dict."""
    raw = await _get_tool(server, "mail_read_message")(ctx, message_id=message_id)
    return json.loads(raw)


async def _delete_message(server, ctx, message_id: str) -> None:
    """Best-effort delete; swallow errors so cleanup never masks a real failure."""
    try:
        await _get_tool(server, "mail_delete_message")(ctx, message_id=message_id)
    except Exception:  # noqa: BLE001 — cleanup-only path
        pass


async def _find_message_id_by_subject(server, ctx, subject: str) -> str | None:
    """Locate a message we just sent by its unique subject.

    We do not rely on the response from ``mail_send_email`` because the
    SDK does not always include ``message_id`` in the body for outbound
    messages; we read from the inbox instead.
    """
    raw = await _get_tool(server, "mail_list_messages")(ctx, limit=20)
    payload = json.loads(raw)
    for msg in payload.get("messages", []):
        if subject in (msg.get("subject") or ""):
            return msg.get("message_id") or msg.get("id")
    return None


@pytest.mark.asyncio
async def test_send_email_md_attachment_reaches_wire(
    live_server: FastMCP,
    live_ctx: _FakeMCPContext,
    live_config: ServerConfig,
    fresh_subject: str,
    md_attachment: dict[str, str],
) -> None:
    """A single ``.md`` attachment must round-trip and be visible on the stored message."""
    send_raw = await _get_tool(live_server, "mail_send_email")(
        live_ctx,
        to=[live_config.inbox_id],
        subject=fresh_subject,
        text="Body for the MD attachment smoke test.",
        attachments=[md_attachment],
    )
    send_payload = json.loads(send_raw)

    # mail_send_email returns either a {"message_id": ..., "thread_id": ...} envelope
    # or a fenced-format message object depending on the SDK. We accept either and
    # locate the message by subject afterwards.
    sent_message_id = send_payload.get("message_id")

    try:
        if sent_message_id is None:
            sent_message_id = await _find_message_id_by_subject(live_server, live_ctx, fresh_subject)
        assert sent_message_id, (
            f"Could not find the sent message by subject in the inbox. send_response={send_payload!r}"
        )

        # Read the stored message back and confirm the attachment survived the wire.
        msg = await _read_message(live_server, live_ctx, sent_message_id)
        attachments = msg.get("attachments")
        assert attachments is not None, (
            f"'attachments' field missing entirely on the stored message (this was the original bug). "
            f"message_id={sent_message_id} subject={fresh_subject!r}"
        )
        assert isinstance(attachments, list) and len(attachments) == 1, (
            f"Expected exactly 1 attachment on the stored message, got {attachments!r}"
        )
        att = attachments[0]
        assert att.get("filename") == "smoke-test.md"
        assert att.get("content_type") == "text/markdown"
        size = att.get("size")
        assert isinstance(size, int) and size > 0, f"Attachment size is missing or zero: {att!r}"
    finally:
        if sent_message_id:
            await _delete_message(live_server, live_ctx, sent_message_id)


@pytest.mark.asyncio
async def test_send_email_multiple_attachments_reach_wire(
    live_server: FastMCP,
    live_ctx: _FakeMCPContext,
    live_config: ServerConfig,
    fresh_subject: str,
    md_attachment: dict[str, str],
    pdf_attachment: dict[str, str],
) -> None:
    """Both .md and .pdf attachments must round-trip when sent together.

    This mirrors the exact scenario described in the 2026-08-21 issue:
    attempts 1 (.md) and 2 (.pdf) failed silently. After the v0.3.5 fix,
    both should arrive intact on the stored message.
    """
    send_raw = await _get_tool(live_server, "mail_send_email")(
        live_ctx,
        to=[live_config.inbox_id],
        subject=fresh_subject,
        text="Body for the multi-attachment smoke test (.md + .pdf).",
        attachments=[md_attachment, pdf_attachment],
    )
    send_payload = json.loads(send_raw)
    sent_message_id = send_payload.get("message_id")

    try:
        if sent_message_id is None:
            sent_message_id = await _find_message_id_by_subject(live_server, live_ctx, fresh_subject)
        assert sent_message_id, f"Could not find the sent message by subject. send_response={send_payload!r}"

        msg = await _read_message(live_server, live_ctx, sent_message_id)
        attachments = msg.get("attachments")
        assert attachments is not None, (
            f"'attachments' field missing entirely on the stored message. message_id={sent_message_id}"
        )
        assert len(attachments) == 2, f"Expected 2 attachments, got {len(attachments)}: {attachments!r}"

        by_name = {att.get("filename"): att for att in attachments}
        assert "smoke-test.md" in by_name, f"Missing .md attachment: {by_name!r}"
        assert "smoke-test.pdf" in by_name, f"Missing .pdf attachment: {by_name!r}"

        md_att = by_name["smoke-test.md"]
        assert md_att.get("content_type") == "text/markdown"
        assert isinstance(md_att.get("size"), int) and md_att["size"] > 0

        pdf_att = by_name["smoke-test.pdf"]
        assert pdf_att.get("content_type") == "application/pdf"
        assert isinstance(pdf_att.get("size"), int) and pdf_att["size"] > 0
    finally:
        if sent_message_id:
            await _delete_message(live_server, live_ctx, sent_message_id)
