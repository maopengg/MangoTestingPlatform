# 数据工厂：工厂实体页面设计

## 1. 页面定位

工厂实体页面负责把一个业务数据对象配置成可创建、可引用、可清理的工厂实体。例如：

- 用户
- 产品
- 订单
- 报销单
- 部门审批

这个页面包含三类能力：

- 数据源选择与表结构发现。
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
| 实体编码 | 例如 order |
| 所属产品 | 关联 `ProjectProduct` |
| 数据库类型 | MySQL/PostgreSQL 等 |
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
- 实体编码
- 数据库类型
- 创建方式
- 状态

## 4. 基础信息

表单字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| 所属项目产品 | 是 | 关联 `ProjectProduct` |
| 实体名称 | 是 | 中文名，例如订单 |
| 实体编码 | 是 | 英文编码，例如 order |
| 默认别名 | 是 | 默认注入上下文的名称，例如订单 |
| 描述 | 否 | 业务说明 |
| 状态 | 是 | 启用/禁用 |

校验规则：

- 同一产品下 `实体编码` 唯一。
- 默认别名不能为空。
- 实体启用前必须至少有一种创建方式。

## 5. 数据源与表发现

数据工厂复用系统已有 `Database` 配置。`Database` 需要新增 `db_type` 字段表示数据库类型。

数据源配置：

| 字段 | 说明 |
| --- | --- |
| 数据源模式 | 固定数据库 / 跟随执行环境 |
| 测试对象 | 选择 `TestObject` |
| 数据库配置 | 选择启用的 `Database` |
| 数据库类型 | 来自 `Database.db_type` |
| 数据库名称 | 来自 `Database.name` |
| 表名 | 下拉选择或手动输入 |

第一期建议实现“固定数据库”，第二期再实现“跟随执行环境”。

发现流程：

```text
选择数据库配置
  ↓
点击读取表
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
| 输出变量 | 是否注入上下文 |
| 输出名 | 例如 订单.order_no |

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
| 上下文别名 | 产品 |

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

支持三类创建方式。

API 创建：

| 配置 | 示例 |
| --- | --- |
| 请求方法 | POST |
| 请求地址 | `/orders` |
| 请求头 | 可引用公共请求头 |
| 请求体 | JSON 模板 |
| 成功条件 | 状态码 200 或响应字段 |
| 主键提取 | `$.data.id` |

SQL 创建：

| 配置 | 示例 |
| --- | --- |
| 插入方式 | 自动 insert / 自定义 SQL |
| SQL 模板 | `insert into orders (...) values (...)` |
| 主键获取 | last_insert_id / returning / 查询 SQL |
| 事务 | 自动提交 |

自定义函数创建：

| 配置 | 示例 |
| --- | --- |
| 函数名 | create_order |
| 入参 | 字段上下文 |
| 出参 | 必须包含主键字段 |

第一期建议实现 API 创建和自动 insert。

## 9. 删除方式

删除方式用于自动清理。

API 删除：

```text
DELETE /orders/${{订单.id}}
```

SQL 删除：

```sql
delete from orders where id = :id
```

删除配置：

| 字段 | 说明 |
| --- | --- |
| 删除方式 | API/SQL/函数 |
| 删除条件 | 主键/唯一字段/自定义条件 |
| 清理顺序 | 数值越大越先清理 |
| 失败处理 | 继续/中断/重试 |

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
| POST | `/data-factory/entity/copy` | 复制实体 |
| PUT | `/data-factory/entity/status` | 启用/禁用 |
| GET | `/data-factory/database/list` | 数据库配置列表 |
| POST | `/data-factory/discover/tables` | 读取表列表 |
| POST | `/data-factory/discover/table` | 读取指定表字段 |
| GET | `/data-factory/field` | 字段规则列表 |
| PUT | `/data-factory/field` | 保存字段规则 |
| POST | `/data-factory/entity/debug-create` | 调试创建 |
| POST | `/data-factory/entity/debug-cleanup` | 清理调试数据 |

## 11. 验收标准

- 可以选择 MySQL/PostgreSQL 类型数据库。
- 可以读取数据库表列表。
- 可以读取 `orders` 表字段。
- 自增主键默认跳过。
- `_id` 字段默认推荐为依赖字段。
- 可以把 `product_id` 关联到产品实体的 `id`。
- 可以把 `user_id` 关联到用户实体的 `id`。
- 调试创建订单时能自动创建产品和用户。
- 调试清理时按订单、产品、用户顺序清理。
