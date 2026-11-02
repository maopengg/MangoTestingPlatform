from __future__ import annotations

from .helpers import (
    ok,
)


def register_schema_tools(mcp):
    @mcp.tool()
    def get_data_factory_schema() -> dict:
        """返回数据工厂 MCP 常用字段、枚举和变量约定。"""
        return ok(
            {
                "generator_type": {
                    0: "跳过",
                    1: "固定值",
                    2: "随机字符串",
                    3: "随机整数",
                    4: "随机小数",
                    5: "当前时间",
                    6: "相对时间",
                    7: "UUID",
                    9: "枚举值",
                    11: "依赖实体字段",
                    13: "测试数据方法",
                },
                "cleanup_strategy": {1: "执行结束", 2: "手动清理", 3: "不清理"},
                "cleanup_policy": {
                    "default": 1,
                    "selection_rule": "用户未明确要求保留数据时，新建模板和绑定 Case 必须优先使用 1=执行结束自动清理；2=手动清理、3=不清理仅在用户明确要求时使用。",
                    "case_override": "Case 绑定默认 1，优先于模板；显式 null 才继承模板。更新工具不传/null 表示不修改，不代表恢复继承。",
                    "scope": "清理本次 execution 创建的主表、关联表及依赖数据；API 额外创建的业务数据必须由 Case 级后置先清理。",
                    "failure": "自动清理失败必须保留执行明细并进入清理失败待办，不得通过手动清理或不清理掩盖失败。",
                },
                "operation_type": {2: "SQL（当前唯一支持的创建和清理方式）"},
                "case_source_type": {1: "API用例", 2: "UI用例", 3: "API接口场景"},
                "execution_source": {1: "模板调试", 2: "手动执行", 3: "系统调用", 4: "API用例", 5: "API接口场景"},
                "cache_variable_pattern": "${{配置名.字段名}}",
                "sql_query_policy": "MCP 不提供任意 SQL 查询工具；表结构发现、用例执行和数据工厂执行能力保持不变。",
                "entity_field_rule_workflow": {
                    "important": "数据实体必须同时有字段规则才能生成完整测试数据。create_data_factory_entity 默认只建实体壳；字段规则需要同步表结构或单独保存。",
                    "recommended_paths": [
                        "批量按表创建：先 list_data_factory_database_tables / get_data_factory_table_schema，再调用 batch_generate_data_factory_entities(sync_fields=True)。",
                        "单表创建并同步字段：调用 create_data_factory_entity(sync_fields=True, test_env=测试环境)。",
                        "手工维护字段：先 create_data_factory_entity，再调用 batch_save_data_factory_fields(entity_id, fields)。",
                    ],
                    "verification": "创建后调用 get_data_factory_entity_detail 或 list_data_factory_fields，确认 fields 不为空并且 generator_type/generator_config 符合业务字段含义。",
                    "template_overrides_scope": "DataFactoryTemplate.field_overrides 和 case 绑定里的 field_overrides 只是在执行模板时覆盖实体字段规则，不能替代实体字段规则本身。",
                    "tools": {
                        "discover_tables": "list_data_factory_database_tables",
                        "discover_schema": "get_data_factory_table_schema",
                        "create_entity_with_schema_fields": "create_data_factory_entity(sync_fields=True, test_env=...)",
                        "update_entity": "update_data_factory_entity",
                        "batch_create_entities_with_schema_fields": "batch_generate_data_factory_entities(sync_fields=True)",
                        "save_fields": "batch_save_data_factory_fields",
                        "preview_fields": "preview_data_factory_field_values",
                    },
                },
                "entity_schema_repair_workflow": {
                    "purpose": "实体因表结构差异被停用时，必须同时修复实体字段规则、直接场景模板和递归引用它的上游场景模板。使用现有 MCP 组合完成，不新增工具。",
                    "steps": [
                        "1. 调用 get_data_factory_entity_detail(entity_id) 获取实体和现有 fields。",
                        "2. 调用 get_data_factory_table_schema(table_name, datasource_alias_id, project_product_id, test_env) 读取指定环境实时表结构。",
                        "3. 对比 columns 与 fields，先说明新增、删除、变更字段和 replace=True 的删除影响。",
                        "4. 构造合并后 fields：同名字段使用 columns 的结构属性，但保留现有 generator_type/generator_config；新字段才使用 columns.recommend。不得直接原样传 columns，否则会覆盖同名字段的生成规则。",
                        "5. 新增必填字段（nullable=False、无默认值、非自增/非生成列）必须能生成非空且业务有效值。外键或 *_id 不得盲目随机，应绑定依赖实体/模板或明确测试数据方法。",
                        "6. 先调用 preview_data_factory_field_values(fields=合并后 fields, entity_id, test_env)；全部有效后再调用 batch_save_data_factory_fields(entity_id, fields=合并后 fields, replace=True)。",
                        "7. 重新查询实体和实时表结构，校验字段名、类型、可空性、主键、自增和长度已一致。",
                        "8. 调用 list_data_factory_templates(entity_id=entity_id, enabled_only=False) 找直接模板；再分页查询该产品全部模板（enabled_only=False），根据 items[].child_template 递归找出所有上游引用模板。",
                        "9. 按直接/子模板在前、上游父模板在后的顺序调用 preview_data_factory_template(template_id, test_env)，检查 can_debug_run、missing_fields、dependencies、output 和 cache_keys。",
                        "10. 新必填字段需要场景级值时，用 update_data_factory_template 修复 field_overrides；由父模板传值时，修复父模板 items[].field_overrides。删除/改名字段还要修复 field_overrides、items[].field_overrides 和 output_config 的失效引用。更新时传 test_env 刷新 config_status。",
                        "11. 重新预览全部受影响模板。只有 can_debug_run=True、missing_fields 为空、依赖树无错误且输出字段有值时才算修复成功。必要时使用 list_data_factory_case_configs 和 preview_data_factory_case_config 检查用例级 field_overrides。",
                        "12. 实体和全部受影响模板都通过后，才调用 update_data_factory_entity(entity_id, status=1) 重新启用实体。",
                    ],
                    "safety_rules": [
                        "必须明确传 test_env，不得用其他环境的表结构修复当前实体。",
                        "表不存在、读取失败、字段不一致、必填字段无有效值，或任一直接/上游模板预览失败时，不得启用实体。",
                        "同步前先告知 replace=True 的删除影响，不得无预览覆盖字段规则。",
                        "更新模板 items 时必须传完整列表，不得因修复单个子模板而丢失其他 items。",
                        "修复只修改平台配置，不会对业务数据库执行 DDL。",
                    ],
                },
                "template_preview_execute_cleanup_workflow": {
                    "preview_data": "查看或编辑配置时调用 preview_data_factory_template(preview_mode='configuration')，不访问业务库且无需环境；主动检查运行环境时使用 preview_mode='environment' 并指定 test_env，不落库。配置预览的 can_debug_run=False 不表示配置不可用，仅表示尚未校验运行环境。",
                    "safe_execute": [
                        "调用 preview_run_data_factory_template_impact(template_id, overrides, context, test_env) 获取即将落库的 payload/output/dependencies 和二次确认 token。",
                        "用户确认预览数据无误后，调用 execute_data_factory_template，并原样传回 preview_token 和 confirm_text。",
                        "execute_data_factory_template 会真实落库并返回 execution_id、execution_no、data、output、cache_keys。",
                    ],
                    "cleanup": [
                        "执行后如需清理，先调用 preview_cleanup_data_factory_execution_impact(execution_id) 查看会删除哪些执行明细。",
                        "用户确认后调用 cleanup_data_factory_execution，并原样传回 preview_token 和 confirm_text。",
                    ],
                    "delete_template": [
                        "删除场景模板前必须调用 preview_delete_data_factory_template_impact(template_id)，查看用例、关联模板、发布版本及受保护执行明细的引用。",
                        "用户确认后调用 delete_data_factory_template，并原样传回 preview_token 和 confirm_text。",
                        "上述引用存在时禁止删除，停用的用例绑定和仍可执行的历史发布版本也计入；推荐先停用 set_data_factory_template_status(status=0)。",
                    ],
                    "safety_rule": "真实执行和清理都属于危险操作，不允许跳过预览确认。",
                },
                "field_rule_payload": {
                    "required": ["name"],
                    "common_fields": {
                        "name": "数据库字段名，必填",
                        "label": "字段展示名/注释，不传时通常使用 name",
                        "db_type": "数据库原始类型，例如 BIGINT、VARCHAR(64)",
                        "platform_type": "平台类型：string/integer/decimal/datetime/date/boolean/json/enum",
                        "nullable": "是否允许为空",
                        "primary_key": "是否主键",
                        "autoincrement": "是否自增",
                        "max_length": "最大长度",
                        "enum_values": "枚举值数组",
                        "generator_type": "生成器类型，见 generator_type",
                        "generator_config": "生成器配置，见 generator_config_rule.common_generator_config",
                        "sort": "字段排序",
                    },
                    "examples": {
                        "tenant_id": {
                            "name": "tenant_id",
                            "label": "租户ID",
                            "db_type": "BIGINT",
                            "platform_type": "integer",
                            "nullable": False,
                            "generator_type": 13,
                            "generator_config": {"value": "${{tenant_id}}"},
                            "sort": 1,
                        },
                        "business_name": {
                            "name": "name",
                            "label": "名称",
                            "db_type": "VARCHAR(128)",
                            "platform_type": "string",
                            "nullable": False,
                            "generator_type": 13,
                            "generator_config": {"value": "AUTO${{str_lowercase(10)}}"},
                            "sort": 2,
                        },
                        "dependency_id": {
                            "name": "category_id",
                            "label": "分类ID",
                            "db_type": "BIGINT",
                            "platform_type": "integer",
                            "nullable": False,
                            "generator_type": 11,
                            "generator_config": {"dependency_entity_id": 12, "field": "id"},
                            "sort": 3,
                        },
                    },
                },
                "generator_config_rule": {
                    "how_to_choose": [
                        "主键自增字段通常使用 generator_type=0 跳过，让数据库生成。",
                        "tenant_id、valid、固定业务状态等确定值使用 generator_type=1 固定值，或 generator_type=13 写 ${{tenant_id}} 这类测试数据表达式。",
                        "名称、编号、手机号、邮箱、地址等业务字符串优先使用 generator_type=13 测试数据方法。",
                        "普通随机字符串可用 generator_type=2；普通数值范围可用 3/4；时间字段可用 5/6。",
                        "枚举字段使用 generator_type=9；外键或前置数据依赖使用 generator_type=11。",
                    ],
                    "generator_type_usage": {
                        0: {
                            "name": "跳过",
                            "use_for": "数据库自增主键、数据库默认值、创建时不需要写入的字段。",
                            "generator_config": {"reason": "可选，说明为什么跳过"},
                            "example": {"generator_type": 0, "generator_config": {"reason": "数据库自增主键"}},
                            "result": "该字段不会进入插入 payload。",
                        },
                        1: {
                            "name": "固定值",
                            "use_for": "固定状态、固定租户、固定开关值，或需要明确写死的字段。",
                            "generator_config": {"value": "任意 JSON 值，可为字符串/数字/布尔/null/对象/数组"},
                            "example": {"generator_type": 1, "generator_config": {"value": 1}},
                            "result": "直接返回 value，并按字段 platform_type 做类型转换。",
                        },
                        2: {
                            "name": "随机字符串",
                            "use_for": "不强调语义的随机编码。",
                            "generator_config": {"prefix": "可选前缀，默认空字符串",
                                                 "length": "随机部分长度，默认 8，必须大于 0"},
                            "example": {"generator_type": 2, "generator_config": {"prefix": "AUTO_", "length": 10}},
                            "result": "prefix + uuid hex 前 length 位。",
                        },
                        3: {
                            "name": "随机整数",
                            "use_for": "数量、排序、范围内整数。",
                            "generator_config": {"min": "最小值，默认 1", "max": "最大值，默认 100，min 不能大于 max"},
                            "example": {"generator_type": 3, "generator_config": {"min": 1, "max": 999}},
                            "result": "闭区间随机整数。",
                        },
                        4: {
                            "name": "随机小数",
                            "use_for": "金额、比例、带小数的数值。",
                            "generator_config": {"min": "最小值，默认 1", "max": "最大值，默认 100",
                                                 "precision": "小数位，默认 2，不能小于 0"},
                            "example": {"generator_type": 4,
                                        "generator_config": {"min": 10, "max": 99, "precision": 2}},
                            "result": "范围内随机 Decimal，并按 precision 保留小数。",
                        },
                        5: {
                            "name": "当前时间",
                            "use_for": "create_time、update_time、生效时间等当前时间字段。",
                            "generator_config": {},
                            "example": {"generator_type": 5, "generator_config": {}},
                            "result": "datetime.now()，再按字段 platform_type 转换。",
                        },
                        6: {
                            "name": "相对时间",
                            "use_for": "过期时间、未来/过去时间。",
                            "generator_config": {"days": "相对天数，默认 0", "hours": "相对小时，默认 0",
                                                 "minutes": "相对分钟，默认 0"},
                            "example": {"generator_type": 6, "generator_config": {"days": 7, "hours": 0, "minutes": 0}},
                            "result": "datetime.now() + timedelta(days/hours/minutes)。",
                        },
                        7: {
                            "name": "UUID",
                            "use_for": "唯一追踪号、外部唯一编码。",
                            "generator_config": {"dash": "是否保留 UUID 横线，默认 false"},
                            "example": {"generator_type": 7, "generator_config": {"dash": False}},
                            "result": "dash=false 返回 32 位 hex；dash=true 返回标准 UUID。",
                        },
                        9: {
                            "name": "枚举值",
                            "use_for": "状态、类型、开关等有限选项字段。",
                            "generator_config": {
                                "values": "枚举值数组；也可使用字段 enum_values",
                                "options": "可选展示项数组，格式 [{label,value}]",
                                "mode": "fixed 或 random，默认 fixed",
                                "value": "mode=fixed 时的固定值；不传则取第一个 values",
                            },
                            "example": {"generator_type": 9,
                                        "generator_config": {"values": [0, 1], "mode": "fixed", "value": 1}},
                            "result": "random 随机取 values；fixed 返回 value 或第一个 values。",
                        },
                        11: {
                            "name": "依赖实体字段",
                            "use_for": "外键字段、需要先创建前置数据再引用其 id/code/name 的字段。",
                            "entity_field_generator_config": {
                                "dependency_entity_id": "依赖的数据实体 ID，必填",
                                "field": "读取依赖实体输出字段，默认 id",
                            },
                            "template_or_case_override_generator_config": {
                                "dependency_entity_id": "依赖的数据实体 ID，必填",
                                "field": "读取依赖实体输出字段，默认 id",
                                "template_id": "可选，指定依赖实体使用哪个状态模板；不传则使用依赖实体默认启用模板",
                                "strategy": "reuse_or_create / must_exist / create_always，默认 reuse_or_create",
                            },
                            "example": {"generator_type": 11,
                                        "generator_config": {"dependency_entity_id": 12, "field": "id"}},
                            "result": "执行时先准备依赖实体数据，再把依赖数据中的 field 值写入当前字段。",
                        },
                        13: {
                            "name": "测试数据方法",
                            "use_for": "手机号、邮箱、姓名、地址、身份证、业务编号、缓存变量、编码处理等表达式生成值。MCP 只推荐使用测试数据分类的方法。",
                            "generator_config": {
                                "value": "测试数据表达式字符串，例如 ${{character_email()}} 或 AUTO${{str_lowercase(10)}}"},
                            "example": {"generator_type": 13,
                                        "generator_config": {"value": "AUTO${{str_lowercase(10)}}"}},
                            "result": "先返回 value 字符串，再通过测试数据引擎替换 ${{...}} 表达式，最后按 platform_type 转换。",
                        },
                    },
                    "priority": [
                        "字符串/文本/名称/编号/邮箱/手机号/地址等字符串类字段，优先使用 generator_type=13 测试数据方法。",
                        "测试数据方法不合适时，再使用 generator_type=2 随机字符串或 generator_type=1 固定值。",
                        "数值、时间、枚举、依赖字段按字段语义分别使用整数/小数/时间/枚举/依赖实体字段。",
                    ],
                    "string_field_recommendation": {
                        "generator_type": 13,
                        "generator_config": {"value": "${{测试数据方法(...)}}"},
                        "how_to_discover_methods": "调用 MCP 工具 list_test_data_methods(keyword=None, include_hidden=False) 获取测试数据方法类型、分组、参数、expression_template 和 example。",
                        "how_to_preview_expression": "调用 MCP 工具 evaluate_test_data_expression(expression='${{方法名(...)}}') 试算表达式。",
                        "method_result_cast": "生成值会按字段 platform_type 转换后保存；字符串字段通常直接保存表达式计算结果。",
                        "usage_steps": [
                            "调用 list_test_data_methods(keyword='name/phone/email/id 等') 查询可用测试数据方法。",
                            "从返回的 method.expression_template 或 method.example 拿到表达式。",
                            "把表达式写入字段规则 generator_config.value。",
                            "调用 preview_data_factory_field_values(fields=[...]) 或 preview_data_factory_template(template_id=...) 预览生成结果。",
                        ],
                        "expression_examples": [
                            "${{character_email()}}",
                            "${{character_phone()}}",
                            "${{character_male_name()}}",
                            "AUTO${{str_lowercase(10)}}",
                            "${{tenant_id}}",
                        ],
                    },
                    "test_data_method_tool": {
                        "tool": "list_test_data_methods",
                        "purpose": "查询随机测试数据/平台变量方法。只返回测试数据分类下的方法。",
                        "arguments": {
                            "keyword": "可选，用字段含义筛选，例如 email、phone、name、address、id",
                            "include_hidden": "默认 false，不返回内部隐藏方法",
                        },
                        "returns": {
                            "items": "按 type_group -> class_group -> method 分组",
                            "method.expression_template": "参数名模板，例如 ${{character_email()}}",
                            "method.example": "带示例参数的可直接试算表达式",
                            "method.parameter": "方法参数定义",
                        },
                    },
                    "common_generator_config": {
                        0: "跳过，无 generator_config 要求",
                        1: {"value": "固定值"},
                        2: {"prefix": "可选前缀", "length": "随机字符串长度，默认 8"},
                        3: {"min": "最小整数，默认 1", "max": "最大整数，默认 100"},
                        4: {"min": "最小小数，默认 1", "max": "最大小数，默认 100", "precision": "小数位，默认 2"},
                        5: "当前时间，无 generator_config 要求",
                        6: {"days": "相对天数", "hours": "相对小时", "minutes": "相对分钟"},
                        7: {"dash": "是否保留 UUID 横线，默认 false"},
                        9: {"values": "枚举数组", "mode": "random 时随机，否则取 value 或第一个枚举",
                            "value": "可选指定枚举值"},
                        11: {"dependency_entity_id": "依赖实体ID", "field": "取值字段，通常为 id"},
                        13: {"value": "测试数据方法表达式，例如 ${{character_email()}}"},
                    },
                    "string_examples": {
                        "email": {"generator_type": 13, "generator_config": {"value": "${{character_email()}}"}},
                        "phone": {"generator_type": 13, "generator_config": {"value": "${{character_phone()}}"}},
                        "name": {"generator_type": 13, "generator_config": {"value": "${{character_male_name()}}"}},
                        "address": {"generator_type": 13, "generator_config": {"value": "${{character_address()}}"}},
                        "fallback_random_code": {"generator_type": 13,
                                                 "generator_config": {"value": "AUTO${{str_lowercase(10)}}"}},
                    },
                },
                "dependency_field_rule": {
                    "entity_field_config": {
                        "generator_type": 11,
                        "generator_config": {
                            "dependency_entity_id": "依赖实体ID",
                            "field": "取值字段，通常为 id",
                        },
                    },
                    "template_or_case_override": {
                        "generator_type": 11,
                        "generator_config": {
                            "dependency_entity_id": "继承数据实体字段规则中的依赖实体ID",
                            "field": "继承数据实体字段规则中的取值字段",
                            "template_id": "可选；指定依赖实体下的状态模板。不传时使用依赖实体的默认启用模板。",
                            "strategy": "reuse_or_create",
                        },
                    },
                    "scene_item_node_reference": {
                        "scope": "仅用于场景模板 items[].field_overrides 或用例覆盖中的 __items__",
                        "generator_type": 11,
                        "generator_config": {
                            "source_node": "root 或 item:<已先执行的关联项ID/名称>",
                            "source_field": "来源节点字段，数据库自增主键通常为 id",
                        },
                        "behavior": "复用同一 execution 中节点落库后的真实字段值，不创建新的依赖模板",
                        "constraints": "只允许引用主节点或排序在当前项之前的兄弟节点；字段必须存在且平台类型一致",
                        "example": {
                            "risk_state_id": {
                                "generator_type": 11,
                                "generator_config": {"source_node": "root", "source_field": "id"},
                            },
                        },
                    },
                    "default_template": "状态模板 is_default=True 时为该实体默认模板；同一实体只保留一个默认模板。",
                },
                "template_usage_scope": {
                    1: {
                        "name": "用例可直接选择",
                        "meaning": "完整业务对象入口模板，会出现在 API/UI case 的数据工厂选择列表中，可直接绑定到用例执行。",
                        "recommended_for": "普通测试用户会直接消费的场景，例如完整订单流程、完整订单、有效用户。",
                    },
                    2: {
                        "name": "仅场景内部引用",
                        "meaning": "内部编排模板，不出现在 API/UI case 选择列表，只能被其他场景模板作为关联模板引用。",
                        "recommended_for": "子表、中间表、绑定关系、节点配置、字段权限等底层模板。",
                    },
                    "important": [
                        "usage_scope 不等于 is_default。",
                        "is_default 只用于依赖实体字段未指定 template_id 时选择该实体的默认启用模板。",
                        "usage_scope 只控制模板是否出现在 case 选择列表以及模板用途语义。",
                    ],
                },
                "examples": {
                    "field_overrides": {
                        "category_name": {
                            "generator_type": 13,
                            "generator_config": {"value": "AUTO${{str_lowercase(10)}}"},
                        },
                        "category_id": {
                            "generator_type": 11,
                            "generator_config": {
                                "dependency_entity_id": 12,
                                "field": "id",
                            },
                        }
                    },
                    "case_body": {
                        "categoryId": "${{创建一级订单.id}}",
                        "categoryName": "${{创建一级订单.category_name}}",
                    },
                },
            }
        )
