# Java Spring Boot 与 Bean Validation 扫描

用 `scripts/scan_springboot_ast.py` 调内置 `SpringBootAstScanner.java` 的 JDK Compiler Tree API，须JDK。只是确定性接口/源码索引，不替代AI追踪，不生成完成链。不以正则证明路由/分支，`rg`仅导航。

适配限Java Spring MVC注解与Jakarta/Javax校验。JAX-RS、WebFlux `RouterFunction`、Kotlin特有、生成或其他不支持路由记Gap，不套MVC假设。

## 路由清单

导入或全限定证明 `org.springframework.web.bind.annotation` 来源才识别类/方法：

- `RequestMapping`；
- `GetMapping`、`PostMapping`、`PutMapping`、`PatchMapping`、`DeleteMapping`。

读 `value`/`path` 数组和 `RequestMapping.method`，合类/方法路径，不折叠版本。

未解常量、同名自定义注解、组合/元映射、`@Profile`/`@Conditional*`、继承、反射、生成源码、动态注册，直到修订匹配OpenAPI/Actuator/运行路由解析前为Gap。

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

不机械将索引变图/Case/断言；仅定位映射、绑定、框架约束、枚举、显式响应状态、源码位置，AI查分支/调用/语义/跨文件后再设计。成功退出、`analysis_ready`、兼容 `case_generation_eligible` 只表示索引可用。

AST不证明产品正确、链完成或运行覆盖。有匹配修订OpenAPI/Actuator/运行数据则核对，否则 `静态接口清单`；只有同修订源码分支JaCoCo证据才称 `运行时分支已命中`。
