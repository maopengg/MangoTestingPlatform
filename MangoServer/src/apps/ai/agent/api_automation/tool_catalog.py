# -*- coding: utf-8 -*-
from src.apps.ai.models import AiMcpTool


class ApiAutomationToolStageCatalog:
    TOOL_GROUPS = {
        "context": [
            "get_current_user_context",
            "list_project_products",
            "list_product_modules",
            "list_case_owners",
            "list_test_environments",
            "ensure_user_test_environment",
        ],
        "api_info": [
            "search_api_infos",
            "get_api_info_detail",
            "create_api_info",
            "create_api_info_from_curl",
            "update_api_info",
        ],
        "headers": [
            "list_api_headers",
            "create_api_header",
            "update_api_header",
        ],
        "api_case": [
            "create_api_case",
            "search_api_cases",
            "get_api_case_detail_full",
            "update_api_case",
            "add_api_case_step",
            "list_api_case_steps",
            "list_api_case_scenarios",
            "create_api_case_scenario",
            "update_api_case_scenario",
            "create_complete_api_case",
        ],
        "assertions": [
            "get_api_case_detail_full",
            "get_api_assertion_schema",
            "get_api_assertion_methods",
            "generate_api_case_scenario_assertions",
            "auto_generate_api_case_scenario_schema",
            "update_api_case_scenario",
        ],
        "extractors": [
            "get_api_extractor_schema",
            "generate_api_case_scenario_extractors",
        ],
        "data_factory": [
            "get_data_factory_schema",
            "list_data_factory_datasource_aliases",
            "list_data_factory_datasource_bindings",
            "list_data_factory_database_tables",
            "get_data_factory_table_schema",
            "list_data_factory_entities",
            "get_data_factory_entity_detail",
            "create_data_factory_entity",
            "batch_generate_data_factory_entities",
            "list_data_factory_fields",
            "batch_save_data_factory_fields",
            "preview_data_factory_field_values",
            "list_data_factory_templates",
            "get_data_factory_template_detail",
            "create_data_factory_template",
            "update_data_factory_template",
            "set_data_factory_template_status",
            "preview_data_factory_template",
            "preview_run_data_factory_template_impact",
            "execute_data_factory_template",
            "list_data_factory_case_configs",
            "update_data_factory_case_config",
            "sort_data_factory_case_configs",
            "preview_data_factory_case_config",
            "bind_data_factory_to_case_source",
            "list_data_factory_executions",
            "get_data_factory_execution_detail",
            "get_data_factory_execution_context",
        ],
        "execution": [
            "run_api_case",
            "get_api_case_run_result",
            "analyze_api_case_failure",
        ],
    }
    STAGE_DEFINITIONS = [
        {
            "stage": "resolve_context",
            "name": "解析项目、模块、负责人和环境",
            "groups": ["context"],
        },
        {
            "stage": "ensure_api_info",
            "name": "查询或维护 API Info",
            "groups": ["api_info"],
        },
        {
            "stage": "configure_headers",
            "name": "维护请求头",
            "groups": ["headers"],
        },
        {
            "stage": "create_or_update_case",
            "name": "创建或覆盖 API Case、步骤和场景",
            "groups": ["api_case"],
        },
        {
            "stage": "configure_data_factory",
            "name": "配置数据工厂",
            "groups": ["data_factory"],
        },
        {
            "stage": "add_assertions",
            "name": "生成断言",
            "groups": ["assertions"],
        },
        {
            "stage": "add_extractors",
            "name": "生成提取器",
            "groups": ["extractors"],
        },
        {
            "stage": "execute_and_diagnose",
            "name": "执行 API Case 并诊断结果",
            "groups": ["execution"],
        },
    ]
    DEFAULT_STAGES = [
        "resolve_context",
        "ensure_api_info",
        "configure_headers",
        "create_or_update_case",
        "add_assertions",
        "add_extractors",
        "execute_and_diagnose",
    ]

    @classmethod
    def catalog_for_tools(cls, tool_map: dict[str, AiMcpTool]) -> list[dict]:
        available_names = {tool.name for tool in tool_map.values()}
        catalog = []
        for item in cls.STAGE_DEFINITIONS:
            tool_names = []
            for group in item["groups"]:
                tool_names.extend(name for name in cls.TOOL_GROUPS.get(group, []) if name in available_names)
            catalog.append(
                {
                    "stage": item["stage"],
                    "name": item["name"],
                    "groups": item["groups"],
                    "available_tool_names": sorted(set(tool_names)),
                }
            )
        return catalog

    @classmethod
    def stage_definition_map(cls) -> dict[str, dict]:
        return {item["stage"]: item for item in cls.STAGE_DEFINITIONS}

    @classmethod
    def stage_tool_names(cls, stage_name: str) -> set[str]:
        definition = cls.stage_definition_map().get(stage_name) or {}
        names: set[str] = set()
        for group in definition.get("groups", []):
            names.update(cls.TOOL_GROUPS.get(group, []))
        return names

    @classmethod
    def tools_for_stage(cls, tool_map: dict[str, AiMcpTool], stage_name: str) -> dict[str, AiMcpTool]:
        allowed_names = cls.stage_tool_names(stage_name)
        return {safe_name: tool for safe_name, tool in tool_map.items() if tool.name in allowed_names}

    @staticmethod
    def openai_tools_for_stage(tools: list[dict], stage_tool_map: dict[str, AiMcpTool]) -> list[dict]:
        safe_names = set(stage_tool_map.keys())
        return [tool for tool in tools if (tool.get("function") or {}).get("name") in safe_names]

    @classmethod
    def normalize_plan(cls, raw_plan: dict | None, skill_content: str) -> dict:
        definition_map = cls.stage_definition_map()
        normalized = []
        seen = set()
        for item in (raw_plan or {}).get("stages") or []:
            stage_name = item.get("stage") if isinstance(item, dict) else None
            if stage_name not in definition_map or stage_name in seen:
                continue
            definition = definition_map[stage_name]
            normalized.append(
                {
                    "stage": stage_name,
                    "name": definition["name"],
                    "reason": item.get("reason") or "",
                    "tool_names": item.get("tool_names") or [],
                }
            )
            seen.add(stage_name)
        for stage_name in cls.default_stage_names(skill_content):
            if stage_name in seen:
                continue
            definition = definition_map[stage_name]
            normalized.append(
                {
                    "stage": stage_name,
                    "name": definition["name"],
                    "reason": "平台默认 API 自动化流程",
                    "tool_names": sorted(cls.stage_tool_names(stage_name)),
                }
            )
            seen.add(stage_name)
        return {
            "summary": (raw_plan or {}).get("summary") or "按 Skill 和 MCP 能力分阶段生成 API 自动化。",
            "stages": normalized,
            "raw_plan": raw_plan or {},
        }

    @classmethod
    def default_stage_names(cls, skill_content: str) -> list[str]:
        stages = list(cls.DEFAULT_STAGES)
        skill_text = (skill_content or "").lower()
        if ("数据工厂" in skill_text or "data factory" in skill_text) and "configure_data_factory" not in stages:
            stages.insert(stages.index("add_assertions"), "configure_data_factory")
        return stages
