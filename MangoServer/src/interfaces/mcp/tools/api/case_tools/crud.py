from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Q

from src.apps.auto_api.models import (
    ApiInfoRelease,
)
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_case.mutation_io import (
    ApiCaseMutationService,
)
from src.apps.auto_api.services.api_case.snapshot import ApiExecutableSnapshotService
from src.apps.auto_api.services.api_case.step import ApiCaseStepService
from src.common.exceptions import MangoServerError
from src.interfaces.mcp.audit import (
    mcp_current_user_id,
)
from src.interfaces.mcp.common import (
    current_user,
    fail,
    ok,
    paginate_queryset,
)
from ..helper_parts.case_result import (
    _case_tree,
)
from ..helper_parts.execution import (
    _create_case_step,
)
from ..helpers import (
    _api_case_version_summary,
    _api_info_revision_summary,
    _require_published_api_case_modify_confirmation,
    _validate_api_case_sql_datasources,
    _validate_scenario_tags,
)


def register_case_crud_tools(mcp):
    @mcp.tool()
    def search_api_cases(
            project_product_id: int | None = None,
            module_id: int | None = None,
            keyword: str | None = None,
            case_people_id: int | None = None,
            level: int | None = None,
            scenario_layer: int | None = None,
            scenario_type: int | None = None,
            scenario_tags: list[str] | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """搜索 API case。"""
        queryset = ApiQuerySelector.api_case().select_related("project_product", "module", "case_people").all()
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if case_people_id is not None:
            queryset = queryset.filter(case_people_id=case_people_id)
        if level is not None:
            queryset = queryset.filter(level=level)
        if scenario_layer is not None:
            queryset = queryset.filter(scenario_layer=scenario_layer)
        if scenario_type is not None:
            queryset = queryset.filter(scenario_type=scenario_type)
        if scenario_tags:
            tag_query = Q()
            for tag in scenario_tags:
                tag_query |= Q(scenario_tags__contains=[tag])
            queryset = queryset.filter(tag_query)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        count = queryset.count()
        offset = max(page - 1, 0) * page_size
        items = []
        for item in queryset.order_by("-id")[offset: offset + page_size]:
            case_config = ApiExecutableSnapshotService.current_case_config(
                item.id,
                item.project_product_id,
            )
            items.append({
                "id": item.id,
                "name": item.name,
                "project_product_id": item.project_product_id,
                "module_id": item.module_id,
                "case_people_id": item.case_people_id,
                "case_flow": item.case_flow,
                "level": item.level,
                "scenario_layer": item.scenario_layer,
                "scenario_type": item.scenario_type,
                "scenario_tags": item.scenario_tags,
                "scenario_description": item.scenario_description,
                "front_public": case_config.get("front_public", []),
                "front_auth_config": case_config.get("front_auth_config", []),
                "status": item.status,
                **_api_case_version_summary(item.id),
            })
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def create_api_case(
            project_product_id: int,
            module_id: int,
            name: str,
            case_people_id: int | None = None,
            level: int = 1,
            scenario_layer: int = 0,
            scenario_type: int = 0,
            scenario_tags: list[str] | None = None,
            scenario_description: str | None = None,
            front_custom: list | None = None,
            front_sql: list | None = None,
            front_headers: list[int] | None = None,
            front_public: list[int] | None = None,
            front_auth_config: list[int] | None = None,
            posterior_sql: list | None = None,
    ) -> dict:
        """创建 API case 主体。

        复杂字段格式见 get_api_case_schema.api_case_fields。front_headers 只传 ApiHeaders.id 数组，
        表示用例级默认请求头；如果某个场景参数 headers 非空，执行时会完全覆盖 front_headers，不会合并。
        如果场景 headers 和 front_headers 都为空，执行时使用当前项目产品下 status=1 的 ApiHeaders。
        front_public/front_auth_config 只传 ID 数组，表示本 case 显式选择的全局变量/授权配置；执行时与默认开启项合并为加载范围。
        front_sql/posterior_sql 每条 SQL 必须传 datasource_alias；可传 test_envs 多选执行环境，不传、null 或 [] 表示全部环境执行。
        SQL 的 key 支持单个缓存变量，也支持 id,name 这种英文逗号分隔多 key；查询结果取第一行，按列名优先、列顺序兜底写入多个缓存变量。
        先调用 list_data_factory_datasource_aliases 查询数据库。
        scenario_layer 表示测试层级：0=接口/组件级（单个接口或组件）、1=模块级（同一模块内多个接口、组件协作）、2=端到端（跨多个模块的完整业务链路）。
        层级按业务覆盖范围判断，不因多步骤、工厂或SQL自动升级。scenario_tags 使用 API、UI、Pytest 和定时任务共用的执行场景枚举。
        production_inspection=生产巡检，仅用于 GET 或 POST 不提交数据的查询接口，不允许包含数据库增删改。
        production_regression=生产回归，可包含增删改接口，但不允许任何数据库操作。
        未提供 case_people_id 时默认使用当前 MCP APIKey/JWT 对应用户作为负责人。
        """
        tag_error = _validate_scenario_tags(scenario_tags)
        if tag_error:
            return fail(tag_error, "INVALID_SCENARIO_TAGS")
        sql_error = _validate_api_case_sql_datasources(front_sql, posterior_sql)
        if sql_error:
            return fail(sql_error, "DATASOURCE_ALIAS_REQUIRED")
        if case_people_id is None:
            case_people_id = current_user().id
        data_obj = ApiCaseMutationService.create(
            {
                "project_product": project_product_id,
                "module": module_id,
                "name": name,
                "case_people": case_people_id,
                "level": level,
                "scenario_layer": scenario_layer,
                "scenario_type": scenario_type,
                "scenario_tags": scenario_tags or [],
                "scenario_description": scenario_description,
                "front_custom": front_custom or [],
                "front_sql": front_sql or [],
                "front_headers": front_headers or [],
                "front_public": front_public or [],
                "front_auth_config": front_auth_config or [],
                "posterior_sql": posterior_sql or [],
            },
            operator_id=current_user().id,
            source="mcp",
        )
        return ok({"case_id": data_obj["id"], "current_user_id": current_user().id, **data_obj}, "API case 创建成功")

    @mcp.tool()
    def update_api_case(
            case_id: int,
            name: str | None = None,
            module_id: int | None = None,
            case_people_id: int | None = None,
            level: int | None = None,
            scenario_layer: int | None = None,
            scenario_type: int | None = None,
            scenario_tags: list[str] | None = None,
            scenario_description: str | None = None,
            front_custom: list | None = None,
            front_sql: list | None = None,
            front_headers: list[int] | None = None,
            front_public: list[int] | None = None,
            front_auth_config: list[int] | None = None,
            posterior_sql: list | None = None,
            preview_token: str | None = None,
            confirm_text: str | None = None,
            callback_checks: list[dict] | None = None,
            resource_cleanup: list[dict] | None = None,
    ) -> dict:
        """更新 API case 主体配置。module_id 可修改所属模块，case_people_id 可修改负责人；复杂字段格式见 get_api_case_schema.api_case_fields。

        front_public/front_auth_config 为 ID 数组，只决定加载范围，不改变平台已有变量类型加载顺序。
        front_sql/posterior_sql 每条 SQL 必须传 datasource_alias；可传 test_envs 多选执行环境，不传、null 或 [] 表示全部环境执行。
        SQL 的 key 支持单个缓存变量，也支持 id,name 这种英文逗号分隔多 key；查询结果取第一行，按列名优先、列顺序兜底写入多个缓存变量。
        先调用 list_data_factory_datasource_aliases 查询数据库。
        如果 Case 已有已发布版本，必须先调用 preview_modify_published_api_case_impact 并传回 preview_token/confirm_text。
        resource_cleanup 配置本Case API创建资源的SQL与ES失败安全清理；规则见 get_api_case_resource_cleanup_schema。
        仅test/dev、单场景POST创建、关闭失败重试；创建名称必须包含本轮变量 ${{api_resource_<规则key>}}。
        支持SQL业务ID、ES文档ID（如group_id）与自增主键分别映射，不能伪装为数据工厂资源。
        """
        confirm_error = _require_published_api_case_modify_confirmation(case_id, preview_token, confirm_text)
        if confirm_error:
            return confirm_error
        tag_error = _validate_scenario_tags(scenario_tags)
        if tag_error:
            return fail(tag_error, "INVALID_SCENARIO_TAGS")
        sql_error = _validate_api_case_sql_datasources(front_sql, posterior_sql)
        if sql_error:
            return fail(sql_error, "DATASOURCE_ALIAS_REQUIRED")
        payload: dict[str, Any] = {"id": case_id}
        for key, value in {
            "name": name,
            "module": module_id,
            "case_people": case_people_id,
            "level": level,
            "scenario_layer": scenario_layer,
            "scenario_type": scenario_type,
            "scenario_tags": scenario_tags,
            "scenario_description": scenario_description,
            "front_custom": front_custom,
            "front_sql": front_sql,
            "front_headers": front_headers,
            "front_public": front_public,
            "front_auth_config": front_auth_config,
            "posterior_sql": posterior_sql,
            "callback_checks": callback_checks,
            "resource_cleanup": resource_cleanup,
        }.items():
            if value is not None:
                payload[key] = value
        data_obj = ApiCaseMutationService.update(
            case_id,
            payload,
            operator_id=current_user().id,
            source="mcp",
        )
        return ok({"case_id": data_obj["id"], **data_obj}, "API case 更新成功")

    @mcp.tool()
    def add_api_case_step(
            case_id: int,
            api_info_id: int | None = None,
            case_sort: int | None = None,
            api_info_release_id: int | None = None,
            api_info_revision_id: int | None = None,
            preview_token: str | None = None,
            confirm_text: str | None = None,
            execution_config: dict[str, Any] | None = None,
    ) -> dict:
        """给 API case 添加接口步骤，并自动创建默认场景参数。

        推荐传 api_info_release_id 或 api_info_revision_id，步骤会固定到对应 API Revision。
        只传 api_info_id 时，默认固定当前已发布 API Revision；如果接口尚未发布，会拒绝添加。
        如果目的是把已有步骤换成另一个接口，不要编辑原步骤的 api_info；
        正确流程是先 delete_api_case_step 删除旧步骤，再 add_api_case_step 新增目标接口，最后 sort_api_case_steps 排序。
        如果 Case 已有已发布版本，必须先调用 preview_modify_published_api_case_impact 并传回 preview_token/confirm_text。
        """
        try:
            confirm_error = _require_published_api_case_modify_confirmation(case_id, preview_token, confirm_text)
            if confirm_error:
                return confirm_error
            pinned_revision_id = api_info_revision_id
            if api_info_release_id is not None:
                release = ApiQuerySelector.api_info_release().filter(
                    id=api_info_release_id,
                    status=ApiInfoRelease.STATUS_PUBLISHED,
                ).first()
                if release is None:
                    return fail("API 发布版本不存在或未发布", "API_INFO_RELEASE_NOT_FOUND")
                api_info_id = api_info_id or release.api_info_id
                pinned_revision_id = release.revision_id
            if pinned_revision_id is not None:
                revision = ApiQuerySelector.api_info_revision().filter(id=pinned_revision_id).first()
                if revision is None:
                    return fail("API Revision 不存在", "API_INFO_REVISION_NOT_FOUND")
                api_info_id = api_info_id or revision.api_info_id
            if api_info_id is None:
                return fail("api_info_id、api_info_release_id、api_info_revision_id 至少传一个。",
                            "API_INFO_ARGUMENT_REQUIRED")
            with transaction.atomic():
                data = _create_case_step(
                    case_id,
                    api_info_id,
                    case_sort,
                    pinned_api_info_revision_id=pinned_revision_id,
                    execution_config=execution_config,
                )
        except Exception as exc:
            return fail(str(exc), "ADD_API_CASE_STEP_FAILED")
        return ok(data, "API case 步骤添加成功")

    @mcp.tool()
    def list_api_case_steps(case_id: int, page: int = 1, page_size: int = 10) -> dict:
        """查询 API case 步骤。"""
        steps = []
        queryset = ApiQuerySelector.api_case_detailed().select_related(
            "api_info", "pinned_api_info_revision",
        ).filter(case_id=case_id).order_by("case_sort")
        queryset, count, page, page_size = paginate_queryset(queryset, page, page_size)
        for item in queryset:
            steps.append(
                {
                    "step_id": item.id,
                    "case_id": item.case_id,
                    "api_info_id": item.api_info_id,
                    "api_name": item.api_info.name,
                    "case_sort": item.case_sort,
                    "execution_config": item.execution_config,
                    "status": item.status,
                    "error_message": item.error_message,
                    **_api_info_revision_summary(item.pinned_api_info_revision),
                }
            )
        return ok({"items": steps, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def update_api_case_step_recovery(
            step_id: int, execution_config: dict[str, Any],
            preview_token: str | None = None, confirm_text: str | None = None,
    ) -> dict:
        """配置最终恢复步骤：主流程结束后执行，失败不被允许失败降级。

        execution_config 当前仅支持 {"is_recovery": true}；空对象关闭恢复。
        不做额外条件判断，恢复失败仍继续后续恢复。沿用场景重试；不提供崩溃补偿或资源互斥。
        """
        step = ApiQuerySelector.api_case_detailed().get(id=step_id)
        confirmation = _require_published_api_case_modify_confirmation(
            step.case_id, preview_token=preview_token, confirm_text=confirm_text,
        )
        if confirmation:
            return confirmation
        return ok(ApiCaseStepService.configure_recovery(
            step_id, execution_config, operator_id=mcp_current_user_id(), source='mcp',
        ))

    @mcp.tool()
    def sort_api_case_steps(
            case_id: int,
            steps: list[dict],
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """调整 API case 步骤顺序。steps 格式为 [{step_id, case_sort}]。

        这对应页面拖动排序。更换步骤接口时，先删除旧步骤并新增目标接口，再用本工具写入最终顺序。
        如果 Case 已有已发布版本，必须先调用 preview_modify_published_api_case_impact 并传回 preview_token/confirm_text。
        """
        confirm_error = _require_published_api_case_modify_confirmation(case_id, preview_token, confirm_text)
        if confirm_error:
            return confirm_error

        ApiCaseStepService.sort_steps(
            case_id,
            steps,
            operator_id=mcp_current_user_id(),
            source="mcp",
        )
        return ok({"case_id": case_id, "steps": steps}, "API case 步骤排序成功")

    @mcp.tool()
    def refresh_api_case_step_from_api_info(
            step_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """从当前步骤已绑定的接口定义同步 params/body_config/sse_config 到步骤下所有场景。

        请求协议和请求体类型执行时统一读取 ApiInfo。本工具不能更换步骤绑定接口；
        更换接口必须使用 delete_api_case_step -> add_api_case_step -> sort_api_case_steps。
        如果 Case 已有已发布版本，必须先调用 preview_modify_published_api_case_impact 并传回 preview_token/confirm_text。
        """
        detail = ApiQuerySelector.api_case_detailed().get(id=step_id)
        confirm_error = _require_published_api_case_modify_confirmation(detail.case_id, preview_token, confirm_text)
        if confirm_error:
            return confirm_error
        count = ApiCaseStepService.refresh_step_parameters(
            step_id,
            operator_id=mcp_current_user_id(),
            source="mcp",
        )
        return ok({"step_id": step_id, "updated_scenarios": count}, "步骤参数同步成功")

    @mcp.tool()
    def get_api_case_detail_full(case_id: int, include_result_data: bool = True) -> dict:
        """查询完整 API case 树：case、steps、api_info、parameters。"""
        try:
            return ok(_case_tree(case_id, include_result_data))
        except MangoServerError as error:
            return fail(error.msg, str(error.code))
