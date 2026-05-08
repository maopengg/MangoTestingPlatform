# 数据工厂：工厂实体页面设计

## 1. 页面定位

工厂实体页面负责把一个业务数据对象配置成可创建、可引用、可清理的工厂实体。例如：

- 用户
- 产品
- 订单
- 报销单
- 部门审批

这个页面包含三类能力：

- 逻辑数据源选择与表结构发现。
- 实体基本信息和创建/删除方式配置。
- 字段规则和依赖字段配置。

## 2. 页面入口

```text
数据工厂 / 工厂实体
路径：/data-factory/entity/index
```

建议页面布局：

```text
左侧：实体列表
右侧：实体详情
  基础信息
  数据源与表发现
  字段规则
  创建方式
  删除方式
  调试运行
```

## 3. 列表功能

列表字段：

| 字段 | 说明 |
| --- | --- |
| ID | 实体 ID |
| 实体名称 | 例如订单 |
| 所属产品 | 关联 `ProjectProduct` |
| 逻辑数据源 | 例如商城主库 |
| 数据库类型 | 来自逻辑数据源 |
| 表名 | 例如 orders |
| 创建方式 | API/SQL/函数 |
| 删除方式 | API/SQL/函数 |
| 状态 | 启用/禁用 |
| 更新时间 | 最近修改时间 |

操作：

- 新增实体
- 编辑实体
- 复制实体
- 删除实体
- 启用/禁用
- 字段同步
- 调试创建

筛选：

- 所属项目/产品
- 实体名称
- 表名
- 数据库类型
- 创建方式
- 状态

## 4. 基础信息

表单字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| 所属项目产品 | 是 | 关联 `ProjectProduct` |
| 实体名称 | 是 | 中文名，例如订单 |
| 描述 | 否 | 业务说明 |
| 状态 | 是 | 启用/禁用 |

校验规则：

- 同一产品、同一逻辑数据源下 `表名` 唯一。
- 实体启用前必须至少有一种创建方式。

## 5. 数据源与表发现

工厂实体不直接绑定某个测试环境下的真实数据库，而是绑定逻辑数据源 `DataFactoryDatasourceAlias`。

表结构发现需要额外选择一个测试环境，用于把逻辑数据源解析成真实 `Database` 后读取表结构。

数据源配置：

| 字段 | 说明 |
| --- | --- |
| 逻辑数据源 | 选择 `DataFactoryDatasourceAlias` |
| 结构发现环境 | 选择 `TestObject`，只用于读取表结构 |
| 真实数据库 | 根据逻辑数据源和测试环境自动解析 |
| 数据库类型 | 来自逻辑数据源和真实数据库校验 |
| 表名 | 下拉选择或手动输入 |

发现流程：

```text
选择逻辑数据源
  ↓
选择结构发现环境
  ↓
点击读取表
  ↓
服务端解析绑定关系得到真实 Database
  ↓
服务端根据 db_type 创建 SQLAlchemy engine
  ↓
inspect(engine).get_table_names()
  ↓
用户选择表
  ↓
读取字段、主键、索引、枚举和外键
  ↓
生成默认字段规则
```

最小发现代码：

```python
from sqlalchemy import create_engine, inspect


def discover_table(db_url: str, table_name: str) -> dict:
    engine = create_engine(db_url, pool_pre_ping=True)
    inspector = inspect(engine)
    pk = inspector.get_pk_constraint(table_name)
    pk_columns = pk.get("constrained_columns", [])

    return {
        "table": table_name,
        "primary_keys": pk_columns,
        "columns": [
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "default": col.get("default"),
                "comment": col.get("comment"),
                "primary_key": col["name"] in pk_columns,
                "autoincrement": col.get("autoincrement"),
            }
            for col in inspector.get_columns(table_name)
        ],
        "indexes": inspector.get_indexes(table_name),
        "foreign_keys": inspector.get_foreign_keys(table_name),
    }
```

## 6. 字段规则

字段规则建议作为实体详情页中的核心表格。

字段列表：

| 字段 | 说明 |
| --- | --- |
| 字段名 | 数据库字段名 |
| 字段说明 | 数据库 comment 或用户自定义 |
| 数据库类型 | 原始类型，例如 VARCHAR(50) |
| 平台类型 | string/integer/decimal 等 |
| 必填 | 根据 nullable 推导 |
| 主键 | 是否主键 |
| 自增 | 是否自增 |
| 生成方式 | 字段如何生成 |
| 生成配置 | 根据生成方式展开 |
| 实际值 | 点击“生成实际值”后展示当前配置生成出的结果 |
| 输出变量 | 是否注入上下文 |
| 输出名 | 例如 order_no |

平台类型归一化：

| 数据库类型 | 平台类型 |
| --- | --- |
| INT / BIGINT / SMALLINT | integer |
| DECIMAL / NUMERIC / FLOAT | decimal |
| VARCHAR / TEXT / CHAR | string |
| DATETIME / TIMESTAMP | datetime |
| DATE | date |
| TINYINT(1) / BOOLEAN | boolean |
| JSON | json |
| ENUM | enum |

生成方式：

