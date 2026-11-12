from __future__ import annotations

from django.db.models import Count

from src.common.utils.redaction import mask_sensitive
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_ui.selectors.querysets import UiQuerySelector
from src.apps.functional_test.enums import (
    ManualTestAutomationTypeEnum,
    ManualTestRelationTypeEnum,
)
from src.apps.functional_test.models import (
    FunctionalTestContextResource,
)
from src.apps.functional_test.presenters import format_automation_binding, format_case, format_case_list, \
    format_context_resource, format_plan, format_plan_case, format_plan_list, format_suite, prepare_case_list_queryset, \
    prepare_case_queryset, prepare_context_resource_queryset, prepare_plan_list_queryset, prepare_suite_queryset
from src.apps.functional_test.selectors.querysets import FunctionalTestQuerySelector
from src.apps.functional_test.services.integration.automation import ManualAutomationService
from src.apps.functional_test.services.execution.execution import FunctionalTestExecutionService
from src.apps.functional_test.services.cases.mutation import FunctionalTestMutationService
from src.apps.functional_test.services.suites.suite import ManualTestSuiteService
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.interfaces.mcp.common import current_user, fail, ok

MAX_PAGE_SIZE = 100
LIST_RESOURCE_TEXT_LIMIT = 300


def _page(page: int = 1, page_size: int = 10) -> tuple[int, int]:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 10), 1), MAX_PAGE_SIZE)
    return page, page_size


def _paginate(queryset, page: int = 1, page_size: int = 10):
    page, page_size = _page(page, page_size)
    total = queryset.count()
    start = (page - 1) * page_size
    return queryset[start: start + page_size], total, page, page_size


def _serializer_error(serializer) -> dict:
    return fail("参数校验失败", "VALIDATION_ERROR", serializer.errors)


def _safe_data(data):
    return mask_sensitive(data)


def _suite_queryset():
    return prepare_suite_queryset(FunctionalTestQuerySelector.manual_test_suite().all())


def _case_queryset():
    return prepare_case_list_queryset(FunctionalTestQuerySelector.manual_test_case().all())


def _resource_queryset():
    return prepare_context_resource_queryset(FunctionalTestQuerySelector.functional_test_context_resource().all())


def _resource_summary(resource: FunctionalTestContextResource) -> dict:
    data = format_context_resource(resource)
    content = data.get("content") or ""
    extracted_text = data.get("extracted_text") or ""
    data["content_preview"] = content[:LIST_RESOURCE_TEXT_LIMIT]
    data["extracted_text_preview"] = extracted_text[:LIST_RESOURCE_TEXT_LIMIT]
    data.pop("content", None)
    data.pop("extracted_text", None)
    return _safe_data(data)


def _normalize_relation_type(value: int | str | None) -> int:
    if value in (None, ""):
        return ManualTestRelationTypeEnum.BOUND.value
    try:
        return int(value)
    except (TypeError, ValueError):
        return ManualTestRelationTypeEnum.BOUND.value


def _normalize_automation_type(value: int | str) -> int | None:
    try:
        automation_type = int(value)
    except (TypeError, ValueError):
        return None
    return automation_type if automation_type in ManualTestAutomationTypeEnum.get_key_list() else None


