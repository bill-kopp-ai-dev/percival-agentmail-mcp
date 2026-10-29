# Percival AgentMail MCP

Project-scoped instructions for the AgentMail MCP server. Read `README.md`,
`.env.example`, and `docs/` before changing its API or runtime configuration.

## Company approval

This project belongs to Positronic Bean Labs (PBLabs), owned by Bill Kopp.
Bill is the sole final decision-maker for decisions requiring owner or company
approval. Technical review, implementation, and routine operations may be
delegated without transferring final approval authority. This does not alter
runtime access or authorize publication, deployment, or production changes.

## Docker and operations

- This server is stdio MCP: stdout is JSON-RPC only, with no TTY, host port or
  HTTP healthcheck. The manager supplies the single init.
- API credentials and inbox identifiers are secrets. Never print them, put
  them in image layers/build args, or include values in inventory or reports.
  Prefer a read-only mounted credential file where supported.
- Percival's broker owns production containers and alone receives Docker access.
  Compose is a local development fixture, not a second production manager.
- Route changes through the owner: Percival WebUI/API or Positronic `/mcp`
  TUI/CLI. Do not edit manager state by hand. Reread revisions and immutable
  image IDs; use fixtures for failures and rollback.
- Live AgentMail calls can send, delete or modify email and may contact a paid
  service. Keep verification offline unless the operator explicitly approves
  a specific live smoke.

## Verification

- CI test suite: `uv run pytest --cov`.
- CI lint: `uv run ruff check .` and `uv run ruff format --check .`.
- Docker CI builds the image and checks version, missing-env handling and
  runtime metadata. Never use a live API key for a Docker smoke.
