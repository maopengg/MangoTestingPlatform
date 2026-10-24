# MangoServer AGENTS.md

MangoServer 是芒果测试平台 Django 后端。本文件约定后端开发规范，重点覆盖 Django/DRF、目录边界、数据工厂、MCP 和迁移边界。完整设计与实施状态见 `../docs/架构设计/Django后端模块化目录重构完整方案.md` 和 `../docs/架构设计/Django后端模块化目录重构实施验收报告.md`。

## 基本原则

1. 修改前先读已有模型、API、selectors、services、enum，不要凭接口名猜逻辑。
2. 优先沿用现有目录风格：`models.py`、`api/`、`services/`、`selectors/`、`enums/`。
3. 业务逻辑尽量放在 `services/`，ViewSet 只负责入参、权限、序列化和响应。
4. 返回结构使用项目已有 `ResponseData.success/error` 风格。
5. 业务异常必须使用所属 App `exceptions/` 中的异常类抛出，例如 `AutoApiError`、`AutoUiError`、`AutoPytestError`；所有 App 异常继承 `MangoServerError`。禁止恢复 `ToolsError`、`SystemEError` 等跨领域万能异常。
6. 通过 `ResponseData.fail` 返回给前端的错误响应文案，必须先定义在 `src/common/responses/response_msg.py`，代码中引用常量，不直接写散落字符串。
7. 业务错误定义归所属 App 的 `exceptions/`；定义较少时直接写在 `exceptions/__init__.py`，定义较多时按业务主题拆分，或先使用 `definitions.py`。`src/common/exceptions/` 只存公共基类、定义类型、标准化逻辑和真正跨 App 的错误；不直接写散落业务文案。
8. 不允许用 `serializers.ValidationError`、`ValueError`、裸 `Exception` 等承载可预期业务错误文案；DRF 字段校验只用于字段格式错误，业务规则冲突必须转换为对应 app 异常。
9. 不要修改无关模块，不要顺手重构老代码。
10. 遇到用户已有工作区改动，必须在其基础上继续，不要回滚。

## 目录架构与依赖边界

MangoServer 是一个 Django 模块化单体，不拆成微服务。标准目录如下：

```text
MangoServer/
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   ├── test.txt
│   ├── master.txt
│   └── local.txt
├── scripts/
├── runtime/                        # 运行产物，不提交
└── src/
    ├── settings/
    ├── urls.py
    ├── asgi.py
    ├── wsgi.py
    ├── apps/
    │   └── <app_name>/
    │       ├── __init__.py
    │       ├── apps.py
    │       ├── models.py|models/
    │       ├── api/
    │       │   ├── __init__.py
    │       │   ├── serializers/
    │       │   ├── views/
    │       │   └── urls.py
    │       ├── selectors/
    │       ├── services/
    │       ├── schemas/
    │       ├── migrations/
    │       └── tests/
    ├── common/
    │   ├── database/
    │   ├── decorators/
    │   ├── enums/
    │   ├── exceptions/
    │   ├── logging/
    │   ├── middleware/
    │   ├── prompts/
    │   ├── responses/
    │   ├── storage/
    │   ├── testing/
    │   ├── utils/
    │   └── validators/
    ├── interfaces/
    │   └── mcp/
    │       ├── server.py
    │       ├── registry.py
    │       ├── authentication.py
    │       └── tools/
    └── processes/
        ├── api_worker/
        ├── scheduler/
        ├── realtime/
        ├── monitoring/
        └── mcp/
```

目录职责和依赖方向：

