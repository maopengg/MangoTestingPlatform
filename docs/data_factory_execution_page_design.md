# 数据工厂：执行记录页面设计

## 1. 页面定位

执行记录页面负责查看每一次数据工厂运行的结果，包括：

- 哪个模板调试或数据工厂执行任务触发了数据创建。
- 创建了哪些实体数据。
- 每条数据的主键、唯一值和上下文。
- 是否已经清理。
- 清理失败的原因。

这个页面是数据工厂可治理的关键。没有执行记录，就无法可靠地自动清理测试数据。

## 2. 页面入口

```text
数据工厂 / 执行记录
路径：/data-factory/execution/index
```

建议页面布局：

```text
上方：筛选区
中间：执行批次列表
右侧/弹窗：执行详情
  上下文 JSON
  创建数据明细
  清理结果
```

## 3. 执行批次列表

列表字段：

| 字段 | 说明 |
| --- | --- |
| 执行编号 | 唯一编号 |
| 来源类型 | 模板调试 / 手动执行 / 系统调用 |
| 阶段 | 前置 / 后置 / 调试 |
| 所属产品 | 关联产品 |
| 来源 | 根据 `source_type/source_id/template_id` 推导展示，不单独落库保存 |
| 测试环境 | TestObject 环境 |
| 执行状态 | 成功/失败/进行中 |
| 清理状态 | 未清理/部分清理/已清理/清理失败 |
| 创建数量 | 创建的数据条数 |
| 创建时间 | 执行时间 |
| 清理时间 | 清理完成时间 |

操作：

- 查看详情
- 手动清理
- 查看上下文 JSON

筛选：

- 执行编号
- 来源类型
- 所属产品
- 用例 ID
- 模板名称
- 执行状态
- 清理状态
- 创建时间范围

## 4. 执行详情

详情分为 4 个区域。

基础信息：

| 字段 | 说明 |
| --- | --- |
| 执行编号 | 本次执行唯一编号 |
| 来源类型 | 模板调试/手动执行/系统调用 |
| 来源 ID | 用例 ID 或模板 ID |
| 执行阶段 | 前置/后置/调试 |
| 执行状态 | 成功/失败 |
| 错误信息 | 执行失败原因 |

上下文：

```json
{
  "用户": {
    "id": 88,
    "username": "AUTO_USER_abc"
  },
  "订单": {
    "id": 3001,
    "order_no": "AUTO_ORDER_1234"
  }
}
```

创建数据明细：

| 字段 | 说明 |
| --- | --- |
| 模板 | 默认用户/已支付订单 |
| 别名 | 用户/订单 |
| 实际数据库 | 创建该数据时解析到的真实 `Database` |
| 主键值 | id |
| 清理策略 | 执行结束/手动/不清理 |
| 清理顺序 | 数值越大越先清理 |
| 清理状态 | 未清理/已清理/失败 |
| 清理错误 | 失败原因 |

清理结果：

| 字段 | 说明 |
| --- | --- |
| 时间 | 清理时间 |
| 实体 | 清理对象 |
| 动作 | SQL 主键删除 |
| 结果 | 成功/失败 |
| 错误 | 错误详情 |

## 5. 清理状态设计

执行批次状态：

| 状态 | 说明 |
| --- | --- |
| 进行中 | 工厂正在执行 |
| 成功 | 创建成功 |
| 失败 | 创建失败 |

明细清理状态：

| 状态 | 说明 |
| --- | --- |
| 未清理 | 创建后尚未清理 |
| 已清理 | 已成功删除 |
| 清理失败 | 删除失败 |
| 跳过清理 | 策略为不清理或手动跳过 |

批次清理状态根据明细聚合：

```text
全部已清理 -> 已清理
部分已清理且部分失败 -> 部分清理
任意失败 -> 清理失败
全部未清理 -> 未清理
```

## 6. 手动清理

当前页面支持按执行批次清理：

| 操作 | 说明 |
| --- | --- |
| 清理当前执行批次 | 清理该 execution 下所有可清理数据 |

清理顺序：

```text
按 cleanup_order 倒序清理
同顺序按执行明细 id 倒序清理
```

