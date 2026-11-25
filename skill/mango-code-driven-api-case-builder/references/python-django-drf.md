# Django / DRF：AI 路由核查

不使用 FastAPI 脚本套扫，也不要求专用扫描器。AI 按入口 Skill 固定仓库/修订及目标配置，从实际 URL 根追到视图，保留源码位置、完整路径、HTTP 方法、处理器与注册依据。

## 接口盘点

- 从 settings/入口核实 `ROOT_URLCONF`，逐层追 `urlpatterns`、`path`、`re_path` 和 `include`；拼接实际前缀，namespace/name 不当作 URL。多个目标配置或条件注册分别说明范围，不能只扫一个 urls 文件就称全产品完整。
- 函数视图核对 `require_http_methods`、`api_view` 及实际方法分派；类视图追 `as_view()`、基类和项目内覆盖的方法，不把普通类方法全算接口，也不把框架默认 OPTIONS/HEAD 猜成独立业务能力。
- DRF 核对 Router 实例、`register`、挂载位置、ViewSet 的有效 action/mixin、显式 `as_view` 方法映射，以及 `@action` 的 detail、methods、url_path 和后续 mapping。未实现/未注册的 action 不计入；basename 不等于 URL 前缀。
- 项目自定义 Router、基类、装饰器、动态 URL 工厂和条件注册追项目内实现；正则/路径转换器保留真实匹配约束，不能用随意替换构造假路径。无法确定的方法、路径或注册条件单列缺口。
- 双向核对全部注册入口和视图候选，区分内部函数、出站客户端及未挂载视图；同处理器重复引用与不同处理器冲突分别处理。有已有同版本 OpenAPI/运行路由则交叉对账，不为扫描启动项目、导入 Django 应用触发初始化或执行管理命令。

## 第二阶段业务分析

逐接口追 serializer 字段及 validate/create/update、permission/authentication、filter/queryset/object 作用域、视图/action、应用服务、事务和项目异常映射；依赖中间件或自定义分派影响业务时核实调用侧规则。框架/ORM 内部仍止于依赖边界，不遍历安装包补图。

接口注册已核实不代表业务预期正确、所有权限已验证或已自动化；两阶段上传、缺口及安全规则沿用入口 Skill。
