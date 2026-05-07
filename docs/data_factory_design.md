# 数据工厂总体设计

## 1. 定位

数据工厂是一个独立的一级菜单和独立的 Django app，目标是提供统一的测试数据创建、状态构造、变量输出和数据清理能力。

它不属于 API 自动化，也不属于 UI 自动化。数据工厂本身只负责：

- 发现数据库表、字段、主键、索引、枚举和依赖关系。
- 配置业务实体，例如用户、商品、订单、报销单。
- 配置字段生成规则，例如固定值、随机值、自动编号、依赖实体字段。
- 配置复杂业务状态，例如已支付订单、已审批报销单。
- 调试运行模板并生成执行上下文。
- 记录创建结果、上下文和清理结果。

## 2. 菜单结构

后端菜单已按一级菜单设计：

```text
数据工厂
  工厂实体     /data-factory/entity/index
  状态模板     /data-factory/template/index
  执行记录     /data-factory/execution/index
```

每个页面的详细设计独立拆分：

- [工厂实体页面设计](data_factory_entity_page_design.md)
- [状态模板页面设计](data_factory_template_page_design.md)
- [执行记录页面设计](data_factory_execution_page_design.md)

## 3. 与现有系统关系

建议新增独立后端 app：

```text
MangoServer/src/auto_test/auto_data_factory
```

数据工厂复用现有系统配置：

| 现有模型 | 作用 |
| --- | --- |
| `ProjectProduct` | 产品归属 |
| `TestObject` | 测试环境和测试对象 |
| `Database` | 具体数据库连接 |

数据源类型建议加在 `Database` 表上，而不是 `ProjectProduct` 表上。原因是一个产品可能同时存在 MySQL、PostgreSQL、Redis、MongoDB 等多个数据源，数据库类型描述的是连接本身。

建议扩展：

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

    @classmethod
    def obj(cls):
        return {
            0: "MySQL",
            1: "PostgreSQL",
            2: "SQLite",
            3: "Oracle",
            4: "SQL Server",
        }
```

## 4. 核心概念

| 概念 | 说明 |
| --- | --- |
| 工厂实体 | 一个业务对象，例如订单，对应一个表或一个创建 API |
| 字段规则 | 每个字段如何生成，例如随机值、依赖字段、表达式 |
| 依赖实体 | 当前实体创建前需要先创建或复用的实体 |
| 状态模板 | 多实体组合后的业务状态，例如已支付订单 |
| 执行上下文 | 当前用例创建出的数据集合 |
| 清理策略 | 执行结束、手动或不清理 |

对应代码版数据工厂：

| 代码版 | 页面版 |
| --- | --- |
| Entity | 工厂实体 |
| Spec | 字段规则 |
| Trait | 状态模板 |
| SubFactory | 依赖实体 |
| Repository | 创建/删除方式 |
| Cleanup Hook | 清理策略 |

## 5. 总体执行链路

```text
触发数据工厂执行
  ↓
解析状态模板和依赖实体
  ↓
根据字段规则生成数据
  ↓
调用 API/SQL/函数创建数据
  ↓
记录创建结果和清理信息
  ↓
写入统一变量上下文
  ↓
按清理策略执行自动或手动清理
  ↓
更新执行记录
```

变量上下文示例：

```json
{
  "用户": {
    "id": 88,
    "username": "AUTO_USER_abc"
  },
  "产品": {
    "id": 101,
    "price": 99.9
  },
  "订单": {
    "id": 3001,
    "order_no": "AUTO_ORDER_1234",
    "product_id": 101,
    "user_id": 88
  }
}
```

变量引用格式：

```text
${{订单.id}}
${{订单.order_no}}
${{用户.username}}
```

## 6. 建议后端目录

```text
auto_data_factory/
  models.py
  urls.py
  views/
    entity.py
    field.py
    template.py
    execution.py
  service/
    datasource.py
    discover.py
    type_cast.py
    expression.py
    runner.py
    cleanup.py
```

## 7. 建议数据模型

核心模型：

| 模型 | 说明 |
| --- | --- |
| `DataFactoryEntity` | 工厂实体 |
| `DataFactoryField` | 字段规则 |
| `DataFactoryTemplate` | 状态模板 |
| `DataFactoryTemplateStep` | 状态模板步骤 |
| `DataFactoryExecution` | 执行批次 |
| `DataFactoryExecutionItem` | 执行批次内创建的数据 |

推荐第一期先实现：

- `DataFactoryEntity`
- `DataFactoryField`
- `DataFactoryTemplate`
- `DataFactoryExecution`
- `DataFactoryExecutionItem`

`DataFactoryTemplateStep` 可以在第二期支持多实体编排时完善。

## 8. 分期建议

第一期：完成数据工厂基础能力。

- 独立 app。
- `Database.db_type`。
- 工厂实体页面。
- 表结构发现。
- 字段规则配置。
- API 创建和 API 删除。
- 模板调试运行。
- 调试数据手动清理。

第二期：完成状态模板。

- 多实体依赖。
- 状态模板步骤。
- SQL 创建和 SQL 删除。
- 模板调试运行。
- 执行记录详情。

第三期：预留调用方接入能力。

- 数据工厂提供统一 runner 给调用方使用。
- 调用方自行管理“什么时候调用、如何合并变量上下文”。

第四期：高级能力。

- 套件级数据工厂。
- 自定义函数创建/删除。
- 查询已有数据模式。
- 工厂配置导入导出。
- 工厂执行血缘图。

## 9. 验收标准

第一期完成后，需要满足：

- 可以在 `Database` 配置中选择 MySQL/PostgreSQL 等数据库类型。
- 可以在“工厂实体”页面选择数据库并发现 `orders` 表。
- 可以将 `product_id`、`user_id` 配置成依赖实体字段。
- 创建订单时能自动创建或复用产品和用户。
- 可以调试运行订单模板并生成 `${{订单.id}}`、`${{订单.order_no}}`。
- 可以按依赖反向清理调试数据。
- 执行记录能查看创建数据、上下文、清理状态和失败原因。
