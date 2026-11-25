# API 创建资源的编写与清理

适用于 API 本轮创建 SQL 行并同步 ES 的 Case，包括预期拒绝创建、同名重复创建和创建后删除。先读 Skill 的授权、运行时数据及生产边界；本教程不授权改业务代码、直接修平台库或清共享数据。

## 1. 先确认目标服务能力

通过 MCP 读取 `get_api_case_schema`、`get_api_case_resource_cleanup_schema`，核对实际 `update_api_case` 的 `resource_cleanup`、`get_api_case_resource_cleanup_results` 和 `cleanup_api_case_resources` 签名。已有连接可能缓存旧工具定义，必要时重新连接再获取。读取 Skill catalog 的版本并更新 Skill 及本参考文件，不只读取旧本地副本。

Schema 和真实工具均支持时才能使用。缺参或返回不支持，记录目标服务、具体字段和错误，停止受影响的写入，不用 SQL 直查工具、脚本、内部 HTTP 或修改平台元数据绕过。表结构发现允许；业务 SQL 证据使用另行授权的专用数据库工具，或正式 Case 已保存的获准 SQL 配置，不创建临时 Case 充当任意查询入口。

## 2. 先建立归属矩阵

每种资源列明：创建方、触发步骤、数据源、租户/创建人来源、精确标识、关联关系、异步副作用及清理方式。工厂资源与 API 资源分别登记，不伪造工厂执行记录。

以下标识用途不同，应分别从目标契约确认：

| 作用 | SQL/响应来源 | 清理用途 |
| --- | --- | --- |
| 自增主键 | 目标表自增字段，由数据库生成 | 锁定 SQL 根行；禁止预填或随机生成 |
| 业务 ID | 业务唯一字段及对应响应路径 | 关联 SQL 子表及 ES 业务身份 |
| ES 文档 ID | 文档标识字段及对应响应路径 | 精确定位 ES `_id`，不是 SQL `_id` |
| 业务版本 | 根行版本及对应响应路径 | 与 ES 中的业务版本比对 |
| ES 并发版本 | ES `_seq_no`、`_primary_term` | 平台条件删除，不能由 Case 编造 |

实际表、字段、响应路径和 ES 映射必须从目标环境 schema、匹配运行版本的写入/同步代码及获准精确观测确认。示例不是其他产品的默认规则。共享前置只读复用，不加入清理目标。

## 3. 正向创建的配置示例

先保存 Case、创建步骤，取得真实步骤 ID 和 API Info ID。触发步骤仅一个场景且关闭失败重试，避免一次规则无法区分多个创建请求。需要多个创建时拆成各有规则的有序步骤，不删原覆盖。

以下是 `update_api_case.resource_cleanup` 的完整列表示例（不是外层 `{ "rules": [...] }`）；数字是说明用资产 ID，须换成目标产品真实 ID。租户和创建人使用本轮已验证缓存，不写死业务 ID：

```json
[
  {
    "key": "record_seed",
    "trigger_step_key": "step-101",
    "api_info_id": 201,
    "sql_datasource_alias_id": 1,
    "es_datasource_alias_id": 2,
    "table": "example_record",
    "primary_key": "_id",
    "business_id_field": "id",
    "document_id_field": "document_id",
    "version_field": "version",
    "tenant_field": "tenant_id",
    "creator_field": "creator_id",
    "unique_field": "name",
    "request_unique_path": "name",
    "tenant_cache_key": "current_tenant_id",
    "creator_cache_key": "current_creator_id",
    "response_id_path": "data.recordId",
    "response_document_id_path": "data.documentId",
    "response_version_path": "data.recordVersion",
    "index_template": "example_record_{tenant}",
    "es_tenant_path": "tenantId",
    "es_business_id_path": "records[].recordId",
    "es_document_id_path": "documentId",
    "es_version_path": "records[].recordVersion",
    "children": [
      {"table": "example_record_child", "foreign_key": "record_id", "root_field": "id", "tenant_field": "tenant_id", "max_rows": 1000}
    ],
    "observation_seconds": 15,
    "poll_seconds": 1
  }
]
```

请求体对应字段使用 `${{api_resource_record_seed}}`，例如 `body_config` 中 `name` 引用该表达式。平台在触发步骤前提供本轮 `AUTO_...` 名称；不要自己固定名称，不为了复制名称额外写前置函数。缓存键、请求路径要与真实请求体及身份上下文一致，不能把示例名字当现成变量。

