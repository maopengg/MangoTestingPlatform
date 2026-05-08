# 数据工厂总体设计

## 1. 定位

数据工厂是一个独立的一级菜单和独立的 Django app，负责统一完成测试数据创建、状态构造、变量输出和数据清理。

它不属于 API 自动化，也不属于 UI 自动化。API/UI 用例后续只需要在自己的前置、后置能力中调用数据工厂 runner，调用关系表由调用方模块维护，数据工厂不维护 `DataFactoryCaseRef` 这类跨模块引用表。

数据工厂当前核心能力：

- 通过 SQLAlchemy 发现真实数据库的表、字段、主键、索引和外键。
- 配置逻辑数据源，让同一套工厂配置可运行在不同测试环境。
- 配置业务实体，例如用户、商品、订单、报销单。
- 配置字段生成规则，例如固定值、随机值、自动编号、依赖实体字段。
- 配置状态模板，例如默认订单、已支付订单。
- 调试运行模板，生成执行上下文。
- 记录创建结果、实际落库数据库和清理结果。
- 前端页面统一采用 `index.vue + config.ts` 结构，表格列、基础表单项从页面逻辑中抽离。

## 2. 菜单结构

```text
数据工厂
  数据源映射   /data-factory/datasource/index
  工厂实体     /data-factory/entity/index
  状态模板     /data-factory/template/index
  执行记录     /data-factory/execution/index
```

页面详细设计：

- [数据源映射页面设计](data_factory_datasource_page_design.md)
- [工厂实体页面设计](data_factory_entity_page_design.md)
- [状态模板页面设计](data_factory_template_page_design.md)
- [执行记录页面设计](data_factory_execution_page_design.md)

## 3. 最终数据源设计

真实项目里，一个产品可能存在多个测试环境，每个环境下数据库名称不同，但表结构一致。例如：

| 环境 | MySQL 连接 | 实际库名 |
| --- | --- | --- |
| dev | dev-mysql:3306 | mall_dev |
| test | test-mysql:3306 | mall_test |
| pre | pre-mysql:3306 | mall_pre |

测试用例需要的是同一套业务工厂，例如“订单工厂”，而不是绑定死 `mall_dev.orders`。因此数据工厂采用三层设计：

| 层级 | 模型 | 作用 |
| --- | --- | --- |
| 真实连接 | `Database` | 系统已有数据库配置，记录 host、port、name、user、password、db_type |
| 逻辑数据源 | `DataFactoryDatasourceAlias` | 数据工厂内的稳定业务数据源，例如 `mall_main`、`payment_db` |
| 环境绑定 | `DataFactoryDatasourceBinding` | 把逻辑数据源绑定到某个测试环境下的真实 `Database` |

实体只绑定逻辑数据源：

```text
订单实体 -> 逻辑数据源 mall_main -> 表 orders
```

运行时再根据测试环境解析真实数据库：

```text
订单模板 + dev 环境
  ↓
订单实体.mall_main
  ↓
查 DataFactoryDatasourceBinding(mall_main, dev)
  ↓
得到 Database(mall_dev)
  ↓
insert mall_dev.orders
```

这样同一套实体、字段、模板配置可以在 dev、test、pre 环境复用。

## 4. 与现有系统关系

数据工厂复用现有系统配置：

| 现有模型 | 作用 |
| --- | --- |
| `ProjectProduct` | 产品归属 |
| `TestObject` | 测试环境 |
| `Database` | 真实数据库连接 |

`Database` 需要增加数据库类型：

```python
class Database(models.Model):
    ...
    db_type = models.SmallIntegerField(verbose_name="数据库类型", default=0)
```

建议枚举：

```python
class DatabaseTypeEnum(BaseEnum):
    MYSQL = 0
    POSTGRESQL = 1
    SQLITE = 2
    ORACLE = 3
    SQLSERVER = 4
```

## 5. 核心模型

| 模型 | 说明 |
| --- | --- |
| `DataFactoryDatasourceAlias` | 逻辑数据源 |
| `DataFactoryDatasourceBinding` | 逻辑数据源与测试环境真实数据库的绑定 |
| `DataFactoryEntity` | 工厂实体，绑定逻辑数据源和表名 |
| `DataFactoryField` | 字段规则 |
| `DataFactoryTemplate` | 状态模板 |
| `DataFactoryExecution` | 执行批次 |
| `DataFactoryExecutionItem` | 执行明细，记录实际使用的真实数据库 |

## 6. 总体执行链路

