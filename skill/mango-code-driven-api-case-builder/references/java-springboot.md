# Java Spring Boot 与 Bean Validation 扫描

由 AI 从启动配置、组件注册、映射声明及处理器核实 Spring 路由，按入口 Skill 的证据与双向对账规则完成清单；无需 JDK 也可直接追踪源码。`scripts/scan_springboot_ast.py` 是可选辅助，内部调用 JDK Compiler Tree API；不以正则命中或脚本结果单独证明完整性。

仅选择上述工具时先运行 `python3 scripts/scan_springboot_ast.py --check-runtime`，可用 `--java-home <已有JDK目录>` 或 `JAVA_HOME` 指定已有运行时。检查实际进程及编译模块，不只看 PATH；缺依赖改由 AI 核实源码，不自动安装/下载，不启动或构建被测应用。最终清单是否可上传取决于注册证据，不取决于是否运行该工具。

工具适配限 Java Spring MVC 注解与 Jakarta/Javax 校验。JAX-RS、WebFlux `RouterFunction`、生成或自定义注册由 AI 追实际入口及绑定关系，不套 MVC 假设；仅未解析部分记 Gap，不因超出工具支持范围直接判不可扫描。

## 路由清单

导入或全限定证明 `org.springframework.web.bind.annotation` 来源才识别类/方法：

- `RequestMapping`；
- `GetMapping`、`PostMapping`、`PutMapping`、`PatchMapping`、`DeleteMapping`。

读 `value`/`path` 数组和 `RequestMapping.method`，合类/方法路径，不折叠版本。

映射注解本身不证明服务端入口：确认官方 Controller/RestController 或本次源码中可追溯至它们的组合注解；Feign 客户端声明不计服务端接口。无注册证据的接口/类映射记 `SPRING_SERVER_REGISTRATION_UNRESOLVED`，继承、外部组合注解或动态注册未解时不静默漏算，也不凭类名认定入口。

同一源码处理方法、相同 Method/规范路径的重复别名合并，`declared_paths` 保留原路径；不同方法的规范身份冲突仍阻塞对应接口。合并不证明所有部署版本的尾斜杠匹配行为相同，需验证的实际路径按部署契约保留，不能跨方法消除冲突。清单质量及局部上传遵循入口 Skill，探索性参数仅影响退出码，不提升完整性。

常量、组合/元映射、继承及自定义注册先由 AI 追项目内定义、注册与调用方；脚本未解析不代表代码无法核实。`@Profile`/`@Conditional*` 等另核目标条件，必要时用已有同修订 OpenAPI/Actuator/运行路由交叉核对；证据仍不足才为对应 Gap，不冒称运行已启用。

清单与分析质量分开。仅影响路由是否存在或Method/path的不确定才阻清单。绑定来源、`@Valid`级联、校验组、自定义validator、响应语义保留已证路由，入其 `analysis_gaps`。仅这些警告时产物成功退出且 `status=completed_with_gaps`，不证明调用链/Case完成。

`--route-prefix` 只给保留路由输出分析警告，越界路由的绑定/校验警告不使选定模块清单失败或降级。

## 请求与校验证据

查参数和DTO字段/record组件：

- `RequestParam`、`PathVariable`、`RequestHeader`、`CookieValue`、`RequestBody`、`RequestPart`、`ModelAttribute`；
- 存在时Jackson别名/必填；
- Jakarta/Javax空、大小、范围、正负、pattern/email、位数、时间；
- 枚举声明、明确默认与必填标记。

内置约束仅认 `jakarta.validation.constraints`/`javax.validation.constraints`。自定义、groups/payload、`@ConvertGroup`、级联 `@Valid`、分组 `@Validated`，查实现/激活组/异常映射前未解。请求绑定、controller、响应状态、校验注解均须官方来源，同名本地/第三方不提供确定契约证据。

## 业务判断由 AI 完成

查controller/service的 `if/else`、三元、`switch`、早返回、显式throws、响应构建及异常映射；脚本不输出推断路径。未追 `@ControllerAdvice`、`@ExceptionHandler`等，不假定异常变HTTP状态。缺else/default须追后续，语法穿透只是待审核项。

## 调用切片

由AI按需追：映射绑定 → 校验/认证租户拦截 → controller/应用服务 → 领域状态 → repository/DB事务 → 外部客户端/事件/异步重试 → 异常响应 → 副作用清理。

只追业务实现、动态分派、自写 advice/拦截、业务 SQL/Mapper XML、事务和异常处理；业务目标未解记 Gap，不凭方法名猜。底层代理、框架 AOP、生成 Mapper、SDK 内部按入口 Skill 止于依赖边界，不下载或反编译依赖包；缺其源码不单独构成 Gap，必要业务结果未知仍须注明。

使用工具时不机械将索引变图/Case/断言；AI 核实其输出并补查分支、调用、语义及跨文件目标后再设计。成功退出、`analysis_ready`、兼容 `case_generation_eligible` 只表示索引可用，不是必须具备的扫描验收字段。

AST不证明产品正确、链完成或运行覆盖。有匹配修订OpenAPI/Actuator/运行数据则核对，否则 `静态接口清单`；只有同修订源码分支JaCoCo证据才称 `运行时分支已命中`。