1. `api/views` 只处理 HTTP 权限、入参、调用和响应；`api/serializers` 只处理 HTTP 字段校验和展示序列化。
2. `selectors` 负责只读 ORM 查询、权限范围、预加载和统计；不得写库或调用 Service。
3. `services` 负责业务校验、写库、事务和流程编排；不得依赖 HTTP Request/Response、`api/views` 或 `api/serializers`。
4. 跨 App 调用只能使用目标 App 的 `selectors`、`services`、稳定 schema 或 presenter，不得导入目标 App 的 HTTP View/Serializer。
5. `interfaces/mcp` 和 `processes` 都是后端进程内的薄适配层，只调用 App 的 Selector/Service，不定义模型、不复制业务规则、不通过内部 HTTP/RPC 绕回本项目。独立 Node.js 项目 `../MangoCLI/` 只通过公开 REST API 调用后端，不属于 `src/interfaces/`。
6. `common` 只存真正无业务归属且被多个 App 复用的能力；`common` 生产代码不得导入 `src.apps.*`。
7. 根目录 `runtime/` 只存日志、上传下载文件、媒体、缓存和工作目录；Python 进程源码只放 `src/processes/`。
8. 禁止恢复 `src/services/`、`src/runtime/`、`src/common/tools/`、`src/common/customization/`、App 单数 `service/`、App 根 `urls.py` 和旧 `views/`。
9. 不建立纯重导出、纯转发的兼容 Python 文件；迁移模块时必须同步修改全部调用方并删除旧文件。
10. 所有包含 Python 模块的源码目录必须提供 `__init__.py`，不得依赖隐式命名空间包。
11. 新增或调整目录、跨层导入后必须运行 `python manage.py test src.apps.system.tests.test_architecture_boundaries --env=dev --keepdb`。

### Django App 固定模板

新增 App 或重构现有 App 时必须使用下列模板，不得只参考顶层分类自由命名：

```text
src/apps/<app_name>/
├── __init__.py
├── apps.py
├── models.py | models/              # Model、QuerySet、Manager
├── api/
│   ├── __init__.py
│   ├── urls.py
│   ├── serializers/
│   │   └── __init__.py
│   └── views/
│       └── __init__.py
├── selectors/
│   └── __init__.py
├── services/
│   └── __init__.py
├── exceptions/
│   └── __init__.py                 # App 业务异常；规模较大时再拆 definitions.py 或业务主题文件
├── tests/
│   ├── __init__.py
│   ├── test_models/
│   ├── test_selectors/
│   ├── test_services/
│   └── test_api/
└── migrations/                      # 有数据库模型时
    └── __init__.py
```

固定规则：

1. 常规业务 App 的基础层固定为 `models`、`api`、`selectors`、`services`、`tests`；有数据库模型时必须有 `migrations`。
2. 对外提供 HTTP 时，`api` 内部固定为 `urls.py`、`serializers/`、`views/`；不使用 App 根 `urls.py`、根 `views/` 或将 Serializer 与 View 混在同一文件。
3. 无查询、无写入或无 HTTP 能力的特殊 App 可省略对应空层；一旦新增该能力，必须回到上述固定位置。
4. `enums/`、`exceptions/`、`constants.py`、`schemas.py|schemas/`、`presenters.py|presenters/`、`formatters.py|formatters/`、`tasks/`、`signals.py`、`management/` 是唯一允许按能力增加的通用扩展位置；枚举和异常固定使用包目录，不使用 `enums.py` 或 `exceptions.py`。
5. 不得新建 `service/`、`views/`、`serializers/`、`crud/`、`handlers/`、`logic/`、`repositories/` 等与标准层并行的自定义目录；确有新的通用层需求时，先修改架构方案和本文件。
6. 领域专用子包（例如 AI 的 `agent/`、`context/`、`model_gateway/`）只能存放该 App 内部的单一领域能力，不得替代 `selectors/services/api`，也不得被其他 App 当作公开入口。
7. 跨 App 稳定输出使用 schema、presenter 或 formatter；其中 schema 定义结构，presenter/formatter 只做输出转换，不承载业务写入。
8. 新 App 必须在交付前检查 AppConfig、`INSTALLED_APPS`、项目总路由、迁移包和架构守卫测试；未注册的空目录不算完成。
9. App 异常包较小时，异常类和错误定义直接写在 `exceptions/__init__.py`；超过约 400 行、50 个定义或形成三个以上稳定业务聚合时再拆文件。`exceptions.py` 与 `exceptions/` 不得并存，不建立旧路径兼容转发。
10. 普通业务错误定义只保存数字 `code` 和 `message`；字符串 `error_code` 仅用于调用方必须机器决策的跨进程状态，并优先来自所属枚举。异常构造函数不得写日志或数据库，REST、MCP 在后端协议边界统一标准化，只有未知异常进入系统异常记录；Node.js CLI 只消费 REST 错误协议。
11. 禁止新增 `ERROR_MSG_*`、`API_ERROR_0001`、`*_ERROR_0001` 等编号式异常定义，常量名必须表达具体业务语义；禁止 `ErrorClass(code, message)`、`ErrorClass(*RESPONSE_MSG_*)` 等兼容构造；每个 App 的数字错误码必须唯一，同一码不得对应不同文案。
12. 业务异常和控制流异常类只能定义在所属 `exceptions/`；MCP Tool 不重复捕获模型 `DoesNotExist`，应复用 App Service 的明确业务异常。未知异常响应不得通过 REST 或 MCP 暴露原始异常字符串、数据库信息或内部路径。
13. 项目不使用 Django Admin、默认 auth User/Group/Permission、Session 和 Messages；禁止新增 `admin.py`、`django.contrib.admin`、`django.contrib.auth.models` 业务依赖或 `request.session`。密码哈希可继续复用 `django.contrib.auth.hashers`，身份与权限统一使用自定义 User、JWT 和 `MenuActionPermission`。
14. 运行时路径统一从 `django.conf.settings` 的 `RUNTIME_DIR`、`DOWNLOAD_DIR`、`UPLOAD_DIR`、`GIT_WORKSPACE_DIR` 等配置获取；禁止恢复带全局实例或导入时创建目录副作用的 `project_dir` 包装器。

