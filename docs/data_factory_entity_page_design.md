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

表结构发现不再在数据工厂页面单独选择测试环境，而是复用平台顶部全局测试环境。页面读取表列表、同步字段、保存后自动同步字段时，都会把顶部环境传给后端，用于把逻辑数据源解析成真实 `Database` 后读取表结构。

数据源配置：

| 字段 | 说明 |
| --- | --- |
| 逻辑数据源 | 选择 `DataFactoryDatasourceAlias` |
| 顶部全局测试环境 | 来自页面顶部环境选择器，只用于解析真实数据库 |
| 真实数据库 | 根据逻辑数据源和测试环境自动解析 |
| 数据库类型 | 来自逻辑数据源和真实数据库校验 |
| 表名 | 下拉选择或手动输入 |

发现流程：

```text
选择逻辑数据源
  ↓
确认顶部已选择测试环境
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

字段规则弹窗不再提供“发现表”和“表下拉框”。实体已经在基础信息中绑定了表名，因此字段同步直接使用当前实体的 `table_name`：

```text
点击“同步当前表字段”
  ↓
读取当前实体的逻辑数据源、产品、表名
  ↓
读取顶部全局测试环境
  ↓
发现当前表字段并刷新字段规则
```

这样可以避免用户在字段规则弹窗里切换到其它表，导致实体表名和字段规则来源不一致。

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
| 生成配置 | 页面直接展示 `generator_config.value` 或可读说明，不展示 JSON |
| 实际值 | 点击“生成实际值”后展示当前配置生成出的结果 |

字段输出规则：

```text
实体创建成功后，默认把当前 payload、主键、唯一字段全部写入运行上下文。
```

页面不再提供“是否输出变量”和“输出名”配置。字段默认可通过模板名称和字段名引用，例如：

```text
${{创建用户.id}}
${{创建用户.username}}
${{创建订单.order_no}}
```

字段规则模型不再保存 `output_enabled`、`output_name`。执行上下文统一按真实字段名输出，减少页面配置和数据库字段冗余。

`必填`、`主键`、`自增` 是数据库结构元数据，不是造数规则。

页面处理规则：

| 字段 | 页面表现 | 是否允许手工修改 |
| --- | --- | --- |
| 必填 | 只读标签：必填/可空 | 否 |
| 主键 | 只读标签：主键/普通 | 否 |
| 自增 | 只读标签：自增/非自增 | 否 |

这些字段只能通过“同步字段”从真实数据库刷新。这样可以避免用户手工修改数据库元数据，导致必填校验、主键跳过、自增字段生成逻辑与真实数据库不一致。

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
| 依赖模板 | 产品表 / 默认产品 |
| 取值字段 | id |
| 依赖策略 | 优先复用已有 |
| 上下文名称 | 默认使用依赖模板名称，也可在高级配置中覆盖 |

依赖策略：

| 策略 | 说明 |
| --- | --- |
| `create_always` | 每次都创建新的依赖实体 |
| `reuse_or_create` | 上下文已有则复用，没有则创建 |
| `must_exist` | 上下文没有则报错 |

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

### 7.1 多级依赖共用同一条数据

当父实体和子实体都依赖同一个实体时，应通过同一个依赖模板实现共享。例如：

```text
订单 -> 用户
订单 -> 产品
产品 -> 用户
```

目标是订单和产品使用同一个用户。

字段规则配置：

| 实体 | 字段 | 生成方式 | 依赖模板 | 取值字段 | 策略 |
| --- | --- | --- | --- | --- | --- |
| 产品 | `user_id` | 依赖实体字段 | 创建用户 | `id` | `reuse_or_create` |
| 订单 | `user_id` | 依赖实体字段 | 创建用户 | `id` | `reuse_or_create` |
| 订单 | `product_id` | 依赖实体字段 | 创建产品 | `id` | `reuse_or_create` |

页面配置要求：

| 页面项 | 说明 |
| --- | --- |
| 依赖模板 | 产品和订单的 `user_id` 必须选择同一个用户模板 |
| 取值字段 | 通常选择 `id` |
| 依赖策略 | 默认使用 `reuse_or_create` |
| 上下文别名 | 默认使用依赖模板名称，页面可后续扩展高级配置 |

预期执行结果：

```text
创建订单模板
  ↓
创建产品模板
  ↓
创建用户模板
  ↓
产品.user_id = 用户.id
  ↓
订单.user_id = 同一个用户.id
  ↓
订单.product_id = 产品.id
```

注意：

- 如果订单和产品都选择同一个“创建用户”模板，则复用同一个用户。
- 如果选择两个不同用户模板，则会创建两个用户。
- 如果策略改为 `create_always`，即使上下文已有用户，也会创建新用户。
- 页面后续建议增加“依赖关系预览树”，用于展示哪些模板会创建、哪些模板会复用。

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
| 失败处理 | 记录失败原因，可在执行记录中查看 |

实体不再配置清理策略。清理策略由状态模板决定，实体只负责清理顺序。这样同一张表可以在不同状态模板中选择不同清理策略，例如“临时订单”手动清理，“基线用户”不清理。

清理范围不是只删除根实体，而是删除一次执行记录中实际创建出的所有实体数据。比如订单模板依赖用户模板和产品模板，并且本次执行自动创建了用户、产品、订单三条数据，那么清理该执行记录时会按顺序全部清理。如果用户来自外部上下文复用，没有在本次执行中创建，则不会生成执行明细，也不会被清理。

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
| POST | `/data-factory/field/preview-values` | 根据当前字段规则生成实际值预览，不落库 |

## 11. 前端页面结构

工厂实体页面采用 `index.vue + config.ts`：

| 文件 | 说明 |
| --- | --- |
| `entity/config.ts` | 实体主列表列、字段规则表格列基础配置 |
| `entity/index.vue` | 实体保存、表发现、字段同步、依赖模板选择、实际值预览 |

操作列统一只保留两个主按钮：

| 主按钮 | 下拉菜单 |
| --- | --- |
| 编辑、字段规则 | 启用/禁用、删除 |

## 12. 验收标准

- 可以选择逻辑数据源。
- 可以使用顶部全局测试环境读取数据库表列表。
- 可以读取 `orders` 表字段。
- 自增主键默认跳过。
- `_id` 字段默认推荐为依赖字段。
- 可以把 `product_id` 关联到产品实体的 `id`。
- 可以把 `user_id` 关联到用户实体的 `id`。
- 可以在字段规则中通过“依赖模板 + 取值字段”下拉完成关联配置。
- 可以点击“生成实际值”预览字段生成结果，空值显示为 `null`。
- 通过状态模板调试创建订单时能自动创建产品和用户。
- 通过执行记录清理时按订单、产品、用户顺序清理。
