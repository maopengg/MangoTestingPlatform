export const perfCommands = Object.freeze([
  { command: "list-scenarios", method: "GET", path: "perf/scenario", summary: "查询性能场景" },
  { command: "get-scenario", method: "GET", path: "perf/scenario/{id}", summary: "查看性能场景及负载配置" },
  { command: "create-scenario", method: "POST", path: "perf/scenario", summary: "创建性能场景" },
  { command: "update-scenario", method: "PUT", path: "perf/scenario/{id}/configuration", summary: "替换性能场景配置（需传 version）" },
  { command: "validate-scenario", method: "POST", path: "perf/scenario/{id}/validate", summary: "校验性能场景" },
  { command: "list-executors", method: "GET", path: "perf/scenario/executors", summary: "查询在线性能执行器" },
  { command: "capacity", method: "GET", path: "perf/capacity/overview", summary: "查看执行器安全容量" },
  { command: "preflight-scenario", method: "POST", path: "perf/scenario/{id}/preflight", summary: "按环境和执行器预检场景容量" },
  { command: "execute-scenario", method: "POST", path: "perf/scenario/{id}/execute", summary: "预检后启动性能场景，立即返回 run_id" },
  { command: "stop-run", method: "POST", path: "perf/run/{id}/stop", summary: "停止性能运行" },
  { command: "list-runs", method: "GET", path: "perf/run", summary: "查询性能运行历史" },
  { command: "get-run", method: "GET", path: "perf/run/{id}", summary: "查看性能运行状态与摘要" },
  { command: "get-run-metrics", method: "GET", path: "perf/run/{id}/metrics", summary: "按 cursor 查询实时客户端指标" },
  { command: "get-run-report", method: "GET", path: "perf/run/{id}", summary: "汇总运行、请求、错误、目标、有效性和节点结果", aggregate: true },
].map((item) => Object.freeze({ ...item, domain: "perf" })));

export function requireScenarioExecutionInput(payload) {
  if (!Number.isInteger(payload.test_env)) {
    throw new Error("执行场景必须指定整数 test_env");
  }
  const selected = payload.selected_executor_fingerprints;
  if (!Array.isArray(selected) || !selected.length
    || selected.some((item) => typeof item !== "string" || !item.trim())
    || new Set(selected).size !== selected.length) {
    throw new Error("执行场景必须明确选择不重复的执行器 selected_executor_fingerprints");
  }
  if (payload.test_env === 2 && payload.production_load_confirmed !== true) {
    throw new Error("生产环境发压必须显式设置 production_load_confirmed=true");
  }
}
