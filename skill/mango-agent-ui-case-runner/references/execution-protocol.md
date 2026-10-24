# AI 执行 UI 的协议

## 无状态调用顺序

读取 Case → 创建执行 token → 初始化本地上下文 → 按需服务端前置 → 执行流程节点 → 按需服务端清理 → 上报步骤 → 完成执行。

平台不新建独立的 agent-run 记录。签名 token 绑定当前用户、Case、环境、参数组、Case 版本、有序页面步骤版本、开始时间及证据策略；AI 维护游标，平台将上报结果写入已有 `execution_result` 体系。

一个 token 执行一个参数组，有效期6小时。Case 或页面步骤版本变化后，丢弃 token 并新建执行。

## 工具契约

| 工具 | 用途 |
| --- | --- |
| `agent_ui_get_case` | 读取不含敏感信息的结构和目标。 |
| `agent_ui_create_execution` | 声明能力，获取全部运行步骤与签名 token。 |
| `agent_ui_execute_runtime` | 执行 token 绑定的服务端操作，包括前置/全局 SQL、SQL 节点、条件分支验证及后置 SQL。 |
| `agent_ui_upload_artifact` | 保存证据并返回签名 `artifact_ref`。 |
| `agent_ui_report_step` | 将单步骤结果写入现有执行结果体系。 |
| `agent_ui_complete_execution` | 保存 UI Case 最终结果和全部步骤摘要。 |

每个写工具都要求 `project_product_id`，服务端与签名 token 核对。禁止编辑或构造执行 token、附件引用。

## 步骤与最终上报

步骤报告包含稳定的 `idempotency_key`、状态、摘要、断言、观察、工具调用摘要、耗时和签名附件引用。相同执行、步骤索引和幂等键再次提交时，返回已保存结果。

最终报告重复携带有序步骤报告，确保即使没有独立 agent-run 状态，Case 结果仍完整。最终通过必须包含全部运行步骤且各出现一次；失败或阻塞可只包含终止前已到达的步骤。

`case_context` 包含前置、所选参数和清理。首次浏览器操作前完成必需前置，最终上报前完成必需清理。缺少获授权工具应为 `blocked`，不是 `skipped`。

每个 token 只维护一个内存变量表。自定义全局、Case 前置自定义变量、所选参数及自定义变量节点都在本地写入，不调用 `agent_ui_execute_runtime`。调用执行工具前，按 [运行值规则](runtime-values.md) 解析全部操作和断言参数。生成的别名与成功操作输出可供同一 Case 后续页面步骤使用。

## 流程节点分派

| 节点类型 | 执行方 |
| --- | --- |
| 元素操作（`0`） | 浏览器工具，先从本地上下文解析参数。 |
| 断言（`1`） | 浏览器/观察工具，保留保存的判定标准。 |
| 数据源（`2`） | `agent_ui_execute_runtime(operation=execute_node)`，合并返回的 `runtime_bindings`。 |
| 自定义变量（`3`） | 本地解析并写入上下文，不调用 MCP。 |
| 条件（`4`） | 按要求观察页面，再通过 `agent_ui_execute_runtime` 验证/选择返回的子分支。 |
| Python 代码（`5`） | 平台沙箱支持该代码契约前保持 `blocked`；禁止用 shell 或本地 `exec` 执行。 |
| 强制等待（`6`） | 客户端按解析后的时长等待，不占用 MCP 请求。 |

`agent_ui_execute_runtime` 请求使用稳定幂等键，包含 `operation`、当前 `runtime_variables`；节点执行还包含 `step_index` 和 `node_id`。禁止发送模型自行提供的 SQL/Python 源码，服务端自行读取签名 Case 快照。
