from __future__ import annotations

from django.db import transaction

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceSourceType
from src.apps.auto_api.models import (
    ApiInfoRelease,
)
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_case.mutation import ApiCaseAggregateMutationService
from src.apps.auto_api.services.api_case.mutation_io import (
    ApiCaseMutationService,
    ApiCaseParameterMutationService,
)
from src.apps.auto_api.services.test_case.test_case import TestCase
from src.apps.test_center.services.execution_result import ExecutionResultService
from src.interfaces.mcp.audit import (
    mcp_with_update_user,
)
from src.interfaces.mcp.common import (
    current_user,
    fail,
    ok,
)
from ..helper_parts.execution import (
    _create_case_step,
    _selected_env,
)
from ..helpers import (
    _normalize_scenario_payload,
    _validate_api_case_sql_datasources,
    _validate_scenario_tags,
)


def register_case_complete_tools(mcp):
    @mcp.tool()
    def create_complete_api_case(
            project_product_id: int,
            module_id: int,
            case_name: str,
            api: dict,
            scenarios: list[dict],
            case_people_id: int | None = None,
            scenario_layer: int = 0,
            scenario_type: int = 0,
            scenario_tags: list[str] | None = None,
            scenario_description: str | None = None,
            headers: list[dict] | None = None,
            case_front_headers: list[int] | None = None,
            case_front_public: list[int] | None = None,
            case_front_auth_config: list[int] | None = None,
            run_after_create: bool = False,
            test_env_id: int | None = None,
            user_id: int | None = None,
    ) -> dict:
        """基于一个已发布接口创建 API Case、步骤、场景，并可选立即执行编辑态。

        创建完成后仅保留 API Case 当前编辑态，不自动生成或发布 Case 修订。
        run_after_create=true 时同样执行当前编辑态；只有准备上线或需要版本留档时，
        才单独调用 create_api_case_revision_from_current 和
        update_api_case_publication_status(target_status='prepublished', revision_id=修订ID)；
        正式发布由项目产品负责人通过同一工具传 target_status='published' 完成。

        未提供 case_people_id 时默认使用当前 MCP APIKey/JWT 对应用户作为负责人。
        出于公共请求头安全控制，本工具不再直接创建 ApiHeaders。需要请求头时，请先对每个必需 header
        调用 preview_create_api_header_impact 并由用户手动确认，再调用 create_api_header 创建，最后把返回 id
        通过 case_front_headers 或 scenarios[].headers 传入。
        如果 scenarios[].headers 非空，执行该场景时会覆盖 case_front_headers，不会合并。
        case_front_public/case_front_auth_config 用于保存 API case 显式选择的全局变量/授权配置 ID。
        api 必须传 api_info_id，并且该接口已经完成调试、生成修订和发布。
        新接口请先调用 create_api_info；MCP/gRPC 请先分别调用
        import_mcp_tool_to_api_info / import_grpc_method_to_api_info。接口调试成功后显式调用
        create_api_info_revision_from_current 和 publish_api_info_revision，最后再调用本工具创建 Case。
        接口协议和请求体类型取已发布 ApiInfo；场景请求数据使用 scenarios[].body_config/sse_config。
        简单/嵌套 JSON 直接填 body_config，变量、提取和常规断言用平台配置；仅无法表达的计算/解码才用场景函数，遵循 get_api_case_schema.execution_rules.function_usage，不用函数兜底失败清理。
        sse_config 暂时保留，后续会并入 body_config；MCP/gRPC 执行配置请放入 body_config.mcp_config/body_config.grpc_config。
        scenarios[] 可以直接传断言字段 ass_jsonpath、ass_general、ass_json_all、ass_text_all、ass_schema。
        scenarios[].allow_failure=true 时，该场景全部重试后仍失败会记为警告，并继续执行后续步骤；默认 false。
        复杂断言格式请先调用 get_api_assertion_schema / get_api_assertion_methods；生成建议后必须把断言字段保存到场景。
        文件上传使用 body_type=multipart 和 body_config.files[].file_id；不能直接传本地路径、URL、裸文件名或二进制内容。
        详细格式见 get_api_case_schema.file_upload_usage。
        scenarios[].front_sql/scenarios[].posterior_sql 每条 SQL 必须传 datasource_alias；可传 test_envs 多选执行环境，
        不传、null 或 [] 表示全部环境执行；先调用 list_data_factory_datasource_aliases 查询数据库。
        SQL 的 key 支持单个缓存变量，也支持 id,name 这种英文逗号分隔多 key；查询结果取第一行，按列名优先、列顺序兜底写入多个缓存变量。
        scenario_layer 表示测试层级：0=接口/组件级（单个接口或组件）、1=模块级（同一模块内多个接口、组件协作）、2=端到端（跨多个模块的完整业务链路）；scenario_tags 使用公共执行场景枚举。
        production_inspection=生产巡检，仅用于 GET 或 POST 不提交数据的查询接口，不允许包含数据库增删改。
        production_regression=生产回归，可包含增删改接口，但不允许任何数据库操作。
        """
        tag_error = _validate_scenario_tags(scenario_tags)
        if tag_error:
            return fail(tag_error, "INVALID_SCENARIO_TAGS")
        if headers:
            return fail(
                "create_complete_api_case 不允许直接创建公共请求头。请先逐个调用 preview_create_api_header_impact，"
                "由用户确认是接口执行必需请求头后，再调用 create_api_header 创建，并通过 case_front_headers 或 scenarios[].headers 绑定。",
                "API_HEADER_CONFIRM_REQUIRED",
                {
                    "headers_count": len(headers),
                    "required_flow": [
                        "list_api_headers 查询是否已有可复用请求头",
                        "preview_create_api_header_impact 预览新增请求头影响",
                        "用户确认该请求头为接口执行必需项",
                        "create_api_header 传回 preview_token/confirm_text 创建",
                        "create_complete_api_case 使用 case_front_headers 绑定已创建请求头 ID",
                    ],
                },
            )
        api_info_id = api.get("api_info_id")
        if api_info_id is None:
            return fail(
                "create_complete_api_case 只负责基于已发布接口创建 Case，不再自动创建、生成或发布接口版本。",
                "PUBLISHED_API_INFO_REQUIRED",
                {
                    "required_flow": [
                        "create_api_info 或协议导入工具创建接口编辑态",
                        "run_api_info 调试当前编辑态",
                        "create_api_info_revision_from_current 生成接口修订",
                        "publish_api_info_revision 发布接口版本",
                        "create_complete_api_case 传 api.api_info_id 创建 Case 编辑态",
                    ],
                },
            )
        for index, scenario in enumerate(scenarios or [], start=1):
            sql_error = _validate_api_case_sql_datasources(
                scenario.get("front_sql"),
                scenario.get("posterior_sql"),
                prefix=f"scenarios[{index}].",
            )
            if sql_error:
                return fail(sql_error, "DATASOURCE_ALIAS_REQUIRED")
        if case_people_id is None:
            case_people_id = current_user(user_id).id
        try:
            caller_user = current_user(user_id)
            with transaction.atomic():
                api_info_release_id = None
                api_info_revision_id = None
                api_obj = ApiQuerySelector.api_info().filter(id=api_info_id).first()
                if api_obj is None:
                    return fail("api.api_info_id 对应接口定义不存在", "API_INFO_NOT_FOUND",
                                {"api_info_id": api_info_id})
                if api_obj.project_product_id != project_product_id:
                    return fail(
                        "api.api_info_id 对应接口定义不属于当前项目产品",
                        "API_INFO_PROJECT_PRODUCT_MISMATCH",
                        {
                            "api_info_id": api_info_id,
                            "api_info_project_product_id": api_obj.project_product_id,
                            "case_project_product_id": project_product_id,
                        },
                    )
                api_release = ApiQuerySelector.api_info_release().filter(
                    api_info_id=api_obj.id,
                    is_current=True,
                    status=ApiInfoRelease.STATUS_PUBLISHED,
                ).first()
                if api_release is None:
                    return fail(
                        "api.api_info_id 对应接口定义还没有已发布版本，请先确认接口配置，生成修订并发布，再创建 API Case。",
                        "API_INFO_RELEASE_REQUIRED",
                        {"api_info_id": api_info_id},
                    )
                api_info_release_id = api_release.id
                api_info_revision_id = api_release.revision_id
                api_info = {"id": api_obj.id, "name": api_obj.name}
                api_case = ApiCaseMutationService.create(
                    mcp_with_update_user(
                        {
                            "project_product": project_product_id,
                            "module": module_id,
                            "name": case_name,
                            "case_people": case_people_id,
                            "level": api.get("level", 1),
                            "scenario_layer": scenario_layer,
                            "scenario_type": scenario_type,
                            "scenario_tags": scenario_tags or [],
                            "scenario_description": scenario_description,
                            "front_headers": case_front_headers or [],
                            "front_public": case_front_public or [],
                            "front_auth_config": case_front_auth_config or [],
                            "front_custom": [],
                            "front_sql": [],
                            "posterior_sql": [],
                        }
                    ),
                    operator_id=caller_user.id,
                    record_config=False,
                    source="mcp",
                )
                step = _create_case_step(
                    api_case["id"],
                    api_info["id"],
                    0,
                    record_config=False,
                    operator_id=caller_user.id,
                    pinned_api_info_revision_id=api_info_revision_id,
                )
                default_parameter_id = step["default_parameter_id"]
                scenario_ids: list[int] = []
                if scenarios:
                    first = scenarios[0]
                    update_payload = {"name": first.get("name", api.get("name") or api_info["name"])}
                    update_payload.update({k: v for k, v in first.items() if k != "name"})
                    update_payload = _normalize_scenario_payload(update_payload)
                    ApiCaseParameterMutationService.update(
                        default_parameter_id,
                        mcp_with_update_user(update_payload),
                        record_config=False,
                        source="mcp",
                    )
                    scenario_ids.append(default_parameter_id)
                    for scenario in scenarios[1:]:
                        scenario_payload = {
                            "case_detailed": step["step_id"],
                            "name": scenario.get("name", api.get("name") or api_info["name"]),
                            **{k: v for k, v in scenario.items() if k != "name"},
                        }
                        scenario_payload = _normalize_scenario_payload(scenario_payload)
                        created_scenario = ApiCaseParameterMutationService.create(
                            mcp_with_update_user(scenario_payload),
                            record_config=False,
                            source="mcp",
                        )
                        scenario_ids.append(created_scenario["id"])
                ApiCaseAggregateMutationService.rebuild_case_flow(api_case["id"])
                run_result = None
                if run_after_create:
                    user = current_user(user_id)
                    env_id = _selected_env(user.id, test_env_id)
                    run_result = TestCase(
                        user_id=user.id,
                        test_env=env_id,
                        case_id=api_case["id"],
                        trace_source_type=ApiCaseTraceSourceType.MCP,
                    ).test_case().model_dump()
                    ExecutionResultService.save_result(
                        source_type=ExecutionResultService.SOURCE_MCP,
                        target_type=ExecutionResultService.TARGET_API_CASE,
                        target_id=api_case["id"],
                        revision_id=None,
                        test_env=env_id,
                        status=run_result.get("status"),
                        error_message=run_result.get("error_message"),
                        result_data=run_result,
                        trigger_user_id=user.id,
                        trace_id=run_result.get("trace_id"),
                    )
                return ok(
                    {
                        "current_user_id": caller_user.id,
                        "case_people_id": case_people_id,
                        "api_info_id": api_info["id"],
                        "api_info_release_id": api_info_release_id,
                        "api_info_revision_id": api_info_revision_id,
                        "case_id": api_case["id"],
                        "revision_id": None,
                        "step_id": step["step_id"],
                        "header_ids": case_front_headers or [],
                        "front_public": case_front_public or [],
                        "front_auth_config": case_front_auth_config or [],
                        "scenario_ids": scenario_ids,
                        "run_result": run_result,
                    },
                    "完整 API case 创建成功",
                )
        except Exception as exc:
            return fail(str(exc), "CREATE_COMPLETE_API_CASE_FAILED")
