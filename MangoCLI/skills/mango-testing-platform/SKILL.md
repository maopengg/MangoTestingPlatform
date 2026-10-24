---
name: mango-testing-platform
description: Operate the Mango testing platform through its Node.js CLI and existing REST APIs for API, UI, performance, data-factory, functional-test, Pytest, reports, scheduled tasks, projects, and system data. Use when an agent must query or change Mango platform resources without using the platform MCP service. Gray configuration is intentionally not exposed by this CLI.
---

# Mango Testing Platform

Use `mango` as the only platform operation adapter. Do not call the platform MCP endpoint, copy MCP-side ORM logic, or access the database to work around a missing command.

Gray configuration is outside this CLI's supported scope. Do not call `/api/gray/*` directly as a workaround.

## Workflow

1. Confirm `mango version` works and that `MANGO_SERVER` or a profile is configured. Use an already authorized profile or token. If authorization is missing, `mango auth login --no-open` prints a URL for the user to open; do not launch a browser from the agent.
2. Locate migrated capabilities with `mango capability list --domain <domain>`. Performance testing uses the separate `mango perf --help` command group, not the legacy MCP migration catalog.
3. Read the command help. Supply simple page API fields with repeated `-p key=value`; supply complex JSON objects with `--input` or `--stdin`.
4. Execute the smallest query needed before a write so target IDs and current state are evidenced.
5. Treat `success: true` and exit code 0 as success. Preserve the response `request_id` when reporting an incident.

Capability input follows the corresponding page REST API contract, not the removed MCP Tool schema. Read [references/usage.md](references/usage.md) for input, status, and error conventions when forming a command.

If a capability is `pending_api`, stop that operation and report its catalog `reason`; backend API work is required. If it is `protocol_mcp`, it belongs to optional third-party MCP protocol testing and is outside the platform-MCP replacement path.

Do not assume that user authorization for a read also authorizes a mutation. For destructive or execution commands, keep the target narrow and follow any preview/confirmation API required by the capability.

For performance tests, read [references/usage.md](references/usage.md) before creating configurations or starting a run. A scenario run requires explicit executor fingerprints and a successful capacity preflight; a plan run requires an explicit stored executor policy. Production load requires an explicit risk confirmation. The CLI controls runs; k6 executes on the selected workers.