```text
选择顶部全局测试环境
  ↓
选择状态模板
  ↓
解析模板关联实体
  ↓
根据实体的逻辑数据源 + 测试环境解析真实 Database
  ↓
根据字段规则生成 payload
  ↓
处理依赖实体字段
  ↓
通过 SQLAlchemy 自动 insert
  ↓
记录 execution、execution_item、实际 Database、上下文
  ↓
按执行记录中的 execution_item 链路清理本次实际创建的数据
```

记录 `execution_item.database` 很关键：即使后续环境绑定被修改，历史执行记录清理时仍然会使用当时实际落库的数据库，避免误删其它环境数据。

清理职责拆分：

| 配置位置 | 职责 |
| --- | --- |
| 工厂实体 | 维护表名、主键、字段规则、清理顺序 |
| 状态模板 | 维护本模板造数后的清理策略：执行结束/手动清理/不清理 |
| 执行明细 | 记录本次执行实际创建的数据、真实数据库、主键值、最终清理策略和清理顺序 |

清理范围以一次执行记录为边界。只要依赖实体在本次造数过程中被自动创建，就会写入同一个 `DataFactoryExecution` 下的 `DataFactoryExecutionItem`，后续清理该执行记录时会一起清理。复用上下文已有数据不会生成执行明细，因此不会被误删。

## 7. 依赖字段设计

依赖字段用于处理 `order.user_id`、`order.product_id` 这类关系。

字段配置示例：

```json
{
  "template_id": 1,
  "field": "id",
  "alias": "用户",
  "strategy": "reuse_or_create"
}
```

执行订单模板时：

```text
生成 order.user_id
  ↓
发现需要依赖“默认用户模板”
  ↓
上下文已有 用户 且策略允许复用，则直接取 用户.id
  ↓
否则先创建用户
  ↓
把 用户.id 写入 order.user_id
```

依赖策略：

| 策略 | 说明 |
| --- | --- |
| `reuse_or_create` | 上下文已有则复用，没有则创建 |
| `must_exist` | 上下文必须已有，否则报错 |
| `create_always` | 每次都创建新的依赖数据 |

### 7.1 共享依赖数据

复杂业务中，不同实体可能依赖同一条上游数据。例如：

```text
订单 orders.user_id -> 用户 users.id
订单 orders.product_id -> 产品 products.id
产品 products.user_id -> 用户 users.id
```

业务期望是：创建订单时，产品和订单关联同一个用户，而不是分别创建两个用户。

数据工厂通过“同一个运行上下文 + 同一个依赖模板 + `reuse_or_create` 策略”支持该场景。

配置规则：

| 当前字段 | 依赖模板 | 取值字段 | 策略 |
| --- | --- | --- | --- |
| `products.user_id` | 创建用户 | `id` | `reuse_or_create` |
| `orders.user_id` | 创建用户 | `id` | `reuse_or_create` |
| `orders.product_id` | 创建产品 | `id` | `reuse_or_create` |

执行顺序示例：

```text
执行“创建订单”模板
  ↓
解析 orders.product_id，发现依赖“创建产品”
  ↓
创建产品前解析 products.user_id，发现依赖“创建用户”
  ↓
上下文不存在“创建用户”，先创建用户
  ↓
context["创建用户"].id = 1001
  ↓
products.user_id = 1001，创建产品
  ↓
context["创建产品"].id = 2001
  ↓
回到订单，解析 orders.user_id，仍然依赖“创建用户”
  ↓
上下文已存在“创建用户”，复用 id=1001
  ↓
orders.user_id = 1001，orders.product_id = 2001，创建订单
```

最终结果：

```text
users.id = 1001
products.user_id = 1001
orders.user_id = 1001
orders.product_id = 2001
```

复用判断规则：

| 条件 | 说明 |
| --- | --- |
| 同一个运行上下文 | 一次模板调试运行或一次用例前置运行共享同一个 context |
| 同一个依赖模板 | 两个字段都选择同一个“创建用户”模板 |
| 同一个上下文别名 | 默认使用依赖模板名称，例如 `创建用户` |
| 策略不是 `create_always` | `reuse_or_create` 会复用，`create_always` 会强制新建 |

如果两个字段选择了不同用户模板，例如“创建产品用户”和“创建订单用户”，则会创建两条用户数据，这是符合配置语义的。

如果后续需要强制不同模板也复用同一条用户，需要增加“依赖上下文别名”高级配置，让多个依赖模板显式写入同一个 alias。

预览数据时，接口会返回 `dependency_tree`，用于在页面上提前确认依赖创建/复用关系。例如：

