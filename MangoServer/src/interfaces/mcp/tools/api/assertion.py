from __future__ import annotations

from src.interfaces.mcp.common import ok
from .helpers import (
    _content_assertion_methods,
    _flatten_assertion_methods,
    _general_assertion_template,
    _selectable_assertion_method_groups,
)


def register_assertion_tools(mcp):
    @mcp.tool()
    def get_api_assertion_methods() -> dict:
        """查询 API 断言方法选项，来源同前端 system/cache/data/key/value?key=ass_select_value。"""
        groups = _selectable_assertion_method_groups()
        content_methods = _content_assertion_methods(groups)
        return ok(
            {
                "source": "cache_data.ass_select_value",
                "groups": groups,
                "response_extract_methods": content_methods,
                "jsonpath_methods": content_methods,
                "flat_methods": _flatten_assertion_methods(groups),
                "recommended": {
                    "jsonpath_equal": "p_is_equal_to",
                    "jsonpath_contains": "p_contains",
                    "jsonpath_null": "p_is_none",
                    "jsonpath_not_null": "p_is_not_none",
                    "jsonpath_true": "p_is_true",
                    "jsonpath_false": "p_is_false",
                    "general_equal": "p_is_equal_to",
                    "regex_extract_equal": "p_is_equal_to",
                },
                "notes": [
                    "响应提取断言的 method 必须使用 jsonpath_methods 中叶子节点的 value，例如 p_is_equal_to，不能使用 eq。",
                    "ass_jsonpath.assertion_type 支持 jsonpath/regex/cache；不传默认 jsonpath。regex 从 response.text 提取，cache 要求 actual 使用完整的 ${{key}} 格式并从当前用例运行缓存取值。",
                    "p_matches/p_does_not_match 已停止提供给新配置；正则表达式应写入 actual，并设置 assertion_type=regex。",
                    "判断 ass_jsonpath.expect 如何传值必须看所选 method 在 jsonpath_methods/flat_methods 中的 parameter 定义。",
                    "断言关系字段 group_logic 可选 AND/OR：AND 是且，OR 是或；不传 group_logic 默认 AND。需要或关系时，多条断言使用相同 group_name 且 group_logic=OR。",
                    "如果 method.parameter 里包含 {f:\"expect\"}，expect 传预期值；如果 parameter 只有 {f:\"actual\"} 或不包含 expect，expect 必须传 null。",
                    "如果响应字段值是 JSON null，不要使用 p_is_equal_to + expect:null，应使用 p_is_none + expect:null。",
                    "如果响应字段值是空字符串，使用 p_is_equal_to + expect:\"\" 或 p_is_empty，不能按 null 处理。",
                    "response.json 可为 object/array/string/number/boolean/null；jsonpath 类型只支持 object/array，regex 类型读取 response.text，cache 类型读取当前运行缓存。",
                    "通用断言保存的是前端级联选项对象，建议先用 get_api_assertion_schema 查看结构。",
                ],
            }
        )

    @mcp.tool()
    def get_api_assertion_schema() -> dict:
        """返回 API 场景断言字段格式。"""
        try:
            general_equal = _general_assertion_template("p_is_equal_to", "${{实际值}}", "预期值")
        except Exception:
            general_equal = {"method": "内容断言 / 值等于什么 / 等于expect", "value": {}}
        return ok(
            {
                "assertion_types": {
                    "ass_json_all": "JSON一致断言。仅适用于 object/array 响应；保存基础、固定的期望 JSON 片段，后端用 p_in_dict 到响应 JSON 中做局部包含匹配，不是全量相等断言；已在这里断言的字段无需再重复写入 ass_jsonpath。",
                    "ass_jsonpath": "响应提取断言。assertion_type=jsonpath 时 actual 是 JSONPath；regex 时 actual 是正则表达式；cache 时 actual 必须是完整的 ${{key}} 缓存表达式。不传 assertion_type 默认 jsonpath。取值后执行 method。可选 group_name/group_logic 配置关系。",
                    "ass_text_all": "文本一致断言。保存完整预期响应文本，后端用 response.text.strip() == expect.strip()。",
                    "ass_general": "通用断言。外层 value 保存前端级联选中的完整对象；parameter[].v 面向 textarea 保存，dict/list 应保存为 JSON 字符串，执行 SQL 断言时会自动反序列化。可选 group_name/group_logic 配置关系，group_logic=AND 表示且，OR 表示或；不传默认 AND。",
                    "ass_sql": "SQL断言。每项必须传 datasource_alias；可传 test_envs 多选执行环境，不传、null 或 [] 表示全部环境执行。运行时按当前项目产品和测试环境解析绑定并执行；仅支持 MySQL、PostgreSQL、SQLite。",
                    "ass_schema": "结构化断言。保存 JSON Schema 对象；也可调用 auto_generate_api_case_scenario_schema 自动生成。",
                },
                "ass_jsonpath": [
                    {"assertion_type": "jsonpath", "actual": "$.code", "method": "p_is_equal_to", "expect": "0"},
                    {"assertion_type": "regex", "actual": "orderId=(\\d+)", "method": "p_is_equal_to",
                     "expect": "10001"},
                    {"assertion_type": "regex", "actual": "error=(\\w+)", "method": "p_is_none", "expect": None},
                    {"assertion_type": "cache", "actual": "${{order_id}}", "method": "p_is_equal_to",
                     "expect": "10001"},
                    {"group_name": "登录成功关系", "group_logic": "OR", "assertion_type": "jsonpath",
                     "actual": "$.code", "method": "p_is_equal_to", "expect": "0"},
                    {"group_name": "登录成功关系", "group_logic": "OR", "assertion_type": "jsonpath",
                     "actual": "$.success", "method": "p_is_true", "expect": None},
                ],
                "regex_extract_rule": {
                    "no_group": "没有捕获组时取完整匹配内容。",
                    "one_group": "一个捕获组时取 group(1)。",
                    "multiple_groups": "多个捕获组时返回捕获值列表。",
                    "no_match": "未匹配时提取结果为 null，再交给所选断言方法判断。",
                },
                "ass_general": [general_equal],
                "ass_sql": [{
                    "actual": "SELECT id FROM orders WHERE order_no=${{order_no}}",
                    "method": "assert_sql_count",
                    "expect": "1",
                    "datasource_alias": 2,
                    "test_envs": [0, 3],
                }],
                "group_rule": {
                    "default": "不传 group_name 或 group_logic 时，按 AND(且) 处理，且未分组断言保持原有逐条全部通过语义。",
                    "and": "同一个 group_name 内 group_logic=AND 时，组内全部断言通过才算通过。",
                    "or": "同一个 group_name 内 group_logic=OR 时，组内任意一条断言通过即算通过。",
                    "input": "MCP 创建/更新保存时可以输入 group_logic=AND 或 OR；小写会自动转大写，其他值按 AND 保存。",
                },
                "ass_json_all": {"code": 0, "data": {"status": 1}},
                "ass_text_all": "完整响应文本",
                "ass_schema": {"type": "object", "properties": {"code": {"type": "integer"}}},
            }
        )
