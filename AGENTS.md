# AGENTS.md

本文件是 `MangoTestingPlatform` 仓库的总开发约束。子项目更细规范见：

- `MangoServer/AGENTS.md`
- `mango-console/AGENTS.md`

## 项目结构

```text
MangoServer/       # Django REST 后端
MangoActuator/     # 桌面执行器
mango-console/     # Vue 3 + TypeScript 前端
MangoCLI/          # 独立 Node.js CLI，通过 REST API 调用后端
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
8. 产品模块层级以 `parent` 关系为唯一展示来源；后端统一返回 `full_path`，前端统一使用公共格式化方法，不使用 `superior_module_1/2` 拼接路径。
9. 测试文件、示例、注释和项目文档不得包含真实业务域名；需要域名样例时统一使用 RFC 保留域名 `example.com`、`example.org` 或 `example.net`。部署和运行环境的显式配置不属于示例，不得为了测试脱敏而擅自替换。

## 页面与操作权限

角色权限必须同时覆盖页面入口、实际操作、服务端接口和数据范围。具体实现与本次修复清单见 [角色页面与操作权限修复说明](docs/架构设计/角色页面与操作权限修复说明.md)。

1. 菜单定义统一维护在 `MangoServer/src/apps/system/services/menu.py`，操作权限与接口映射统一维护在 `MangoServer/src/apps/user/services/permission.py`；前端消费后端权限树，不另建权限清单。
2. 每个可授权叶子页面必须使用唯一且稳定的 `permissionKey`，操作键使用 `<页面键>:<操作>`。不同业务页面不得共用页面键；菜单分组只负责组织层级，不计入已授权页面数。
3. 新增、删除或调整页面和操作时，必须同步检查菜单注册、HTTP 权限映射、MCP 权限策略、前端路由和全部操作入口。操作列表只登记实际存在且受校验的能力，不保留无入口、无接口或语义不符的权限。
4. 前端操作显式声明权限：表格操作统一使用 `MangoTableActions.permission`，普通按钮和状态开关使用 `v-permission` 或公共权限判断；不得按按钮文案推断权限。行内操作、更多菜单和点击执行均须遵守权限，权限更新后立即生效，并保留原有 `v-if` / `v-show` 业务条件。
5. 跨页面操作按目标业务能力校验，不能借用承载页面的权限。例如套件中的用例编辑使用用例编辑权限，AI 执行使用 `ai.task:execute`。只有多个授权入口确实能访问同一能力时，才可显式配置“任一权限满足”的规则。
6. 前端隐藏入口不能替代服务端鉴权。REST 与 MCP 必须复用所属 App 的权限规则和数据范围；列表、详情、内容、最新结果、导出及执行结果等读取接口也必须校验相应操作权限与项目/产品范围，禁止仅凭记录 ID 或报告关联绕过范围。
7. 状态字段统一登记在 `MangoServer/src/apps/user/constants.py` 的 `STATUS_PERMISSION_FIELDS`，后端通过菜单 `statusFields` 提供给前端，不在页面或 MCP 中重复维护。只更新状态要求 `:status`，同时更新内容与状态要求 `:edit` 和 `:status`；MCP 修改状态参数执行同样校验。
8. 共用编辑表单的请求必须显式传递目标 `permissionKey`，由公共请求层根据状态字段登记移除未授权的状态字段，并保持原始表单数据和服务端状态。服务端仍须独立拒绝越权请求，不能依赖前端过滤。
9. 导出必须通过受导出权限和数据范围约束的只读接口获取数据，选中行导出也不能绕过校验。清理、调试、执行、通知等操作必须独立校验；只读页面加载不得自动触发无权限的生成、执行或其他写操作。
10. 游客与公开分享使用显式权限边界。公开报告仅放行约定的查看、导出和下载能力；重试、停止、通知等操作仍须登录角色授权。新增执行和写操作不得自动进入游客权限。
11. 角色切换时立即清理旧权限树和选中键，并忽略过期请求响应；仅在当前角色权限加载成功且具备编辑权限时允许保存。保存期间禁止切换角色或并发修改角色，提交时固定角色 ID 与权限键快照；修改自身角色后须刷新权限和路由，失去当前页面权限时跳转到可访问页面。
12. 权限键升级只允许明确的旧键规范化映射。拆分页面或新增操作必须由管理员重新授权，不得把旧权限自动扩展为更多权限；读取和保存时过滤失效键，避免旧授权继续生效。
13. 汇总、概览和列表接口必须按调用者权限裁剪响应字段，不能附带其他独立页面的数据或未授权的详情；异常堆栈、上下文、实例元数据和日志查询等信息不能只靠前端隐藏。

## 内部包

本项目依赖两个本地内部包：

- `/Users/mango/code/mango_tools`：提供 `mangotools`，执行器和后端都依赖。
- `/Users/mango/code/mango_automation`：提供 `mangoautomation`，执行器依赖。

修改内部包代码后的处理规则：

1. 修改 `/Users/mango/code/mango_tools` 中代码后，必须自动执行：

   ```bash
   cd /Users/mango/code/mango_tools
   .venv/bin/python sync_local_package.py
   ```

   该脚本会使用 `mango_tools` 自己的虚拟环境打包，并安装到 `MangoActuator` 和 `MangoServer` 的虚拟环境中。

2. 修改 `/Users/mango/code/mango_automation` 中代码后，必须自动执行：

   ```bash
   cd /Users/mango/code/mango_automation
   .venv/bin/python sync_local_package.py
   ```

   该脚本会使用 `mango_automation` 自己的虚拟环境打包，并安装到 `MangoActuator` 的虚拟环境中。

3. 若只是查看、分析或读取内部包代码，不需要执行同步脚本。
4. 同步脚本复制到 `MangoActuator/local_packages/`、`MangoServer/local_packages/` 的内部包 wheel 可以提交到 git，因为这些包后续可能不会上传到 PyPI。
5. 若脚本执行失败，最终说明失败原因、已完成到哪一步，以及目标虚拟环境是否可能处于部分更新状态。

## 后端 MangoServer

常用命令：

```bash
cd MangoServer
python manage.py runserver --env=dev 0.0.0.0:8000
sh scripts/start_dev_services.sh
```

后端目录采用 Django 模块化单体结构：

```text
MangoServer/
├── requirements/                 # base/dev/test/master/local 分层依赖
├── runtime/                      # 日志、媒体、缓存等运行产物，不提交
└── src/
    ├── apps/                     # Django 业务 App
    │   └── <app>/
    │       ├── __init__.py
    │       ├── apps.py
    │       ├── models.py|models/ # Django Model/QuerySet/Manager
    │       ├── api/              # __init__ + urls + serializers + views
    │       ├── selectors/        # 只读查询
    │       ├── services/         # 写操作和业务流程
    │       ├── tests/
    │       └── migrations/       # 有数据库模型时使用
    ├── common/                   # 无业务归属的跨 App 公共能力
    ├── interfaces/               # 后端进程内的 MCP 等协议适配层
    ├── processes/                # worker/scheduler/realtime/monitoring/mcp 进程入口
    └── settings/
