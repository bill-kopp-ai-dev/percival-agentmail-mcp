# syntax=docker/dockerfile:1.7
# =====================================================================
#  Percival AgentMail MCP — runtime image.
#
#  Multi-stage build: a uv-powered builder stage resolves the project
#  lockfile and installs the package in non-editable mode into a
#  virtualenv, which is then copied into a slim, non-root Python
#  runtime. The resulting image speaks stdio MCP over stdin/stdout and
#  exposes no TCP ports.
#
#  Build arguments:
#    VERSION        — SemVer from pyproject.toml. Default 0.0.0.
#                     Stamped on org.opencontainers.image.version.
#    GIT_SHA        — short commit SHA for traceability. Default
#                     "unknown". Stamped on image.revision.
#    PYTHON_VERSION — Python minor version. Default 3.12 (matches CI).
#    UV_VERSION     — pinned uv release. Default 0.5.11.
# =====================================================================

ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.5.11

# ---------------------------------------------------------------------
#  Stage 1 — builder (uv + Bookworm toolchain)
# ---------------------------------------------------------------------
# NOTE: WORKDIR is set to /app (the eventual runtime path) so that
# uv writes the virtualenv and console_script shebangs to /app/.venv
# from the start. Copying the venv verbatim into the runtime stage
# therefore preserves the absolute paths the scripts depend on.
FROM ghcr.io/astral-sh/uv:${UV_VERSION}-python${PYTHON_VERSION}-bookworm-slim@sha256:cc9311ae7d42ccb51f6ac10c8ab8526de8a3f484b36349fd87af8e5ced7079c0 AS builder

ARG VERSION=0.0.0
ARG GIT_SHA=unknown

WORKDIR /app

# Lock uv behavior for reproducibility inside the builder.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Copy the lockfile, project metadata and README first so the
# dependency layer caches independently of the source tree.
COPY pyproject.toml uv.lock README.md ./

# Install dependencies only — the project itself will be installed
# in a second pass after the source is in place.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project --locked

# Bring in the source, then install the project itself in
# non-editable mode so its code lives inside the venv site-packages
# (no source mount needed at runtime).
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-editable --locked

# ---------------------------------------------------------------------
#  Stage 2 — runtime (slim Python, non-root, stdio MCP)
# ---------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe AS runtime

ARG VERSION=0.0.0
ARG GIT_SHA=unknown

# OCI image labels — drive discovery from registries, scanners and
# Docker Desktop. Authors credit the current copyright holder while
# preserving the historical team attribution.
LABEL org.opencontainers.image.title="Percival AgentMail MCP" \
      org.opencontainers.image.description="Percival AgentMail MCP server — the Nanobot agent's own email service" \
      org.opencontainers.image.source="https://github.com/bill-kopp-ai-dev/percival-agentmail-mcp" \
      org.opencontainers.image.documentation="https://github.com/bill-kopp-ai-dev/percival-agentmail-mcp/blob/main/README.md" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.authors="Positronic Bean Labs (historically: percival.OS Team)" \
      org.opencontainers.image.vendor="Positronic Bean Labs" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${GIT_SHA}"

ARG DEBIAN_SNAPSHOT=20261009T000000Z
RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s trixie main\n' "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list \
    && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s trixie-security main\n' "$DEBIAN_SNAPSHOT" >> /etc/apt/sources.list \
    && rm -f /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Non-root user. Fixed UID/GID (1000/1000) so the image is portable
# across CI runners and developer hosts. No password, no shell.
RUN groupadd --system --gid 1000 app && \
    useradd --system --uid 1000 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

# Copy the prebuilt virtualenv (deps + project + console_scripts) and
# the project metadata for offline introspection. The venv already
# lives under /app/.venv, so the absolute shebang paths inside it
# remain valid after the copy.
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/pyproject.toml /app/pyproject.toml
COPY --from=builder --chown=app:app /app/README.md /app/README.md

# Runtime defaults (override at run-time via -e or env_file). PATH
# puts the venv first so the entry point resolves correctly.
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    HOME=/app \
    AGENTMAIL_TIMEOUT=30 \
    AGENTMAIL_MAX_RESULTS=25

USER app

# stdio MCP transport — no EXPOSE, no HEALTHCHECK. The recommended
# liveness probe is `docker run --rm -i <image> --version` which
# exits 0 with the package version once the venv is importable.
ENTRYPOINT ["percival-agentmail-mcp"]
CMD []