### 日志管理

1. 后端日志固定使用 `runtime/logs/<service>/{app.log,error.log,django.log}`，不按 App 拆文件，不在业务代码内自建 FileHandler。
2. 业务代码使用 `src.common.logging.log` 或 `logging.getLogger(__name__)`；新增运行进程必须复用统一配置并设置稳定的 `MANGO_SERVICE_NAME`。
3. 后端文件轮转必须保持多进程安全；不得将 `ConcurrentRotatingFileHandler` 换回普通 `RotatingFileHandler`。
4. 当前异常需要堆栈时使用 `exception()`；禁止记录 Token、Authorization、Cookie、密码和完整敏感请求体。
5. 完整文件布局、环境变量和验证要求见 `docs/架构设计/日志管理规范.md`。

## 命令边界

11. 后端目录是 `MangoServer/`。
12. 常用启动命令：`python manage.py runserver --env=dev 0.0.0.0:8000`；多服务本地启动使用 `sh scripts/start_dev_services.sh`。
13. 本地虚拟环境通常是 `.venv/`，Windows 下可用 `.\.venv\Scripts\python.exe`。
14. 后端依赖按环境使用 `requirements/dev.txt`、`requirements/test.txt`、`requirements/master.txt`；公共依赖写入 `base.txt`，本地 wheel 写入 `local.txt`，不得恢复根目录 `requirements.txt` 或 `requirements-local.txt`。
15. 开发过程中不允许执行生成迁移脚本命令。
16. 开发过程中不允许执行迁移命令。
17. 迁移脚本由用户自己生成和执行。
18. 如模型发生变化，只说明需要迁移，不要运行 `makemigrations` 或 `migrate`。

## 模型与迁移

四类模型的目录与职责边界：