```

`src/processes/` 是 Python 源码；根目录 `runtime/` 仅保存运行产物，两者不得混用。项目是一个 Django 工程和一套 ORM，不因存在多个进程入口而复制业务逻辑或通过内部 HTTP/RPC 调用其他模块。

后端开发约束：

1. 业务逻辑尽量放在 `services/`，ViewSet 只负责入参、权限、序列化和响应。
2. 返回结构沿用 `ResponseData.success/error`。
3. 业务异常必须使用所属 App `exceptions/` 中的异常类抛出，例如 `AutoApiError`、`AutoUiError`、`AutoPytestError`；所有 App 异常继承 `MangoServerError`。禁止恢复 `ToolsError`、`SystemEError` 等跨领域万能异常。
4. 通过 `ResponseData.fail` 返回给前端的错误响应文案，必须先定义在 `src/common/responses/response_msg.py`，代码中引用常量，不直接写散落字符串。
5. 业务错误定义归所属 App 的 `exceptions/`；定义较少时直接写在 `exceptions/__init__.py`，定义较多时按业务主题拆分，或先使用 `definitions.py`。`src/common/exceptions/` 只存公共基类、定义类型、标准化逻辑和真正跨 App 的错误；不直接写散落业务文案。
6. 不允许用 `serializers.ValidationError`、`ValueError`、裸 `Exception` 等承载可预期业务错误文案；DRF 字段校验只用于字段格式错误，业务规则冲突必须转换为对应 app 异常。
7. 模型改动要同步检查 serializer、services、selectors、MCP 和前端返回字段。
8. `JSONField` 必须有明确结构约定，不随意存任意 JSON。
9. 外键删除策略按业务数据生命周期设计：强依赖的附属数据随主业务资产删除时使用 `CASCADE`，避免保留无用孤儿数据；上层归属、项目产品、模块、用例等边界关系优先使用 `PROTECT` 防止误删；审计、来源、最近操作人等弱引用允许 `SET_NULL`。
10. 列表接口注意 `select_related`、`prefetch_related`，避免 N+1。
11. 枚举按业务归属放置：App 私有枚举必须在 `MangoServer/src/apps/<app>/enums/`，真正跨 App 且无业务归属的枚举放在 `MangoServer/src/common/enums/`，后端与执行器共同使用的跨进程协议枚举放在 `mangotools.enums`；禁止为了方便把 App 私有枚举放进 `common`。
12. 每个 `enums/` 按业务主题拆文件，例如 `case.py`、`execution.py`、`auth.py`，不恢复 `tools.py`、`system.py`、`api.py` 这类大杂烩枚举文件；包级 `__init__.py` 只能显式导出稳定枚举，整个后端和执行器源码禁止 `import *`。
12.1 Service、Selector、Process、View、Serializer 和 MCP 适配层不得定义业务枚举或用常量类模拟枚举；业务代码引用所属 App 或共享协议包中的枚举，不散落数字、字符串魔法值。
12.2 后端与执行器通过网络交换的枚举必须只有一个定义源；Socket 协议按方向使用 `Server*CommandEnum` 和 `Actuator*EventEnum`，不得再创建同名但取值不同的两套枚举。
12.3 枚举迁移必须一次性更新全部调用方并删除旧文件，不保留兼容转发；枚举值、数据库字段值和 `/system/enum` key 未经迁移设计不得改变。
12.4 `/system/enum` 只能由显式注册表生成；新增、删除或调整面向前端的枚举时，必须同步注册表、前端展示与测试。
12.5 修改枚举后必须运行枚举清单、架构守卫和相关业务测试；架构守卫必须覆盖枚举位置、星号导入、Service/Process 伪枚举和同名不同值。
13. 开发过程中不允许执行生成迁移脚本命令。
14. 开发过程中不允许执行迁移命令。
15. 迁移脚本由用户自己生成和执行。
16. 如模型发生变化，只说明需要迁移，不要运行 `makemigrations` 或 `migrate`。
17. 新增 MCP 增删改工具时，必须确认是否会被 `src/interfaces/mcp/server.py` 的演示环境写操作拦截识别；如属于新增、修改、删除、清理、上传、绑定、执行落库等写操作，工具命名应使用既有前缀或同步更新 MCP 写操作分类规则。
18. 后端 AI 提示词统一放在 `MangoServer/src/common/prompts/catalog/`，按业务能力拆分 YAML；静态 system/user 正文、角色、输出契约、版本和场景配置必须登记到显式 registry。Python 只负责 Pydantic 校验、安全模板渲染和动态消息组装；Service、View、Model、process、任务执行器不得内联提示词正文。
19. 后端不使用 Django Admin、默认 auth User/Group/Permission、Session 和 Messages；禁止新增 `admin.py`、`django.contrib.admin`、`django.contrib.auth.models` 业务依赖或 `request.session`。密码哈希只可复用无数据库依赖的 `django.contrib.auth.hashers`，身份与权限统一使用自定义 User、JWT 和菜单权限体系。
20. 可选模型字段必须同时声明数据库与业务表单语义：`null=True` 的字段必须设置 `blank=True`；允许空列表或空对象的 `JSONField(default=list/dict)` 也必须设置 `blank=True`。非字符串字段是否允许 `NULL` 仍按业务语义决定，不能为了绕过校验随意增加 `null=True`。
21. 所有业务模型表和字段必须提供可读的 `verbose_name`；Django 5.2 下由统一模型元数据规则同步为原生 `db_table_comment`/`db_comment`，供数据库与第三方工具读取。特殊数据库说明可显式设置 `db_comment` 覆盖默认值。
22. 新表和高频查询改动必须同时评估索引：以真实 `filter/exclude/order_by/group by`、数据量和执行计划为依据设计复合索引；等值过滤列在前，范围与排序列在后；避免重复外键/唯一索引、重复前缀索引和低区分度状态字段的无依据单列索引。索引必须使用明确且稳定的名称，并评估写入放大。
19. HTTP 路由只放在各 App 的 `api/urls.py`，项目总路由直接 include；不得恢复 App 根 `urls.py`、旧 `views/` 或其他纯转发兼容模块。
20. `interfaces/mcp` 和 `processes` 只能作为薄适配层调用所属 App 的 `selectors/services`，不得直接复制业务规则、依赖 HTTP View/Serializer 或直接操作模型管理器。
21. 不得重新创建 `src/services/`、`src/runtime/`、`src/common/tools/`、`src/common/customization/` 或 App 单数 `service/`；新增 Python 目录必须包含 `__init__.py`。
22. 后端目录或导入关系变化后必须运行 `src.apps.system.tests.test_architecture_boundaries`。
23. App 内部结构也是固定架构：基础项为 `__init__.py`、`apps.py`、`models.py|models/`、`api/`、`selectors/`、`services/`、`tests/`；`api/` 内固定使用 `urls.py`、`serializers/`和 `views/`。无数据库模型或无 HTTP 能力的特殊 App 可省略对应层，但不得自创 `crud/`、`handlers/`、`logic/` 等并行分层。
24. `enums/`、`exceptions/`、`constants.py`、`schemas.py|schemas/`、`presenters.py|presenters/`、`formatters.py|formatters/`、`tasks/`、`signals.py`、`management/` 是按能力选用的固定扩展位置；枚举和异常固定使用包目录，不使用 `enums.py` 或 `exceptions.py`。相同职责不得放到其他自定义目录。
24.1 App 异常包较小时，异常类和错误定义直接写在 `exceptions/__init__.py`；超过约 400 行、50 个定义或形成三个以上稳定业务聚合时再拆文件。`exceptions.py` 与 `exceptions/` 不得并存，不建立旧路径兼容转发。
24.2 普通业务错误定义只保存数字 `code` 和 `message`；字符串 `error_code` 仅用于调用方必须机器决策的跨进程状态，并优先来自所属枚举。异常构造函数不得写日志或数据库，REST、MCP 在后端协议边界统一标准化，只有未知异常进入系统异常记录；`MangoCLI` 只解析 REST 错误响应。
24.3 禁止新增 `ERROR_MSG_*`、`API_ERROR_0001`、`*_ERROR_0001` 等编号式异常定义，常量名必须表达具体业务语义；禁止 `ErrorClass(code, message)`、`ErrorClass(*RESPONSE_MSG_*)` 等兼容构造；每个 App 的数字错误码必须唯一，同一码不得对应不同文案。
24.4 业务异常和控制流异常类只能定义在所属 `exceptions/`；MCP Tool 不重复捕获模型 `DoesNotExist`，应复用 App Service 的明确业务异常。未知异常响应不得通过 REST 或 MCP 暴露原始异常字符串、数据库信息或内部路径；`MangoCLI` 不得绕过 REST 获取后端异常对象。
25. 四类模型边界固定：Django Model 只放 App 的 `models.py|models/`；Pydantic Schema 只放 App 的 `schemas/` 或 `common/schemas/`；DRF Serializer 只放 `api/serializers/`；dataclass 只用于单进程内部计算状态，不作为 HTTP/MCP/Socket/队列协议。
26. 后端与执行器共享的跨进程模型必须放在 `mangotools/contracts/` 并继承 `ContractModel`；两端不得重复定义。字段漂移通过接收方所属 App 的显式 adapter 转换，不在 Service 中兼容旧字段。
27. App Schema 按用途选择 `StrictSchema`、`TrimmedStrictSchema`、`FrozenSchema` 或 `OrmSchema`；禁止恢复 `schemas/models/`，大型 Schema 与 Django Model 文件按业务聚合拆分。
28. 模型或 Schema 迁移必须更新全部引用并直接删除旧文件，不保留纯重导出；共享协议变更必须同步内部 wheel、JSON Schema 快照和协议往返测试。
29. `CreatedAtModel`、`TimeStampedModel` 等 ORM 抽象基类必须先完成全项目字段矩阵和 migration state 评估，不得在普通目录重构中顺手抽取。完整规范见 `docs/架构设计/项目模型与Schema分层规范.md`。
30. 后端日志固定为 `runtime/logs/<service>/{app.log,error.log,django.log}`，执行器保持按级别日志文件；业务模块不得自建 FileHandler 或自行拼接日志路径。
31. 后端日志轮转必须保持多进程安全；修改日志门面或配置后必须验证真实调用位置、异常堆栈、重复 Handler、文件路由和多进程轮转。完整规范见 `docs/架构设计/日志管理规范.md`。
32. AI App 的 `agent/` 只存工作流、规划器、生成器和领域算法；上下文、文档、预算、租约、任务阶段、Skill、MCP 调用和 Harness 等 Service 固定放在 `apps/ai/services/`，AI Worker 入口固定放在 `src/processes/ai_worker/`，不得恢复 `apps/ai/runtime/` 或顶层 `apps/ai/harness/`。
33. AI 的 MCP 查询必须通过 `apps/ai/selectors` 和协议无关 presenter 输出，不得依赖 DRF Serializer；跨 App 读取调用目标 App Selector，跨 App 写入调用目标 App Service。

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
10. 表格操作列宽度按实际按钮数量收敛：1-2 个操作优先 `120`，3 个操作优先 `140`，确有 4 个及以上高频外显操作时再放宽；不要无脑使用大宽度。
11. 表格中的启用/停用、默认开启、是否生效等二元状态优先使用 `a-switch size="small"`，通过 `beforeChange` 等机制确保接口成功后再切换；只读状态才使用 tag。
12. 列表页表格外的新增、创建、导入等主按钮优先使用 `size="small"`，与既有管理页保持紧凑一致。
13. 宽内容只允许在表格、代码面板、画布内部滚动。
14. JSON 大编辑优先使用 `MangoJsonEditDrawer` 或现有公共组件。
15. 流程图节点颜色必须有清晰含义，避免误导用户。
16. 所有接口请求、异步保存/删除/执行、组件懒加载和耗时渲染都必须有 loading 状态。
17. loading 状态要绑定到对应按钮、表格、面板或局部区域，不用全页遮罩替代局部反馈。
18. 多区域页面优先分区 loading；只有所有关键区域都无可展示数据时，才允许整页 loading。
19. 列表页搜索逻辑优先参照既有页面，例如 `/uitest/page/index`：分页参数使用 `page` + `pageSize`，不要使用 `size`；请求前清理空搜索条件（`''`、`null`、`undefined`）；`ProjectProductSelect`/级联选择值必须转换为真实产品 ID 后再传给后端。
19.1 列表搜索下拉框只要后端支持 `__in`、数组或逗号分隔的集合查询，就必须提供多选；使用 `FormItem` 的页面统一调用 `enableMultiSelectSearch`，多值按 `key__in=value1,value2` 提交，重置为空数组，并以折叠标签避免撑宽搜索区。只有存在上下级依赖、专用单值协议或后端明确不支持集合查询时才允许保留单选，并在 `npm run search:audit` 的例外清单中说明原因。
20. 表格使用 `table.indexColumn` 时，必须在 `index` 列 cell slot 中显式渲染 `record.id`，不要让 ID 列读取不存在的 `index` 字段。
21. `ModalDialog` 只负责统一外壳，页面仍需按内容控制宽度和密度：短表单优先约 `520-560px`，字段较多但可并排的表单优先约 `700-760px` 并使用紧凑双列；长文本、SQL、代码、说明字段独占整行。
22. 配置类半屏窗口和抽屉表单优先使用左右布局：label 在左，输入框/下拉框/开关在右，同一配置项必须呈现为同一行，例如“服务地址 [输入框]”；除长文本、JSON、说明型内容外，不默认使用上下堆叠表单。
23. 表格或业务区域存在横向/纵向溢出时，优先使用 `a-table` 自身的横向、纵向滚动条并默认显示；通过有限高度容器和 `scroll.x`、`scroll.y` 让横向条位于表格底边、纵向条位于表格右侧，不能要求用户先滚到页面或表格内容末尾，也不额外复制代理滚动条。项目导航工作台使用原生双向滚动时必须开启 `contained-body`。
24. 所有前端页面和公共组件必须兼容不同 CSS 视口宽度与显示缩放，统一复用全局显示密度方案，不得为单个页面另写 2K/4K 放大逻辑。CSS 固定尺寸写入样式块并交由全局 PostCSS 转为 `rem`；参与布局的 JavaScript 数值使用 `scaleDensityPixels` / `scaleDensityLength`；不得用内联固定 `px`、`zoom` 或页面级 `transform: scale()` 绕过全局方案。Arco 表格列宽与滚动宽度、Modal 和 Drawer 宽度、Avatar 数值尺寸由全局适配层统一缩放，业务代码不得再次预乘密度比例。详细边界和验证要求见 `mango-console/AGENTS.md`。

## 验证

1. 后端改动优先跑最小相关测试或 compile 检查。
2. 模块级业务规则以对应子目录 `AGENTS.md` 或模块文档为准。
3. 前端样式/组件改造后优先跑 `npm run theme:audit`。
4. 常规前端页面、样式、表格和搜索交互小改动，不默认跑 `npm run build:dev`；优先使用 `npm run theme:audit`、`npm run table:audit` 和静态检查。
5. 阶段验收、构建风险或用户明确要求时再跑 `npm run build:dev`。
6. `npm run tsc` 可能有历史全量类型问题，需区分是否由本次改动引入。
7. 新增或修改页面布局、组件尺寸、表格、弹窗、抽屉、画布或图表后必须执行 `npm run responsive:audit`；涉及表格时同时执行 `npm run table:audit`。
8. 新增或修改列表搜索下拉框后必须执行 `npm run search:audit`。
9. 修改菜单、角色权限、接口权限或前端操作控制后，必须运行相关权限测试；覆盖授权与拒绝、只读/游客边界、项目/产品范围、状态与编辑组合以及角色切换和保存竞态。后端按影响范围运行 `test_permissions`、`test_menu_beta` 和执行结果权限测试；前端运行 `node --test tests/operation-permission.test.mjs tests/role-permission-selection.test.mjs`。涉及 HTTP/MCP 映射时同步验证两种入口，导入关系变化时运行架构守卫。
