from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.module_coverage_case import ModuleCoverageCaseSnapshotSerializer, \
    ModuleCoverageCaseSerializer
from src.apps.auto_api.api.views.module_coverage_common import (
    filter_module_scope,
    page_response,
    require_project_scope,
    scope_queryset,
)
from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageCaseStatus,
    ModuleCoverageSyncAction,
)
from src.apps.auto_api.models import (
    ModuleCoverageCase,
    ModuleCoverageInterfaceSnapshot,
    ModuleCoverageScan,
)
from src.apps.auto_api.services.coverage.module_coverage import ModuleCoverageService
from src.apps.auto_api.services.coverage.module_coverage_diff import build_structured_diff
from src.apps.test_center.services.project.product_module import ProductModuleService
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001


class ModuleCoverageCaseViews(ViewSet):
    model = ModuleCoverageCase
    serializer_class = ModuleCoverageCaseSerializer

    @staticmethod
    def queryset(request, include_removed=False):
        """构建当前用户可访问的模块用例覆盖记录查询集"""
        queryset = ModuleCoverageCase.objects.filter(current_snapshot__isnull=False)
        if not include_removed:
            queryset = queryset.filter(removed_at__isnull=True)
        queryset = scope_queryset(request, queryset).select_related(
            "project_product", "project_product__project", "module", "api_case",
            "api_case_revision", "last_seen_scan", "current_snapshot",
            "last_reviewed_scan", "module_interface", "module_interface__current_snapshot",
        )
        return ProductModuleService.with_full_paths(queryset, "module")

    @action(methods=["get"], detail=False)
    @error_response("system")
    def list(self, request: Request):
        """获取模块用例覆盖记录列表"""
        change_status = request.query_params.get("change_status")
        include_removed = (
                request.query_params.get("include_removed") == "true"
                or change_status == ModuleCoverageCaseStatus.REMOVED
        )
        queryset = self.queryset(request, include_removed=include_removed)
        queryset = filter_module_scope(request, queryset)
        for field in (
                "project_product", "status", "execution_result", "coverage_validity",
                "repository_key", "branch", "scenario_layer", "scenario_type",
        ):
            value = request.query_params.get(field)
            if value not in (None, ""):
                lookup = f"{field}_id" if field in {"project_product", "module"} else field
                queryset = queryset.filter(**{lookup: value})
        scenario_tag = request.query_params.get("scenario_tag")
        if scenario_tag:
            queryset = queryset.filter(scenario_tags__contains=[scenario_tag])
        keyword = request.query_params.get("name")
        if keyword:
            queryset = queryset.filter(name__icontains=keyword)
        interface_name = request.query_params.get("interface_name")
        if interface_name:
            queryset = queryset.filter(interface_name__icontains=interface_name)
        if change_status == ModuleCoverageCaseStatus.REMOVED:
            queryset = queryset.filter(removed_at__isnull=False)
        elif change_status in ModuleCoverageSyncAction.values:
            queryset = queryset.filter(
                removed_at__isnull=True,
                current_snapshot__sync_action=change_status,
            )
        return ResponseData.success(RESPONSE_MSG_0001, page_response(queryset, request, self.serializer_class))

    @action(methods=["get"], detail=False)
    @error_response("system")
    def retrieve(self, request: Request):
        """获取模块用例覆盖记录详情"""
        item = self.queryset(request, include_removed=True).get(id=request.query_params.get("id"))
        data = self.serializer_class(item).data
        data["current_snapshot_detail"] = ModuleCoverageCaseSnapshotSerializer(item.current_snapshot).data
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def snapshots(self, request: Request):
        """获取模块用例覆盖记录历史快照"""
        item = self.queryset(request, include_removed=True).get(id=request.query_params.get("id"))
        queryset = item.snapshots.select_related("scan", "api_case", "api_case_revision").order_by("-id")
        return ResponseData.success(
            RESPONSE_MSG_0001,
            page_response(queryset, request, ModuleCoverageCaseSnapshotSerializer),
        )

    @action(methods=["get"], detail=False)
    @error_response("system")
    def flow(self, request: Request):
        """获取模块用例覆盖调用流程"""
        item = self.queryset(request, include_removed=True).get(id=request.query_params.get("id"))
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ModuleCoverageService.case_flow(item),
        )

    @action(methods=["get"], detail=False)
    @error_response("system")
    def diff(self, request: Request):
        """比较模块用例覆盖记录版本差异"""
        item = self.queryset(request, include_removed=True).get(id=request.query_params.get("id"))
        rows = list(item.snapshots.select_related("scan").order_by("-id")[:2])
        current = ModuleCoverageCaseSnapshotSerializer(rows[0]).data if rows else None
        previous = ModuleCoverageCaseSnapshotSerializer(rows[1]).data if len(rows) > 1 else None
        return ResponseData.success(RESPONSE_MSG_0001, {
            "current": current,
            "previous": previous,
            "diff": build_structured_diff(current, previous),
        })

    @action(methods=["get"], detail=False)
    @error_response("system")
    def metrics(self, request: Request):
        """获取模块用例覆盖记录指标"""
        project_product = request.query_params.get("project_product")
        project_product_id = int(project_product) if project_product not in (None, "") else None
        if project_product_id is not None:
            require_project_scope(request, project_product_id)
        module_id = request.query_params.get("module")
        module_ids = request.query_params.get("module__in")
        repository_key = request.query_params.get("repository_key") or None
        branch = request.query_params.get("branch") or None
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ModuleCoverageService.metrics(
                project_product_id,
                int(module_id) if module_id and not module_ids else None,
                repository_key,
                branch,
                case_queryset=filter_module_scope(
                    request, scope_queryset(request, ModuleCoverageCase.objects.all()),
                ),
                scan_queryset=filter_module_scope(
                    request, scope_queryset(request, ModuleCoverageScan.objects.all()),
                ),
                interface_queryset=filter_module_scope(
                    request, scope_queryset(request, ModuleCoverageInterfaceSnapshot.objects.all()),
                ),
            ),
        )

    @action(methods=["get"], detail=False)
    @error_response("system")
    def overview(self, request: Request):
        """获取模块用例覆盖记录概览"""
        product = request.query_params.get("project_product")
        if product:
            require_project_scope(request, int(product))
        modules = scope_queryset(request, TestCenterQuerySelector.product_module())
        interfaces = scope_queryset(request, ModuleCoverageInterfaceSnapshot.objects.all())
        cases = scope_queryset(request, ModuleCoverageCase.objects.all())
        scans = scope_queryset(request, ModuleCoverageScan.objects.all())
        if product:
            modules = modules.filter(project_product_id=product)
            interfaces = interfaces.filter(project_product_id=product)
            cases = cases.filter(project_product_id=product)
            scans = scans.filter(project_product_id=product)
        selected = request.query_params.get("module__in") or request.query_params.get("module")
        return ResponseData.success(RESPONSE_MSG_0001, ModuleCoverageService.overview(
            modules=modules, interfaces=interfaces, cases=cases, scans=scans,
            repository_key=request.query_params.get("repository_key"),
            branch=request.query_params.get("branch"),
            module_ids=[int(item) for item in selected.split(",") if item.strip()] if selected else None,
        ))

    @action(methods=["put"], detail=False)
    @error_response("system")
    def binding(self, request: Request):
        """更新模块用例覆盖记录的资产绑定"""
        item = self.queryset(request).get(id=request.data.get("id"))
        item = ModuleCoverageService.bind_api_case(item.id, int(request.data.get("api_case_id")))
        return ResponseData.success(RESPONSE_MSG_0001, self.serializer_class(item).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def archive_batch(self, request: Request):
        """批量归档模块用例覆盖记录"""
        queryset = self.queryset(request).filter(id__in=request.data.get("ids") or [])
        count = ModuleCoverageService.archive_cases(list(queryset.values_list("id", flat=True)))
        return ResponseData.success(RESPONSE_MSG_0001, {"archived": count})

    @action(methods=["post"], detail=False)
    @error_response("system")
    def batch_upload(self, request: Request):
        """批量上传模块用例覆盖记录"""
        scan_id = int(request.data.get("scan_id"))
        scan = ModuleCoverageService.get_uploading_scan(scan_id)
        require_project_scope(request, scan.project_product_id)
        data = ModuleCoverageService.upload_cases(scan_id, request.data.get("items") or [])
        return ResponseData.success(RESPONSE_MSG_0001, data)
