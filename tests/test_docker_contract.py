"""Static contract checks for the AgentMail MCP image.

Two owners, one init. The launcher owns the init layer (``docker run
--init`` / Compose ``init: true``) and the image embeds none: a tini in
the image would stack a second supervision layer on top of the
launcher's own init and mask which process is actually responsible for
SIGTERM.

These tests read the deployment files as text, so they need no Docker
daemon and catch the drift before it reaches CI.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = REPO_ROOT / "Dockerfile"
COMPOSE = REPO_ROOT / "docker-compose.yml"


def _instructions(path: Path) -> str:
    """Return the file's instructions, without the comment lines."""
    text = path.read_text(encoding="utf-8")
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def _service_block(contents: str, service_name: str) -> str:
    """Return one top-level Compose service block for focused checks."""
    start = re.search(rf"^  {re.escape(service_name)}:\s*$", contents, re.MULTILINE)
    assert start, f"Compose service {service_name!r} must exist"
    next_service = re.search(r"^  [a-zA-Z0-9_-]+:\s*$", contents[start.end() :], re.MULTILINE)
    end = start.end() + next_service.start() if next_service else len(contents)
    return contents[start.start() : end]


def test_dockerfile_embeds_no_init_so_the_launcher_owns_it() -> None:
    """The image must not embed an init of its own."""
    instructions = _instructions(DOCKERFILE)
    assert "tini" not in instructions, (
        "the image must not embed an init; the launcher provides it (docker run --init / compose init: true)"
    )
    entrypoint = re.search(r"^ENTRYPOINT\s+\[(.+)\]$", instructions, re.MULTILINE)
    assert entrypoint, "Dockerfile must declare an exec-form ENTRYPOINT"
    assert "tini" not in entrypoint.group(1)


def test_compose_declares_the_single_init() -> None:
    """The launcher side of the contract: exactly one init, owned by Compose."""
    service = _service_block(COMPOSE.read_text(encoding="utf-8"), "server")
    assert "init: true" in service, (
        "the compose service must declare init: true so the launcher owns "
        "the init layer and the container stops cleanly on SIGTERM"
    )


def test_compose_stop_grace_exceeds_server_shutdown_bound() -> None:
    service = _service_block(COMPOSE.read_text(encoding="utf-8"), "server")
    assert "stop_grace_period: 10s" in service


def test_dockerfile_runs_as_non_root() -> None:
    """The image must not start as root under a plain ``docker run``."""
    matches = re.findall(r"^USER\s+(\S+)", _instructions(DOCKERFILE), re.MULTILINE)
    assert matches, "Dockerfile must declare a USER directive"
    assert matches[-1] == "app", f"the runtime stage must run as the non-root 'app' user, got USER {matches[-1]}"
    uid = re.search(r"--uid\s+(\d+)", _instructions(DOCKERFILE))
    assert uid, "the non-root user must be created with an explicit --uid"
    assert int(uid.group(1)) >= 1000, f"the image UID must be >= 1000 to avoid host-UID collisions, got {uid.group(1)}"


def test_dockerfile_reinstalls_project_from_copied_source() -> None:
    instructions = _instructions(DOCKERFILE)
    assert "uv sync --no-dev --no-editable --locked --reinstall-package percival-agentmail-mcp" in instructions


def test_stdio_service_has_no_http_surface() -> None:
    """stdio transport: stdin in, JSON-RPC out — no ports, no healthcheck."""
    service = _service_block(COMPOSE.read_text(encoding="utf-8"), "server")
    assert "stdin_open: true" in service
    assert "tty: false" in service
    assert "ports:" not in service
    assert "healthcheck:" not in service