| 生成方式 | 说明 |
| --- | --- |
| 跳过 | 自增主键或数据库默认值 |
| 固定值 | 手动输入固定值 |
| 随机字符串 | 前缀、长度、大小写 |
| 随机整数 | 最小值、最大值 |
| 随机小数 | 范围、精度 |
| 当前时间 | 当前 datetime |
| 相对时间 | 当前时间偏移 |
| UUID | UUID 或无横线 UUID |
| 自动编号 | `AUTO_ORDER_${uuid8}` |
| 枚举值 | 固定或随机枚举 |
| 表达式 | `${{unit_price}} * ${{quantity}}` |
| 依赖实体字段 | 从依赖实体取字段 |
| SQL 查询结果 | 查询并取单个值 |
| 测试数据方法 | 调用 `ObtainTestData().replace("${{方法名(参数)}}")` |

测试数据方法配置：

| 字段 | 说明 |
| --- | --- |
| `value` | 固定值或 `${{}}` 表达式，例如 `${{character_email()}}` |

示例：

```json
{"value":"${{character_email()}}"}
```

常用字段推荐：

| 字段 | 推荐生成方式 | 生成配置 |
| --- | --- | --- |
| `username` | 测试数据方法 | `{"value":"${{str_lowercase(10)}}"}` |
| `email` | 测试数据方法 | `{"value":"${{character_email()}}"}` |
| `full_name` | 测试数据方法 | `{"value":"${{character_male_name()}}"}` |
| `phone` | 测试数据方法 | `{"value":"${{character_phone()}}"}` |
| `password` | 固定值 | `{"value":"123456"}` |
| `address` | 测试数据方法 | `{"value":"${{character_address()}}"}` |

所有生成结果中的字符串 `value` 都会经过 `ObtainTestData().replace()`，所以固定值也可以写 `${{}}` 表达式。页面后续应提供方法下拉框，用户选择“生成邮箱”等中文名称后，由前端自动生成上述配置。JSON 只作为高级配置展示。

## 7. 依赖字段

当字段是 `product_id`、`user_id` 这类依赖字段时，页面应该提供下拉配置。

配置项：

| 字段 | 示例 |
| --- | --- |
| 生成方式 | 依赖实体字段 |
| 依赖实体 | 产品 |
| 依赖模板 | 默认产品 |
| 取值字段 | id |
| 依赖策略 | 优先复用已有 |
| 上下文名称 | 默认使用依赖模板名称，也可在高级配置中覆盖 |

依赖策略：

| 策略 | 说明 |
| --- | --- |
| 自动创建 | 每次都创建新的依赖实体 |
| 优先复用已有 | 上下文已有则复用，没有则创建 |
| 必须已存在 | 上下文没有则报错 |
| 查询已有 | 根据条件查已有数据 |

订单示例：

| 当前字段 | 依赖实体 | 取值字段 |
| --- | --- | --- |
| product_id | 产品 | id |
| user_id | 用户 | id |

执行效果：

```text
创建订单
  ↓
先创建或复用产品
  ↓
先创建或复用用户
  ↓
product_id = 产品.id
user_id = 用户.id
  ↓
创建订单
```

## 8. 创建方式

当前已实现 SQL 自动创建。实体配置中的 `create_type` 保留了 API/SQL/函数扩展位，但当前 runner 只执行自动 insert。

SQL 自动创建：

| 配置 | 示例 |
| --- | --- |
| 插入方式 | 自动 insert |
| 表名 | `orders` |
| 字段来源 | 实体字段规则和模板字段覆盖 |
| 主键获取 | SQLAlchemy insert result 或 payload 中的主键字段 |
| 事务 | 自动提交 |

暂未实现：

- API 创建。
- 自定义 SQL 创建。
- 自定义函数创建。

## 9. 删除方式

删除方式用于自动清理。

当前已实现 SQL 主键删除。执行时会在 `DataFactoryExecutionItem.database` 中记录真实落库数据库，清理时使用该数据库删除，避免环境绑定变更导致误删。

```sql
delete from orders where id = :id
```

删除配置：

| 字段 | 说明 |
| --- | --- |
| 删除方式 | 当前实现 SQL 主键删除 |
| 删除条件 | 实体主键字段和执行明细主键值 |
| 清理顺序 | 数值越大越先清理 |
| 失败处理 | 记录失败原因，可在执行记录中重试 |

清理顺序示例：

```text
订单 cleanup_order = 30
产品 cleanup_order = 20
用户 cleanup_order = 10
```

清理时倒序：

```text
订单 -> 产品 -> 用户
```

## 10. 接口设计

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/data-factory/entity` | 实体列表 |
| POST | `/data-factory/entity` | 新增实体 |
| PUT | `/data-factory/entity` | 修改实体 |
| DELETE | `/data-factory/entity` | 删除实体 |
| POST | `/data-factory/entity/copy` | 当前返回“不支持复制”，实体是表级定义 |
| PUT | `/data-factory/entity/status` | 启用/禁用 |
| GET | `/data-factory/datasource-alias` | 逻辑数据源列表 |
| POST | `/data-factory/discover/tables` | 读取表列表 |
| POST | `/data-factory/discover/table` | 读取指定表字段 |
| GET | `/data-factory/field` | 字段规则列表 |
| POST | `/data-factory/field/batch-save` | 批量保存字段规则 |

## 11. 验收标准

- 可以选择逻辑数据源。
- 可以选择结构发现环境并读取数据库表列表。
- 可以读取 `orders` 表字段。
- 自增主键默认跳过。
- `_id` 字段默认推荐为依赖字段。
- 可以把 `product_id` 关联到产品实体的 `id`。
- 可以把 `user_id` 关联到用户实体的 `id`。
- 通过状态模板调试创建订单时能自动创建产品和用户。
- 通过执行记录清理时按订单、产品、用户顺序清理。
