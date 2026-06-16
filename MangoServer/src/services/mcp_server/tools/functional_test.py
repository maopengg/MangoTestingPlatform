from __future__ import annotations

from django.db.models import Count

from src.apps.auto_api.models import ApiCase
from src.apps.ai.service.core import mask_sensitive
from src.apps.auto_ui.models import UiCase
from src.apps.system.models import ProductModule
from src.apps.functional_test.models import (
    FunctionalTestContextResource,
    ManualTestAutomationBinding,
    ManualTestCase,
    ManualTestSuite,
)
from src.apps.functional_test.service.automation import ManualAutomationService
from src.apps.functional_test.service.suite import ManualTestSuiteService
from src.apps.functional_test.views.automation_binding import ManualTestAutomationBindingSerializer
from src.apps.functional_test.views.case import ManualTestCaseListSerializer, ManualTestCaseSerializer, ManualTestCaseSerializerC
from src.apps.functional_test.views.context_resource import FunctionalTestContextResourceSerializer, FunctionalTestContextResourceSerializerC
from src.apps.functional_test.views.suite import ManualTestSuiteSerializer, ManualTestSuiteSerializerC
from src.common.enums.manual_test_enum import (
    FunctionalTestContextKeyEnum,
    FunctionalTestContextUrlTypeEnum,
    ManualTestAutomationTypeEnum,
    ManualTestRelationTypeEnum,
)
from src.services.mcp_server.common import current_user, fail, ok


MAX_PAGE_SIZE = 100
LIST_RESOURCE_TEXT_LIMIT = 300


def _page(page: int = 1, page_size: int = 20) -> tuple[int, int]:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 20), 1), MAX_PAGE_SIZE)
    return page, page_size


def _paginate(queryset, page: int = 1, page_size: int = 20):
    page, page_size = _page(page, page_size)
    total = queryset.count()
    start = (page - 1) * page_size
    return queryset[start : start + page_size], total, page, page_size


def _serializer_error(serializer) -> dict:
    return fail("参数校验失败", "VALIDATION_ERROR", serializer.errors)


def _safe_data(data):
    return mask_sensitive(data)


def _suite_queryset():
    return ManualTestSuiteSerializerC.setup_eager_loading(ManualTestSuite.objects.all())


def _case_queryset():
    return ManualTestCaseListSerializer.setup_eager_loading(ManualTestCase.objects.all())


def _resource_queryset():
    return FunctionalTestContextResourceSerializerC.setup_eager_loading(FunctionalTestContextResource.objects.all())


def _resource_summary(resource: FunctionalTestContextResource) -> dict:
    data = FunctionalTestContextResourceSerializerC(instance=resource).data
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


def _context_key_valid(value: int | str) -> bool:
    try:
        return int(value) in FunctionalTestContextKeyEnum.get_key_list()
    except (TypeError, ValueError):
        return False


