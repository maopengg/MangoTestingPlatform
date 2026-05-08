# 数据工厂关联清理保留方案

## 1. 背景

当前数据工厂清理逻辑以一次执行记录 `DataFactoryExecution` 为边界，只清理本次执行过程中实际创建并写入 `DataFactoryExecutionItem` 的数据。

例如一次执行创建了：

```text
users.id = 1
products.id = 2, products.user_id = 1
orders.id = 3, orders.user_id = 1, orders.product_id = 2
```

当前清理会根据执行明细逐条按主键删除这些数据。

但如果数据库中还存在其它关联数据：

```text
coupons.user_id = 1
addresses.user_id = 1
order_logs.order_id = 3
```

这些数据如果不是本次数据工厂创建的，就不会出现在执行明细中，当前清理逻辑不会自动删除。

## 2. 保留能力目标

后续可以增加“关联清理”能力：

```text
以本次创建的数据为根节点
  ↓
递归发现依赖它的子表数据
  ↓
先删除子表数据
  ↓
再删除父表数据
```

目标是支持类似场景：

```text
清理 users.id = 1
  ↓
自动发现并清理 products.user_id = 1
  ↓
自动发现并清理 orders.product_id = products.id
  ↓
自动发现并清理 order_logs.order_id = orders.id
  ↓
最后删除 users.id = 1
```

这样可以避免因为外键约束导致父表数据删除失败。

## 3. 当前不直接实现的原因

关联清理有较高风险，不能默认无条件开启。

主要风险：

| 风险 | 说明 |
| --- | --- |
| 误删历史测试数据 | 子表中可能存在不是本次数据工厂创建的数据，但它们关联了本次创建的父数据 |
| 数据库缺少真实外键 | 很多测试库没有完整外键约束，无法自动发现关系 |
| 跨库/跨数据源关联 | 业务关系可能跨多个逻辑数据源，数据库无法直接推导 |
| 删除范围不可预期 | 一个用户可能关联订单、地址、优惠券、日志等大量数据 |
| 性能风险 | 深层递归扫描大表可能影响测试环境性能 |

因此当前版本先保持：

```text
默认只清理本次执行记录创建的数据
```

关联清理作为后续增强项保留。

## 4. 推荐设计

### 4.1 清理范围策略

后续可以在状态模板中增加清理范围配置：

| 策略 | 说明 |
| --- | --- |
| 仅清理本次创建数据 | 默认策略，只删除 `DataFactoryExecutionItem` 记录的数据 |
| 清理本次创建数据及关联子数据 | 递归删除依赖本次数据的子表数据 |

字段建议：

```python
cleanup_scope = models.SmallIntegerField(default=1)
```

枚举建议：

```text
1 = EXECUTION_ONLY       # 仅本次创建数据
2 = WITH_RELATED_CHILDREN # 本次创建数据 + 关联子数据
```

### 4.2 关联来源

关联关系可以来自两类来源。

第一类：数据库真实外键。

通过 SQLAlchemy inspector 获取外键：

```python
from sqlalchemy import inspect

inspector = inspect(engine)
foreign_keys = inspector.get_foreign_keys(table_name)
```

适合数据库有完整外键约束的场景。

第二类：数据工厂逻辑关联规则。

如果数据库没有外键，可以增加数据工厂关系配置表：

```python
class DataFactoryRelation(models.Model):
    project_product = models.ForeignKey(ProjectProduct, on_delete=models.PROTECT)
    datasource_alias = models.ForeignKey(DataFactoryDatasourceAlias, on_delete=models.PROTECT)
    parent_entity = models.ForeignKey(DataFactoryEntity, related_name='parent_relations', on_delete=models.CASCADE)
    parent_field = models.CharField(max_length=128)
    child_entity = models.ForeignKey(DataFactoryEntity, related_name='child_relations', on_delete=models.CASCADE)
    child_field = models.CharField(max_length=128)
    status = models.SmallIntegerField(default=1)
```

示例：

| 父实体 | 父字段 | 子实体 | 子字段 |
| --- | --- | --- | --- |
| 用户 | id | 产品 | user_id |
| 用户 | id | 订单 | user_id |
| 产品 | id | 订单 | product_id |
| 订单 | id | 订单日志 | order_id |

推荐优先级：

```text
逻辑关联规则 > 数据库真实外键
```

原因是测试库可能没有外键，逻辑关系更可控。

