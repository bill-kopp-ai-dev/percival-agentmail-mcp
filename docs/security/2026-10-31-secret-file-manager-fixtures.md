# Secret-file manager fixtures — AgentMail Stage-2

**Scope:** isolated local fixtures with synthetic secret contents and a mock
AgentMail HTTP service. The candidate image was
`percival-agentmail-mcp:0.4.0-stage2-ebdd933`, image ID
`sha256:bfa3fb1f3147867d9d5fc269b0b66fdc4b17f0f7a865703c337c01b52ee9c2ce`.
No real inbox, secret, manager state, registry or published image was used.

## Positronic manager

- The replay harness is
  `/home/bill/.positronic/runtime/tmp/opencode/positronic-agentmail-secret-e2e.ts`.
  It created a temporary `ManagedServers` home, installed the local image ID only
  into that temporary fixture, and saved two existing host file references as
  read-only secret mounts.
- The manager generated `AGENTMAIL_API_KEY_FILE` and
  `AGENTMAIL_INBOX_ID_FILE`, started the container through
  `ManagedStdioTransport`, completed MCP `initialize` and `tools/list`, then
  called `mail_get_status` against an HTTP mock on a disposable Docker bridge.
- Status was `online`; the response contained neither synthetic secret value
  nor the inbox ID. Temporary manager files, mock container and local fixture
  files were removed at test completion.

## Percival manager and broker policy

- The replay harness is
  `/home/bill/.positronic/runtime/tmp/opencode/nanobot-catalog-secret-e2e.py`.
- Invoked `DockerMcpService.install_catalog_app` against a temporary schema-2
  config with a synthetic app profile and the two file-secret targets. A
  fixture broker supplied acquisition/health responses and used the real
  `MountPolicy.docker_args` to produce the read-only bind arguments; the app
  container was launched by the conformance helper with a mock provider.
- The resulting mount/environment configuration was passed to the Docker
  conformance helper. The local app container completed MCP `initialize`,
  `tools/list` and `mail_get_status` against the helper's internal HTTP mock;
  output checks covered both synthetic secrets. Capabilities export omitted
  the host source paths.
- This exercises the manager service/profile resolver and broker mount-policy
  code with a fixture broker. It does **not** exercise the running Percival
  broker RPC process or mutate its manager state.

## Remaining gate

Neither fixture authorizes AgentMail installation. The Index has no
installable AgentMail release/digest, and the profile remains `draft`. A
Percival broker-process E2E plus operational file-permission verification
remain required before enabling managed installation; the Positronic fixture
does not claim a deployed manager configuration.
