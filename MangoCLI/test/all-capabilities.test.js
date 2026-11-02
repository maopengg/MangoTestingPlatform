import test from "node:test";
import assert from "node:assert/strict";
import { PassThrough, Writable } from "node:stream";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { catalog } from "../src/catalog.js";
import { run } from "../src/cli.js";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function sink() {
  return new Writable({ write(_chunk, _encoding, callback) { callback(); } });
}

test("every completed capability dispatches its declared REST method and path", async () => {
  const claims = Buffer.from(JSON.stringify({ id: 7, username: "tester", exp: 4102444800 })).toString("base64url");
  const token = `header.${claims}.signature`;
  const completed = catalog.filter((item) => item.status === "complete");
  assert.equal(completed.length, 251);

  for (const spec of completed) {
    let observed;
    const fetchImpl = async (url, init) => {
      observed = { url: new URL(url), init };
      return new Response('{"code":200,"msg":"ok","data":{}}', {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    };
    const argv = ["node", "mango", "--server", "https://example.com", spec.domain, spec.command];
    if (spec.multipart) argv.push("--file", path.join(projectRoot, "package.json"));
    await run(argv, {
      stdin: new PassThrough(),
      stdout: sink(),
      stderr: sink(),
      env: { MANGO_TOKEN: token },
      fetchImpl,
    });
    assert.equal(observed.init.method, spec.method, spec.legacy_name);
    assert.equal(observed.url.pathname, `/api/${spec.path}`, spec.legacy_name);
    assert.equal(observed.init.headers.Authorization, token, spec.legacy_name);
  }
});