def register_functional_test_tools(mcp):
    @mcp.tool()
    def list_functional_test_suites(
            project_product_id: int | None = None,
            module_id: int | None = None,
            requirement_name: str | None = None,
            iteration: str | None = None,
            owner_id: int | None = None,
            sync_status: int | None = None,
            status: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询功能测试需求列表。"""
        queryset = _suite_queryset()
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if requirement_name:
            queryset = queryset.filter(requirement_name__contains=requirement_name)
        if iteration:
            queryset = queryset.filter(iteration__contains=iteration)
        if owner_id is not None:
            queryset = queryset.filter(owner_id=owner_id)
        if sync_status is not None:
            queryset = queryset.filter(sync_status=sync_status)
        if status is not None:
            queryset = queryset.filter(status=status)
        items, total, page, page_size = _paginate(queryset, page, page_size)
        return ok(
            _safe_data({"items": format_suite(items, many=True), "total": total, "page": page, "page_size": page_size}))

    @mcp.tool()
    def get_functional_test_suite_detail(suite_id: int, include_cases: bool = False,
                                         include_resources: bool = False) -> dict:
        """查询功能测试需求详情，可选返回用例和上下文资料摘要。"""
        suite = _suite_queryset().get(id=suite_id)
        data = format_suite(suite)
        if include_cases:
            cases = _case_queryset().filter(suite_id=suite_id).order_by("case_no", "id")
            data["cases"] = format_case_list(cases, many=True)
        if include_resources:
            resources = _resource_queryset().filter(suite_id=suite_id)
            data["context_resources"] = [_resource_summary(item) for item in resources]
        return ok(_safe_data(data))

    @mcp.tool()
    def create_functional_test_suite(
            project_product_id: int,
            owner_id: int,
            module_id: int | None = None,
            requirement_name: str | None = None,
            iteration: str | None = None,
            status: int = 1,
    ) -> dict:
        """创建功能测试需求。project_product_id 和 owner_id 必填。"""
        payload = {
            "project_product": project_product_id,
            "module": module_id,
            "requirement_name": requirement_name,
            "iteration": iteration,
            "owner": owner_id,
            "status": status,
        }
        result = FunctionalTestMutationService.create_suite(payload, current_user().id)
        if result.errors:
            return fail("参数校验失败", "VALIDATION_ERROR", result.errors)
        suite = result.instance
        return ok(_safe_data(format_suite(_suite_queryset().get(id=suite.id))), "功能测试需求创建成功")

    @mcp.tool()
    def update_functional_test_suite(suite_id: int, fields: dict) -> dict:
        """修改功能测试需求。fields 使用 ManualTestSuite 字段名。"""
        payload = {"id": suite_id, **(fields or {})}
        result = FunctionalTestMutationService.update_suite(
            suite_id,
            payload,
            current_user().id,
        )
        if result.errors:
            return fail("参数校验失败", "VALIDATION_ERROR", result.errors)
        suite = result.instance
        return ok(_safe_data(format_suite(_suite_queryset().get(id=suite.id))), "功能测试需求修改成功")

    @mcp.tool()
    def delete_functional_test_suite(suite_id: int) -> dict:
        """删除旧需求工作区及其资料；已生成的用例库资产会保留，只解除旧需求来源。"""
        result = FunctionalTestMutationService.delete_suites([suite_id])
        return ok({"suite_id": suite_id, **result}, "功能测试需求删除成功")

    @mcp.tool()
    def list_functional_test_cases(
            suite_id: int | None = None,
            project_product_id: int | None = None,
            module_id: int | None = None,
            title: str | None = None,
            case_no: str | None = None,
            test_type: int | None = None,
            scenario_layer: int | None = None,
            scenario_type: int | None = None,
            scenario_tag: str | None = None,
            change_status: int | None = None,
            automation_impact_status: int | None = None,
            owner_id: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询功能测试用例。列表返回轻量字段和自动化绑定。"""
        queryset = _case_queryset()
        filters = {
            "suite_id": suite_id,
            "project_product_id": project_product_id,
            "module_id": module_id,
            "scenario_layer": scenario_layer,
            "scenario_type": scenario_type,
            "change_status": change_status,
            "automation_impact_status": automation_impact_status,
            "owner_id": owner_id,
        }
        for key, value in filters.items():
            if value is not None:
                queryset = queryset.filter(**{key: value})
        if title:
            queryset = queryset.filter(title__contains=title)
        if case_no:
            queryset = queryset.filter(case_no__contains=case_no)
        if test_type is not None:
            queryset = queryset.filter(test_types__contains=[int(test_type)])
        if scenario_tag is not None:
            queryset = queryset.filter(scenario_tags__contains=[scenario_tag])
        items, total, page, page_size = _paginate(queryset, page, page_size)
        return ok(_safe_data(
            {"items": format_case_list(items, many=True), "total": total, "page": page, "page_size": page_size}))

    @mcp.tool()
    def get_functional_test_case_detail(case_id: int) -> dict:
        """查询功能测试用例详情，包括需求、项目产品、模块、负责人和自动化绑定。"""
        case = prepare_case_queryset(FunctionalTestQuerySelector.manual_test_case().all()).get(id=case_id)
        return ok(_safe_data(format_case(case)))

    @mcp.tool()
    def create_functional_test_case(fields: dict) -> dict:
        """创建功能测试用例库资产。必须传 project_product、module、owner、case_no、title、test_point（测试场景）、test_types、priority、scenario_layer、scenario_type、scenario_tags；三级分类均可为空，不得传执行结果。"""
        result = FunctionalTestMutationService.create_case(
            dict(fields or {}),
            current_user().id,
        )
        if result.errors:
            return fail("参数校验失败", "VALIDATION_ERROR", result.errors)
        case = result.instance
        return ok(_safe_data(
            format_case(prepare_case_queryset(FunctionalTestQuerySelector.manual_test_case().all()).get(id=case.id))),
            "功能测试用例创建成功")

    @mcp.tool()
    def update_functional_test_case(case_id: int, fields: dict) -> dict:
        """修改功能测试用例。fields 使用 ManualTestCase 字段名。"""
        payload = {"id": case_id, **(fields or {})}
        result = FunctionalTestMutationService.update_case(
            case_id,
            payload,
            current_user().id,
        )
        if result.errors:
            return fail("参数校验失败", "VALIDATION_ERROR", result.errors)
        case = result.instance
        return ok(_safe_data(
            format_case(prepare_case_queryset(FunctionalTestQuerySelector.manual_test_case().all()).get(id=case.id))),
            "功能测试用例修改成功")

    @mcp.tool()
    def delete_functional_test_case(case_id: int) -> dict:
        """删除单个功能测试用例。"""
        result = FunctionalTestMutationService.delete_cases([case_id])
        return ok({"case_id": case_id, **result}, "功能测试用例删除成功")

    @mcp.tool()
    def batch_delete_functional_test_cases(suite_id: int, case_ids: list[int]) -> dict:
        """批量删除功能测试用例，只删除属于指定需求的用例。"""
        ids = [int(item) for item in (case_ids or []) if str(item).isdigit()]
        if not ids:
            return fail("case_ids 不能为空", "CASE_IDS_EMPTY")
        result = FunctionalTestMutationService.delete_cases(ids, suite_id=suite_id)
        return ok({"suite_id": suite_id, **result}, "功能测试用例批量删除成功")

    @mcp.tool()
    def list_functional_test_context_resources(
            suite_id: int | None = None,
            context_key: int | None = None,
            content_type: int | None = None,
            enabled: bool | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询功能测试上下文资料。列表只返回内容摘要，详情接口返回完整内容。"""
        queryset = _resource_queryset()
        if suite_id is not None:
            queryset = queryset.filter(suite_id=suite_id)
        if context_key is not None:
            queryset = queryset.filter(context_key=context_key)
        if content_type is not None:
            queryset = queryset.filter(content_type=content_type)
        if enabled is not None:
            queryset = queryset.filter(enabled=enabled)
        items, total, page, page_size = _paginate(queryset, page, page_size)
        return ok(_safe_data({"items": [_resource_summary(item) for item in items], "total": total, "page": page,
                              "page_size": page_size}))

    @mcp.tool()
    def get_functional_test_context_resource_detail(resource_id: int) -> dict:
        """查询功能测试上下文资料详情，返回完整文本和解析文本。"""
        resource = _resource_queryset().get(id=resource_id)
        return ok(_safe_data(format_context_resource(resource)))

    @mcp.tool()
    def create_functional_test_context_resource(fields: dict) -> dict:
        """创建功能测试上下文资料。只保存文本/URL/文件元数据，不接收二进制内容；飞书 URL 暂不支持。"""
        payload = dict(fields or {})
        result = FunctionalTestMutationService.create_context_resource(
            payload,
            current_user().id,
        )
        if result.errors:
            return fail("参数校验失败", "VALIDATION_ERROR", result.errors)
        resource = result.instance
        return ok(_safe_data(format_context_resource(_resource_queryset().get(id=resource.id))),
                  "功能测试上下文资料创建成功")

    @mcp.tool()
    def update_functional_test_context_resource(resource_id: int, fields: dict) -> dict:
        """修改功能测试上下文资料。fields 使用 FunctionalTestContextResource 字段名。"""
        payload = {"id": resource_id, **(fields or {})}
        result = FunctionalTestMutationService.update_context_resource(
            resource_id,
            payload,
            current_user().id,
        )
        if result.errors:
            return fail("参数校验失败", "VALIDATION_ERROR", result.errors)
        resource = result.instance
        return ok(_safe_data(format_context_resource(_resource_queryset().get(id=resource.id))),
                  "功能测试上下文资料修改成功")

    @mcp.tool()
    def delete_functional_test_context_resource(resource_id: int) -> dict:
        """删除功能测试上下文资料。"""
        result = FunctionalTestMutationService.delete_context_resources([resource_id])
        return ok({"resource_id": resource_id, **result}, "功能测试上下文资料删除成功")

    @mcp.tool()
    def list_functional_test_automation_bindings(
            case_id: int | None = None,
            suite_id: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询功能测试用例的自动化绑定关系。"""
        queryset = FunctionalTestQuerySelector.manual_test_automation_binding().select_related("manual_case",
                                                                                               "api_case",
                                                                                               "ui_case").all()
        if case_id is not None:
            queryset = queryset.filter(manual_case_id=case_id)
        if suite_id is not None:
            queryset = queryset.filter(manual_case__suite_id=suite_id)
        queryset, total, page, page_size = _paginate(queryset.order_by("-id"), page, page_size)
        return ok(_safe_data({
            "items": format_automation_binding(queryset, many=True),
            "total": total,
            "page": page,
            "page_size": page_size,
        }))

    @mcp.tool()
    def bind_functional_test_automation_case(
            case_id: int,
            automation_type: int,
            automation_case_id: int,
            relation_type: int | None = None,
    ) -> dict:
        """绑定功能测试用例到 API/UI 自动化用例。automation_type: 0=API自动化, 1=UI自动化。"""
        automation_type = _normalize_automation_type(automation_type)
        if automation_type is None:
            return fail("automation_type 不合法", "INVALID_AUTOMATION_TYPE",
                        {"valid_values": ManualTestAutomationTypeEnum.obj()})
        manual_case = FunctionalTestQuerySelector.manual_test_case().get(id=case_id)
        if automation_type == ManualTestAutomationTypeEnum.API.value and not ApiQuerySelector.api_case().filter(
                id=automation_case_id).exists():
            return fail("API Case 不存在", "API_CASE_NOT_FOUND", {"automation_case_id": automation_case_id})
        if automation_type == ManualTestAutomationTypeEnum.UI.value and not UiQuerySelector.ui_case().filter(
                id=automation_case_id).exists():
            return fail("UI Case 不存在", "UI_CASE_NOT_FOUND", {"automation_case_id": automation_case_id})
        binding = ManualAutomationService.bind(
            manual_case,
            automation_type,
            int(automation_case_id),
            _normalize_relation_type(relation_type),
            current_user().id,
        )
        return ok(_safe_data(format_automation_binding(binding)), "功能测试自动化用例绑定成功")

    @mcp.tool()
    def list_functional_test_case_modules(
            project_product_id: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """按功能测试用例自身项目产品/模块统计模块导航。"""
        queryset = FunctionalTestQuerySelector.manual_test_case().filter(module__isnull=False)
        products_queryset = queryset
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
            case_counts = {
                item["module_id"]: item["case_count"]
                for item in queryset.values("module_id").annotate(case_count=Count("id"))
            }
            module_queryset = TestCenterQuerySelector.product_module().filter(
                project_product_id=project_product_id
            ).select_related("parent", "parent__parent").order_by("level", "sort", "id")
        else:
            case_counts = {
                item["module_id"]: item["case_count"]
                for item in queryset.values("module_id").annotate(case_count=Count("id"))
            }
            module_queryset = TestCenterQuerySelector.product_module().filter(id__in=case_counts).select_related(
                "parent", "parent__parent"
            ).order_by("project_product_id", "level", "sort", "id")
        modules = [
            {
                "key": item.id,
                "title": item.name,
                "parent_id": item.parent_id,
                "level": item.level,
                "path": ManualTestSuiteService.module_path(item),
                "case_count": case_counts.get(item.id, 0),
            }
            for item in module_queryset
        ]
        products = (
            products_queryset.values("project_product_id", "project_product__name")
            .annotate(case_count=Count("id"))
            .order_by("project_product__name")
        )
        page, page_size = _page(page, page_size)
        module_count = len(modules)
        offset = (page - 1) * page_size
        paged_modules = modules[offset: offset + page_size]
        return ok(
            {
                "products": [{"key": item["project_product_id"], "title": item["project_product__name"],
                              "case_count": item["case_count"]} for item in products],
                "modules": paged_modules,
                "module_count": module_count,
                "page": page,
                "page_size": page_size,
            }
        )

    @mcp.tool()
    def get_functional_test_suite_stats(suite_id: int) -> dict:
        """刷新并查询功能测试需求统计。"""
        ManualTestSuiteService.refresh_stats(suite_id)
        suite = FunctionalTestQuerySelector.manual_test_suite().get(id=suite_id)
        return ok(
            {
                "suite_id": suite.id,
                "case_count": suite.case_count,
                "automated_case_count": suite.automated_case_count,
                "automation_coverage_percent": float(suite.automation_coverage_percent),
                "need_optimize_count": suite.need_optimize_count,
                "sync_status": suite.sync_status,
                "last_sync_time": suite.last_sync_time.strftime("%Y-%m-%d %H:%M:%S") if suite.last_sync_time else None,
            }
        )

    @mcp.tool()
    def list_functional_test_plans(
            project_product_id: int | None = None,
            scope_type: int | None = None,
            status: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询功能测试计划。"""
        queryset = prepare_plan_list_queryset(FunctionalTestQuerySelector.functional_test_plan().all())
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if scope_type is not None:
            queryset = queryset.filter(scope_type=scope_type)
        if status is not None:
            queryset = queryset.filter(status=status)
        items, total, page, page_size = _paginate(queryset, page, page_size)
        return ok(_safe_data(
            {"items": format_plan_list(items, many=True), "total": total, "page": page, "page_size": page_size}))

    @mcp.tool()
    def create_functional_test_plan(fields: dict) -> dict:
        """创建功能测试计划。fields 至少包含 name、project_product、scope_type、owner。"""
        result = FunctionalTestMutationService.create_plan(fields or {}, current_user().id)
        if result.errors:
            return fail("参数校验失败", "VALIDATION_ERROR", result.errors)
        plan = result.instance
        return ok(_safe_data(format_plan(plan)), "测试计划创建成功")

    @mcp.tool()
    def add_functional_test_plan_cases(plan_id: int, case_ids: list[int]) -> dict:
        """从用例库批量选择用例加入测试计划，计划会保存选例时快照。"""
        data = FunctionalTestExecutionService.add_plan_cases(plan_id, case_ids)
        return ok(data, "计划用例添加成功")

    @mcp.tool()
    def start_functional_test_plan(plan_id: int) -> dict:
        """开始单次功能测试计划。"""
        plan = FunctionalTestExecutionService.start_plan(plan_id, current_user().id)
        return ok(_safe_data(format_plan(plan)), "测试计划已开始")

    @mcp.tool()
    def update_functional_test_plan_case(plan_case_id: int, fields: dict) -> dict:
        """编辑计划用例快照或填写本次测试结果。"""
        item = FunctionalTestExecutionService.update_plan_case(plan_case_id, fields or {}, current_user().id)
        return ok(_safe_data(format_plan_case(item)), "计划用例保存成功")

    @mcp.tool()
    def finish_functional_test_plan(plan_id: int) -> dict:
        """完成单次功能测试计划。"""
        plan = FunctionalTestExecutionService.finish_plan(plan_id, current_user().id)
        return ok(_safe_data(format_plan(plan)), "测试计划已完成")
