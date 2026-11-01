"""Exercise the container's stdio MCP contract without network access."""

from __future__ import annotations

import argparse
import json
import os
import re
import selectors
import subprocess
import sys
import tempfile
import time
import uuid


def redact_secrets(text: str, entries: list[str]) -> str:
    for entry in entries:
        _, _, value = entry.partition("=")
        if value:
            text = text.replace(value, "[redacted]")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--mount", action="append", default=[])
    parser.add_argument("--env", action="append", default=[])
    parser.add_argument("--secret-env", action="append", default=[])
    parser.add_argument(
        "--secret-file",
        action="append",
        default=[],
        help="synthetic file secret for conformance: NAME=VALUE",
    )
    parser.add_argument(
        "--redact-value",
        action="append",
        default=[],
        help="synthetic value to check for leakage without passing it to the container",
    )
    parser.add_argument("--expected-tool", action="append", default=[])
    parser.add_argument("--safe-tool", choices=("mail_get_status", "mail_get_version", "mail_get_inbox_info"))
    parser.add_argument("--expected-uid", type=int)
    parser.add_argument("--compose-file", default="docker-compose.yml")
    parser.add_argument("--compose-service")
    parser.add_argument("--compose-profile", action="append", default=[])
    parser.add_argument("--mock-agentmail", action="store_true")
    args = parser.parse_args()
    for item in args.secret_file:
        name, separator, value = item.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) or not value:
            parser.error("--secret-file format is NAME=non-empty-synthetic-value")
    sensitive_entries = [*args.secret_env, *args.secret_file, *args.redact_value]
    if args.expected_uid is not None:
        probe = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network=none",
                "--entrypoint",
                "python",
                args.image,
                "-c",
                "import os; print(os.getuid())",
            ],
            check=False,
            text=True,
            capture_output=True,
            timeout=30,
        )
        if probe.returncode or probe.stdout.strip() != str(args.expected_uid):
            print(
                f"container UID mismatch: expected {args.expected_uid}, got {probe.stdout.strip()!r}", file=sys.stderr
            )
            return 1
    if args.compose_service:
        compose = ["docker", "compose", "-f", args.compose_file]
        for profile in args.compose_profile:
            compose += ["--profile", profile]
        try:
            rendered = subprocess.run(
                [*compose, "config", "--format", "json"],
                check=False,
                text=True,
                capture_output=True,
                timeout=30,
            )
            config = json.loads(rendered.stdout) if rendered.returncode == 0 else {}
        except (json.JSONDecodeError, subprocess.TimeoutExpired):
            config = {}
        service = config.get("services", {}).get(args.compose_service)
        if not isinstance(service, dict):
            print(f"Compose service missing: {args.compose_service}", file=sys.stderr)
            return 1
        healthcheck = service.get("healthcheck")
        if (
            service.get("stdin_open") is not True
            or service.get("tty", False) is not False
            or service.get("ports")
            or service.get("restart") not in (None, "no")
            or (healthcheck and healthcheck.get("disable") is not True)
        ):
            print(f"Compose stdio contract failed for {args.compose_service}", file=sys.stderr)
            return 1
    network = f"agentmail-ci-{uuid.uuid4().hex[:10]}" if args.mock_agentmail else "none"
    mock_name = f"agentmail-mock-{uuid.uuid4().hex[:10]}"
    tempdir = (
        tempfile.TemporaryDirectory(prefix="percival-agentmail-ci-")
        if args.mock_agentmail or args.secret_file
        else None
    )
    command = ["docker", "run", "--rm", "-i", "--init", f"--network={network}"]
    if args.mock_agentmail:
        subprocess.run(["docker", "network", "create", "--internal", network], check=True, capture_output=True)
        mock_server = "\n".join(
            (
                "from http.server import BaseHTTPRequestHandler, HTTPServer",
                "import json",
                "class Handler(BaseHTTPRequestHandler):",
                "    def do_GET(self):",
                "        body = json.dumps({",
                "            'pod_id': 'ci-pod', 'inbox_id': 'ci@example.com',",
                "            'email': 'ci@example.com', 'created_at': '2026-01-01T00:00:00Z',",
                "            'updated_at': '2026-01-01T00:00:00Z',",
                "        }).encode()",
                "        self.send_response(200)",
                "        self.send_header('Content-Type', 'application/json')",
                "        self.send_header('Content-Length', str(len(body)))",
                "        self.end_headers()",
                "        self.wfile.write(body)",
                "    def log_message(self, *args): pass",
                "HTTPServer(('0.0.0.0', 8123), Handler).serve_forever()",
            )
        )
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                mock_name,
                "--network",
                network,
                "--network-alias",
                "agentmail-mock",
                "--entrypoint",
                "python",
                args.image,
                "-c",
                mock_server,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        site_dir = os.path.join(tempdir.name, "site")
        os.mkdir(site_dir)
        with open(os.path.join(site_dir, "sitecustomize.py"), "w", encoding="utf-8") as handle:
            handle.write(
                "from agentmail.environment import AgentMailEnvironment\n"
                "for name in ('PROD', 'PROD_X_402', 'PROD_MPP', 'EU_PROD'):\n"
                "    env = getattr(AgentMailEnvironment, name, None)\n"
                "    if env is not None:\n"
                "        env.http = 'http://agentmail-mock:8123'\n"
            )
        args.mount.append(f"type=bind,source={site_dir},destination=/tmp/ci-sitecustomize,readonly")
        args.env.append("PYTHONPATH=/tmp/ci-sitecustomize")
        configured_names = {item.partition("=")[0] for item in [*args.env, *args.secret_env, *args.secret_file]}
        if not {"AGENTMAIL_INBOX_ID", "AGENTMAIL_INBOX_ID_FILE"} & configured_names:
            args.env.append("AGENTMAIL_INBOX_ID=ci@example.com")
        probe_code = (
            "import urllib.request; urllib.request.urlopen("
            "'http://127.0.0.1:8123/v0/inboxes/ci@example.com', timeout=1)"
        )
        for _ in range(60):
            probe = subprocess.run(
                [
                    "docker",
                    "exec",
                    mock_name,
                    "python",
                    "-c",
                    probe_code,
                ],
                capture_output=True,
            )
            if probe.returncode == 0:
                break
            time.sleep(0.5)
        else:
            subprocess.run(["docker", "rm", "-f", mock_name], capture_output=True)
            subprocess.run(["docker", "network", "rm", network], capture_output=True)
            tempdir.cleanup()
            raise RuntimeError("local AgentMail fixture did not become ready")
    if args.secret_file:
        assert tempdir is not None
        secret_dir = os.path.join(tempdir.name, "secrets")
        os.makedirs(secret_dir, mode=0o700)
        for item in args.secret_file:
            name, _, value = item.partition("=")
            source = os.path.join(secret_dir, name.lower())
            with open(source, "w", encoding="utf-8") as handle:
                handle.write(value)
            os.chmod(source, 0o444)
            target = f"/app/.secrets/{name.lower()}"
            args.mount.append(f"type=bind,source={source},destination={target},readonly")
            args.env.append(f"{name}_FILE={target}")
    for mount in args.mount:
        command += ["--mount", mount]
    for item in args.env + args.secret_env:
        command += ["--env", item]
    command.append(args.image)
    requests = (
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "percival-ci", "version": "0.1.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    process = None
    selector = None
    responses = []
    stdout_lines: list[str] = []
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        assert process.stdin is not None and process.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)

        def send(request: dict) -> None:
            process.stdin.write(json.dumps(request) + "\n")
            process.stdin.flush()

        def wait_for_response(request_id: int) -> bool:
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if not selector.select(deadline - time.monotonic()):
                    continue
                line = process.stdout.readline()
                if not line:
                    break
                stdout_lines.append(line)
                try:
                    response = json.loads(line)
                except json.JSONDecodeError:
                    print(
                        f"stdout line is not JSON-RPC: {redact_secrets(line[:300], sensitive_entries)!r}",
                        file=sys.stderr,
                    )
                    return False
                responses.append(response)
                if response.get("id") == request_id:
                    return True
            return False

        send(requests[0])
        if not wait_for_response(1):
            raise RuntimeError("MCP initialize response timed out or was invalid")
        send(requests[1])
        send(requests[2])
        if not wait_for_response(2):
            raise RuntimeError("MCP tools/list response timed out or was invalid")
        if args.safe_tool:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": args.safe_tool, "arguments": {}},
                }
            )
            if not wait_for_response(3):
                raise RuntimeError(f"MCP safe tool call timed out or was invalid: {args.safe_tool}")
        process.stdin.close()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise RuntimeError("stdio MCP process did not exit after stdin closed") from None
        trailing_stdout = process.stdout.read()
        result_stdout = "".join(stdout_lines) + trailing_stdout
        result_stderr = process.stderr.read()
        for line in trailing_stdout.splitlines():
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError:
                raise RuntimeError(
                    f"stdout line is not JSON-RPC: {redact_secrets(line[:300], sensitive_entries)!r}"
                ) from None
    except (BrokenPipeError, OSError, RuntimeError) as exc:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        print(str(exc), file=sys.stderr)
        if process is not None and process.stderr is not None:
            print(redact_secrets(process.stderr.read()[-4000:], sensitive_entries), file=sys.stderr)
        return 1
    finally:
        if selector is not None:
            selector.close()
        if args.mock_agentmail:
            subprocess.run(["docker", "rm", "-f", mock_name], capture_output=True)
            subprocess.run(["docker", "network", "rm", network], capture_output=True)
        if tempdir is not None:
            tempdir.cleanup()
    if process.returncode:
        print(f"container exited {process.returncode}; stderr follows:", file=sys.stderr)
        print(redact_secrets(result_stderr[-4000:], sensitive_entries), file=sys.stderr)
        return 1
    by_id = {response.get("id"): response for response in responses if "id" in response}
    if 1 not in by_id or "result" not in by_id[1]:
        print("MCP initialize response missing or invalid", file=sys.stderr)
        return 1
    tools = by_id.get(2, {}).get("result", {}).get("tools")
    if not isinstance(tools, list) or not tools:
        print("tools/list returned no tools", file=sys.stderr)
        return 1
    names = {tool.get("name") for tool in tools if isinstance(tool, dict)}
    missing = sorted(set(args.expected_tool) - names)
    if missing:
        print(f"tools/list missing expected tools: {missing}", file=sys.stderr)
        return 1
    if args.safe_tool and by_id.get(3, {}).get("result", {}).get("isError"):
        print(f"MCP safe tool returned an error: {args.safe_tool}", file=sys.stderr)
        return 1
    if args.safe_tool == "mail_get_status":
        content = by_id[3]["result"].get("content", [])
        tool_text = next(
            (item.get("text") for item in content if isinstance(item, dict) and item.get("type") == "text"),
            None,
        )
        try:
            tool_result = json.loads(tool_text) if isinstance(tool_text, str) else {}
        except json.JSONDecodeError:
            tool_result = {}
        if tool_result.get("status") != "online":
            print("MCP mail_get_status did not report the mock service as online", file=sys.stderr)
            return 1
    for item in sensitive_entries:
        name, _, value = item.partition("=")
        locations = [
            location
            for location, output in (("stdout", result_stdout), ("stderr", result_stderr))
            if value and value in output
        ]
        if locations:
            source = result_stderr[-1200:] if "stderr" in locations else result_stdout[-1200:]
            excerpt = redact_secrets(source, args.secret_env)
            print(
                f"configured value for {name} leaked to MCP {', '.join(locations)}; "
                f"redacted excerpt follows:\n{excerpt}",
                file=sys.stderr,
            )
            return 1
    calls = " + " + args.safe_tool if args.safe_tool else ""
    print(f"stdio MCP conformance passed: initialize + tools/list{calls} ({len(tools)} tools)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