1. Django Model 只放在 `src/apps/<app>/models.py|models/`，负责表、关系、QuerySet、Manager 和最小领域行为。
2. Pydantic Schema 只放在 `src/apps/<app>/schemas/` 或 `src/common/schemas/`，负责 Service 输入输出、JSONField 结构、快照和值对象；不得直接查询 ORM。
3. DRF Serializer 只放在 `src/apps/<app>/api/serializers/`，只服务 HTTP 校验和展示；Service、Selector、Process 和 MCP 不得导入。Node.js CLI 通过 REST 契约交互，不导入任何 Django Python 模块。
4. dataclass 只表达单进程内部计算状态和值对象，不作为 HTTP、MCP、Socket、任务或队列协议。
5. 后端与执行器共享的 wire payload 固定放在 `mangotools/contracts/` 并继承 `ContractModel`，不得在两端重复定义；同名字段漂移必须由所属 App 的显式 adapter 转换。
6. App Schema 按语义选择 `StrictSchema`、`TrimmedStrictSchema`、`FrozenSchema`、`OrmSchema`；跨进程协议使用 `ContractModel` 的追加字段兼容策略。
7. 禁止 `schemas/models/`；Schema 与 Django Model 文件按业务聚合拆分，`__init__.py` 只显式导出稳定名称。
8. 模块迁移必须一次性更新全部引用并删除旧文件，不保留纯转发。共享协议变更必须更新 JSON Schema 快照并执行序列化往返测试。
9. ORM 时间审计基类的抽取必须单独进行字段矩阵与 migration state 评估，不得与目录拆分混做。当前 `perf.AuditModel` 保持 App 私有。
10. 完整规范、基类选择、共享协议和验收命令见 `../docs/架构设计/项目模型与Schema分层规范.md`。

17. 修改模型前先确认历史迁移和线上表结构。
18. 新增字段要考虑默认值、历史数据、空值和序列化兼容。
19. 删除字段时同步检查 serializer、services、selectors、MCP 和前端返回字段。
20. `JSONField` 必须有明确结构约定，不能随意存任意 JSON。
21. JSON 配置建议配合 Pydantic、校验函数或枚举常量定义结构。
22. 外键删除策略优先参考相邻模型，并按业务数据生命周期设计。
23. 强依赖的附属数据随主业务资产删除时使用 `CASCADE`，避免保留无用孤儿数据，例如元素删除时清理元素快照、自愈记录等附属记录。
24. 上层归属、项目产品、模块、用例、页面、步骤等边界关系优先使用 `PROTECT`，防止删除上层对象时静默清理大量业务数据。
25. 审计、来源、最近操作人、可选引用等弱关系允许 `SET_NULL`，不应因为用户或来源记录删除而误删主记录。
26. 表名沿用 `db_table` 显式命名风格。
26.1 `null=True` 表示数据库允许 `NULL` 时，字段必须同时设置 `blank=True`，保证 Model、Serializer 和 `full_clean()` 的可选语义一致；`JSONField(default=list/dict)` 允许空容器时也必须设置 `blank=True`。不得用 Service 绕过模型校验掩盖字段定义错误。
26.2 所有业务模型和字段必须有可读的 `verbose_name`。`src.common.database.model_metadata.apply_database_comments()` 会在 Django 启动后将其同步为原生 `db_table_comment`/`db_comment`；数据库说明与界面名称不同时，可显式声明 `db_comment`，统一逻辑不得覆盖显式值。
26.3 新表、新列表接口和高频任务查询必须评估索引。索引设计以实际查询条件、排序/分组、表规模和只读执行计划为依据：复合索引通常先放稳定等值条件，再放范围条件和排序字段；不要重复主键、唯一约束、外键自动索引或已有复合索引前缀；低区分度状态字段原则上不单独建索引，应与时间、归属或任务领取字段组合。
26.4 `Meta.indexes` 中的索引必须显式命名，名称表达查询用途并满足数据库长度限制。新增索引需说明对应查询路径和写入成本；模型调整后运行架构守卫，但迁移脚本仍由用户生成和执行。

## 序列化与查询

