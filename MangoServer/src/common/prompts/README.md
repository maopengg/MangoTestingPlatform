# 后端 AI 提示词目录

所有后端 AI 提示词统一由本目录管理。业务模块只准备动态数据并调用加载器或消息构造函数。

## 结构

```text
prompts/
├── catalog/       # 按业务能力拆分的 YAML 静态正文、版本、所有者和场景配置
├── base.py        # 无代码执行能力的安全模板渲染
├── loader.py      # YAML 加载、Pydantic 校验与进程内缓存
├── registry.py    # 显式 prompt_id -> YAML 文件注册表
└── *.py           # 少量需要保持领域 API 的消息构造器
```

`PromptDefinition` 按项目架构约束定义在 `src/common/schemas/prompt.py`。

## 规则

1. YAML 必须包含 `id`、`version`、`owner`、`description`；未知字段会校验失败。
2. 静态 system/user 正文、角色约束、输出契约、场景 focus 和固定规则写入 `catalog/*.yaml`。
3. 动态业务数据只在 Python 中裁剪、序列化，再通过 `{{ variable }}` 注入；模板不支持表达式和代码执行。
4. 新文件必须在 `registry.py` 显式登记，文件中的 `id` 必须与注册 ID 一致。
5. 修改提示词语义或输出结构必须提升 `version`，使用缓存的业务要把版本加入缓存键。
6. Service、View、Model、process 和 Agent 代码不得定义提示词正文；用户输入、测试桩和普通界面文案不属于提示词。
7. 数据库中的 Skill/MCP 自定义内容属于运行时配置，可以作为明确标记的动态上下文组合，但不能替代平台静态提示词目录。
8. Django `check` 会校验全部 YAML、注册完整性和数据契约；校验失败时禁止带病部署。

## 调用示例

```python
from src.common.prompts import get_prompt

prompt = get_prompt("ai.json_repair")
messages = [
    {"role": "system", "content": prompt.system},
    {"role": "user", "content": prompt.render("user", content=raw, error_message=msg, line=1, column=2)},
]
```
