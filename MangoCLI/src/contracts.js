import { perfCommands } from "./perf.js";

const field = (name, type, description, required = false) => ({ name, type, required, description });
const id = field("--id", "positive integer", "URL 路径中的场景或运行 ID", true);
const page = field("page", "integer", "页码，从 1 开始");
const pageSize = field("pageSize", "integer", "每页条数");
const product = field("project_product", "integer", "项目产品 ID；用于限定查询范围");
const environment = "环境枚举：0 测试、1 预发、2 生产、3 开发、4 验收、5 仿真";
const list = [product, page, pageSize];
const scenarioBase = [
  field("base.name", "string", "性能场景名称"),
  field("base.load_type", "concurrency | arrival_rate | iteration_rate", "可省略；保存时按 load_config.profile 推导底层负载模型"),
  field("base.default_executor_count", "integer", "期望分配的执行器节点数"),
  field("base.node_failure_policy", "strict | continue", "节点失败时全部终止或满足最小节点后继续"),
  field("base.min_ready_nodes", "integer | null", "最少就绪节点数，不得大于执行器数"),
];
const load = [
  field("load_config.name", "string", "单套负载的名称"),
  field("load_config.profile", "constant_concurrency | fixed_iterations | staircase | linear_ramp | spike | soak | constant_arrival_rate | constant_iteration_rate", "压测方案；决定条件字段并覆盖 base.load_type", true),
  field("load_config.duration_seconds", "integer", "固定并发、定量任务截止时间、长稳态和固定速率的运行秒数；其他方案由阶段字段自动计算"),
  field("load_config.target_users", "integer", "目标或峰值并发；所有并发方案必填，不得少于执行器数"),
  field("load_config.total_iterations", "integer", "定量任务的完整 Case 总执行次数；全部执行器合计目标"),
  field("load_config.start_users", "integer", "线性爬坡的起始并发，或突刺测试的基线并发"),
  field("load_config.step_users", "integer", "阶梯加压每阶增加的并发用户数"),
  field("load_config.step_interval_seconds", "integer", "阶梯加压每阶持续的秒数"),
  field("load_config.ramp_seconds", "integer", "线性爬坡或突刺上升的秒数"),
  field("load_config.hold_seconds", "integer", "峰值保持秒数，可为 0"),
  field("load_config.baseline_seconds", "integer", "突刺测试基线阶段秒数"),
  field("load_config.recovery_seconds", "integer", "突刺测试恢复阶段秒数"),
  field("load_config.target_rate", "number", "固定速率方案的 Case 启动速率，不是 HTTP 请求速率"),
  field("load_config.rate_time_unit", "second | minute", "目标速率的时间单位"),
  field("load_config.preallocated_vus", "integer", "开放负载模型的预分配 VU 数"),
  field("load_config.max_vus", "integer", "开放负载模型允许的最大 VU 数"),
  field("load_config.user_wait_min_ms", "integer", "两次完整 Case 迭代之间的最短等待，毫秒，默认 0"),
  field("load_config.user_wait_max_ms", "integer", "两次完整 Case 迭代之间的最长等待，毫秒，必须不小于最小值"),
];
const goal = [
  field("performance_goal.template_key", "recommended | custom", "推荐或自定义目标；默认 recommended，三项指标按 AND 判定"),
  field("performance_goal.p95_ms", "integer", "P95 响应时间上限，毫秒；默认 500"),
  field("performance_goal.max_error_rate", "number 0..1", "错误率上限；0.01 表示 1%"),
  field("performance_goal.min_load_achievement_rate", "number 0..1", "最低负载达成率；0.95 表示 95%"),
];
const perf = {
  "list-scenarios": { fields: list, example: "mango perf list-scenarios -p project_product=1 -p page=1 -p pageSize=20" },
  "get-scenario": { fields: [id], example: "mango perf get-scenario --id 3" },
  "create-scenario": { fields: [
    field("project_product", "integer", "所属项目产品 ID", true),
    field("module", "integer", "所属业务模块 ID", true),
    field("name", "string", "场景名称，同一产品内唯一", true),
    field("engine", "k6", "性能测试引擎；当前仅支持 k6，默认 k6"),
    field("load_type", "concurrency | arrival_rate | iteration_rate", "负载模型；默认 concurrency"),
    field("target_users", "integer", "并发模型目标用户数；默认 10"),
    field("target_rate", "number", "开放负载模型目标速率；该模型必填"),
    field("duration_seconds", "integer", "默认持续秒数；默认 60"),
    field("default_executor_count", "integer", "默认执行器数量；默认 1"),
    field("node_failure_policy", "strict | continue", "节点失败处理方式；默认 strict"),
    field("min_ready_nodes", "integer | null", "至少就绪的执行器数量"),
    field("user_wait_min_ms", "integer", "最短迭代等待，毫秒"),
    field("user_wait_max_ms", "integer", "最长迭代等待，毫秒"),
    field("status", "0 | 1", "禁用或启用；默认 1"),
    field("tags", "string[]", "标签，每项最多 32 字符"),
    field("description", "string", "可选描述"),
  ], example: "mango perf create-scenario -p project_product=1 -p module=2 -p name=登录压测" },
  "update-scenario": { fields: [id,
    field("version", "integer", "从 get-scenario 读取的当前版本；防止覆盖他人修改", true),
    field("source_case_release_id", "integer", "已发布且兼容性能模式的API自动化 Case 发布 ID", true),
    field("base", "object", "场景基本信息及执行器策略的字段容器"),
    ...scenarioBase,
    field("load_config", "object", "单套负载配置对象", true), ...load,
    field("performance_goal", "object", "单套性能目标；结果判定，不中止运行", true), ...goal,
  ], example: "mango perf update-scenario --id 3 --input scenario-configuration.json" },
  "validate-scenario": { fields: [id], example: "mango perf validate-scenario --id 3" },
  "list-executors": { fields: [], example: "mango perf list-executors" },
  capacity: { fields: [], example: "mango perf capacity" },
  "preflight-scenario": { fields: [id,
    field("test_env", "integer", `本次运行环境；${environment}`, true),
    field("selected_executor_fingerprints", "string[]", "本次显式选择的执行器指纹；建议至少一项"),
  ], example: "mango perf preflight-scenario --id 3 -p test_env=1 -p 'selected_executor_fingerprints=[\"user:1\"]'" },
  "execute-scenario": { fields: [id,
    field("test_env", "integer", `本次运行环境；${environment}`, true),
    field("selected_executor_fingerprints", "string[]", "本次显式选择的执行器指纹；数量须等于场景 default_executor_count，且不得重复", true),
    field("production_load_confirmed", "boolean", "test_env=2 时必须为 true"),
    field("remark", "string", "本次运行备注，最多 512 字符"),
  ], example: "mango perf execute-scenario --id 3 -p test_env=1 -p 'selected_executor_fingerprints=[\"user:1\"]'" },
  "stop-run": { fields: [id], example: "mango perf stop-run --id 42" },
  "list-runs": { fields: list, example: "mango perf list-runs -p project_product=1 -p page=1" },
  "get-run": { fields: [id], example: "mango perf get-run --id 42" },
  "get-run-metrics": { fields: [id,
    field("cursor", "opaque string", "上次响应返回的不透明 cursor；首次请求省略，不是数字偏移"),
    field("max_points", "integer 1..2000", "单次返回的采样点数；默认 500"),
    field("scope_type", "global | request | stage | node", "只查看指定指标范围"),
    field("scope_key", "string", "指定范围下的键，与 scope_type 搭配使用"),
  ], example: "mango perf get-run-metrics --id 42 -p max_points=200" },
  "get-run-report": { fields: [id], example: "mango perf get-run-report --id 42", note: "聚合读取运行详情、请求、错误、目标、有效性和节点结果，共 6 个只读接口。" },
};

export function perfCommandContract(command) {
  const spec = perfCommands.find((item) => item.command === command);
  if (!spec) return null;
  const details = perf[command];
  return {
    domain: "perf", command, summary: spec.summary, method: spec.method,
    path: `/api/${spec.path}`, schema_status: "documented",
    parameters: details.fields,
    example: details.example,
    note: ["--id 是路径参数；GET 的 -p 参数进入查询串，其他方法进入 JSON 请求体。嵌套字段请用 --input JSON 文件传递。", details.note].filter(Boolean).join(" "),
  };
}

export function formatCommandContract(contract) {
  const lines = [`接口: ${contract.method} ${contract.path}`];
  if (contract.parameters.length) {
    lines.push("请求参数:");
    for (const item of contract.parameters) {
      lines.push(`  ${item.name}  ${item.type}${item.required ? "  必填" : ""}  ${item.description}`);
    }
  } else {
    lines.push("请求参数: 无");
  }
  lines.push(contract.note);
  if (contract.example) lines.push(`示例: ${contract.example}`);
  lines.push(`机器可读: mango perf describe ${contract.command}`);
  return `\n${lines.join("\n")}\n`;
}

export const documentedPerfCommandCount = Object.keys(perf).length;
