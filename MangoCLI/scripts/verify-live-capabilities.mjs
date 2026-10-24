import { catalog } from "../src/catalog.js";
import { request } from "../src/client.js";
import { loadRuntime } from "../src/config.js";

const profileIndex = process.argv.indexOf("--profile");
const profile = profileIndex >= 0 ? process.argv[profileIndex + 1] : "default";
const runtime = await loadRuntime({ profile });
runtime.timeout = 20000;
if (!runtime.server || !runtime.token) throw new Error(`profile ${profile} 未配置 server 或尚未登录`);

const completed = catalog.filter((item) => item.status === "complete");
const routeSpecs = [...new Map(completed.map((item) => [`${item.method} ${item.path}`, item])).values()];
const SIDE_EFFECT_PATTERN = /^(run|debug|execute|test|export|retry|trigger|sync|refresh|evaluate)_/;
const safeGets = completed.filter((item) => item.method === "GET" && !SIDE_EFFECT_PATTERN.test(item.legacy_name));

async function verifyGet(spec) {
  try {
    await request(runtime, spec, { page: 1, pageSize: 1 });
    return { capability: spec.legacy_name, path: spec.path, result: "passed" };
  } catch (error) {
    if (error.exitCode === 5) {
      return { capability: spec.legacy_name, path: spec.path, result: "reached_business_validation", reason: error.message };
    }
    return { capability: spec.legacy_name, path: spec.path, result: "failed", reason: error.message, exit_code: error.exitCode };
  }
}

async function mapLimited(items, limit, callback) {
  const output = new Array(items.length);
  let cursor = 0;
  async function worker() {
    while (cursor < items.length) {
      const index = cursor++;
      output[index] = await callback(items[index]);
    }
  }
  await Promise.all(Array.from({ length: limit }, worker));
  return output;
}

const getResults = await mapLimited(safeGets, 3, verifyGet);
const getFailures = getResults.filter((item) => item.result === "failed");
const summary = {
  generated_at: new Date().toISOString(),
  profile,
  completed_capabilities: completed.length,
  unique_method_paths: routeSpecs.length,
  route_contract: {
    verification: "MangoServer CliCatalogRouteTests",
    note: "真实 OPTIONS 会触发部分 ViewSet 元数据错误，路径和方法改由 Django resolver 测试。",
  },
  safe_get: {
    total: getResults.length,
    passed: getResults.filter((item) => item.result === "passed").length,
    reached_business_validation: getResults.filter((item) => item.result === "reached_business_validation").length,
    failed: getFailures.length,
  },
  skipped_side_effect_gets: completed
    .filter((item) => item.method === "GET" && SIDE_EFFECT_PATTERN.test(item.legacy_name))
    .map((item) => item.legacy_name),
  mutation_execution_policy: "POST/PUT/DELETE 仅验证真实路由和 Allowed 方法，不对 dev 现有业务数据执行写入、删除或任务触发。",
  safe_get_failures: getFailures,
  safe_get_business_rejections: getResults.filter((item) => item.result === "reached_business_validation"),
};
process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
if (getFailures.length) process.exitCode = 1;
