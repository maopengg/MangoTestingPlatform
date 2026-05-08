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
选择状态模板和测试环境
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
按清理策略使用 execution_item.database 删除数据
```

记录 `execution_item.database` 很关键：即使后续环境绑定被修改，历史执行记录清理时仍然会使用当时实际落库的数据库，避免误删其它环境数据。

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

## 10. 验收标准

- 可以在数据库配置中选择 MySQL/PostgreSQL 等类型。
- 可以在“数据源映射”页面创建逻辑数据源。
- 可以把逻辑数据源绑定到不同测试环境下的真实数据库。
- 可以在“工厂实体”页面选择逻辑数据源。
- 可以选择某个测试环境读取表列表和字段。
- 可以把 `product_id`、`user_id` 配置成依赖字段。
- 调试运行模板时必须选择测试环境。
- 创建数据时根据测试环境落到正确数据库。
- 清理时使用执行明细记录的真实数据库删除数据。