清理范围：

- 清理对象是同一个 `DataFactoryExecution` 下的所有未清理执行明细。
- 根模板创建的数据会清理。
- 依赖模板在本次执行中自动创建的数据也会清理。
- 复用上下文已有的数据不会生成执行明细，因此不会被清理，避免误删业务基线数据。

清理确认弹窗需要展示：

- 将清理多少条数据。
- 涉及哪些实体。
- 清理后不可恢复。

重复清理过滤：

| 场景 | 处理 |
| --- | --- |
| 批次已清理 | 页面直接提示“当前执行记录已清理，无需重复清理” |
| 接口收到已清理批次 | 返回成功响应和明确提示，不重复执行 SQL 删除 |
| 明细已清理 | 清理服务过滤掉已清理明细 |

## 7. 自动清理触发点

单次执行清理：

```text
数据工厂执行结束
  ↓
查询需要自动清理的执行明细
  ↓
按 cleanup_order 倒序清理
```

调试清理：

```text
模板调试运行
  ↓
用户点击一键清理
```

## 8. 数据模型建议

执行批次：

```python
class DataFactoryExecution(models.Model):
    execution_no = models.CharField(max_length=64, unique=True)
    source_type = models.SmallIntegerField()  # TEMPLATE_DEBUG/MANUAL/SYSTEM
    source_id = models.IntegerField(null=True)
    template_id = models.IntegerField(null=True)
    project_product = models.ForeignKey("auto_system.ProjectProduct", on_delete=models.PROTECT)
    test_object = models.ForeignKey("auto_system.TestObject", null=True, on_delete=models.PROTECT)
    stage = models.SmallIntegerField()
    status = models.SmallIntegerField(default=1)
    cleanup_status = models.SmallIntegerField(default=0)
    context = models.JSONField(default=dict)
    error_message = models.TextField(null=True)
    create_time = models.DateTimeField(auto_now_add=True)
    cleanup_time = models.DateTimeField(null=True)
```

执行明细：

```python
class DataFactoryExecutionItem(models.Model):
    execution = models.ForeignKey(DataFactoryExecution, on_delete=models.CASCADE)
    template = models.ForeignKey("auto_data_factory.DataFactoryTemplate", null=True, on_delete=models.PROTECT)
    database = models.ForeignKey("auto_system.Database", null=True, on_delete=models.PROTECT)
    alias = models.CharField(max_length=64)
    primary_value = models.CharField(max_length=256)
    data = models.JSONField(default=dict)
    cleanup_strategy = models.SmallIntegerField(default=1)
    cleanup_order = models.IntegerField(default=100)
    cleanup_status = models.SmallIntegerField(default=0)
    cleanup_error = models.TextField(null=True)
    create_time = models.DateTimeField(auto_now_add=True)
    cleanup_time = models.DateTimeField(null=True)
```

## 9. 接口设计

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/data-factory/execution` | 执行批次列表 |
| GET | `/data-factory/execution/detail` | 执行详情 |
| GET | `/data-factory/execution/item` | 创建明细列表 |
| POST | `/data-factory/execution/cleanup` | 清理执行批次 |
| GET | `/data-factory/execution/context` | 获取上下文 JSON |

## 10. 前端页面结构

执行记录页面采用 `index.vue + config.ts`：

| 文件 | 说明 |
| --- | --- |
| `execution/config.ts` | 执行记录主表列、执行明细表格列 |
| `execution/index.vue` | 详情加载、清理、错误展示 |

操作列：

| 主按钮 | 下拉菜单 |
| --- | --- |
| 详情、清理 | 无 |

## 11. 验收标准

- 可以查看所有数据工厂执行批次。
- 可以按来源、状态、清理状态筛选。
- 可以查看上下文 JSON。
- 可以查看每条创建数据的模板、主键和完整数据。
- 可以查看每条创建数据实际使用的数据库。
- 可以手动清理单个执行批次。
- 已清理的执行批次再次点击清理时返回明确提示，不重复清理。
- 清理时按依赖倒序执行。
- 清理失败时能看到明确错误。