```text
创建订单
├─ 创建产品：创建
│  └─ 创建用户：创建
└─ 创建用户：复用
```

这棵树只用于预览说明，不落库；真正调试运行时使用同一套上下文复用规则执行。

## 8. 类型一致性保证

字段类型通过三层保证：

| 层级 | 说明 |
| --- | --- |
| 表发现 | SQLAlchemy inspector 读取真实数据库字段类型、可空、主键、自增、长度 |
| 类型归一化 | 把 DB 类型映射为平台类型，例如 `VARCHAR -> string`、`INT -> integer`、`DECIMAL -> decimal` |
| 运行校验 | 生成值入库前做必填、长度、枚举和类型转换校验 |

如果字段类型不匹配，runner 会在 insert 前报错，而不是把错误延迟到数据库异常。

## 9. 分期边界

当前已实现范围：

- 独立 `auto_data_factory` app。
- `Database.db_type`。
- 逻辑数据源和环境绑定。
- 工厂实体、字段规则、状态模板、执行记录。
- MySQL/PostgreSQL/SQLite URL 构建。
- 表结构发现。
- SQL 自动 insert。
- 调试运行和手动清理。
- 前端数据源映射、工厂实体、状态模板、执行记录页面。

暂不处理范围：

- API/UI 用例前置、后置接入。
- API/UI 调用关系表。
- 多步骤状态模板编排表。
- 自定义 API 创建/删除。
- 自定义函数创建/删除。

## 10. 前端统一风格

数据工厂前端页面需要与 `mango-console/src/views/apitest/case` 的页面组织方式保持一致：

```text
页面目录
  index.vue   页面渲染、接口调用、弹窗状态、业务动作
  config.ts   搜索项、表格列、基础表单项、固定列宽
```

统一规则：

| 规则 | 说明 |
| --- | --- |
| 表格列配置 | 主列表和抽屉明细表格列统一放入 `config.ts` |
| 页面渲染 | `index.vue` 使用 `v-for="item of tableColumns"` 渲染列 |
| 特殊单元格 | 状态标签、枚举翻译、操作列等留在 `index.vue` 的 slot 中 |
| 操作按钮 | 每行只保留 2 个主按钮，其余放入 `···` 下拉菜单 |
| 复杂交互 | 字段规则、依赖模板、预览结果等复杂交互可以保留在 `index.vue` |
| 环境选择 | 数据工厂不再单独选择结构发现环境，统一读取顶部全局测试环境 |

四个页面对应配置文件：

| 页面 | 配置文件 | 说明 |
| --- | --- | --- |
| 数据源映射 | `datasource/config.ts` | 逻辑数据源列、绑定明细列 |
| 工厂实体 | `entity/config.ts` | 实体列、字段规则列 |
| 状态模板 | `template/config.ts` | 模板列、预览字段列 |
| 执行记录 | `execution/config.ts` | 执行记录列、执行明细列 |

## 11. 后端视图组织

数据工厂后端 `views` 按“一张表一个文件”组织。每个表级文件中同时维护：

- 写入 Serializer。
- 查询 SerializerC。
- CRUD。
- 该表独有的 ViewSet 动作。

表级文件：

| 模型 | 文件 |
| --- | --- |
| `DataFactoryDatasourceAlias` | `views/datasource_alias.py` |
| `DataFactoryDatasourceBinding` | `views/datasource_binding.py` |
| `DataFactoryEntity` | `views/entity.py` |
| `DataFactoryField` | `views/field.py` |
| `DataFactoryTemplate` | `views/template.py` |
| `DataFactoryExecution` | `views/execution.py` |
| `DataFactoryExecutionItem` | `views/execution_item.py` |

非表级能力单独保留：

| 能力 | 文件 |
| --- | --- |
| 表结构发现、连接测试 | `views/discover.py` |

## 12. 验收标准

- 可以在数据库配置中选择 MySQL/PostgreSQL 等类型。
- 可以在“数据源映射”页面创建逻辑数据源。
- 可以把逻辑数据源绑定到不同测试环境下的真实数据库。
- 可以在“工厂实体”页面选择逻辑数据源。
- 可以使用顶部全局测试环境读取表列表和字段。
- 可以把 `product_id`、`user_id` 配置成依赖字段。
- 预览状态模板时可以看到依赖关系树，区分“创建”和“复用”。
- 调试运行模板时必须先选择顶部全局测试环境。
- 创建数据时根据测试环境落到正确数据库。
- 清理时使用执行明细记录的真实数据库删除数据。
- 数据工厂四个前端页面表格列配置抽离到 `config.ts`，操作列风格统一。
