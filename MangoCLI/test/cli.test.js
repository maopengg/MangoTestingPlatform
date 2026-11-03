import test from "node:test";
import assert from "node:assert/strict";
import { PassThrough, Writable } from "node:stream";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { run } from "../src/cli.js";

function capture() {
  let value = "";
  return {
    stream: new Writable({ write(chunk, _encoding, callback) { value += chunk; callback(); } }),
    value: () => value,
  };
}

test("REST command sends page API query and authorization", async () => {
  const stdout = capture();
  const stderr = capture();
  let observed;
  const fetchImpl = async (url, init) => {
    observed = { url: String(url), init };
    return new Response('{"code":200,"msg":"ok","data":{"id":1}}', {
      status: 200,
      headers: { "Content-Type": "application/json", "X-Request-ID": "req-1" },
    });
  };
  const claims = Buffer.from(JSON.stringify({ id: 7, exp: 4102444800 })).toString("base64url");
  const token = `header.${claims}.signature`;
  await run([
    "node", "mango", "--server", "https://example.com", "api", "search-api-infos",
    "-p", "page=2", "-p", "project_product=1",
  ], {
    stdin: new PassThrough(), stdout: stdout.stream, stderr: stderr.stream,
    env: { MANGO_TOKEN: token }, fetchImpl,
  });
  assert.equal(observed.url, "https://example.com/api/api/info?page=2&project_product=1");
  assert.equal(observed.init.method, "GET");
  assert.equal(observed.init.headers.Authorization, token);
  const output = JSON.parse(stdout.value());
  assert.equal(output.success, true);
  assert.equal(output.request_id, "req-1");
});

test("an invalid server token is cleared, reauthorized, and the command is retried once", async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), "mango-cli-reauth-"));
  const configPath = path.join(directory, "config.json");
  const claims = Buffer.from(JSON.stringify({ id: 7, exp: 4102444800 })).toString("base64url");
  const oldToken = `header.${claims}.old`;
  const newToken = `header.${claims}.new`;
  await writeFile(configPath, JSON.stringify({
    current: "dev",
    profiles: { dev: { server: "https://example.com", web_url: "https://example.com", token: oldToken } },
  }));
  let businessRequests = 0;
  const fetchImpl = async (url, init = {}) => {
    const value = String(url);
    if (value.includes("/api/cli/auth/version")) {
      return new Response('{"code":200,"msg":"ok","data":{"version":"7.2.3"}}', { status: 200 });
    }
    if (value.endsWith("/api/cli/auth/token")) {
      return new Response(JSON.stringify({
        code: 200, msg: "ok", data: { token: newToken, user_id: 7, username: "tester" },
      }), { status: 200 });
    }
    businessRequests += 1;
    if (businessRequests === 1) {
      return new Response('{"code":"302","msg":"token 无效，请检查后重试","data":null}', { status: 401 });
    }
    assert.equal(init.headers.Authorization, newToken);
    return new Response('{"code":200,"msg":"ok","data":{"retried":true}}', { status: 200 });
  };
  const stdin = new PassThrough();
  stdin.isTTY = true;
  const stdout = capture();
  await run([
    "node", "mango", "--config", configPath, "api", "search-api-infos",
  ], {
    stdin,
    stdout: stdout.stream,
    stderr: capture().stream,
    env: {},
    fetchImpl,
    openBrowser: (authorizationUrl) => {
      const params = new URLSearchParams(new URL(authorizationUrl).hash.split("?", 2)[1]);
      const callback = new URL(params.get("redirect_uri"));
      callback.searchParams.set("code", "new-code");
      callback.searchParams.set("state", params.get("state"));
      fetch(callback).catch(() => {});
    },
  });
  assert.equal(businessRequests, 2);
  assert.equal(JSON.parse(stdout.value()).data.retried, true);
  const saved = JSON.parse(await readFile(configPath, "utf8"));
  assert.equal(saved.profiles.dev.token, newToken);
});

test("pending API capability is not executable", async () => {
  const stdout = capture();
  const stderr = capture();
  await assert.rejects(
    run(["node", "mango", "api", "get-api-case-schema"], {
      stdin: new PassThrough(), stdout: stdout.stream, stderr: stderr.stream, env: {},
    }),
    (error) => error.exitCode === 2,
  );
  assert.match(stderr.value(), /unknown command/);
});

test("capability list exposes pending reasons", async () => {
  const stdout = capture();
  await run(["node", "mango", "capability", "list", "--status", "pending_api"], {
    stdin: new PassThrough(), stdout: stdout.stream, stderr: capture().stream, env: {},
  });
  const output = JSON.parse(stdout.value());
  assert.equal(output.data.count, 59);
  assert.ok(output.data.items.every((item) => item.reason));
});

test("config set assigns --server to the subcommand profile", async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), "mango-cli-config-"));
  const configPath = path.join(directory, "config.json");
  await run([
    "node", "mango", "--config", configPath,
    "config", "set", "--name", "dev", "--server", "https://example.com",
  ], { stdin: new PassThrough(), stdout: capture().stream, stderr: capture().stream, env: {} });
  const config = JSON.parse(await readFile(configPath, "utf8"));
  assert.equal(config.current, "dev");
  assert.equal(config.profiles.dev.server, "https://example.com");
});
