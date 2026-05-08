# 数据工厂实体批量生成设计

## 1. 背景

当前工厂实体需要逐个新增：

```text
选择产品 -> 选择逻辑数据源 -> 选择表名 -> 保存实体 -> 同步字段规则
```

如果一个业务库中有很多表，逐个配置效率较低。

因此在“工厂实体”页面增加“批量生成”能力：一次加载当前逻辑数据源下所有表，用户勾选需要生成的表，确认后批量创建工厂实体和字段规则。

## 2. 功能入口

页面：

```text
数据工厂 / 工厂实体
```

按钮位置：页面右上角，和“新增实体”同级。

```text
[新增实体] [批量生成]
```

点击“批量生成”后，打开右侧半屏抽屉。

## 3. 交互设计

### 3.1 抽屉布局

抽屉建议宽度：`50%` 或 `720px` 起步。

标题：

```text
批量生成工厂实体
```

顶部配置区：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| 产品 | 是 | 选择 `ProjectProduct` |
| 逻辑数据源 | 是 | 选择 `DataFactoryDatasourceAlias` |
| 顶部测试环境 | 是 | 复用系统顶部全局环境，不在抽屉里单独选择 |
| 同步字段规则 | 是 | 默认开启，批量创建实体后自动同步字段规则 |
| 已存在实体 | 是 | 默认跳过已存在表实体 |

按钮：

```text
[加载表] [生成]
```

### 3.2 表格区域

点击“加载表”后，根据：

```text
产品 + 逻辑数据源 + 顶部全局测试环境
```

调用表发现接口加载所有表。

表格字段：

| 字段 | 说明 | 是否可编辑 |
| --- | --- | --- |
| 勾选 | 是否生成该表实体 | 是 |
| 表名 | 数据库真实表名 | 否 |
| 表注释 | 数据库表 comment | 否 |
| 实体名称 | 默认表注释，没有表注释则表名 | 是 |
| 状态 | 可生成/已存在/缺少表名/异常 | 否 |
| 说明 | 已存在实体名称或异常原因 | 否 |

实体名称规则：

```text
if table_comment:
    entity_name = table_comment
else:
    entity_name = table_name
```

用户只能修改 `实体名称`，不能修改表名、逻辑数据源、产品、主键等结构信息。

原因：

```text
批量生成是基于真实数据库结构生成实体定义，避免用户在批量模式中修改结构导致实体和数据库不一致。
```

### 3.3 勾选规则

默认勾选策略建议：

| 表状态 | 默认是否勾选 | 说明 |
| --- | --- | --- |
| 当前逻辑数据源下未生成实体 | 勾选 | 可直接生成 |
| 当前逻辑数据源下已存在实体 | 不勾选 | 默认跳过 |
| 表结构读取失败 | 不勾选 | 禁止生成 |

用户可取消勾选未生成的表。

已存在实体行建议禁用勾选，避免重复创建。

### 3.4 生成流程

```text
点击批量生成
  ↓
打开右侧抽屉
  ↓
选择产品、逻辑数据源
  ↓
点击加载表
  ↓
后端读取所有表和表注释
  ↓
前端展示表格，默认填充实体名称
  ↓
用户勾选需要生成的表并调整实体名称
  ↓
点击生成
  ↓
后端批量创建实体
  ↓
逐表读取字段结构
  ↓
批量生成字段规则
  ↓
返回成功、跳过、失败明细
  ↓
刷新工厂实体列表
```

## 4. 后端设计

### 4.1 表发现接口增强

现有接口：

```text
POST /data-factory/discover/tables
```

当前应返回：

```json
[
  {
    "name": "orders",
    "comment": "订单表"
  },
  {
    "name": "users",
    "comment": "用户表"
  }
]
```

该接口已能作为批量生成的表列表来源。

### 4.2 批量生成接口

新增接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/data-factory/entity/batch-generate` | 批量生成工厂实体和字段规则 |

请求示例：

```json
{
  "project_product": 22,
  "datasource_alias": 1,
  "test_env": 2,
  "sync_fields": true,
  "skip_exists": true,
  "tables": [
    {
      "table_name": "users",
      "name": "用户表"
    },
    {
      "table_name": "orders",
      "name": "订单表"
    }
  ]
}
```

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `project_product` | 是 | 产品 ID |
| `datasource_alias` | 是 | 逻辑数据源 ID |
| `test_env` | 是 | 顶部全局环境 ID |
| `sync_fields` | 否 | 是否同步字段规则，默认 `true` |
| `skip_exists` | 否 | 已存在实体是否跳过，默认 `true` |
| `tables` | 是 | 用户勾选的表 |
| `tables[].table_name` | 是 | 数据库表名 |
| `tables[].name` | 是 | 实体名称 |

响应示例：

```json
{
  "success": 2,
  "skipped": 1,
  "failed": 1,
  "items": [
    {
      "table_name": "users",
      "name": "用户表",
      "status": "success",
      "entity_id": 10,
      "field_count": 8,
      "message": "生成成功"
    },
    {
      "table_name": "products",
      "name": "产品表",
      "status": "skipped",
      "entity_id": 9,
      "field_count": 0,
      "message": "当前逻辑数据源下已存在实体"
    },
    {
      "table_name": "bad_table",
      "name": "异常表",
      "status": "failed",
      "entity_id": null,
      "field_count": 0,
      "message": "读取表结构失败：xxx"
    }
  ]
}
```

### 4.3 后端处理规则

每张表处理流程：

```text
校验 table_name/name
  ↓
