# AGENTS.md

本文件是 `qfei-auto-platform` 仓库的总开发约束。子项目更细规范见：

- `MangoServer/AGENTS.md`
- `mango-console/AGENTS.md`

## 项目结构

```text
MangoServer/       # Django REST 后端
MangoActuator/     # 桌面执行器
mango-console/     # Vue 3 + TypeScript 前端
```

芒果测试平台是面向 UI、API、性能、监控等测试场景的低代码自动化平台。开发时优先保证稳定、可维护、可排查，不做无关重构。

## 通用原则

1. 修改前先读现有实现，优先沿用项目已有模式。
2. 不回滚用户已有改动，不修改无关文件。
3. 手工编辑优先使用 `apply_patch`。
4. 搜索文件和文本优先使用 `rg`。
5. 注释只写复杂业务原因，不写显而易见的代码翻译。
6. 不输出敏感 token、Authorization、密码到日志或文档。
7. 最终说明改了哪些文件、是否需要迁移、跑了哪些验证。

## 后端 MangoServer

常用命令：

```bash
cd MangoServer
python manage.py runserver --env=dev 0.0.0.0:8000
sh scripts/start_dev_services.sh
```

后端开发约束：

1. 业务逻辑尽量放在 `service/`，ViewSet 只负责入参、权限、序列化和响应。
2. 返回结构沿用 `ResponseData.success/error`。
3. 业务异常优先使用现有 `ToolsError` 或模块异常。
4. 通过 `ResponseData.fail` 返回给前端的错误响应文案，必须先定义在 `src/common/tools/view/response_msg.py`，代码中引用常量，不直接写散落字符串。
5. 通过 `ToolsError` 或异常抛出的业务错误文案，必须先定义在 `src/common/exceptions/error_msg.py`，代码中引用常量，不直接写散落字符串。
6. 模型改动要同步检查 serializer、service、MCP、前端返回字段。
7. `JSONField` 必须有明确结构约定，不随意存任意 JSON。
8. 列表接口注意 `select_related`、`prefetch_related`，避免 N+1。
9. 枚举统一放在 `src/common/enums/` 或模块既有枚举位置。
10. Service 中尽量引用枚举，不要散落数字魔法值。
11. 开发过程中不允许执行生成迁移脚本命令。
12. 开发过程中不允许执行迁移命令。
13. 迁移脚本由用户自己生成和执行。
14. 如模型发生变化，只说明需要迁移，不要运行 `makemigrations` 或 `migrate`。
15. 新增 MCP 增删改工具时，必须确认是否会被 `src/services/mcp_server/app.py` 的演示环境写操作拦截识别；如属于新增、修改、删除、清理、上传、绑定、执行落库等写操作，工具命名应使用既有前缀或同步更新 MCP 写操作分类规则。

## 前端 mango-console

常用命令：

```bash
cd mango-console
npm run dev
npm run build:dev
npm run tsc
npm run theme:audit
```

前端开发约束：

1. Vue 3 + TypeScript + Vite + Arco Design + Pinia。
2. 后台测试平台优先服务扫描、排查、配置和连续操作。
3. 风格要求：企业级、数据密集、紧凑、干净统一。
4. 未明确要求时，不启动或占用 `5173`。
5. 样式优先使用 `--m-*` token。
6. 不新增硬编码颜色、`--color-*`、`--primary-*`。
7. 全局自定义 class 必须使用 `mango-` 前缀。
8. 列表页优先使用 `TableBody + TableHeader + TableFooter`。
9. 表格操作列优先使用 `MangoTableActions`，删除/移除/清理必须 `danger: true`。
10. 宽内容只允许在表格、代码面板、画布内部滚动。
11. JSON 大编辑优先使用 `MangoJsonEditDrawer` 或现有公共组件。
12. 流程图节点颜色必须有清晰含义，避免误导用户。
13. 所有接口请求、异步保存/删除/执行、组件懒加载和耗时渲染都必须有 loading 状态。
14. loading 状态要绑定到对应按钮、表格、面板或局部区域，不用全页遮罩替代局部反馈。
15. 多区域页面优先分区 loading；只有所有关键区域都无可展示数据时，才允许整页 loading。

## 验证

1. 后端改动优先跑最小相关测试或 compile 检查。
2. 模块级业务规则以对应子目录 `AGENTS.md` 或模块文档为准。
3. 前端样式/组件改造后优先跑 `npm run theme:audit`。
4. 阶段验收或构建风险时跑 `npm run build:dev`。
5. `npm run tsc` 可能有历史全量类型问题，需区分是否由本次改动引入。
