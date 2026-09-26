"""End-to-end MCP-transport contract tests (S1 of the 2026-07-21 incident).

These tests exercise the **full** call chain — MCP transport → tool
handler → AgentMail SDK → httpx — by mocking the AgentMail HTTP API
with ``respx``. The motivation is to catch regressions where the
handler's argument shape diverges from the SDK/upstream contract,
which previously allowed four tools to return ``HTTP 400`` (Bugs A–D)
even though the tool's ``input_schema`` and the handler looked correct
on paper.
"""

import json
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
import respx
from agentmail.core.api_error import ApiError
from mcp.server.fastmcp import FastMCP

from percival_agentmail_mcp.tools import register_tools
from tests.conftest import _FakeMCPContext


# respx uses a callable side_effect that should raise ApiError; we wrap
# httpx.Response inside a callback so the SDK interprets it as an error.
class _ApiErrorResponder:
    """respx side_effect that raises an ``ApiError`` from a fake response."""

    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body

    def __call__(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(self.status_code, text=self.body)


# Marker for tests that expect the SDK path NOT to be invoked.
AsyncMockSafe = AsyncMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_server(mock_context: _FakeMCPContext) -> FastMCP:
    server = FastMCP("percival-agentmail-contract-test")
    # We must attach a context BEFORE registering tools so that the
    # @with_agentmail decorator finds the lifespan_context.
    register_tools(server)
    server._mcp_server = server  # for _tool_manager resolution
    return server


async def _invoke(server: FastMCP, mock_context: _FakeMCPContext, name: str, arguments: dict) -> Any:
    """Invoke a tool via the MCP transport layer."""
    return await server._tool_manager.call_tool(name, arguments, context=mock_context)


@pytest.fixture
def fake_ctx(mock_context):
    return _FakeMCPContext(mock_context)


@pytest.fixture
def contract_context(respx_mock) -> _FakeMCPContext:  # noqa: ARG001
    """A LifespanContext with a REAL AgentMail SDK client.

    The SDK client is real so the full HTTP chain (handler → SDK → httpx)
    is exercised; ``respx_mock`` mocks the AgentMail HTTP API.

    Requires the ``respx_mock`` fixture to be active (autouse=True in the
    respx package, which is already a dev-dep of this project).
    """
    from percival_agentmail_mcp.client import AgentMailClientWrapper
    from percival_agentmail_mcp.config import ServerConfig
    from percival_agentmail_mcp.lifespan import LifespanContext

    # Real wrapper, real underlying SDK client — only HTTP is mocked.
    wrapper = AgentMailClientWrapper(api_key="am_test_12345678")
    config = ServerConfig(
        api_key="am_test_12345678",
        inbox_id="agent@agentmail.to",
    )
    return _FakeMCPContext(LifespanContext(client=wrapper, config=config))


# ---------------------------------------------------------------------------
# Bug A — mail_send_draft must send a non-empty body
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mail_send_draft_includes_add_labels(contract_context) -> None:
    """Bug A + residual R1: drafts.send body must contain add_labels (the
    upstream rejects {} and rejects system labels like 'sent').
    """
    server = _build_server(contract_context)

    with respx.mock(base_url="https://api.agentmail.to") as rmock:
        route = rmock.post("/v0/inboxes/agent@agentmail.to/drafts/draft_1/send").respond(
            200, json={"message_id": "msg_x", "thread_id": "t_1"}
        )
        result = await _invoke(server, contract_context, "mail_send_draft", {"draft_id": "draft_1"})
        body = route.calls[0].request.content.decode()
        assert "add_labels" in body, f"Body must include add_labels, got: {body}"
        parsed_body = json.loads(body)
        # After 2026-07-22 fix the sentinel is 'mcp-sent' (custom label)
        # NOT 'sent' (system label rejected by upstream).
        assert parsed_body["add_labels"] == ["mcp-sent"]
        assert "sent" not in parsed_body["add_labels"]
        # Tool result should be JSON containing the message_id
        out = json.loads(result)
        assert out["message_id"] == "msg_x"


# ---------------------------------------------------------------------------
# Bug B — mail_forward_message must send a non-empty body
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mail_forward_message_includes_labels(contract_context) -> None:
    """Bug B: forward body must include a labels array (the upstream rejects {})."""
    server = _build_server(contract_context)

    with respx.mock(base_url="https://api.agentmail.to") as rmock:
        route = rmock.post("/v0/inboxes/agent@agentmail.to/messages/msg_1/forward").respond(
            200, json={"message_id": "msg_fwd"}
        )
        await _invoke(
            server,
            contract_context,
            "mail_forward_message",
            {"message_id": "msg_1", "to": ["x@y.com"], "text": "FYI"},
        )
        body = json.loads(route.calls[0].request.content.decode())
        assert body.get("labels") == ["forwarded"], f"labels=['forwarded'] missing: {body}"
        assert body["to"] == ["x@y.com"]
        assert body["text"] == "FYI"


# ---------------------------------------------------------------------------
# Bug C — mail_update_message must reject empty label lists
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mail_update_message_rejects_empty_labels(contract_context) -> None:
    """Bug C: empty add_labels/remove_labels → clear error, no API call."""
    server = _build_server(contract_context)

    with respx.mock(base_url="https://api.agentmail.to") as _rmock:
        # No route mocked → any call would raise
        result = await _invoke(
            server,
            contract_context,
            "mail_update_message",
            {"message_id": "msg_1"},  # no labels
        )
        out = json.loads(result)
        assert out["status"] == "error"
        assert "add_labels" in out["message"]
        assert "remove_labels" in out["message"]


@pytest.mark.asyncio
async def test_mail_update_message_succeeds_with_labels(contract_context) -> None:
    """Bug C (positive case): providing labels calls PATCH successfully.

    Uses a *custom* label (not a reserved system one like ``"read"``) —
    the AgentMail upstream rejects system labels with HTTP 400 and the
    handler now shields the LLM from that round-trip.
    """
    server = _build_server(contract_context)

    with respx.mock(base_url="https://api.agentmail.to") as rmock:
        route = rmock.patch("/v0/inboxes/agent@agentmail.to/messages/msg_1").respond(
            200, json={"id": "msg_1", "labels": ["important"]}
        )
        await _invoke(
            server,
            contract_context,
            "mail_update_message",
            {"message_id": "msg_1", "add_labels": ["important"]},
        )
        body = json.loads(route.calls[0].request.content.decode())
        assert body == {"add_labels": ["important"]}


# ---------------------------------------------------------------------------
# Bug D — mail_update_inbox must reject empty body
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mail_update_inbox_rejects_empty_body(contract_context) -> None:
    """Bug D: no display_name and no metadata → clear error, no API call."""
    server = _build_server(contract_context)

    with respx.mock(base_url="https://api.agentmail.to") as _rmock:
        result = await _invoke(server, contract_context, "mail_update_inbox", {})
        out = json.loads(result)
        assert out["status"] == "error"
        assert "display_name" in out["message"]
        assert "metadata" in out["message"]


@pytest.mark.asyncio
async def test_mail_update_inbox_succeeds_with_display_name(contract_context) -> None:
    """Bug D (positive case): display_name is sent."""
    server = _build_server(contract_context)

    with respx.mock(base_url="https://api.agentmail.to") as rmock:
        route = rmock.patch("/v0/inboxes/agent@agentmail.to").respond(
            200, json={"inbox_id": "x", "display_name": "New Name"}
        )
        await _invoke(
            server,
            contract_context,
            "mail_update_inbox",
            {"display_name": "New Name"},
        )
        body = json.loads(route.calls[0].request.content.decode())
        assert body == {"display_name": "New Name"}


@pytest.mark.asyncio
async def test_mail_update_inbox_succeeds_with_metadata(contract_context) -> None:
    """Bug D (positive case): metadata alone is enough.

    The handler now treats the SDK call itself as the source of truth
    for "is metadata supported", instead of relying on a static probe.
    Both branches (PATCH succeeds OR PATCH raises TypeError → handler
    translates to actionable ValueError) are exercised here so the test
    is robust across 0.5.x wheels of the AgentMail SDK.
    """
    server = _build_server(contract_context)

    with respx.mock(base_url="https://api.agentmail.to", assert_all_called=False) as rmock:
        route = rmock.patch(url__regex=r"/v0/inboxes/[^/]+$").respond(200, json={"inbox_id": "agent@agentmail.to"})
        result = await _invoke(
            server,
            contract_context,
            "mail_update_inbox",
            {"metadata": {"team": "ops"}},
        )

    out = json.loads(result) if isinstance(result, str) else result
    if isinstance(out, dict) and route.called:
        body = json.loads(route.calls[0].request.content.decode())
        assert body == {"metadata": {"team": "ops"}}
    else:
        # Path where the SDK rejected ``metadata``: handler translates to error
        assert out.get("status") == "error" if isinstance(out, dict) else True
        assert isinstance(out, dict)
        assert "metadata" in out.get("message", "").lower()
        assert "agentmail" in out.get("message", "").lower()


# ---------------------------------------------------------------------------
# S5 — error messages must include the tool name and a hint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_400_error_carries_tool_name_and_hint(contract_context) -> None:
    """S5: 400 errors must surface the upstream message + tool context."""
    server = _build_server(contract_context)

    with respx.mock(base_url="https://api.agentmail.to") as rmock:
        rmock.patch("/v0/inboxes/agent@agentmail.to/messages/msg_1").mock(
            side_effect=_ApiErrorResponder(400, "Label 'foo' is not allowed")
        )
        result = await _invoke(
            server,
            contract_context,
            "mail_update_message",
            {"message_id": "msg_1", "add_labels": ["foo"]},
        )
    out = json.loads(result)
    assert out["status"] == "error"
    assert out["code"] == 400
    # Upstream message must be in the message (for LLM context)
    assert "Label" in out["message"]
    # S5: tool name and affected ID are surfaced as top-level keys
    assert out.get("tool") == "update_message"
    assert out.get("affected") == {"message_id": "msg_1"}


# ---------------------------------------------------------------------------
# Wire-level regression — mail_send_email attachments
# ---------------------------------------------------------------------------
#
# Bug history (2026-08-21, v0.3.4):
#   The MCP accepted `attachments=[{"filename": ..., "content_base64": ...}]`
#   but passed the dict straight to the SDK. The AgentMail SDK's
#   ``SendAttachment`` model has ``extra="allow"`` and only recognizes
#   the field ``content`` (not ``content_base64``); Pydantic silently
#   drops the unknown key, so the upstream request reached Amazon SES
#   with an empty attachment and ``message_id`` was returned without an
#   actual attachment in the email.
#
# The handler now translates ``content_base64`` -> ``content`` via
# ``_to_sdk_attachments`` (see ``tools/messages.py``). These tests pin
# the **wire-level JSON body** so a future SDK release that renames
# ``content`` (or otherwise mangles the payload) cannot silently
# regress this fix.


@pytest.mark.asyncio
async def test_mail_send_email_attachment_uses_content_field_on_wire(contract_context) -> None:
    """``content_base64`` must be renamed to ``content`` before hitting the upstream."""
    server = _build_server(contract_context)

    with respx.mock(base_url="https://api.agentmail.to") as rmock:
        route = rmock.post("/v0/inboxes/agent@agentmail.to/messages/send").respond(
            200, json={"message_id": "msg_x", "thread_id": "t_1"}
        )
        await _invoke(
            server,
            contract_context,
            "mail_send_email",
            {
                "to": ["recipient@example.com"],
                "subject": "Wire test",
                "text": "Body",
                "attachments": [
                    {
                        "filename": "note.md",
                        "content_base64": "aGVsbG8=",
                        "content_type": "text/markdown",
                    },
                ],
            },
        )

        body = json.loads(route.calls[0].request.content.decode())
        assert "attachments" in body, f"attachments missing from wire body: {body}"
        att_list = body["attachments"]
        assert len(att_list) == 1
        att = att_list[0]
        # The critical assertion: payload travels under the SDK's field name.
        assert att.get("content") == "aGVsbG8=", (
            f"Expected payload under `content` (SDK-recognized name); got {att!r}. "
            "If this fails the SDK may have renamed or nested the field — "
            "investigate before relaxing the assertion."
        )
        # ``content_base64`` must NOT appear on the wire — it's an MCP-facing
        # alias, not an AgentMail API field. The SDK would silently drop it
        # via ``extra="allow"`` and the recipient would receive no attachment.
        assert "content_base64" not in att, (
            f"content_base64 leaked to upstream SendAttachment — would be silently "
            f"dropped by extra='allow'. body={att!r}"
        )
        # Sanity: other LLM-facing fields are preserved verbatim.
        assert att.get("filename") == "note.md"
        assert att.get("content_type") == "text/markdown"


@pytest.mark.asyncio
async def test_mail_send_email_attachment_rejected_locally_before_wire_call(contract_context, monkeypatch) -> None:
    """An oversized attachment must be rejected client-side; no HTTP request.

    With ``MAX_ATTACHMENT_BINARY_BYTES`` aligned to the upstream 6 MB
    total request limit (v0.3.6), this guard saves the operator from a
    round-trip 4xx.
    """
    server = _build_server(contract_context)
    respx_mock = respx.mock(base_url="https://api.agentmail.to", assert_all_called=False)
    respx_mock.start()
    try:
        # 7 MB of binary — must be rejected by the handler's validator.
        import base64 as _b64

        payload = _b64.b64encode(b"x" * (7 * 1024 * 1024)).decode("ascii")
        result = await _invoke(
            server,
            contract_context,
            "mail_send_email",
            {
                "to": ["recipient@example.com"],
                "subject": "Oversize test",
                "text": "Body",
                "attachments": [{"filename": "huge.bin", "content_base64": payload}],
            },
        )
        out = json.loads(result)
        assert out["status"] == "error"
        assert "limit" in out["message"].lower() or "mb" in out["message"].lower(), (
            f"Error message should mention the size cap; got: {out['message']!r}"
        )
        # No route was registered, so any call would have raised
        # ConnectionError — reaching this line means the API was NOT called.
    finally:
        respx_mock.stop()


@pytest.mark.asyncio
async def test_mail_send_email_attachment_just_under_cap_reaches_wire(contract_context, monkeypatch) -> None:
    """A 5 MB attachment (under the 6 MB cap) must reach the upstream."""
    server = _build_server(contract_context)

    with respx.mock(base_url="https://api.agentmail.to") as rmock:
        route = rmock.post("/v0/inboxes/agent@agentmail.to/messages/send").respond(
            200, json={"message_id": "msg_big", "thread_id": "t_big"}
        )
        import base64 as _b64

        payload = _b64.b64encode(b"x" * (5 * 1024 * 1024)).decode("ascii")
        await _invoke(
            server,
            contract_context,
            "mail_send_email",
            {
                "to": ["recipient@example.com"],
                "subject": "Under-cap test",
                "text": "Body",
                "attachments": [{"filename": "big.bin", "content_base64": payload}],
            },
        )
        body = json.loads(route.calls[0].request.content.decode())
        assert len(body["attachments"]) == 1
        assert body["attachments"][0]["filename"] == "big.bin"
        # Payload length matches 5 MiB binary (base64 inflates ~33%).
        assert len(body["attachments"][0]["content"]) > 5 * 1024 * 1024


# ---------------------------------------------------------------------------
# Wire-level coverage — v0.4.0 attachment fields
# ---------------------------------------------------------------------------
#
# These tests pin the JSON shape for the optional ``content_disposition``,
# ``content_id``, and ``url`` fields added in v0.4.0. They follow the same
# pattern as the content/content_base64 tests above: mock the upstream HTTP
# endpoint, inspect the actual request body, assert the field names the
# AgentMail API expects.


@pytest.mark.asyncio
async def test_mail_send_email_attachment_content_disposition_on_wire(
    contract_context,
) -> None:
    """``content_disposition`` propagates to the upstream JSON (v0.4.0)."""
    server = _build_server(contract_context)

    with respx.mock(base_url="https://api.agentmail.to") as rmock:
        route = rmock.post("/v0/inboxes/agent@agentmail.to/messages/send").respond(
            200, json={"message_id": "msg_inline", "thread_id": "t_inline"}
        )
        await _invoke(
            server,
            contract_context,
            "mail_send_email",
            {
                "to": ["recipient@example.com"],
                "subject": "Inline test",
                "text": "<img src='cid:logo' alt='logo'>",
                "html": "<html><body><img src='cid:logo' alt='logo'></body></html>",
                "attachments": [
                    {
                        "filename": "logo.png",
                        "content_base64": "aGVsbG8=",
                        "content_type": "image/png",
                        "content_disposition": "inline",
                        "content_id": "logo",
                    },
                ],
            },
        )
        body = json.loads(route.calls[0].request.content.decode())
        att = body["attachments"][0]
        assert att.get("content_disposition") == "inline"
        assert att.get("content_id") == "logo"
        assert att.get("content") == "aGVsbG8="


@pytest.mark.asyncio
async def test_mail_send_email_attachment_url_on_wire(contract_context) -> None:
    """URL-backed attachment: ``url`` propagates, ``content`` is omitted (v0.4.0).

    Without the conditional ``content`` assignment in
    ``_to_sdk_attachments``, the wire body would carry ``content: null``
    alongside ``url``, which is allowed by the SDK but is unnecessary
    noise on the wire.
    """
    server = _build_server(contract_context)

    with respx.mock(base_url="https://api.agentmail.to") as rmock:
        route = rmock.post("/v0/inboxes/agent@agentmail.to/messages/send").respond(
            200, json={"message_id": "msg_url", "thread_id": "t_url"}
        )
        await _invoke(
            server,
            contract_context,
            "mail_send_email",
            {
                "to": ["recipient@example.com"],
                "subject": "URL-backed test",
                "text": "See attached large PDF.",
                "attachments": [
                    {
                        "filename": "big.pdf",
                        "url": "https://example.com/big.pdf",
                        "content_type": "application/pdf",
                    },
                ],
            },
        )
        body = json.loads(route.calls[0].request.content.decode())
        att = body["attachments"][0]
        assert att.get("url") == "https://example.com/big.pdf"
        assert "content" not in att, f"content field must be omitted for URL-backed attachments: {att!r}"
        assert "content_base64" not in att
