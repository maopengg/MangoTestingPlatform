from django.db.models import F, Q
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.module_coverage_interface import ModuleCoverageInterfaceSnapshotSerializer, \
    ModuleCoverageInterfaceSerializer
from src.apps.auto_api.api.views.module_coverage_case import ModuleCoverageCaseViews
from src.apps.auto_api.api.views.module_coverage_common import (
    filter_module_scope,
    page_response,
    request_user_id,
    require_project_scope,
    scope_queryset,
)
from src.apps.auto_api.models import ModuleCoverageInterfaceSnapshot
from src.apps.auto_api.services.coverage.module_coverage import ModuleCoverageService
from src.apps.auto_api.services.coverage.module_coverage_diff import build_structured_diff
from src.apps.test_center.services.project.product_module import ProductModuleService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001


class ModuleCoverageInterfaceViews(ViewSet):
    model = ModuleCoverageInterfaceSnapshot
    serializer_class = ModuleCoverageInterfaceSnapshotSerializer

    @action(methods=["get"], detail=False)
    @error_response("system")
    def list(self, request: Request):
        """获取模块接口覆盖记录列表"""
        queryset = scope_queryset(
            request,
            ModuleCoverageInterfaceSnapshot.objects.all(),
        ).select_related(
            "project_product", "project_product__project", "module", "scan",
            "api_info", "api_info__module", "api_info_revision", "module_interface",
        )
        queryset = ProductModuleService.with_full_paths(queryset, "module")
        queryset = ProductModuleService.with_full_paths(queryset, "api_info__module")
        queryset = filter_module_scope(request, queryset)
        for field in ("project_product", "repository_key", "branch"):
            value = request.query_params.get(field)
            if value not in (None, ""):
                lookup = f"{field}_id" if field in {"project_product", "module"} else field
                queryset = queryset.filter(**{lookup: value})
        keyword = request.query_params.get("name")
        if keyword:
            queryset = queryset.filter(Q(interface_name__icontains=keyword) | Q(url__icontains=keyword))
        resolution_status = request.query_params.get("resolution_status")
        api_info_binding_status = request.query_params.get("api_info_binding_status")
        if api_info_binding_status:
            queryset = queryset.filter(api_info_binding_status=api_info_binding_status)
        lifecycle_status = request.query_params.get("status")
        if lifecycle_status:
            queryset = queryset.filter(lifecycle_status=lifecycle_status)
        include_removed = request.query_params.get("include_removed") == "true"
        data = ModuleCoverageService.interface_page(
            queryset,
            request.query_params.get("page") or 1,
            request.query_params.get("pageSize") or 20,
            include_removed,
            resolution_status,
            request.query_params.get("coverage_policy"),
            resolution_statuses=request.query_params.get("resolution_status__in", "").split(",") if request.query_params.get("resolution_status__in") else None,
            analysis_statuses=request.query_params.get("analysis_status__in", "").split(",") if request.query_params.get("analysis_status__in") else None,
            coverage_statuses=request.query_params.get("coverage_status__in", "").split(",") if request.query_params.get("coverage_status__in") else None,
            methods=request.query_params.get("method__in", "").split(",") if request.query_params.get("method__in") else None,
            sync_actions=request.query_params.get("sync_action__in", "").split(",") if request.query_params.get("sync_action__in") else None,
            coverage_reason=request.query_params.get("coverage_reason"),
            api_info_id=request.query_params.get("api_info_id") or None,
        )
        data["items"] = ModuleCoverageInterfaceSerializer(data["items"], many=True).data
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def retrieve(self, request: Request):
        """获取模块接口覆盖记录详情"""
        queryset = scope_queryset(request, ModuleCoverageInterfaceSnapshot.objects.all()).select_related(
            "project_product", "module", "scan", "api_info", "api_info__module",
            "api_info_revision", "module_interface",
        )
        queryset = ProductModuleService.with_full_paths(queryset, "module")
        queryset = ProductModuleService.with_full_paths(queryset, "api_info__module")
        interface_snapshot = queryset.filter(
            Q(module_interface__current_snapshot_id=F("id"))
            | Q(module_interface__isnull=True, is_current=True)
        ).get(id=request.query_params.get("id"))
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ModuleCoverageService.interface_detail(
                interface_snapshot,
                ModuleCoverageCaseViews.queryset(request, include_removed=True),
                request.query_params.get("case_page") or 1,
                request.query_params.get("case_page_size") or 100,
            ),
        )

    @action(methods=["get"], detail=False)
    @error_response("system")
    def snapshots(self, request: Request):
        """获取模块接口覆盖记录历史快照"""
        interface_snapshot = scope_queryset(
            request, ModuleCoverageInterfaceSnapshot.objects.all(),
        ).get(id=request.query_params.get("id"))
        queryset = ModuleCoverageInterfaceSnapshot.objects.filter(
            project_product_id=interface_snapshot.project_product_id,
            module_id=interface_snapshot.module_id,
            repository_key=interface_snapshot.repository_key,
            branch=interface_snapshot.branch,
            source_key_hash=interface_snapshot.source_key_hash,
        ).select_related("scan", "module", "api_info", "api_info_revision").order_by("-id")
        return ResponseData.success(
            RESPONSE_MSG_0001,
            page_response(queryset, request, ModuleCoverageInterfaceSnapshotSerializer),
        )

    @action(methods=["get"], detail=False)
    @error_response("system")
    def diff(self, request: Request):
        """比较模块接口覆盖记录版本差异"""
        interface_snapshot = scope_queryset(
            request, ModuleCoverageInterfaceSnapshot.objects.all(),
        ).get(id=request.query_params.get("id"))
        snapshots = ModuleCoverageInterfaceSnapshot.objects.filter(
            project_product_id=interface_snapshot.project_product_id,
            module_id=interface_snapshot.module_id,
            repository_key=interface_snapshot.repository_key,
            branch=interface_snapshot.branch,
            source_key_hash=interface_snapshot.source_key_hash,
        )
        snapshot_ids = [
            request.query_params.get("current_snapshot_id"),
            request.query_params.get("previous_snapshot_id"),
        ]
        if all(snapshot_ids):
            rows = list(snapshots.filter(id__in=snapshot_ids).select_related("scan"))
            row_map = {str(row.id): row for row in rows}
            ordered = [row_map.get(str(value)) for value in snapshot_ids]
        else:
            ordered = list(snapshots.select_related("scan").order_by("-id")[:2])
        current = ModuleCoverageInterfaceSnapshotSerializer(ordered[0]).data if ordered else None
        previous = (
            ModuleCoverageInterfaceSnapshotSerializer(ordered[1]).data
            if len(ordered) > 1 and ordered[1] else None
        )
        return ResponseData.success(RESPONSE_MSG_0001, {
            "current": current,
            "previous": previous,
            "diff": build_structured_diff(current, previous),
        })

    @action(methods=["get"], detail=False)
    @error_response("system")
    def binding_preview(self, request: Request):
        """预览接口覆盖记录的用例关联"""
        interface_snapshot = scope_queryset(
            request, ModuleCoverageInterfaceSnapshot.objects.all(),
        ).get(id=request.query_params.get("id"))
        data = ModuleCoverageService.preview_interface_binding_correction(
            interface_snapshot.id,
            request.query_params.get("api_info_id"),
            request.query_params.get("api_info_revision_id"),
        )
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["put"], detail=False)
    @error_response("system")
    def binding(self, request: Request):
        """更新模块接口覆盖记录的资产绑定"""
        interface_snapshot = scope_queryset(
            request, ModuleCoverageInterfaceSnapshot.objects.all(),
        ).get(id=request.data.get("id"))
        data = ModuleCoverageService.update_interface_binding(
            interface_snapshot.id,
            request.data.get("api_info_id"),
            request.data.get("api_info_revision_id"),
            request_user_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def policy(self, request: Request):
        """更新模块接口覆盖策略"""
        data = ModuleCoverageService.update_interface_policy(
            request.data.get("interface_ids"), request.data.get("policy"),
            request.data.get("reason", ""), request_user_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def batch_upload(self, request: Request):
        """批量上传模块接口覆盖记录"""
        scan_id = int(request.data.get("scan_id"))
        scan = ModuleCoverageService.get_uploading_scan(scan_id)
        require_project_scope(request, scan.project_product_id)
        data = ModuleCoverageService.upload_interfaces(scan_id, request.data.get("items") or [])
        return ResponseData.success(RESPONSE_MSG_0001, data)
