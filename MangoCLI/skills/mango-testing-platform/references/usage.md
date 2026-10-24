# Mango CLI usage contract

## Discovery

```bash
mango capability list
mango capability list --domain api
mango capability list --status pending_api
mango <domain> --help
mango <domain> <command> --help
```

The legacy capability domains are `system`, `project`, `file`, `data-method`, `todo`, `api`, `ui`, `data-factory`, `functional-test`, `pytest`, `result`, `report`, `task`, and `ai`. Performance testing is a separate `mango perf` command group. Gray configuration is intentionally not exposed through the CLI.

The REST API accepts the same JWT used by the web page, sent directly in `Authorization`. It does not accept the old MCP `mango_...` APIKey. Use an authorized profile, `MANGO_TOKEN`, or import a page JWT through `mango auth import --token-stdin`; never pass a token as a command-line argument. `mango auth login --no-open` prints an authorization URL without launching a browser.

Every first-stage command is the old MCP Tool name converted from snake_case to kebab-case. For example, `search_api_infos` becomes `mango api search-api-infos`. This naming is for migration traceability only; request fields are those of the mapped page REST API.

`mango perf` is not part of that legacy naming map. Use `mango perf --help` for its commands. Record detail commands require `--id` with a positive integer. Start with `list-executors` and `capacity`, then call `preflight-scenario` with the intended environment and executor fingerprints before `execute-scenario`. The latter repeats preflight and refuses to start when `can_run` is not true. For plans, configure explicit executors for every enabled item before `execute-plan`; the service performs final capacity reservation. Use `get-run` for status, `get-run-metrics` for cursor-based live metrics, and `get-run-report` for the final aggregate. The CLI does not run k6 locally.

## Input

- GET commands convert all input fields to URL query parameters.
- POST, PUT, and DELETE commands encode input as a JSON object.
- `-p key=value` attempts to parse each value as JSON, so numbers, booleans, arrays, objects, and `null` retain their types. Unquoted text remains a string.
- `--input path.json`, `--input -`, and `--stdin` accept a JSON object. Repeated `-p` fields override fields from that object.
- Multipart upload commands require `--file`; additional form fields use `-p`.

Examples:

```bash
mango api search-api-infos -p project_product=1 -p page=1 -p pageSize=20
mango api create-api-info --input api-info.json
printf '%s' '{"id":1001,"name":"new name"}' | mango api update-api-info --stdin
```

## Output and failures

JSON is the default. `--output raw` returns the server body unchanged. The normalized envelope contains `success`, `message`, optional `data`, `warnings`, `error_code`, and `request_id`.

Exit codes are: `0` success, `2` CLI/input error, `3` unauthenticated, `4` forbidden, `5` platform business failure, `6` HTTP/network failure, and `7` timeout.

`pending_api` capabilities are intentionally not executable. Use the emitted reason as the required backend contract gap; do not substitute a superficially similar endpoint.