def _is_feishu_url_type(value: int | str | None) -> bool:
    try:
        return int(value) == FunctionalTestContextUrlTypeEnum.FEISHU.value
    except (TypeError, ValueError):
        return False


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
        page_size: int = 20,
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
        return ok(_safe_data({"items": ManualTestSuiteSerializerC(instance=items, many=True).data, "total": total, "page": page, "page_size": page_size}))

    @mcp.tool()
    def get_functional_test_suite_detail(suite_id: int, include_cases: bool = False, include_resources: bool = False) -> dict:
        """查询功能测试需求详情，可选返回用例和上下文资料摘要。"""
        suite = _suite_queryset().get(id=suite_id)
        data = ManualTestSuiteSerializerC(instance=suite).data
        if include_cases:
            cases = _case_queryset().filter(suite_id=suite_id).order_by("case_no", "id")
            data["cases"] = ManualTestCaseListSerializer(instance=cases, many=True).data
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
        serializer = ManualTestSuiteSerializer(data=payload)
        if not serializer.is_valid():
            return _serializer_error(serializer)
        suite = serializer.save()
        ManualTestSuiteService.refresh_stats(suite.id)
        return ok(_safe_data(ManualTestSuiteSerializerC(instance=_suite_queryset().get(id=suite.id)).data), "功能测试需求创建成功")

    @mcp.tool()
    def update_functional_test_suite(suite_id: int, fields: dict) -> dict:
        """修改功能测试需求。fields 使用 ManualTestSuite 字段名。"""
        suite = ManualTestSuite.objects.get(id=suite_id)
        payload = {"id": suite_id, **(fields or {})}
        serializer = ManualTestSuiteSerializer(suite, data=payload, partial=True)
        if not serializer.is_valid():
            return _serializer_error(serializer)
        suite = serializer.save()
        ManualTestSuiteService.refresh_stats(suite.id)
        return ok(_safe_data(ManualTestSuiteSerializerC(instance=_suite_queryset().get(id=suite.id)).data), "功能测试需求修改成功")

    @mcp.tool()
    def delete_functional_test_suite(suite_id: int) -> dict:
        """删除功能测试需求，会级联删除该需求下功能测试用例、资料和绑定。"""
        suite = ManualTestSuite.objects.get(id=suite_id)
        case_count = ManualTestCase.objects.filter(suite_id=suite_id).count()
        resource_count = FunctionalTestContextResource.objects.filter(suite_id=suite_id).count()
        suite.delete()
        return ok({"suite_id": suite_id, "deleted_case_count": case_count, "deleted_resource_count": resource_count}, "功能测试需求删除成功")

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
        scenario_tag: int | None = None,
        change_status: int | None = None,
        automation_impact_status: int | None = None,
        owner_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
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
            queryset = queryset.filter(scenario_tags__contains=[int(scenario_tag)])
        items, total, page, page_size = _paginate(queryset, page, page_size)
        return ok(_safe_data({"items": ManualTestCaseListSerializer(instance=items, many=True).data, "total": total, "page": page, "page_size": page_size}))

    @mcp.tool()
    def get_functional_test_case_detail(case_id: int) -> dict:
        """查询功能测试用例详情，包括需求、项目产品、模块、负责人和自动化绑定。"""
        case = ManualTestCaseSerializerC.setup_eager_loading(ManualTestCase.objects.all()).get(id=case_id)
        return ok(_safe_data(ManualTestCaseSerializerC(instance=case).data))

    @mcp.tool()
    def create_functional_test_case(fields: dict) -> dict:
        """创建功能测试用例。必须传 suite、project_product、module、owner、case_no、title、test_point、test_types、priority、scenario_layer、scenario_type、scenario_tags。"""
        payload = dict(fields or {})
        required = ["suite", "project_product", "module", "owner", "case_no", "title", "test_point", "test_types", "priority", "scenario_layer", "scenario_type", "scenario_tags"]
        missing = [field for field in required if payload.get(field) in (None, "", [])]
        if missing:
            return fail("创建功能测试用例缺少必填字段，请先查询需求详情、项目产品、模块和用户后再创建。", "REQUIRED_FIELDS_MISSING", {"missing_fields": missing})
        serializer = ManualTestCaseSerializer(data=payload)
        if not serializer.is_valid():
            return _serializer_error(serializer)
        case = serializer.save()
        ManualTestSuiteService.refresh_stats(case.suite_id)
        return ok(_safe_data(ManualTestCaseSerializerC(instance=ManualTestCaseSerializerC.setup_eager_loading(ManualTestCase.objects.all()).get(id=case.id)).data), "功能测试用例创建成功")

    @mcp.tool()
    def update_functional_test_case(case_id: int, fields: dict) -> dict:
        """修改功能测试用例。fields 使用 ManualTestCase 字段名。"""
        case = ManualTestCase.objects.get(id=case_id)
        payload = {"id": case_id, **(fields or {})}
        serializer = ManualTestCaseSerializer(case, data=payload, partial=True)
        if not serializer.is_valid():
            return _serializer_error(serializer)
        case = serializer.save()
        ManualTestSuiteService.refresh_stats(case.suite_id)
        return ok(_safe_data(ManualTestCaseSerializerC(instance=ManualTestCaseSerializerC.setup_eager_loading(ManualTestCase.objects.all()).get(id=case.id)).data), "功能测试用例修改成功")

    @mcp.tool()
    def delete_functional_test_case(case_id: int) -> dict:
        """删除单个功能测试用例。"""
        case = ManualTestCase.objects.get(id=case_id)
        suite_id = case.suite_id
        case.delete()
        ManualTestSuiteService.refresh_stats(suite_id)
        return ok({"case_id": case_id, "suite_id": suite_id}, "功能测试用例删除成功")

    @mcp.tool()
    def batch_delete_functional_test_cases(suite_id: int, case_ids: list[int]) -> dict:
        """批量删除功能测试用例，只删除属于指定需求的用例。"""
        ids = [int(item) for item in (case_ids or []) if str(item).isdigit()]
        if not ids:
            return fail("case_ids 不能为空", "CASE_IDS_EMPTY")
        queryset = ManualTestCase.objects.filter(suite_id=suite_id, id__in=ids)
        deleted_ids = list(queryset.values_list("id", flat=True))
        queryset.delete()
        ManualTestSuiteService.refresh_stats(suite_id)
        return ok({"suite_id": suite_id, "deleted_case_ids": deleted_ids, "deleted_count": len(deleted_ids), "ignored_case_ids": [item for item in ids if item not in deleted_ids]}, "功能测试用例批量删除成功")

    @mcp.tool()
    def list_functional_test_context_resources(
        suite_id: int | None = None,
        context_key: int | None = None,
        content_type: int | None = None,
        enabled: bool | None = None,
        page: int = 1,
        page_size: int = 20,
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
        return ok(_safe_data({"items": [_resource_summary(item) for item in items], "total": total, "page": page, "page_size": page_size}))

    @mcp.tool()
    def get_functional_test_context_resource_detail(resource_id: int) -> dict:
        """查询功能测试上下文资料详情，返回完整文本和解析文本。"""
        resource = _resource_queryset().get(id=resource_id)
        return ok(_safe_data(FunctionalTestContextResourceSerializerC(instance=resource).data))

    @mcp.tool()
    def create_functional_test_context_resource(fields: dict) -> dict:
        """创建功能测试上下文资料。只保存文本/URL/文件元数据，不接收二进制内容；飞书 URL 暂不支持。"""
        payload = dict(fields or {})
        if not _context_key_valid(payload.get("context_key")):
            return fail("context_key 不合法", "INVALID_CONTEXT_KEY", {"valid_values": FunctionalTestContextKeyEnum.obj()})
        if _is_feishu_url_type(payload.get("url_type")):
            return fail("飞书 URL 类型暂不支持", "FEISHU_URL_NOT_SUPPORTED")
        user = current_user()
        payload["create_user"] = user.id
        payload["update_user"] = user.id
        serializer = FunctionalTestContextResourceSerializer(data=payload)
        if not serializer.is_valid():
            return _serializer_error(serializer)
        resource = serializer.save()
        return ok(_safe_data(FunctionalTestContextResourceSerializerC(instance=_resource_queryset().get(id=resource.id)).data), "功能测试上下文资料创建成功")

    @mcp.tool()
    def update_functional_test_context_resource(resource_id: int, fields: dict) -> dict:
        """修改功能测试上下文资料。fields 使用 FunctionalTestContextResource 字段名。"""
        resource = FunctionalTestContextResource.objects.get(id=resource_id)
        payload = {"id": resource_id, **(fields or {})}
        if "context_key" in payload and not _context_key_valid(payload.get("context_key")):
            return fail("context_key 不合法", "INVALID_CONTEXT_KEY", {"valid_values": FunctionalTestContextKeyEnum.obj()})
        if _is_feishu_url_type(payload.get("url_type")):
            return fail("飞书 URL 类型暂不支持", "FEISHU_URL_NOT_SUPPORTED")
        payload["update_user"] = current_user().id
        serializer = FunctionalTestContextResourceSerializer(resource, data=payload, partial=True)
        if not serializer.is_valid():
            return _serializer_error(serializer)
        resource = serializer.save()
        return ok(_safe_data(FunctionalTestContextResourceSerializerC(instance=_resource_queryset().get(id=resource.id)).data), "功能测试上下文资料修改成功")

    @mcp.tool()
    def delete_functional_test_context_resource(resource_id: int) -> dict:
        """删除功能测试上下文资料。"""
        resource = FunctionalTestContextResource.objects.get(id=resource_id)
        suite_id = resource.suite_id
        resource.delete()
        return ok({"resource_id": resource_id, "suite_id": suite_id}, "功能测试上下文资料删除成功")

    @mcp.tool()
    def list_functional_test_automation_bindings(case_id: int | None = None, suite_id: int | None = None) -> dict:
        """查询功能测试用例的自动化绑定关系。"""
        queryset = ManualTestAutomationBinding.objects.select_related("manual_case", "api_case", "ui_case").all()
        if case_id is not None:
            queryset = queryset.filter(manual_case_id=case_id)
        if suite_id is not None:
            queryset = queryset.filter(manual_case__suite_id=suite_id)
        return ok(_safe_data({"items": ManualTestAutomationBindingSerializer(instance=queryset, many=True).data, "total": queryset.count()}))

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
            return fail("automation_type 不合法", "INVALID_AUTOMATION_TYPE", {"valid_values": ManualTestAutomationTypeEnum.obj()})
        manual_case = ManualTestCase.objects.get(id=case_id)
        if automation_type == ManualTestAutomationTypeEnum.API.value and not ApiCase.objects.filter(id=automation_case_id).exists():
            return fail("API Case 不存在", "API_CASE_NOT_FOUND", {"automation_case_id": automation_case_id})
        if automation_type == ManualTestAutomationTypeEnum.UI.value and not UiCase.objects.filter(id=automation_case_id).exists():
            return fail("UI Case 不存在", "UI_CASE_NOT_FOUND", {"automation_case_id": automation_case_id})
        binding = ManualAutomationService.bind(
            manual_case,
            automation_type,
            int(automation_case_id),
            _normalize_relation_type(relation_type),
            current_user().id,
        )
        return ok(_safe_data(ManualTestAutomationBindingSerializer(instance=binding).data), "功能测试自动化用例绑定成功")

    @mcp.tool()
    def list_functional_test_case_modules(project_product_id: int | None = None) -> dict:
        """按功能测试用例自身项目产品/模块统计模块导航。"""
        queryset = ManualTestCase.objects.filter(module__isnull=False)
        products_queryset = queryset
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
            case_counts = {
                item["module_id"]: item["case_count"]
                for item in queryset.values("module_id").annotate(case_count=Count("id"))
            }
            modules = [
                {
                    "key": item.id,
                    "title": item.name,
                    "superior_module_1": item.superior_module_1,
                    "superior_module_2": item.superior_module_2,
                    "case_count": case_counts.get(item.id, 0),
                }
                for item in ProductModule.objects.filter(project_product_id=project_product_id).order_by(
                    "superior_module_1",
                    "superior_module_2",
                    "name",
                )
            ]
        else:
            modules = [
                {
                    "key": item["module_id"],
                    "title": item["module__name"],
                    "superior_module_1": item["module__superior_module_1"],
                    "superior_module_2": item["module__superior_module_2"],
                    "case_count": item["case_count"],
                }
                for item in queryset.values("module_id", "module__name", "module__superior_module_1", "module__superior_module_2")
                .annotate(case_count=Count("id"))
                .order_by("module__superior_module_1", "module__superior_module_2", "module__name")
            ]
        products = (
            products_queryset.values("project_product_id", "project_product__name")
            .annotate(case_count=Count("id"))
            .order_by("project_product__name")
        )
        return ok(
            {
                "products": [{"key": item["project_product_id"], "title": item["project_product__name"], "case_count": item["case_count"]} for item in products],
                "modules": modules,
            }
        )

    @mcp.tool()
    def get_functional_test_suite_stats(suite_id: int) -> dict:
        """刷新并查询功能测试需求统计。"""
        ManualTestSuiteService.refresh_stats(suite_id)
        suite = ManualTestSuite.objects.get(id=suite_id)
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
