---
name: mango-agent-ui-case-runner
description: 由具备浏览器能力的 AI 通过 agent_ui_ MCP 协议逐步执行已有 Mango UI Case，获取运行数据、自主选择浏览器工具、执行操作与断言、上传证据并保存结果。适用于用户要求 AI 直接执行 UI Case，而非委托桌面执行器的场景。
---

# AI 执行 UI Case

## 适用范围

用于 AI 自己执行已有 Mango UI Case。测试平台负责 Case 定义、证据和结果持久化；AI 负责选择浏览器工具、执行和维护内存中的步骤游标。

执行编排只能使用 `agent_ui_` MCP 工具。浏览器操作可使用当前环境可用的浏览器、计算机控制、Playwright 或等效工具。禁止调用 `run_ui_case`，该接口属于委托执行器的另一条执行链路。

本 Skill 不授权修改 Case、页面步骤、元素、断言或自愈配置。运行时可以调整操作方式，但未经用户另行明确授权，不得回写配置。

准备阶段会拒绝带平台数据工厂绑定或灰度配置切换的 Case，因为这些能力需要可恢复的服务端准备/回滚租约。不得绕过拦截或手工复现其数据库副作用。

执行前读取 [执行协议](references/execution-protocol.md) 和 [运行值与变量替换](references/runtime-values.md)；首次上报步骤前读取 [证据与断言](references/evidence-and-assertions.md)。

## 必须遵循的流程

1. 确定准确的 `case_id` 和测试环境，不得在同名 Case 之间猜测。
2. 盘点当前 AI 实际可用的浏览器和证据工具。
3. 调用 `agent_ui_get_case` 查看不含敏感信息的结构，确认目标 Case。
4. 调用 `agent_ui_create_execution`，传入 `capabilities.available_tools`、明确的证据策略和 `parameter_set_index`。一个签名执行 token 对应一个参数组及返回的全部运行步骤。没有浏览器控制工具时不创建执行，报告能力缺口。
5. 返回的运行步骤、token 和浏览器授权均为敏感、短期执行数据。禁止在对话或日志中输出授权缓存、Cookie、token、密码、环境秘密或完整变量内容。
6. 每个 token 只维护一个内存变量表。无需 MCP 调用，先按 `runtime_step.public_data_list` 中自定义全局变量（`type=0`）初始化，再写入 `case_context.front_custom`，最后写入所选参数组；各来源保持保存顺序，后写覆盖同名键。自定义变量节点也写入此表。所有页面步骤、操作、断言和清理共享该表，结束后丢弃。禁止每个页面步骤各建一个表，也禁止仅为普通全局变量、Case 前置自定义变量、参数或自定义节点调用 `agent_ui_execute_runtime`。
7. 操作和断言前，按 `mangotools.data_processor.DataProcessor.replace` 的标准行为递归解析参数中的 `${{...}}`。`${{str_random_string()|模版名称}}` 表示生成一个10位 ASCII 字母数字串，缓存为 `模版名称` 并在此使用；`${{模版名称}}` 只读取缓存，绝不生成新值。文档中的 `\|` 只是 Markdown 表格转义，不是运行值的一部分。完整规则见 `runtime-values.md`。
8. 存在前置/全局**数据源**操作时，调用 `agent_ui_execute_runtime(operation=prepare_case)` 并传当前 `runtime_variables`，将返回的 `runtime_bindings` 合并到同一变量表。自定义全局、`front_custom`、参数和自定义变量节点不调用此接口。按保存顺序执行页面步骤及节点；SQL/数据源节点调用 `operation=execute_node` 并合并输出，自定义变量节点在本地解析并保存键值。节点分派见执行协议。
9. 存在后置数据源操作时，最终完成前调用 `operation=cleanup_case`，始终传入当前变量表，以使用浏览器流程生成的值。服务端必需操作不可用或返回阻塞时，禁止静默跳过。
10. 能确定性判断的断言直接验证。仅当保存的断言确实要求时使用语义或视觉判断，并记录观察与支撑证据。
11. 按策略调用 `agent_ui_upload_artifact`，保存返回的签名 `artifact_ref`，禁止构造或修改。失败或阻塞时，浏览器支持截图就上传截图。
12. 每个逻辑结果调用一次 `agent_ui_report_step`，传入从0开始的 `step_index`、执行 token、项目产品 ID 和稳定唯一的 `idempotency_key`。
13. 最后一个已到达步骤结束后调用 `agent_ui_complete_execution`，最终载荷重复携带已执行步骤报告；通过结果必须包含全部运行步骤且各出现一次。

## 不可放宽的结果规则

- 操作完成不等于步骤通过，必须检查保存的成功条件和断言。
- 不得因为页面看起来合理，就将失败断言改判为通过。
- Case 语义未证明重试安全时，不重试破坏性操作。
- 步骤摘要、观察、截图、文件名和工具调用摘要不得暴露运行秘密。
- 禁止把未解析的 `${{...}}` 传入浏览器、shell、数据库、断言或外部工具。变量缺失或函数不支持时，使当前节点失败，并以脱敏原因上报步骤失败或阻塞，不得猜值。
- 缺少必需浏览器能力、身份、测试数据或可观察证据时，报告阻塞。
- 保留原业务含义，不得为了 AI 执行方便而放宽判定标准。

## 完成汇报

最终结果保存后，简要返回执行 ID、执行结果 ID、最终状态、已完成/总步骤数、失败或阻塞步骤摘要及证据链接，不复述敏感运行数据。
