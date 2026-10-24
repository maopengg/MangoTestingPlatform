# Python FastAPI 与 Pydantic 扫描

使用 `scripts/scan_fastapi_ast.py`，它是 Python AST 确定性接口/源码索引器，不替代 AI 追踪或生成完成业务链。发现后仅用 `rg` 导航。

适配仅限 FastAPI/Starlette 路由与 Pydantic；Flask、Django、Sanic、生成路由或不支持构造记越界 Gap，不套 FastAPI 假设。

## 路由清单

仅静态确认的 `FastAPI`、`Starlette`、`APIRouter` 实例识别 HTTP 装饰器：

- `get`、`post`、`put`、`patch`、`delete`、`options`、`head`；
- `api_route(..., methods=[...])`；
- Starlette 兼容 `route(..., methods=[...])`；
- 可静态解析 router 前缀和无条件模块级装饰器别名。

FastAPI/Starlette/Pydantic 符号须证明官方导入来源。同名本地、歧义/条件导入、重新绑定、未解决项目转导出不算框架证据。

动态路径/方法、条件/嵌套路由注册、程序化修改、未解 `include_router`、挂载、反射、生成和monkey patch记清单Gap，不凭装饰器拼写猜路由。

## 请求契约入口

索引只记handler参数及AST注解/默认供导航，AI须查：

- path/query/header/cookie/body/form/file/dependency 参数；
- Pydantic 字段、别名、默认、`Literal`、枚举、联合、集合、受限类型、`Annotated`；
- `Field` 长度、范围、regex/pattern、倍数等约束；
- v1/v2字段/模型validator、跨字段、规范化及显式抛错。

脚本不解释模型体/validator；模型名是追踪入口，不证明约束或业务结果。区别框架拒绝和controller/service业务拒绝，写精确状态/业务码前查异常封装。

## 调用切片

索引后由AI而非脚本按需追：请求schema/依赖 → handler → 应用服务 → 领域校验/状态机 → repository/租户过滤 → 外部/异步 → 异常响应映射 → 副作用/清理。

触发、结果、权威对照、数据和清理准确才停止。未解动态调用、registry、依赖实现或异常映射记Gap。不能因handler调了service就称链完整；跨文件影响行为的导入函数、依赖、领域/仓储、异常和异步外部都需追，无法证明的动态分派/注入目标保留Gap。

## 控制流

AI从相关链提成功变体、早返回、`if/elif`、`match`、显式raises及映射异常，脚本有意忽略函数体。无else/wildcard须追后续才定HTTP结果，语法穿透不是判定依据。

不机械将索引转图/场景/断言；只用来定位路由、参数、注解/默认和行号，AI验证模型、validator、分支、调用、语义和跨文件目标后才建图Case。成功退出、`analysis_ready`、兼容别名 `case_generation_eligible` 仅说明索引结构可用。

AST是候选证据，不是产品真理、完成链或运行覆盖；有匹配修订OpenAPI/运行路由则核对，否则标 `静态接口清单`。只有同修订/源码分支arc的 `coverage.py --branch` 证明时才报 `运行时分支已命中`。
