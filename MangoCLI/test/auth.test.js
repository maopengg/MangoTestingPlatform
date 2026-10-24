import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { PassThrough, Writable } from "node:stream";
import { run } from "../src/cli.js";

function sink() {
  let value = "";
  return {
    stream: new Writable({ write(chunk, _encoding, callback) { value += chunk; callback(); } }),
    value: () => value,
  };
}

test("auth import stores the page JWT in selected profile", async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), "mango-cli-auth-"));
  const configPath = path.join(directory, "config.json");
  const claims = Buffer.from(JSON.stringify({ id: 7, username: "tester", exp: 4102444800 })).toString("base64url");
  const token = `header.${claims}.signature`;
  const stdin = new PassThrough();
  stdin.end(`${token}\n`);
  const stdout = sink();
  await run([
    "node", "mango", "--config", configPath, "--server", "https://example.com",
    "auth", "import", "--token-stdin",
  ], { stdin, stdout: stdout.stream, stderr: sink().stream, env: {} });

  const config = JSON.parse(await readFile(configPath, "utf8"));
  assert.equal(config.profiles.default.token, token);
  assert.equal(JSON.parse(stdout.value()).user_id, 7);
});
