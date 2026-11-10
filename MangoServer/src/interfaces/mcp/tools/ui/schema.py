from __future__ import annotations

from mangotools.enums import TaskEnum

from src.apps.auto_api.enums.case import (
    ApiCaseScenarioLayerEnum,
    ApiCaseScenarioTagEnum,
    ApiCaseScenarioTypeEnum,
)
from src.apps.auto_ui.enums import UiPublicTypeEnum
from src.apps.test_center.enums import CaseLevelEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from .helpers import (
    DriveTypeEnum,
    ElementExpEnum,
    ElementOperationEnum,
    ok,
)
from .helpers import _enum_options


def register_schema_tools(mcp):
    @mcp.tool()
    def get_ui_automation_schema() -> dict:
        """返回 UI 自动化 MCP 字段、枚举、方法来源和 JSON 格式说明。"""
        ui_public_sql_schema = {
            "type": "object",
            "fields": ["project_product_id", "test_env_ids", "type", "name", "key", "value", "datasource_alias_id",
                       "status"],
            "format": {
                "test_env_ids": "测试环境枚举数组；传 []、null 或不传表示环境通用；传 [0,3] 表示测试环境和开发环境均可用。旧 test_env_id 仍兼容并会迁移为 [test_env_id]。",
                "type": "0=自定义公共变量，1=SQL 公共变量，2=代码变量。",
                "key": "SQL 类型可填写单个缓存 key，也可填写英文逗号分隔的多个 key，如 id,name；多 key 会从 SQL 查询结果第一行按列名优先、列顺序兜底写入多个缓存变量。",
                "value": "SQL 类型填写查询一行数据的 SQL 语句；自定义类型填写普通值；代码变量必须定义 variable(context) 并返回 dict。",
                "datasource_alias_id": "SQL 类型必填，传逻辑数据库 DataFactoryDatasourceAlias.id；自定义和代码变量可不传。",
                "status": "0=默认关闭，只有 case 前置里显式选择到 front_public 才加载；1=默认开启，当前项目产品和环境范围内所有 case 自动加载。",
            },
            "common_environment_rule": "环境通用不是环境枚举值，而是 test_envs=[]；list_ui_public_variables(common_only=True) 只查通用变量；update_ui_public_variable(test_env_is_common=True 或 test_env_ids=[]) 可把已有变量改为通用环境。",
            "lookup_rule": "创建或更新 SQL 公共变量前，先调用 list_data_factory_datasource_aliases(project_product_id=当前产品ID) 查询逻辑数据库 ID，然后把返回的 datasource_alias_id 传给本字段。",
            "query_rule": "已有 UI 公共变量可调用 list_ui_public_variables(project_product_id=当前产品ID, type=1) 查询，返回 datasource_alias_id 和 datasource_alias_name。",
            "example": {
                "project_product_id": 1,
                "test_env_ids": [0, 3],
                "type": 1,
                "name": "查询登录用户",
                "key": "id,name",
                "value": "SELECT id,name FROM user WHERE id=${{user_id}}",
                "datasource_alias_id": 2,
                "status": 1,
            },
        }
        ui_case_sql_schema = {
            "type": "list[object]",
            "format": [
                {"sql": "SQL语句", "key_list": "查询结果缓存key，可为空", "datasource_alias": "逻辑数据库ID，可为空"}],
            "datasource_alias": {
                "field": "datasource_alias",
                "type": "int | null",
                "source": "数据工厂逻辑数据库 DataFactoryDatasourceAlias.id",
                "lookup_tool": "list_data_factory_datasource_aliases(project_product_id=当前产品ID)",
                "rule": "多数据库测试环境下，UI case 的 SQL 前置或后置必须传 datasource_alias；单库老数据可为空并由后端/执行器兜底。",
            },
            "variable_support": "sql 支持 ${{变量}}、${{随机方法()}}、${{数据工厂.字段}} 等表达式，执行前由测试数据引擎替换。",
        }
        return ok(
            {
                "enums": {
                    "drive_type": _enum_options(DriveTypeEnum),
                    "element_exp": _enum_options(ElementExpEnum),
                    "element_operation": _enum_options(ElementOperationEnum),
                    "ui_public_type": _enum_options(UiPublicTypeEnum),
                    "case_level": _enum_options(CaseLevelEnum),
                    "task_status": _enum_options(TaskEnum),
                    "scenario_layer": _enum_options(ApiCaseScenarioLayerEnum),
                    "scenario_type": _enum_options(ApiCaseScenarioTypeEnum),
                    "scenario_tags": _enum_options(ApiCaseScenarioTagEnum),
                    "environment": _enum_options(EnvironmentEnum),
                },
                "ui_case_fields": {
                    "scenario_layer": "与 API case 一致：0=接口/组件级（单个接口或组件）、1=模块级（同一模块内多个接口、组件协作）、2=端到端（跨多个模块的完整业务链路）。",
                    "scenario_type": "正常/异常/边界/权限/数据/流程。",
                    "scenario_tags": {
                        "description": "执行场景，与 API、Pytest Case 和定时任务共用同一枚举。",
                        "selection_guidance": [
                            "UI case 的接口/组件级、模块级、端到端分层放在 scenario_layer，不放在 scenario_tags。",
                            "production_inspection=生产巡检，用于生产只读健康检查；UI case 使用该场景时不允许包含 SQL 前后置、页面步骤 SQL、SQL 断言或数据工厂造数/清理。",
                            "production_regression=生产回归，允许覆盖生产回归流程，但不允许任何数据库操作。",
                        ],
                    },
                    "parametrize": [
                        {"name": "参数组", "parametrize": [{"key": "name", "value": "AUTO", "test_envs": [1, 2]}]}],
                    "front_custom": [{"key": "tenant_id", "value": "${{tenant_id}}", "test_envs": [1, 2]}],
                    "environment_scope": {
                        "field": "test_envs",
                        "description": "parametrize 参数项和 front_custom 自定义变量均可选择多个适用环境。",
                        "common_rule": "字段缺失、null 或空数组时表示环境通用；非空时仅在当前执行环境包含于 test_envs 时生效。",
                    },
                    "front_public": {
                        "type": "list[int]",
                        "default": [],
                        "description": "当前 UI case 显式选择的 UiPublic.id 列表。",
                        "execution": "执行时与默认开启的 UiPublic 合并为加载范围；status=0 默认关闭的变量只有被 case.front_public 显式选择才加载；只决定加载哪些变量，不改变平台已有变量类型加载顺序。",
                        "load_order": ["自定义变量", "SQL变量", "代码变量"],
                        "example": [100, 101],
                    },
                    "front_auth_config": {
                        "type": "list[int]",
                        "default": [],
                        "description": "当前 UI case 显式选择的 UiAuthConfig.id 列表。",
                        "execution": "执行时与默认开启的 UiAuthConfig 合并为加载范围；后端会归并可直接应用的授权缓存后发送给执行器。",
                        "example": [20, 21],
                    },
                    "front_sql": {
                        **ui_case_sql_schema,
                        "description": "UI case 执行前执行 SQL。sql 是 SQL 语句；查询结果第一行写入 SQL 缓存 key_list。",
                        "example": [{"sql": "SELECT id FROM user LIMIT 1", "key_list": "user", "datasource_alias": 2}],
                    },
                    "posterior_sql": {
                        **ui_case_sql_schema,
                        "description": "UI case 执行结束后执行 SQL。sql 是 SQL 语句；写操作通常不需要 key_list。",
                        "example": [{"sql": "UPDATE table SET valid=0 WHERE id=${{id}}", "datasource_alias": 2}],
                    },
                },
                "ui_public": ui_public_sql_schema,
                "flow_data": {
                    "format": {
                        "nodes": [{"id": "node-id", "position": {"x": 0, "y": 0}, "type": 0, "label": "点击",
                                   "config": {"id": 1}}],
                        "edges": [{"id": "edge-id", "source": {"node_id": "a", "position": "bottom"},
                                   "target": {"node_id": "b", "position": "top"}}],
                    },
                    "rule": "nodes[].config.id 必须指向已保存的 PageStepsDetailed.id；保存步骤详情后同步更新对应节点 config.id。",
                },
                "page_step_detail": {
                    "type_0_or_1": "必须传 ope_key，ope_key 来自 get_ui_operation_methods/get_ui_assertion_methods 的叶子 value；ope_value 保存方法 parameter 数组并把输入写到 v。",
                    "type_2": {"sql_execute": [{"sql": "SELECT ...", "key_list": "cache_key"}]},
                    "type_3": {"custom": [{"key": "name", "value": "value"}]},
                    "type_4": {"condition_value": {"expect": "预期值"}},
                    "type_5": {"func": "python code"},
                },
                "ui_page": {
                    "url_unique_rule": "同一项目产品下，具体页面 URL 不允许重复；/ 允许重复；保存时会忽略末尾 / 做重复判断。",
                },
                "ui_element": {
                    "category": "元素分类为必填字段。数据库允许空是为了兼容旧数据，新建和更新都会校验不能为空。",
                    "category_examples": ["搜索区域", "表格", "弹窗", "表单区域", "工具栏", "详情区域"],
                    "ai_tools": [
                        "list_ui_element_categories",
                        "get_ui_element_ai_info",
                        "create_ui_element_snapshot",
                        "create_ui_element_heal_record",
                        "update_ui_element_from_heal_record",
                    ],
                },
                "case_data": "推荐通过 refresh_ui_case_step_cache_data 生成，不建议 AI 手工拼。",
                "dangerous_actions": "删除类必须先 preview_delete_*_impact，再传回 preview_token 和 confirm_text。",
                "notes": [
                    "production_inspection=生产巡检，用于生产只读健康检查；production_regression=生产回归，允许覆盖生产回归流程；两者都不允许任何数据库操作。",
                    "UI case 的 front_sql、posterior_sql 如在多数据库测试环境中使用，先调用 list_data_factory_datasource_aliases(project_product_id) 查询逻辑数据库 ID，再写入 datasource_alias。",
                    "page_step_detail.type=2 的 sql_execute 目前保持既有格式 [{sql,key_list}]，暂不在 MCP schema 中声明 datasource_alias。",
                    "UI 公共变量 type=1(SQL) 已接入 datasource_alias_id，创建或更新前先查询逻辑数据库并传入 datasource_alias_id。",
                    "UI case.front_public 保存 UiPublic ID；UI case.front_auth_config 保存 UiAuthConfig ID；它们只扩大加载范围，不改变变量类型加载顺序。",
                ],
            }
        )