27. 列表接口注意 `select_related`、`prefetch_related`，避免 N+1。
28. 详情接口如果返回嵌套对象，应统一 serializer 输出。
29. 搜索字段要和前端查询组件一致。
30. 每个数据库模型原则上分别对应 `api/views/<model_or_table>.py` 与 `api/serializers/<model_or_table>.py`；ViewSet、Serializer 和 Service 不再混放在同一文件。
31. 参考 API Case 的 serializer 分层：无 `C` serializer 用于写入和轻量基础字段，`C` serializer 用于需要嵌套对象的读取展示。
32. 表相关的自定义接口必须放在 `api/views/` 中该表对应的 ViewSet 下，例如 `ApiCaseViews`；ViewSet 必须显式声明 `model` 和 `serializer_class`。
33. 如果一个接口最终创建、查询、更新或展示某张表的数据，应归到该表对应的 `api/views` 文件；跨表业务流程放入所属 App 的 Service，不新建游离的聚合 View 文件承载业务方法。
34. 禁止新增仅用于旧导入路径的聚合、重导出或转发文件；`__init__.py` 只导出明确、稳定的包级公开接口。
35. 列表接口不要随意增加冗余 `*_name`、`*_id` 展示字段；优先返回真实外键字段或必要的嵌套对象。
36. 当列表项包含父对象且只需父对象基础字段时，父对象使用无 `C` serializer，避免父对象内部的项目产品、模块、用户等再次展开成大对象。
37. 项目产品、模块字段如果页面需要展示层级路径，可在当前列表项上返回必要嵌套对象；不要让嵌套父对象继续展开无关外键。
38. 大列表接口谨慎返回重字段、大 JSON、长文本、上下文资料正文和多层嵌套对象。
39. 按模块过滤时考虑跨模块依赖，不能阻断合法关联实体。

### 产品模块路径

- 产品模块完整路径统一由 `ProductModule.get_full_path()` 基于 `parent` 关系生成，并通过模块 serializer 的 `full_path` 返回；业务代码不得使用 `superior_module_1/2` 拼接展示路径。
- Serializer 使用 `ProductModuleSerializers` 或 `ProductModuleSerializersC` 嵌套返回模块时，必须实现 `setup_eager_loading` 并调用 `ProductModuleService.with_full_paths(queryset, '<模块关系字段>')`，禁止在逐条序列化时查询父模块。
- 新增或修改嵌套模块 serializer 后必须执行 `python scripts/audits/product_module_path_audit.py`，确保没有遗漏模块路径预加载。

## AI 与功能测试约定

40. `functional_test` 只负责需求、用例、资料、绑定、统计和落库；AI、Skill、MCP、Agent、上下文历史、任务阶段和对话展示统一放在 `ai` app。
40.1 `ai/agent/` 只保存 Agent 工作流、规划器、生成器和领域算法；带 `Service` 职责的上下文、文档、预算、租约、任务阶段、Skill、MCP 调用和 Harness 实现必须放在 `ai/services/` 的对应业务子包。
40.2 AI Worker 的进程入口固定放在 `src/processes/ai_worker/`，仅调用 `ai.services`；不得恢复 `ai/runtime/`。Harness 不建立 App 顶层并行目录，固定放在 `ai/services/harness/`。
40.3 AI 的 MCP 查询输出使用 `ai/selectors` 与协议无关 presenter，不得复用 DRF Serializer；跨 App 读取调用目标 App Selector，跨 App 写入调用目标 App Service。
41. 功能测试用例由 AI 生成时，不要求 AI 输出 `project_product_id`、`module_id`，后端落库必须使用当前需求的项目产品和模块。
42. 用户手动新增或编辑功能测试用例时，可以单独修改用例自己的项目产品和模块；读取、筛选、模块导航和 API 自动化生成以用例自身字段为准。
43. 功能测试用例编号统一使用 `FT-{四位序号}`，AI 生成和后端兜底都遵守同一规则。
44. 生成 API 自动化时，Skill 决定执行规范，MCP 提供真实工具能力；后端只做基础结果校验和业务落库校验。
- 提示词集中管理：所有后端 AI 静态提示词统一放在 `src/common/prompts/catalog/`，按业务能力拆分 YAML，并在 `registry.py` 显式登记。YAML 保存正文、角色、输出格式、场景 focus、owner 和 version；Python 只做 Pydantic 校验、安全模板渲染和动态消息组装。Service、View、Model、process、任务执行器只传入业务数据，不允许内联 system/user 提示词。测试桩、用户原始输入以及数据库中的 Skill/MCP 自定义内容不属于平台静态提示词正文。

