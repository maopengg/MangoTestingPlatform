from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.module_coverage_scan import ModuleCoverageScanSerializer
from src.apps.auto_api.api.views.module_coverage_common import (
    filter_module_scope,
    page_response,
    request_user_id,
    require_project_scope,
    scope_queryset,
)
from src.apps.auto_api.enums.module_coverage import ModuleCoverageScanStatus
from src.apps.auto_api.exceptions import (
    AutoApiError,
    QUALITY_COVERAGE_TASK_STATUS_NOT_ALLOWED,
)
from src.apps.auto_api.models import ModuleCoverageScan
from src.apps.auto_api.services.module_coverage import ModuleCoverageService
from src.apps.test_center.services.product_module import ProductModuleService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001


class ModuleCoverageScanViews(ViewSet):
    model = ModuleCoverageScan
    serializer_class = ModuleCoverageScanSerializer

    @staticmethod
    def queryset(request):
        queryset = scope_queryset(request, ModuleCoverageScan.objects.all()).select_related(
            "project_product", "project_product__project", "module", "target_interface",
        )
        return ProductModuleService.with_full_paths(queryset, "module")

    @action(methods=["get"], detail=False)
    @error_response("system")
    def list(self, request: Request):
        queryset = self.queryset(request)
        queryset = filter_module_scope(request, queryset)
        for field in (
                "project_product", "status", "scan_mode", "scope_type",
                "repository_key", "branch", "commit_sha", "target_interface",
        ):
            value = request.query_params.get(field)
            if value not in (None, ""):
                lookup = f"{field}_id" if field in {"project_product", "module"} else field
                queryset = queryset.filter(**{lookup: value})
        return ResponseData.success(RESPONSE_MSG_0001, page_response(queryset, request, self.serializer_class))

    @action(methods=["get"], detail=False)
    @error_response("system")
    def retrieve(self, request: Request):
        item = self.queryset(request).get(id=request.query_params.get("id"))
        data = self.serializer_class(item).data
        data["upload_status"] = ModuleCoverageService.upload_status(item)
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def create(self, request: Request):
        ModuleCoverageService.require_fields(request.data, ModuleCoverageService.REQUIRED_SCAN_FIELDS)
        require_project_scope(request, int(request.data["project_product_id"]))
        scan = ModuleCoverageService.create_scan(request.data, request_user_id(request))
        return ResponseData.success(RESPONSE_MSG_0001, self.serializer_class(scan).data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def validation(self, request: Request):
        scan = self.queryset(request).get(id=request.query_params.get("id"))
        return ResponseData.success(RESPONSE_MSG_0001, ModuleCoverageService.validation(scan))

    @action(methods=["get"], detail=False)
    @error_response("system")
    def upload_status(self, request: Request):
        scan = self.queryset(request).get(id=request.query_params.get("id"))
        return ResponseData.success(RESPONSE_MSG_0001, ModuleCoverageService.upload_status(
            scan, request.query_params.get("page") or 1, request.query_params.get("pageSize") or 100,
        ))

    @action(methods=["put"], detail=False)
    @error_response("system")
    def update_status(self, request: Request):
        scan = self.queryset(request).get(id=request.data.get("id"))
        requested = request.data.get("status")
        if requested == ModuleCoverageScanStatus.COMPLETED:
            scan = ModuleCoverageService.complete_scan(
                scan.id,
                confirm_scope_reduction=bool(request.data.get("confirm_scope_reduction")),
            )
        elif requested == ModuleCoverageScanStatus.COMPLETED_WITH_GAPS:
            scan = ModuleCoverageService.complete_scan_with_gaps(scan.id)
        elif requested == ModuleCoverageScanStatus.CANCELLED and scan.status == ModuleCoverageScanStatus.UPLOADING:
            scan.status = ModuleCoverageScanStatus.CANCELLED
            scan.save(update_fields=["status", "update_time"])
        else:
            raise AutoApiError(QUALITY_COVERAGE_TASK_STATUS_NOT_ALLOWED,
                               value=(scan.status, requested),
                               )
        return ResponseData.success(RESPONSE_MSG_0001, self.serializer_class(scan).data)