`children` 按删除顺序排列，均以精确根身份加租户定位；核实真实外键、业务引用和行数上限，不能凭表名推断关联已列全。上限按真实场景评估，不能遇到超限就无依据扩大。表结构变更后，核实真实关联再更新对应 Case 的清理规则。

更新 `resource_cleanup` 是完整列表替换：先回读原列表，保留其他合法规则，不只提交本次新增项；不传表示保留，`[]` 会清空配置。保存后回读 Case，核对步骤、规则、请求唯一名称及原业务断言全部保留。

### ES 数组的边界

- 对象路径用 `owner.id`，数组身份用 `records[].recordId`，不是 `records.recordId` 或 `records[0].recordId`。
- 当前仅支持首段的一层数组；业务 ID 与业务版本必须在同一数组，如 `records[].recordVersion`。
- 整份文档删除要求数组恰好包含一个本轮对象。数组空、多元素、夹带其他对象、身份/版本不匹配均拒绝；不能写成“找到一个匹配元素即可删整文档”。共享多对象文档需要其他已验证的安全能力，不能关闭归属校验绕过。
- `sourceVersion` 不自动等于业务版本；按实际同步代码选择对应字段。平台仍验证精确索引 UUID、文档 ID、租户、业务身份/版本及条件删除版本。

## 4. 负向创建与重复名称怎么写

**预期拒绝也要配置资源清理。** 后端回归可能意外创建成功，不能以“本来应该失败”为由只写拒绝断言、不配清理。

当前支持的明确拒绝契约是字段精确匹配布尔 `false`，例如接口确有此契约时配置 `"rejection_response": {"success": false}`。它只是清理分支判据，不替代“请求被拒绝、数据未部分保存”的业务断言。不能为符合该契约修改响应或伪造 `success=false`；若接口只有数值错误码，应如实报告该分支尚不支持，不能猜测填入数值或字符串。

- 返回完整创建 ID、文档 ID 和版本：先登记本轮资源，再做业务断言；负向断言失败后仍自动清理。
- 明确拒绝且没有任何创建标识：平台在完整观察窗口核查没有本轮新增 SQL。没有产生资源时，不宣称对一个未知 ES 文档做过回查；结合业务写入契约判断是否仍有未覆盖副作用。
- 超时、5xx、部分标识或拒绝后发现新增行：保留待核查/清理失败证据，不能伪装成“没有创建”，不重复发送创建请求碰运气。

重复名称测试需要两个独立步骤和两条规则：先建 `record_seed`；第二规则使用新 `key=record_duplicate`、真实第二步骤 ID，并配置 `"name_source_key": "record_seed"`。第二请求名称引用 `${{api_resource_record_duplicate}}`，平台复用同执行前序资源名称；两个规则的目标数据源、根表、身份字段和租户来源保持一致。第二请求意外成功时单独登记，按逆序清理本轮创建的两条记录；不接管其他执行或共享同名行，不把“创建被允许”改成业务通过。

## 5. 执行、清理与验收

1. 回读目标环境的绑定写权限、真实结构、完整 Case 与清理列表，核对每个创建步骤单场景、无失败重试；原生能力可表达的请求、变量、断言不藏进函数。
2. 在授权的 test/dev 完整执行编辑态。平台先冻结创建前唯一键与目标，取得响应身份后登记；不使用工厂的“插入前 ES 必须不存在”规则冒认 API 响应后的文档为存量。
3. 无论断言成功、失败或后续步骤失败，都查看执行级清理结果。先清 SQL 子行和根行，再核验 ES 归属并条件删除，完整观察窗口防止异步写回，末尾连续零残留核验。单 Case 同步清理或正式报告调度清理，以当前入口实现为准，不提前报通过。
4. 调 `get_api_case_resource_cleanup_results(case_id=..., trace_id=..., page=1, page_size=10)`，分页查完全部资源；需要详情用精确 `resource_id`。核对实际创建资源数、SQL/ES 清理、失败及未知占用，不只看步骤成功数。
5. 用获准专用工具独立精确核对本轮 SQL 根/关联及 ES 文档；逻辑删除、`valid=false`、数据库查零、工厂成功均不能单独证明 ES 零残留。索引不存在、连接/权限失败不能冒充文档不存在。
6. 在授权范围验证业务成功路径及受控断言失败后的清理，不改共享 Case 断言刷失败。业务失败保留失败；“业务通过/清理失败”和“业务失败/清理成功”分别汇报，未闭环不提交预发布。业务失败后是否继续其他 Case 遵守用户约定，不自动扩围。

