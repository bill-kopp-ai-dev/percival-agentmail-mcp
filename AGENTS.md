# Percival AgentMail MCP

Project-scoped instructions for the AgentMail MCP server. Read `README.md`,
`.env.example`, and `docs/` before changing its API or runtime configuration.

## Owner and decision authority

Positronic Bean Labs (PBLabs) is owned by Bill Kopp (`bill.kopp.dev@gmail.com`;
`labs.positronicbean.com`). Bill is the sole owner, operator, implementer, decision
maker, and signatory for this application and its IaC. There is no separate
company approver, reviewer, or acceptance chain.

For work Bill requests, proceed without seeking duplicate approvals or
acceptances. One clear authorization from Bill covers the requested scope.
Clarify only material ambiguity or an unbounded side effect; a general ownership
statement does not authorize work outside the request.

## Runtime and operations

- This server is stdio MCP: stdout is JSON-RPC only, with no TTY, host port or
  HTTP healthcheck. The manager supplies the single init.
- API credentials and inbox identifiers are secrets. Never print them, put
  them in image layers/build args, or include values in inventory or reports.
  Prefer a read-only mounted credential file where supported.
- Percival's broker owns production containers and alone receives Docker access.
  Compose is a local development fixture, not a second production manager.
- Route changes through the owner: Percival WebUI/API or Positronic `/mcp`
  TUI/CLI. Do not edit manager state by hand. Reread revisions and immutable
  image IDs when changing managed state; use fixtures for failures and rollback.
- Live AgentMail calls can send, delete or modify email and may contact a paid
  service. Keep verification offline unless Bill explicitly authorizes the
  specific live operation. Do not infer permission to send, delete, publish,
  deploy, or change production from a general request to implement or test.

## Proportionate verification

- For runtime changes, run the relevant tests and the CI checks:
  `uv run pytest --cov`, `uv run ruff check .`, and
  `uv run ruff format --check .`. For documentation-only changes, use focused
  checks such as `git diff --check`.
- Verify each changed source or artifact once with the relevant check. Do not
  repeat a passing check or require separate reports/acceptances for the same
  unchanged artifact. Record concise results or link to the existing CI evidence.
- Keep verification offline by default. Docker CI builds the image and checks
  version, missing-environment handling, MCP stdio, and runtime metadata; never
  use a live API key for a Docker smoke.