## 枚举规范

45. App 私有业务枚举固定放在 `src/apps/<app>/enums/`；真正跨 App、无业务归属的枚举才放 `src/common/enums/`；后端与执行器共同使用的跨进程协议枚举放在 `mangotools.enums`。
46. `enums/` 必须按业务主题拆分文件，例如 `case.py`、`execution.py`、`auth.py`；禁止恢复 `tools.py`、`system.py`、`api.py`、`ui.py` 等大杂烩文件。
47. `enums/__init__.py` 只允许显式导出稳定公开枚举；整个 `MangoServer/src` 与 `MangoActuator/src` 禁止 `import *`。
48. Service、Selector、Process、View、Serializer 和 MCP 适配层不得定义业务枚举，也不得用只含大写常量的类模拟枚举。
48.1 后端与执行器交换的任务状态、用例类型、客户端类型和 Socket 消息类型必须使用共享协议包的单一定义；Socket 下发命令与上报事件分别使用 `Server*CommandEnum`、`Actuator*EventEnum`，不得使用同名不同值枚举。
48.2 枚举迁移必须同步更新所有引用并删除旧文件，不建立兼容重导出文件；已有数据库值、接口 key 和枚举 value 默认保持不变。
48.3 `/system/enum` 由 `EnumCatalogService.catalog()` 显式注册，不得通过通配符导入或运行时扫描隐式暴露枚举；接口 key 是前端协议的一部分。
48.4 枚举值变更必须同步检查数据库字段、Serializer、Service、Process、MCP、REST 契约、Node.js CLI、执行器、前端展示和测试。
48.5 修改枚举后必须运行 `python scripts/audits/enum_inventory.py`、`python manage.py test src.apps.system.tests.test_architecture_boundaries src.apps.system.tests.test_enum_catalog --env=dev --keepdb`，并确认没有同名不同值枚举。
48.6 数据工厂执行状态语义：`0 失败，1 通过，2 待开始，3 进行中`。

## 数据工厂核心约定

49. 工厂实体只描述单表字段规则，不直接绑定具体业务场景。
50. 场景模板是业务入口，可以包含一个主模板和多个关联模板。
51. 后端模型可继续叫 `DataFactoryTemplate`，产品语义是“场景模板”。
52. `DataFactoryTemplateItem` 表示场景里的关联模板。
53. 关联模板默认启用，不再设计 `enabled` 字段。
54. 关联模板清理策略继承场景模板，不再单独维护 `cleanup_strategy`。
55. 关联模板顺序使用 `sort`，后端按 `sort,id` 执行。
56. 执行场景模板时，主模板和关联模板共享同一个运行上下文。
57. 子模板依赖主模板时，应复用上下文，不应重复创建主表。
58. 工厂实体字段规则中的“依赖实体字段”只保存依赖实体和字段。
59. 状态/场景/API 覆盖层才选择具体依赖模板。
60. 依赖字段执行仍以 `template_id` 创建依赖数据。
61. 多表场景必须通过关联模板表达，不要让主表反向自动创建所有子表。

## MCP 规范

