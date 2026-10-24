import test from "node:test";
import assert from "node:assert/strict";
import { PassThrough, Writable } from "node:stream";
import { run } from "../src/cli.js";
import { perfCommands } from "../src/perf.js";
import { documentedPerfCommandCount, perfCommandContract } from "../src/contracts.js";

const claims = Buffer.from(JSON.stringify({ id: 7, exp: 4102444800 })).toString("base64url");
const token = `header.${claims}.signature`;

function capture() {
  let value = "";
  return {
    stream: new Writable({ write(chunk, _encoding, callback) { value += chunk; callback(); } }),
    value: () => value,
  };
}

function response(data) {
  return new Response(JSON.stringify({ code: 200, msg: "ok", data }), { status: 200 });
}

async function invoke(args, fetchImpl) {
  const stdout = capture();
  const stderr = capture();
  const execute = () => run(["node", "mango", "--server", "https://example.com", "perf", ...args], {
    stdin: new PassThrough(), stdout: stdout.stream, stderr: stderr.stream,
    env: { MANGO_TOKEN: token }, fetchImpl,
  });
  return { execute, stdout, stderr };
}

test("performance commands are distinct from legacy MCP migration catalog", () => {
  assert.equal(perfCommands.length, 14);
  assert.equal(new Set(perfCommands.map((item) => item.command)).size, perfCommands.length);
  assert.equal(documentedPerfCommandCount, perfCommands.length);
  assert.ok(perfCommands.every((item) => perfCommandContract(item.command)));
});

test("performance command exposes human and machine readable parameter contracts without login", async () => {
  const describe = await invoke(["describe", "execute-scenario"], async () => { throw new Error("unexpected request"); });
  await describe.execute();
  const contract = JSON.parse(describe.stdout.value()).data;
  assert.equal(contract.method, "POST");
  assert.equal(contract.path, "/api/perf/scenario/{id}/execute");
  assert.equal(contract.parameters.find((item) => item.name === "selected_executor_fingerprints").required, true);
  assert.match(contract.parameters.find((item) => item.name === "production_load_confirmed").description, /test_env=2/);

  const help = await invoke(["get-run-metrics", "--help"], async () => { throw new Error("unexpected request"); });
  await help.execute();
  assert.match(help.stdout.value(), /cursor/);
  assert.match(help.stdout.value(), /不透明/);
  assert.match(help.stdout.value(), /mango perf describe get-run-metrics/);
});

test("performance detail resolves numeric ID and keeps query fields", async () => {
  const seen = [];
  const { execute, stdout } = await invoke(["get-run-metrics", "--id", "9", "-p", "cursor=5"], async (url, init) => {
    seen.push({ url: String(url), method: init.method });
    return response({ points: [] });
  });
  await execute();
  assert.deepEqual(seen, [{ url: "https://example.com/api/perf/run/9/metrics?cursor=5", method: "GET" }]);
  assert.deepEqual(JSON.parse(stdout.value()).data, { points: [] });
});

test("performance path rejects invalid ID before network access", async () => {
  let calls = 0;
  const { execute } = await invoke(["get-run", "--id", "../other"], async () => {
    calls += 1;
    return response({});
  });
  await assert.rejects(execute(), (error) => error.exitCode === 2);
  assert.equal(calls, 0);
});

test("scenario configuration uses versioned PUT body without changing its shape", async () => {
  let observed;
  const { execute } = await invoke([
    "update-scenario", "--id", "3", "-p", "version=4",
    "-p", 'load_config={"name":"基础负载","duration_seconds":20,"target_users":2}',
  ], async (url, init) => {
    observed = { url: String(url), method: init.method, body: JSON.parse(init.body) };
    return response({ id: 3, version: 5 });
  });
  await execute();
  assert.equal(observed.url, "https://example.com/api/perf/scenario/3/configuration");
  assert.equal(observed.method, "PUT");
  assert.equal(observed.body.version, 4);
  assert.deepEqual(observed.body.load_config, {
    name: "基础负载", duration_seconds: 20, target_users: 2,
  });
});

test("scenario execution requires selected executors and does not start when preflight fails", async () => {
  const seen = [];
  const { execute, stdout } = await invoke([
    "execute-scenario", "--id", "3", "-p", "test_env=1",
    "-p", 'selected_executor_fingerprints=["user:1"]',
  ], async (url, init) => {
    seen.push({ url: String(url), body: JSON.parse(init.body) });
    return response({ can_run: false, required_per_node: 100 });
  });
  await assert.rejects(execute(), (error) => error.exitCode === 5);
  assert.equal(seen.length, 1);
  assert.equal(seen[0].url, "https://example.com/api/perf/scenario/3/preflight");
  assert.equal(JSON.parse(stdout.value()).data.can_run, false);
});

test("scenario execution starts only after successful capacity preflight", async () => {
  const seen = [];
  const { execute, stdout } = await invoke([
    "execute-scenario", "--id", "3", "-p", "test_env=1",
    "-p", 'selected_executor_fingerprints=["user:1","user:2"]',
  ], async (url, init) => {
    seen.push({ url: String(url), body: JSON.parse(init.body) });
    return response(seen.length === 1 ? { can_run: true } : { run_id: 42, status: "starting" });
  });
  await execute();
  assert.deepEqual(seen.map((item) => item.url), [
    "https://example.com/api/perf/scenario/3/preflight",
    "https://example.com/api/perf/scenario/3/execute",
  ]);
  assert.deepEqual(seen[0].body.selected_executor_fingerprints, ["user:1", "user:2"]);
  assert.equal(JSON.parse(stdout.value()).data.run_id, 42);
});

test("production load needs explicit confirmation before preflight", async () => {
  let calls = 0;
  const { execute } = await invoke([
    "execute-scenario", "--id", "3", "-p", "test_env=2",
    "-p", 'selected_executor_fingerprints=["user:1"]',
  ], async () => { calls += 1; return response({}); });
  await assert.rejects(execute(), (error) => error.exitCode === 2);
  assert.equal(calls, 0);
});

test("run report aggregates read-only result sections", async () => {
  const seen = [];
  const { execute, stdout } = await invoke(["get-run-report", "--id", "42"], async (url) => {
    const value = String(url);
    seen.push(value);
    return response({ source: value.split("/").at(-1) });
  });
  await execute();
  const report = JSON.parse(stdout.value()).data;
  assert.equal(seen.length, 6);
  assert.equal(report.run.source, "42");
  assert.equal(report.requests.source, "requests");
  assert.equal(report.nodes.source, "nodes");
});

test("aggregated report supports raw output", async () => {
  const stdout = capture();
  await run([
    "node", "mango", "--server", "https://example.com", "--output", "raw",
    "perf", "get-run-report", "--id", "42",
  ], {
    stdin: new PassThrough(), stdout: stdout.stream, stderr: capture().stream,
    env: { MANGO_TOKEN: token }, fetchImpl: async () => response({ value: 1 }),
  });
  const output = JSON.parse(stdout.value());
  assert.equal(output.run.value, 1);
  assert.equal(output.thresholds.value, 1);
});
