import test from "node:test";
import assert from "node:assert/strict";
import { catalog } from "../src/catalog.js";

test("catalog covers all legacy MCP tools without duplicates", () => {
  assert.equal(catalog.length, 324);
  assert.equal(new Set(catalog.map((item) => item.legacy_name)).size, 324);
  assert.deepEqual(
    Object.fromEntries([...new Set(catalog.map((item) => item.status))].map((status) => [
      status,
      catalog.filter((item) => item.status === status).length,
    ])),
    { complete: 258, pending_api: 59, protocol_mcp: 7 },
  );
});

test("complete capabilities have routes and pending capabilities have reasons", () => {
  for (const item of catalog) {
    assert.ok(item.domain && item.command && item.status);
    if (item.status === "complete") assert.ok(item.method && item.path);
    if (item.status === "pending_api") assert.ok(item.reason && item.reason !== "未映射");
  }
});
