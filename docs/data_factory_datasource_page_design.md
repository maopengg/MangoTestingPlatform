# 数据工厂：数据源映射页面设计

## 1. 页面定位

数据源映射页面负责把“稳定的业务数据源名称”映射到“不同测试环境下的真实数据库连接”。

它解决的问题是：测试环境数据库名称可能不同，但数据工厂实体和模板应该复用同一套配置。

示例：

| 逻辑数据源 | 测试环境 | 真实数据库 |
| --- | --- | --- |
| mall_main | dev | mall_dev |
| mall_main | test | mall_test |
| mall_main | pre | mall_pre |

工厂实体只绑定 `mall_main`，执行时选择 `dev/test/pre`，系统自动解析真实数据库。

## 2. 页面入口

```text
数据工厂 / 数据源映射
路径：/data-factory/datasource/index
```

## 3. 页面结构

```text
上方：逻辑数据源列表
右侧/弹窗：新增、编辑逻辑数据源
抽屉：当前逻辑数据源的环境绑定列表
```

## 4. 逻辑数据源

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| 所属产品 | 是 | 关联 `ProjectProduct` |
| 名称 | 是 | 中文名，例如商城主库 |
| 编码 | 是 | 稳定编码，例如 `mall_main` |
| 数据库类型 | 是 | MySQL/PostgreSQL/SQLite |
| 描述 | 否 | 业务说明 |
| 状态 | 是 | 启用/禁用 |

规则：

- 同一产品下逻辑数据源编码唯一。
- 工厂实体只能选择启用的逻辑数据源。
- 逻辑数据源类型必须与绑定的真实数据库类型一致。

## 5. 环境绑定

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| 逻辑数据源 | 是 | 当前抽屉选中的逻辑数据源 |
| 测试环境 | 是 | 关联 `TestObject` |
| 真实数据库 | 是 | 关联系统数据库配置 `Database` |
| 描述 | 否 | 说明 |
| 状态 | 是 | 启用/禁用 |

规则：

- 同一个逻辑数据源在同一个测试环境下只能有一个启用绑定。
- 真实数据库的 `db_type` 必须等于逻辑数据源的 `db_type`。
- 运行模板、发现表结构时都通过绑定关系解析真实数据库。

## 6. 解析流程

```text
输入：datasource_alias_id + 顶部全局测试环境
  ↓
查找 DataFactoryDatasourceBinding
  ↓
校验绑定启用
  ↓
校验 db_type 一致
  ↓
返回真实 Database
```

找不到绑定时应给出明确错误：

```text
逻辑数据源未绑定当前测试环境
```

## 7. 接口设计

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/data-factory/datasource-alias` | 逻辑数据源列表 |
| POST | `/data-factory/datasource-alias` | 新增逻辑数据源 |
| PUT | `/data-factory/datasource-alias` | 修改逻辑数据源 |
| DELETE | `/data-factory/datasource-alias` | 删除逻辑数据源 |
| GET | `/data-factory/datasource-binding` | 环境绑定列表 |
| POST | `/data-factory/datasource-binding` | 新增环境绑定 |
| PUT | `/data-factory/datasource-binding` | 修改环境绑定 |
| DELETE | `/data-factory/datasource-binding` | 删除环境绑定 |

## 8. 前端页面结构

数据源映射页面采用 `index.vue + config.ts`：

| 文件 | 说明 |
| --- | --- |
| `datasource/config.ts` | 逻辑数据源主表列、环境绑定明细列 |
| `datasource/index.vue` | 逻辑数据源 CRUD、环境绑定 CRUD |

操作列统一只保留两个主按钮：

| 主按钮 | 下拉菜单 |
| --- | --- |
| 编辑、环境绑定 | 删除 |

## 9. 验收标准

- 可以创建逻辑数据源。
- 可以给逻辑数据源绑定多个测试环境。
- 绑定时会校验数据库类型一致。
- 工厂实体页面可以选择逻辑数据源。
- 表发现和模板调试运行都可以通过“逻辑数据源 + 顶部全局测试环境”解析真实数据库。
