import test from "node:test";
import assert from "node:assert/strict";
import { catalog } from "../src/catalog.js";

test("catalog covers supported tools without retired AI management commands", () => {
  assert.equal(catalog.length, 310);
  assert.equal(new Set(catalog.map((item) => item.legacy_name)).size, 310);
  assert.equal(catalog.some((item) => item.domain === "ai" || item.path?.startsWith("ai/")), false);
  assert.deepEqual(
    Object.fromEntries([...new Set(catalog.map((item) => item.status))].map((status) => [
      status,
      catalog.filter((item) => item.status === status).length,
    ])),
    { complete: 251, pending_api: 59 },
  );
});

test("complete capabilities have routes and pending capabilities have reasons", () => {
  for (const item of catalog) {
    assert.ok(item.domain && item.command && item.status);
    if (item.status === "complete") assert.ok(item.method && item.path);
    if (item.status === "pending_api") assert.ok(item.reason && item.reason !== "未映射");
  }
});
