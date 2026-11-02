# Mango CLI

`mango` 是芒果测试平台 REST API 的 Node.js/Commander 客户端。它不连接 MCP、不访问数据库，也不包含测试平台业务逻辑。

CLI 与测试平台使用同一个发布版本号。`mango auth login` 在打开网页前调用轻量版本校验接口；版本一致才允许继续授权，版本不一致则直接在终端提示升级。业务命令不会重复查询版本或下载命令目录。

## 安装

```bash
npm install
npm link
mango version
```

要求 Node.js 18 或更高版本。`npm link` 在 macOS、Windows 和 Linux 上都会把 `mango` 注册为全局命令；也可以不 link，直接使用 `node bin/mango.js`。发布时可使用 `npm pack` 生成跨平台 npm 包，不再需要 Go SDK 或分别交叉编译系统二进制。

验证：

```bash
npm run check
npm test
```

## 配置

```bash
mango config set --name dev --server http://127.0.0.1:8000 --web-url http://127.0.0.1:5173
```

页面 REST API 只接受登录 JWT，并要求直接使用 `Authorization: <JWT>`；`mango_...` APIKey 只适用于旧 MCP 服务，CLI 不使用它。

交互终端执行下面的命令即可登录：

```bash
mango --profile dev auth login
mango auth status
```

CLI 会打开测试平台授权页：浏览器已登录时自动完成授权，未登录时登录后自动返回授权页。CLI 命令发现本地 Token 缺失或过期时，也会在交互终端自动触发相同流程。该流程使用 PKCE 一次性授权码，CLI 不读取浏览器 localStorage，JWT 不会进入回调 URL。`MANGO_TOKEN` 和 `auth import --token-stdin` 仅保留给 CI 或故障排查。

平台版本变化会改变服务端 `SECRET_KEY`，因此旧 JWT 会自然验签失败。业务命令收到 HTTP 401 后会删除当前 profile 的失效 Token；交互终端自动重新授权并只重试原命令一次，非交互环境则退出并提示重新登录。HTTP 403 权限不足不会触发重新登录。

## 调用

第一阶段命令沿用原 MCP Tool 名并转换为 kebab-case，按领域分组，便于逐项核对迁移结果：

命令的请求参数遵循对应页面 REST API 契约，不承诺继续兼容旧 MCP Tool 的参数名或 MCP 聚合响应；这正是 CLI 直接调用 API、放弃 MCP 服务的边界。

```bash
mango api search-api-infos -p project_product=1 -p page=1 -p pageSize=10
mango api create-api-info --input api-info.json
mango ui search-ui-pages -p project_product_id=1
mango data-factory list-data-factory-templates -p project_product_id=1
```

### 性能测试

`mango perf` 直接调用现有性能测试 REST API；实际发压仍由已选执行器上的 k6 完成。它不连接 MCP，也不会在本机启动 k6。性能命令独立于旧 MCP Tool 的 310 项迁移目录，可通过 `mango perf --help` 查看。

每个性能命令都提供与 MCP Tool 类似的参数契约：`mango perf execute-scenario --help` 显示接口、请求字段的类型、含义、必填条件与示例；`mango perf describe execute-scenario` 输出同一契约的 JSON，供 Agent 或脚本读取，无需登录。`--id` 是路径参数；GET 的 `-p` 是查询参数，POST/PUT 的 `-p` 是 JSON 请求体顶层字段。嵌套对象请通过 `--input` 或 `--stdin` 传完整 JSON。契约以性能 REST API 为准，不复用旧 MCP 参数名。

```bash
mango perf list-scenarios -p project_product=1 -p page=1 -p pageSize=20
mango perf get-scenario --id 3
mango perf create-scenario --input scenario.json
mango perf update-scenario --id 3 --input scenario-configuration.json
mango perf list-plans -p project_product=1
mango perf get-plan --id 5
mango perf create-plan --input plan.json
mango perf update-plan --id 5 --input plan-configuration.json
mango perf list-executors
mango perf capacity
```

更新配置的 JSON 必须包含当前 `version`，具体字段沿用页面 REST API 的 `base`、`load_config`、`performance_goal` 或计划的 `items` 等结构。先读取详情确认版本，再提交替换配置。

直接执行场景必须指定测试环境与执行器。CLI 会先请求容量预检；`can_run` 不为 `true` 时不会发送执行请求。生产环境（`test_env=2`）还必须显式确认：

```bash
mango perf preflight-scenario --id 3 -p test_env=1 \
  -p 'selected_executor_fingerprints=["user:1","user:2"]'
mango perf execute-scenario --id 3 -p test_env=1 \
  -p 'selected_executor_fingerprints=["user:1","user:2"]'
mango perf execute-scenario --id 3 -p test_env=2 \
  -p 'selected_executor_fingerprints=["user:1","user:2"]' \
  -p production_load_confirmed=true
```

计划执行使用计划及计划项中已保存的执行器策略。CLI 会先读取计划、确认每个启用项均明确指定执行器，再调用计划配置校验；实际容量仍由服务端启动运行时检查。启动命令只返回 `run_id`，不等待整个压测结束。不要在容量检查失败时反复发起运行。

```bash
mango perf execute-plan --id 5
mango perf list-runs -p project_product=1 -p page=1 -p pageSize=20
mango perf get-run --id 42
mango perf get-run-metrics --id 42 -p max_points=200
mango perf get-run-report --id 42
mango perf stop-run --id 42
```

`get-run-report` 聚合运行摘要、请求统计、错误、性能目标、有效性、节点和计划子运行，适合最终结果分析；实时趋势使用支持游标的 `get-run-metrics`。首次查询省略 `cursor`，后续传上次响应返回的不透明 `cursor` 字符串，不能用数字偏移。`--id` 只接受正整数。错误仍使用 CLI 统一 JSON 响应和退出码。

复杂 POST/PUT/DELETE 数据通过 JSON 文件或 stdin 输入：

```bash
mango api create-api-case --input case.json
printf '%s' '{"id":1001,"name":"新名称"}' | mango api update-api-case --stdin
```

文件上传：

```bash
mango file upload-system-file --file ./payload.json \
  -p project_product=1 -p name=payload.json -p allow_download=true
```

查看全部 310 项迁移状态（灰度 MCP/CLI 能力已退出范围）：

```bash
mango capability list
mango capability list --status pending_api
mango capability list --domain api
```

`pending_api` 表示现有页面 REST API 无法等价、安全地承载该能力，CLI 不会复制 MCP 业务代码来绕过缺口。`protocol_mcp` 仅用于可选的第三方 MCP 协议测试能力。


Agent 接入说明位于 `skills/mango-testing-platform/SKILL.md`。该 Skill 强制通过 CLI/REST 操作平台，并在能力为 `pending_api` 时返回目录中的后端缺口原因。
