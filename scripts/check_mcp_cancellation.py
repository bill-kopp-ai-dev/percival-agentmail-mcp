"""Exercise both terminal paths against real SDK session streams, offline."""

import anyio
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.session import ServerSession
from mcp.shared.message import SessionMessage
from mcp.shared.session import RequestResponder


async def main():
    for order in ("cancel-respond", "respond-cancel", "cancel-cancel"):
        incoming, reader = anyio.create_memory_object_stream(16)
        writer, outgoing = anyio.create_memory_object_stream(16)
        session = ServerSession(reader, writer, Server("stage2-regression").create_initialization_options())
        completed = []
        responder = RequestResponder(1, None, types.PingRequest(method="ping"), session, completed.append)
        # CancelScope cancellation normally unwinds the handler. A synchronous
        # handler may return before reaching a checkpoint; shielding reproduces
        # that late response deterministically, without changing the responder.
        with responder:
            with anyio.CancelScope(shield=True):
                for action in order.split("-"):
                    if action == "cancel":
                        await responder.cancel()
                    else:
                        await responder.respond(types.EmptyResult())
        assert len(completed) == 1
        assert outgoing.statistics().current_buffer_used == 1, "duplicate terminal response"
        message = outgoing.receive_nowait()
        assert isinstance(message, SessionMessage)
        assert message.message.root.id == 1
        # A different request must still be handled by this session.
        with RequestResponder(2, None, types.PingRequest(method="ping"), session, completed.append) as next_request:
            await next_request.respond(types.EmptyResult())
        assert outgoing.receive_nowait().message.root.id == 2
        assert len(completed) == 2
        await incoming.aclose()
        await reader.aclose()
        await writer.aclose()
        await outgoing.aclose()
        print(order + ": pass; one terminal response, next request succeeds")


anyio.run(main)
