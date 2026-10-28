"""Tests for sanitized top-level startup failures."""

import json
import selectors
import signal
import subprocess
import sys
import textwrap
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import anyio
import pytest

from percival_agentmail_mcp import server


class _FailingServer:
    def run(self) -> None:
        raise RuntimeError("transport sentinel must stay private")


def test_main_sanitizes_startup_failure(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setattr(server, "create_server", lambda _debug: _FailingServer())
    monkeypatch.setattr("sys.argv", ["percival-agentmail-mcp"])

    with pytest.raises(SystemExit) as error:
        server.main()

    assert error.value.code == 1
    assert "RuntimeError" in caplog.text
    assert "transport sentinel" not in caplog.text
    assert "Traceback" not in caplog.text


def test_main_debug_keeps_local_diagnostics(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setattr(server, "create_server", lambda _debug: _FailingServer())
    monkeypatch.setattr("sys.argv", ["percival-agentmail-mcp", "--debug"])

    with pytest.raises(SystemExit) as error:
        server.main()

    assert error.value.code == 1
    assert "transport sentinel" in caplog.text
    assert "Traceback" in caplog.text


def test_sigterm_runs_lifespan_shutdown_and_exits_cleanly() -> None:
    script = textwrap.dedent(
        """
        import sys
        from contextlib import asynccontextmanager
        from percival_agentmail_mcp.server import AgentMailFastMCP

        @asynccontextmanager
        async def lifespan(_server):
            try:
                yield {}
            finally:
                print("LIFESPAN_SHUTDOWN_RAN", file=sys.stderr, flush=True)

        mcp = AgentMailFastMCP("signal-test", lifespan=lifespan)

        @mcp.tool(name="delayed_work")
        async def delayed_work():
            import anyio
            await anyio.sleep(0.5)
            return "work completed"

        mcp.run()
        """
    )
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stderr is not None
    assert process.stdin is not None
    assert process.stdout is not None
    deadline = time.monotonic() + 10
    with selectors.DefaultSelector() as selector:
        selector.register(process.stderr, selectors.EVENT_READ)
        while time.monotonic() < deadline:
            assert selector.select(timeout=max(0, deadline - time.monotonic())), "server did not install signal handler"
            line = process.stderr.readline()
            if "Termination signal handlers active" in line:
                break
        else:
            process.kill()
            process.communicate(timeout=5)
            pytest.fail("server did not install signal handler")

    process.stdin.write(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "signal-test", "version": "1.0"},
                },
            }
        )
        + "\n"
    )
    process.stdin.flush()
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        assert selector.select(timeout=10), "initialize response not received"
        init_response = json.loads(process.stdout.readline())
    assert init_response["id"] == 1

    process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
    process.stdin.write(
        '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"delayed_work","arguments":{}}}\n'
    )
    process.stdin.flush()
    time.sleep(0.1)
    process.send_signal(signal.SIGTERM)
    time.sleep(server.SIGNAL_DRAIN_SECONDS + 0.1)
    _stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 0
    assert "LIFESPAN_SHUTDOWN_RAN" in stderr
    assert "Received SIGTERM" in stderr
    assert "Shutdown grace window ended" in stderr
    tool_response = next(json.loads(line) for line in _stdout.splitlines() if json.loads(line).get("id") == 2)
    assert "work completed" in str(tool_response)


@pytest.mark.asyncio
async def test_bounded_client_close_is_shielded_from_cancellation() -> None:
    wrapper = SimpleNamespace(aclose=AsyncMock())

    with anyio.CancelScope() as cancel_scope:
        cancel_scope.cancel()
        await server._close_client_bounded(wrapper)

    wrapper.aclose.assert_awaited_once()