## 5. 清理算法设计

### 5.1 总体流程

```text
读取 execution 下所有未清理 item
  ↓
根据 item.template.entity 找到根实体和主键值
  ↓
根据清理范围判断是否需要关联清理
  ↓
如果仅清理本次创建数据：按 execution_item 主键删除
  ↓
如果开启关联清理：递归查找子表数据
  ↓
生成删除计划
  ↓
按子表 -> 父表顺序删除
  ↓
更新 execution_item 清理状态
```

### 5.2 删除计划结构

```json
{
  "table": "orders",
  "primary_key": "id",
  "primary_value": 3,
  "source": "execution_item",
  "children": [
    {
      "table": "order_logs",
      "primary_key": "id",
      "primary_value": 10,
      "source": "related_child"
    }
  ]
}
```

### 5.3 递归发现逻辑

伪代码：

```python
def build_delete_plan(entity, primary_value, visited):
    key = (entity.id, primary_value)
    if key in visited:
        return None
    visited.add(key)

    children = []
    relations = find_child_relations(entity)
    for relation in relations:
        child_rows = query_child_rows(
            child_entity=relation.child_entity,
            child_field=relation.child_field,
            parent_value=primary_value,
        )
        for child_row in child_rows:
            child_primary_value = child_row[relation.child_entity.primary_key]
            child_plan = build_delete_plan(relation.child_entity, child_primary_value, visited)
            children.append(child_plan)

    return DeletePlan(entity=entity, primary_value=primary_value, children=children)
```

### 5.4 删除顺序

删除计划执行时必须后序遍历：

```text
先删除 children
再删除 current node
```

例如：

```text
用户
  产品
    订单
      订单日志
```

实际删除：

```text
订单日志 -> 订单 -> 产品 -> 用户
```

## 6. 页面设计保留

后续可以在“状态模板”页面增加：

| 字段 | 说明 |
| --- | --- |
| 清理策略 | 执行结束/手动/不清理 |
| 清理范围 | 仅本次创建数据/本次创建数据及关联子数据 |
| 最大递归深度 | 防止关联层级过深，默认 5 |
| 预览关联清理 | 清理前展示即将删除的表和行数 |

清理确认弹窗应展示：

| 内容 | 说明 |
| --- | --- |
| 根数据 | 本次执行记录创建的数据 |
| 关联数据 | 递归发现的子表数据 |
| 删除顺序 | 子表到父表 |
| 风险提示 | 关联子数据可能包含非本次创建的数据 |

## 7. 接口设计保留

可以新增清理预览接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/data-factory/execution/cleanup-preview` | 预览本次清理将删除哪些数据 |
| POST | `/data-factory/execution/cleanup` | 执行清理，支持清理范围参数 |

请求示例：

```json
{
  "execution_id": 1,
  "cleanup_scope": 2,
  "max_depth": 5
}
```

响应示例：

```json
{
  "execution_id": 1,
  "items": [
    {
      "table": "order_logs",
      "count": 2,
      "source": "related_child"
    },
    {
      "table": "orders",
      "count": 1,
      "source": "execution_item"
    },
    {
      "table": "products",
      "count": 1,
      "source": "execution_item"
    },
    {
      "table": "users",
      "count": 1,
      "source": "execution_item"
    }
  ]
}
```

## 8. 与 cleanup_order 的关系

如果未来实现关联清理，`cleanup_order` 的重要性会下降。

推荐演进方向：

| 阶段 | 处理方式 |
| --- | --- |
| 当前阶段 | 保留 `cleanup_order`，用于本次执行明细之间的删除顺序 |
| 关联清理阶段 | 优先使用关系图自动推导删除顺序 |
| 稳定后 | 可考虑移除 `cleanup_order`，避免用户手工维护顺序 |

最终更理想的清理顺序应来自关系图，而不是用户手填数字。

## 9. 验收标准保留

后续实现时应满足：

- 可以预览关联清理范围。
- 可以看到即将删除的表、行数和删除顺序。
- 默认不会清理非本次执行创建的数据。
- 开启关联清理后，可以递归清理依赖本次数据的子表数据。
- 数据库有外键时，可以自动发现关系。
- 数据库没有外键时，可以通过逻辑关联规则发现关系。
- 清理时按子表到父表顺序执行。
- 清理失败时能明确展示失败表、主键和错误原因。
- 支持最大递归深度，避免循环关系或异常深度导致风险。