62. MCP 工具描述要面向调用者，不要只写后端字段名。
63. 创建/更新场景模板时要支持 `items`。
64. MCP 返回场景模板详情要包含主模板字段和关联模板列表。
65. MCP 应明确工厂实体是单表规则，场景模板是完整业务对象。
66. MCP 入参示例必须和后端校验结构一致。
67. 前端能力变更时，MCP 文案和参数也要同步。
68. MCP Tool 必须优先调用所属 App 的 Selector、Service、schema 和 presenter；不得导入 `api/views` 或 `api/serializers`，也不得通过兼容聚合文件间接依赖 HTTP 层。
69. 功能测试 MCP 写操作必须复用现有 serializer/service 规则，不能绕过功能测试用例必填、枚举、绑定和统计刷新校验。
70. AI 查询 MCP 只提供任务、阶段、工具调用、上下文、Skill、MCP 服务和工具快照等只读能力，不提供绕过页面的 AI 配置写入。
71. MCP 查询类工具必须支持分页：所有 `list_*`、`search_*` 以及会返回明细列表的查询工具，都应提供 `page`、`page_size` 入参，默认 `page=1`、`page_size=10`；返回结构统一包含 `items`、`count`、`page`、`page_size`。调用方需要更多数据时自行翻页，不允许默认一次性返回大列表。
72. MCP 详情类工具如果内嵌可能超过 10 条的子列表，应优先提供独立分页查询工具；确需在详情中返回子列表时，也必须提供子列表分页参数，例如 `case_page`、`case_page_size`，默认只返回 10 条。
73. 新增 MCP 写操作工具时，必须走 `src/interfaces/mcp/server.py` 统一演示环境写操作校验；工具名优先使用既有写操作前缀：`create_`、`add_`、`copy_`、`upload_`、`bind_`、`batch_`、`batch_generate_`、`execute_`、`debug_run_`、`update_`、`set_`、`sort_`、`refresh_`、`auto_generate_`、`delete_`、`cleanup_`、`clear_`。
74. 如果新增 MCP 工具会写库、改配置、上传文件、绑定关系、清理数据或真实执行落库，但工具名无法使用上述前缀，必须同步更新 `src/interfaces/mcp/server.py` 的 `_tool_operation` 分类；如果是查询、预览、分析或允许演示环境执行的测试任务，确认不需要加入写操作分类。
75. 新增 MCP 工具或独立领域端点后，必须验证工具同时注册到主 `/mcp` 和对应领域端点，并通过带目标权限身份的真实 MCP `list_tools` 调用确认客户端能够扫描到；不能只检查注册函数或未经过中间件的工具列表。

## API 协议兼容

73. 已存在接口路径尽量保持兼容，例如 `/data-factory/template`。
74. 产品文案可从“状态模板”改为“场景模板”；外部 URL 可按兼容要求保留，但 Python 模块不得为旧路径保留转发文件。
75. 接口新增字段要兼容老客户端缺省值。
76. 接口移除字段前可在 serializer 入参处忽略旧字段，避免老请求失败。
77. 不要让前端必须一次性加载所有实体、模板、字段。
78. 大数据量场景应按模块、实体懒加载。

## 测试与验证

79. 常规后端改动至少运行 `python -m compileall -q src`、`python manage.py check --env=dev` 和最小相关测试。
79.1 目录、模块位置或跨层导入发生变化时，必须运行架构守卫测试，并扫描确认旧路径没有重新出现。
79.2 修改 `src/processes/` 或管理命令时，必须至少验证对应管理命令的 `--help` 导入，避免部署后进程无法启动。
79.3 修改 `requirements/`、Dockerfile 或安装脚本时，必须检查所有引用路径；环境具备 Docker 时执行 Docker 构建检查。
79.4 数据工厂改动至少跑相关 compile/test 或最小测试集。
80. 场景模板测试要覆盖无关联模板、有关联模板、子模板缺字段。
81. 跨模块依赖要作为重要验证场景。
82. 复用上下文要验证不会重复创建主表。
83. 修改枚举后要验证前端展示和后端状态流转。

## 代码风格

84. Python 代码保持项目既有格式，不引入不必要的新框架。
85. 注释只写复杂业务原因，不写显而易见的代码翻译。
86. 查询条件、JSON key、枚举 key 尽量集中定义。
87. Service 方法要命名清楚，避免一个方法同时做预览、执行、清理。
88. 事务边界要明确，执行造数和执行记录更新需考虑失败状态。
89. 记录日志时避免输出敏感 token、Authorization、密码。
90. 最终交付时说明改了哪些文件、是否需要迁移、跑了哪些验证。