检查同一产品 + 逻辑数据源 + 表名是否已存在实体
  ↓
如果存在且 skip_exists=true，则跳过
  ↓
如果不存在，创建 DataFactoryEntity
  ↓
如果 sync_fields=true，读取表结构
  ↓
创建 DataFactoryField
  ↓
记录结果
```

默认实体字段：

| 字段 | 默认值 |
| --- | --- |
| `project_product` | 请求中的产品 |
| `datasource_alias` | 请求中的逻辑数据源 |
| `name` | 用户填写的实体名称 |
| `table_name` | 数据库表名 |
| `primary_key` | 表结构主键第一个字段，没有则 `id` |
| `unique_key` | 第一个单字段唯一索引，没有则空 |
| `source_mode` | 逻辑数据源模式 |
| `create_type` | SQL |
| `delete_type` | SQL |
| `cleanup_order` | 默认 `100` |
| `status` | 启用 |

字段规则生成：

复用现有单表同步逻辑：

```text
DataFactoryDiscover.get_table_schema
  ↓
DataFactoryFieldViews.normalize_field_data
  ↓
DataFactoryFieldSerializer 校验
  ↓
DataFactoryField 保存
```

建议抽出公共 service，避免 `batch_save` 和 `batch_generate` 重复代码。

## 5. 前端设计

### 5.1 状态变量

建议新增：

```ts
const batchVisible = ref(false)
const batchLoading = ref(false)
const batchGenerating = ref(false)
const batchRows = ref<any[]>([])
const batchSelectedKeys = ref<string[]>([])
const batchForm = reactive({
  project_product: null,
  datasource_alias: null,
  sync_fields: true,
  skip_exists: true,
})
```

### 5.2 批量表格列

建议放入：

```text
mango-console/src/views/data-factory/entity/config.ts
```

列配置：

```ts
export const batchEntityTableColumns = useTableColumn([
  { title: '表名', key: 'table_name', dataIndex: 'table_name', width: 180 },
  { title: '表注释', key: 'table_comment', dataIndex: 'table_comment', width: 180 },
  { title: '实体名称', key: 'name', dataIndex: 'name', width: 220 },
  { title: '状态', key: 'status', dataIndex: 'status', width: 120 },
  { title: '说明', key: 'message', dataIndex: 'message' },
])
```

`实体名称` 单元格使用 input：

```vue
<a-input v-model="record.name" :disabled="record.disabled" />
```

### 5.3 加载表逻辑

```text
点击加载表
  ↓
校验产品、逻辑数据源、顶部环境
  ↓
调用 /data-factory/discover/tables
  ↓
再调用实体列表接口，判断哪些表已存在
  ↓
合并成 batchRows
```

合并结果示例：

```ts
{
  table_name: 'orders',
  table_comment: '订单表',
  name: '订单表',
  status: 'ready',
  message: '可生成',
  disabled: false,
}
```

已存在：

```ts
{
  table_name: 'users',
  table_comment: '用户表',
  name: '用户表',
  status: 'exists',
  message: '当前逻辑数据源下已存在实体',
  disabled: true,
}
```

### 5.4 生成逻辑

```text
点击生成
  ↓
取已勾选且不是 disabled 的行
  ↓
校验每一行 name 不为空
  ↓
调用 /data-factory/entity/batch-generate
  ↓
根据响应更新每一行状态
  ↓
刷新实体列表
```

生成完成后抽屉不自动关闭，便于用户查看失败原因。

提供按钮：

```text
[关闭] [重新加载] [生成]
```

## 6. 异常处理

| 场景 | 页面提示 |
| --- | --- |
| 未选择产品 | 请选择产品 |
| 未选择逻辑数据源 | 请选择逻辑数据源 |
| 未选择顶部测试环境 | 请先选择顶部测试环境 |
| 未勾选表 | 请至少选择一张表 |
| 实体名称为空 | 第 N 行实体名称不能为空 |
| 表已存在 | 当前逻辑数据源下已存在实体，默认跳过 |
| 字段同步失败 | 实体创建成功，但字段同步失败，展示失败原因 |

## 7. 权限和安全

批量生成只创建平台配置表，不直接向业务数据库写入数据。

但它会读取业务库结构，因此仍然依赖：

```text
逻辑数据源 + 顶部测试环境 -> 真实 Database
```

如果无法解析真实数据库，应直接失败并提示。

## 8. 验收标准

- 工厂实体页面有“批量生成”按钮。
- 点击后打开右侧半屏抽屉。
- 抽屉中可以选择产品和逻辑数据源。
- 点击加载表后可以显示当前逻辑数据源下所有表。
- 表格展示表名、表注释、实体名称、状态、说明。
- 实体名称默认使用表注释，没有表注释则使用表名。
- 用户只能编辑实体名称。
- 已存在实体的表默认不勾选且不可选。
- 用户勾选多张表后可以一键生成实体。
- 生成实体时可以同步生成字段规则。
- 生成完成后展示成功、跳过、失败明细。
- 生成完成后刷新工厂实体列表。
