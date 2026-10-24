# 运行值与变量替换

case_context、case_data、操作/断言参数、前置和清理的所有值都遵本规则，与 `mangotools.data_processor.DataProcessor.replace` 实现一致；可用时以实现为准。

## 标准实现

能导入平台包时每执行一个DataProcessor，初始化缓存并用replace，不另写解析器：

```python
from mangotools.data_processor import DataProcessor

processor = DataProcessor()
processor.set_dict_cache(initial_variables)
resolved = processor.replace(raw_value)
current_variables = processor.get_all()
```

现有实现递归list、字典键值；先最内层表达式；含括号按已注册数据函数，否则按缓存键；恰一个普通竖线拆expression/cache_key并缓存；缺键抛平台业务错；完整单表达式保原生类型；嵌入转文本且带引号表达式有JSON安全替换；完整表达式解析None变空串；最终字符串trim。

标准解析器不可用，仅实现当前Case明确需要且文档定义的兼容子集，不猜未知函数。

## 运行作用域

每execution_token/选定参数组一个内存表，本地初始化不需MCP。优先序：

1. runtime_step.public_data_list的type0自定义全局，重复页面副本按全局ID去重且保返回顺序，后选同名覆盖默认；
2. 当前环境case_context.front_custom保存顺序；
3. 当前环境case_context.selected_parameter_set.parametrize保存顺序；
4. 执行中成功SQL/数据源runtime_bindings、自定义节点、浏览器输出、生成别名。

每本地项先用当时表解析值再按准确键存。自定义节点同理不调agent_ui_execute_runtime。type0普通上下文非服务端工作；type1数据源走服务端，type2代码变量在隔离沙箱前阻塞。

仅服务端运行需要时传request.runtime_variables，仅合并返回runtime_bindings。跨所有页面共享，不跨token/参数组复用；不另建服务端run表，不打印全表（可含凭据、个人数据、下载路径、业务值）。

## 表达式

### 生成、绑定、替换

真实值：

```text
${{str_random_string()|模版名称}}
```

文档表中的反斜线竖线是Markdown转义；使用MCP原始普通竖线，不给运行数据加反斜线。原始MCP确实含转义时按格式错误，不静默改平台数据。

解析节点参数时：str_random_string默认10位ASCII字母数字；如传正整数16用指定长度；缓存准确键模版名称；调用浏览器/工具前以同一生成值替换。

```text
expression: ${{str_random_string()|模版名称}}
generated:  a8K2pQ9xLm
runtime map: {"模版名称": "a8K2pQ9xLm"}
tool value: a8K2pQ9xLm
```

函数表达式每求值必调用并覆盖别名，匹配标准实现。每执行尝试只解析一次，用同值调用和上报；不要准备同次调用时重复解析。整节点重试重新解析可能产生新值并覆盖。

### 读取、替换

```text
${{模版名称}}
```

按准确缓存键读取并替换：

```text
runtime map: {"模版名称": "a8K2pQ9xLm"}
expression: ${{模版名称}}
tool value: a8K2pQ9xLm
```

跨页面有效，创建模板生成值应是后续查询/断言同一值，读取表达式绝不再生成。

### 嵌入表达式

长字符串内逐表达式解析转文本：

```text
模板-${{模版名称}}-回归
```

变为：

```text
模板-a8K2pQ9xLm-回归
```

整个参数单表达式保原生类型，None为空串，非浏览器工具的数值/布尔/list/object尤其重要。

标准解析也遍历字典键。query_key=user_id_type时：

```json
{"${{query_key}}": "user_id"}
```

解析为：

```json
{"user_id_type": "user_id"}
```

嵌套先内后外，key=123456时 `${{md5_32_small(${{key}})}}`先替换key再调md5。

## 其他输出绑定

成功后才将声明输出放同表：file_key绑定下载本地引用供 `${{下载文件1}}` 后续文档断言；set_cache_key绑定文本URL标题属性脚本结果；SQL前置合runtime_bindings；全局/前置/参数/自定义节点按序本地解析绑定。生产操作没成功不提前绑定。

## 每节点解析顺序

1. 用当前表，不按页面新建。
2. 递归字典列表。
3. 先内层表达式。
4. 已解析表达式有函数语法时调注册函数；位置/关键字按标准解析，引号与配平JSON/list参数允许逗号。
5. 仅恰一个普通竖线时，左求值后写右键。
6. 普通键读取。
7. 确认无未解表达式。
8. 调选择的执行工具。
9. 成功后存声明输出。

## 失败规则

- 缺变量：不传原表达式，当前节点失败，脱敏如 `运行变量“模版名称”尚未生成`，页面步骤失败。
- 不支持函数：不编近似数据，报平台函数当前AI不可用导致阻塞。
- 参数/别名语法非法：节点失败，不静默随机兜底。
- 重试每尝试只解析一次，重复求生成式按实现会覆盖缓存，不同次行为要意识到。
- 秘密只在目标工具边界解析，摘要观察文件名日志及可行截图脱敏。

## 跨步骤示例

```text
Step 0 / Node 118
input_value = ${{str_random_string()|模版名称}}
=> generate a8K2pQ9xLm
=> variables["模版名称"] = "a8K2pQ9xLm"
=> input a8K2pQ9xLm

Step 1 / Node 128
input_value = ${{模版名称}}
=> read variables["模版名称"]
=> input a8K2pQ9xLm

Step 1 / Node 131
expect = ${{模版名称}}
=> read variables["模版名称"]
=> assert page text contains a8K2pQ9xLm
```
