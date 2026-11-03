import assert from "node:assert/strict";
import { execFile, spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtemp, readFile } from "node:fs/promises";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";

const exec = promisify(execFile);

function execWithInput(file, args, input) {
  return new Promise((resolve, reject) => {
    const child = spawn(file, args, { stdio: ["pipe", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve({ stdout, stderr });
      else reject(Object.assign(new Error(stderr || `command exited with ${code}`), { code, stdout, stderr }));
    });
    child.stdin.end(input);
  });
}
const archive = path.resolve(process.argv[2] || "mango-testing-platform-cli-7.2.3.tgz");
await readFile(archive);
const prefix = await mkdtemp(path.join(os.tmpdir(), "mango-cli-package-smoke-"));
await exec("npm", ["install", "--global", "--prefix", prefix, archive]);
const mango = process.platform === "win32"
  ? path.join(prefix, "mango.cmd")
  : path.join(prefix, "bin", "mango");

const version = JSON.parse((await exec(mango, ["version"])).stdout);
assert.equal(version.version, "7.2.3");

const capabilities = JSON.parse((await exec(mango, ["capability", "list", "--status", "complete"])).stdout);
assert.equal(capabilities.data.count, 259);

const claims = Buffer.from(JSON.stringify({ id: 7, username: "tester", exp: 4102444800 })).toString("base64url");
const token = `header.${claims}.signature`;
const configPath = path.join(prefix, "config.json");
await execWithInput(
  mango,
  ["--config", configPath, "--server", "http://127.0.0.1", "auth", "import", "--token-stdin"],
  `${token}\n`,
);
const status = JSON.parse((await exec(mango, ["--config", configPath, "auth", "status"])).stdout);
assert.equal(status.authenticated, true);
assert.equal(status.user_id, 7);

const browserConfigPath = path.join(prefix, "browser-config.json");
let browserTokenRequest;
const browserTokenServer = http.createServer(async (request, response) => {
  if (request.method === "GET" && request.url === "/api/cli/auth/version?version=7.2.3") {
    response.writeHead(200, { "Content-Type": "application/json", "Connection": "close" });
    response.end(JSON.stringify({ code: 200, msg: "ok", data: { version: "7.2.3" } }));
    return;
  }
  let raw = "";
  for await (const chunk of request) raw += chunk;
  browserTokenRequest = JSON.parse(raw);
  response.writeHead(200, { "Content-Type": "application/json", "Connection": "close" });
  response.end(JSON.stringify({
    code: 200,
    msg: "ok",
    data: { token, user_id: 7, username: "tester" },
  }));
});
await new Promise((resolve) => browserTokenServer.listen(0, "127.0.0.1", resolve));
try {
  const browserAddress = browserTokenServer.address();
  const child = spawn(mango, [
    "--config", browserConfigPath,
    "--server", `http://127.0.0.1:${browserAddress.port}`,
    "--web-url", "https://example.com",
    "auth", "login", "--no-open", "--wait", "5s",
  ], { stdio: ["ignore", "pipe", "pipe"] });
  const childExit = new Promise((resolve) => child.once("close", resolve));
  let browserStdout = "";
  let browserStderr = "";
  child.stderr.on("data", (chunk) => { browserStderr += chunk; });
  const authorizationUrl = await new Promise((resolve, reject) => {
    child.stdout.on("data", (chunk) => {
      browserStdout += chunk;
      const newline = browserStdout.indexOf("\n");
      if (newline >= 0) resolve(browserStdout.slice(0, newline));
    });
    child.once("error", reject);
  });
  const hashQuery = new URL(authorizationUrl).hash.split("?", 2)[1];
  const params = new URLSearchParams(hashQuery);
  const callback = new URL(params.get("redirect_uri"));
  callback.searchParams.set("code", "package-one-time-code");
  callback.searchParams.set("state", params.get("state"));
  await fetch(callback);
  const browserExit = await childExit;
  assert.equal(browserExit, 0, browserStderr);
  assert.equal(browserTokenRequest.code, "package-one-time-code");
  const expectedChallenge = createHash("sha256")
    .update(browserTokenRequest.code_verifier)
    .digest("base64url");
  assert.equal(params.get("code_challenge"), expectedChallenge);
  assert.equal(params.get("version"), "7.2.3");
  assert.equal(params.has("token"), false);
  const browserConfig = JSON.parse(await readFile(browserConfigPath, "utf8"));
  assert.equal(browserConfig.profiles.default.token, token);
}
finally {
  browserTokenServer.closeAllConnections();
  await new Promise((resolve) => browserTokenServer.close(resolve));
}

let observed;
const server = http.createServer((request, response) => {
  observed = { url: request.url, authorization: request.headers.authorization };
  response.writeHead(200, {
    "Connection": "close",
    "Content-Type": "application/json",
    "X-Request-ID": "package-smoke",
  });
  response.end(JSON.stringify({ code: 200, msg: "ok", data: [{ id: 1 }] }));
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
try {
  const address = server.address();
  const result = JSON.parse((await exec(mango, [
    "--config", configPath,
    "--server", `http://127.0.0.1:${address.port}`,
    "api", "search-api-infos", "-p", "page=2", "-p", "project_product=1",
  ])).stdout);
  assert.equal(result.success, true);
  assert.equal(result.request_id, "package-smoke");
  assert.equal(observed.url, "/api/api/info?page=2&project_product=1");
  assert.equal(observed.authorization, token);
} finally {
  server.closeAllConnections();
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
}

let pendingExitCode;
try {
  await exec(mango, ["api", "get-api-case-schema"]);
} catch (error) {
  pendingExitCode = error.code;
}
assert.equal(pendingExitCode, 2);

process.stdout.write(`${JSON.stringify({
  success: true,
  archive,
  isolated_prefix: prefix,
  version: version.version,
  complete_capabilities: capabilities.data.count,
  page_jwt_forwarded: true,
  browser_pkce_login: true,
  pending_command_exit: pendingExitCode,
}, null, 2)}\n`);
