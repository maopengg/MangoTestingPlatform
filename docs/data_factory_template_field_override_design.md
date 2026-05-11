# 数据工厂状态模板字段覆盖方案

## 背景

工厂实体字段规则定义的是实体字段的默认生成方式。状态模板需要在不修改实体默认规则的前提下，对某个模板中的字段生成方式进行覆盖。例如实体默认 `type=0`，但“已启用状态”模板中希望 `type=1`。

## 数据结构

不新增数据库表，继续使用 `DataFactoryTemplate.field_overrides` 这个 JSONField。字段未出现在 `field_overrides` 中表示不覆盖，继续使用工厂实体字段规则。

`field_overrides` 的标准结构：

```json
{
  "type": {
    "generator_type": 1,
    "generator_config": {
      "value": "1"
    }
  },
  "name": {
    "generator_type": 13,
    "generator_config": {
      "value": "${{character_male_name()}}"
    }
  },
  "remark": {
    "generator_type": 0,
    "generator_config": {
      "reason": "该模板不生成备注"
    }
  }
}
```

`generator_type` 取值与工厂实体字段规则一致：

| 值 | 含义 |
| --- | --- |
| 0 | 跳过 |
| 1 | 固定值 |
| 2 | 随机字符串 |
| 3 | 随机整数 |
| 4 | 随机小数 |
| 5 | 当前时间 |
| 6 | 相对时间 |
| 7 | UUID |
| 8 | 自动编号 |
| 9 | 枚举值 |
| 10 | 表达式 |
| 11 | 依赖实体字段 |
| 12 | SQL查询结果 |
| 13 | 测试数据方法 |

## 后端规则

后端新增 Pydantic 模型对 `field_overrides` 做强类型解析：

- key：字段名
- value：字段覆盖规则
- `generator_type`：必填，整数
- `generator_config`：可选，默认 `{}`

执行优先级：

```text
请求 overrides > 状态模板 field_overrides > 工厂实体字段规则
```

合并时不会修改数据库中的实体字段规则，而是基于运行时字段副本生成有效字段列表。

## 前端方案

状态模板编辑弹窗中的“字段覆盖(JSON)”改为可复用组件 `FieldOverrideEditor`。

组件职责：

- 根据实体字段列表渲染表格
- 每行默认“不覆盖”
- 用户可以选择覆盖生成方式并填写覆盖配置
- 保存时只输出有覆盖的字段
- 组件对 `field_overrides` 使用 TypeScript 类型约束

建议列：

```text
字段 / 说明 / 默认生成方式 / 覆盖方式 / 覆盖配置 / 可空 / 主键 / DB类型 / 平台类型
```

## 示例

实体默认规则：

```json
{
  "type": {
    "generator_type": 1,
    "generator_config": {
      "value": "0"
    }
  }
}
```

状态模板覆盖规则：

```json
{
  "type": {
    "generator_type": 1,
    "generator_config": {
      "value": "1"
    }
  }
}
```

最终生成数据时 `type` 为 `1`。
