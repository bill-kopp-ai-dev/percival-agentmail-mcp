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
    """Bug C (positive case): providing labels calls PATCH successfully."""
    server = _build_server(contract_context)

    with respx.mock(base_url="https://api.agentmail.to") as rmock:
        route = rmock.patch("/v0/inboxes/agent@agentmail.to/messages/msg_1").respond(
            200, json={"id": "msg_1", "labels": ["read"]}
        )
        await _invoke(
            server,
            contract_context,
            "mail_update_message",
            {"message_id": "msg_1", "add_labels": ["read"]},
        )
        body = json.loads(route.calls[0].request.content.decode())
        assert body == {"add_labels": ["read"]}


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
    """Bug D (positive case): metadata alone is enough — when supported.

    Different 0.5.x SDK wheels ship with and without the ``metadata``
    kwarg on ``inboxes.update``. The handler probes via
    ``_sdk_supports_metadata`` and returns a clear error when not
    supported. On both branches this test must NOT flake on CI.
    """
    from percival_agentmail_mcp.tools.inbox import _sdk_supports_metadata

    server = _build_server(contract_context)

    # ``assert_all_called=False`` plus ``url__regex`` avoids a
    # response-method assertion error if any stray traffic hits the
    # wire and tolerates trailing slashes / encoding differences.
    with respx.mock(base_url="https://api.agentmail.to", assert_all_called=False) as rmock:
        route = rmock.patch(url__regex=r"/v0/inboxes/[^/]+$").respond(200, json={"inbox_id": "agent@agentmail.to"})
        result = await _invoke(
            server,
            contract_context,
            "mail_update_inbox",
            {"metadata": {"team": "ops"}},
        )

    out = json.loads(result)
    if _sdk_supports_metadata():
        # The success path returns the serialized Inbox object (no envelope)
        assert "inbox_id" in out, f"expected Inbox-like response on success path; got: {out}"
        assert route.called, "PATCH /v0/inboxes/<id> was not called by the handler"
        body = json.loads(route.calls[0].request.content.decode())
        assert body == {"metadata": {"team": "ops"}}
    else:
        # The handler raised ValueError before hitting the API; ensure
        # the error envelope tells the LLM to upgrade ``agentmail``.
        assert out.get("status") == "error"
        assert "metadata" in out.get("message", "").lower()
        assert "agentmail" in out.get("message", "").lower()
        assert not route.called, "PATCH must not be called when SDK doesn't accept metadata"


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
