import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, readFile } from "node:fs/promises";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { browserLogin } from "../src/browser-auth.js";

function listen(server) {
  return new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
}

test("browser login completes PKCE loopback flow without exposing JWT in callback", async () => {
  const claims = Buffer.from(JSON.stringify({ id: 9, username: "cli-user", exp: 4102444800 })).toString("base64url");
  const token = `header.${claims}.signature`;
  let expectedChallenge;
  let tokenRequest;
  const platform = http.createServer(async (request, response) => {
    if (request.method === "GET" && request.url === "/api/cli/auth/version?version=7.2.2") {
      response.writeHead(200, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ code: 200, msg: "ok", data: { version: "7.2.2" } }));
      return;
    }
    let raw = "";
    for await (const chunk of request) raw += chunk;
    tokenRequest = JSON.parse(raw);
    const actual = createHash("sha256").update(tokenRequest.code_verifier).digest("base64url");
    assert.equal(actual, expectedChallenge);
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ code: 200, msg: "ok", data: { token, user_id: 9, username: "cli-user" } }));
  });
  await listen(platform);
  const directory = await mkdtemp(path.join(os.tmpdir(), "mango-browser-auth-"));
  const address = platform.address();
  const runtime = {
    server: `http://127.0.0.1:${address.port}`,
    webUrl: "https://example.com",
    configPath: path.join(directory, "config.json"),
    profileName: "test",
  };
  let authorizationUrl;
  try {
    const result = await browserLogin(runtime, {
      waitMs: 2000,
      openBrowser: (value) => {
        authorizationUrl = new URL(value.replace("/#/cli-auth?", "/cli-auth?"));
        expectedChallenge = authorizationUrl.searchParams.get("code_challenge");
        const callback = new URL(authorizationUrl.searchParams.get("redirect_uri"));
        callback.searchParams.set("code", "one-time-code");
        callback.searchParams.set("state", authorizationUrl.searchParams.get("state"));
        fetch(callback).catch(() => {});
      },
    });
    assert.equal(result.token, token);
    assert.equal(authorizationUrl.searchParams.get("version"), "7.2.2");
    assert.equal(authorizationUrl.searchParams.has("token"), false);
    assert.equal(new URL(tokenRequest.redirect_uri).searchParams.has("token"), false);
    const config = JSON.parse(await readFile(runtime.configPath, "utf8"));
    assert.equal(config.profiles.test.token, token);
  } finally {
    platform.closeAllConnections();
    await new Promise((resolve) => platform.close(resolve));
  }
});

test("browser login stops before opening a page when the CLI version is outdated", async () => {
  let opened = false;
  const fetchImpl = async () => new Response(JSON.stringify({
    code: 300,
    msg: "CLI 版本与服务器不一致，请升级到最新版本后重新登录",
    data: { latest_version: "7.2.2" },
  }), { status: 200, headers: { "Content-Type": "application/json" } });
  await assert.rejects(
    browserLogin({ server: "https://example.com" }, {
      fetchImpl,
      openBrowser: () => { opened = true; },
    }),
    (error) => error.exitCode === 8 && /7\.2\.2/.test(error.message),
  );
  assert.equal(opened, false);
});