同一根资源会被后续更新/删除、版本字段会变化时，先核对当前所有权/版本快照如何随业务动作维护。不能假定创建时冻结的版本永远有效；版本冲突或共享文档需保留证据，不能改规则放宽核验来通过。

目标 MCP Schema 支持 `version_updates` 时，在原创建规则里声明每个后续版本变更步骤，例如：

```json
{
  "version_updates": [
    {
      "trigger_step_key": "step-102",
      "api_info_id": 202,
      "request_id_in_url": true,
      "response_id_path": "data.id",
      "response_version_path": "data.version",
      "success_response": {"success": true}
    }
  ]
}
```

这是创建规则的字段片段，不是另一条创建规则；替换示例步骤/接口ID，回读完整列表后保存。
请求ID来自正文时改用 `request_id_path`，与 `request_id_in_url` 二选一。变更步骤单场景、关闭失败重试，
响应须返回本轮业务ID和递增版本；请求前SQL身份/版本须与原证据一致，响应后SQL必须精确匹配新版本，
其余身份不变。平台保留创建快照，另存本执行版本证据链，清理使用已核实的末端版本并继续ES条件删除。
接口未返回新版本、请求超时、外部修改、证据不连续时不能自动采用SQL当前版本；报告明确缺口，
不能伪造响应或补写历史版本。教程字段片段不能直接作为 `resource_cleanup` 的完整载荷。

只清同一资源一次：原生规则覆盖的 SQL/ES 不再交给旧 `posterior_sql` 或末尾业务步骤重复兜底删除。迁移旧配置前逐项证明原生规则已覆盖全部目标及依赖顺序；保留原业务删除测试步骤和无关清理，不能整批清空未审计后置。

## 6. 历史失败如何恢复

先查原 `trace_id/resource_id` 台账并确认原执行已结束，再用 `cleanup_api_case_resources(case_id=..., resource_id=..., preview=true)` 预检；在已有精确清理授权内核实目标后以 `preview=false` 清理，不重跑创建。只有配置预览没有执行，不称清理成功。

原冻结映射错误时，当前工具支持 `identity_mapping` 修正 ES 身份/版本路径；旧附属表实际已不存在时，可用 `child_mapping` 指定 `original_table/table/foreign_key`。必须先预览，证明原 SQL、响应及 ES 精确归属未变，再实际处理；需要修改权限，平台单独审计操作者/时间，不能手工覆盖原快照。更正路径不授权更换文档、租户、数据源或扩大删除范围。工具缺参、文档多归属、版本变化或身份不足时停止该项恢复。

历史创建请求实际被拒绝、但旧规则未配置拒绝契约时，核对工具支持 `rejection_recovery`，
以 `{"rejection_response":{"success":false}}` 先预览再处理。平台必须自行读取原Trace的完整执行结果，
核对校验和、Case/环境/执行人、唯一请求步骤、冻结名称及原始拒绝响应，并确认没有创建标识或未知占用。
调用者只提供待核对契约，不能自报“未创建”替代证据。预览不修改台账；实际恢复仍执行完整无新增观察，
补证单独审计、不覆盖旧规则、不改业务判定。原结果缺失、只有数据库零行、存在部分ID或5xx/超时均不能恢复为未创建。

更新 Case 规则只影响后续执行，不会自动修历史冻结规则。历史没有资源台账不能靠手工补所有权追溯接管；未知占用也不能直接清空或加配额绕过。

## 7. 判断阻塞是否真的由平台造成

- Schema/工具确实不支持必需安全能力：平台能力缺口，记录具体缺参或失败，不发送新的写请求。
- 服务已支持但 Case 缺规则、路径少 `[]`、旧表/外键未迁移：修 Case 配置并完整验证，不继续引用旧平台阻塞结论。
- 缺少筛选交集等对照数据：测试前置不足，设计合格隔离对照及清理，不能靠放宽断言或只验 HTTP 200 通过。
- 接口违背已确认业务契约：业务失败；即使清理成功也不能标通过。
