from django.db.models import Q

from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageApiInfoBindingStatus,
    ModuleCoverageCaseStatus,
    ModuleCoverageScanStatus,
    ModuleCoverageSyncAction,
)
from src.apps.auto_api.exceptions import (
    AutoApiError,
    QUALITY_COVERAGE_TASK_STATUS_NOT_ALLOWED,
)
from src.apps.auto_api.presenters import format_module_coverage_case, format_module_coverage_case_snapshot, \
    format_module_coverage_interface, format_module_coverage_interface_snapshot, format_module_coverage_scan
from src.apps.auto_api.schemas.module_coverage import ModuleCoverageCaseUploadItem
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.module_coverage import ModuleCoverageService
from src.apps.auto_api.services.module_coverage_diff import build_structured_diff
from src.apps.test_center.services.product_module import ProductModuleService
from src.interfaces.mcp.common import current_user, ok, paginate_queryset


def register_module_coverage_tools(mcp):
    @mcp.tool()
    def create_module_coverage_scan(
            project_product_id: int,
            repository_key: str,
            repository_name: str,
            branch: str,
            commit_sha: str,
            idempotency_key: str,
            expected_case_count: int,
            expected_interface_count: int,
            module_id: int | None = None,
            scan_mode: str = "full",
            scope_type: str = "module",
            target_interface_id: int | None = None,
            include_descendants: bool = False,
            base_commit_sha: str | None = None,
            test_env: int | None = None,
            skill_version: str = "1",
            schema_version: int = 3,
            inventory_only: bool = False,
    ) -> dict:
        """按模块盘点接口：scope_type=module、module_id必填、inventory_only=true、expected_case_count=0，允许省略链路及Case。默认false仍执行完整链路分析；project兼容历史无模块盘点，不作为默认流程。"""
        scan = ModuleCoverageService.create_scan({
            "project_product_id": project_product_id,
            "module_id": module_id,
            "repository_key": repository_key,
            "repository_name": repository_name,
            "branch": branch,
            "commit_sha": commit_sha,
            "idempotency_key": idempotency_key,
            "expected_case_count": expected_case_count,
            "expected_interface_count": expected_interface_count,
            "scan_mode": scan_mode,
            "scope_type": scope_type,
            "target_interface_id": target_interface_id,
            "include_descendants": include_descendants,
            "base_commit_sha": base_commit_sha,
            "test_env": test_env,
            "skill_version": skill_version,
            "schema_version": schema_version,
            "inventory_only": inventory_only,
        }, current_user().id)
        return ok(format_module_coverage_scan(scan), "模块覆盖扫描已创建")

    @mcp.tool()
    def batch_upsert_module_coverage_interfaces(scan_id: int, items: list[dict]) -> dict:
        """分批上传接口快照。inventory_only模块盘点可省略Mermaid/节点/Case，但保留真实模块范围且不清空历史分析；完整分析仍需调用图。"""
        return ok(ModuleCoverageService.upload_interfaces(scan_id, items), "扫描接口已接收")

    @mcp.tool()
    def batch_upsert_module_coverage_cases(
            scan_id: int,
            items: list[ModuleCoverageCaseUploadItem],
    ) -> dict:
        """分批上传 Case。已绑定场景在 item 顶层传 ApiCase ID；deferred 场景在 payload.remark 同时填写暂不处理原因和重新启用条件。"""
        normalized_items = [
            item.model_dump(mode="json") if isinstance(item, ModuleCoverageCaseUploadItem) else item
            for item in items
        ]
        return ok(ModuleCoverageService.upload_cases(scan_id, normalized_items), "扫描 Case 已接收")

    @mcp.tool()
    def get_module_coverage_scan_validation(scan_id: int) -> dict:
        """完成前核对数量与范围；inventory_only模块清单无需链路即可生效。完整分析仍校验路径及链路，valid_with_gaps仅允许审计关闭。"""
        return ok(ModuleCoverageService.validation(ApiQuerySelector.module_coverage_scan().get(id=scan_id)))

    @mcp.tool()
    def get_module_coverage_scan_upload_status(
            scan_id: int,
            page: int = 1,
            page_size: int = 100,
    ) -> dict:
        """分页查询已接收的 source_key，用于断点续传。"""
        scan = ApiQuerySelector.module_coverage_scan().get(id=scan_id)
        return ok(ModuleCoverageService.upload_status(scan, page, page_size))

    @mcp.tool()
    def get_module_coverage_scan(scan_id: int) -> dict:
        """查询一次模块扫描及其新增、修改、未变化、移除统计。"""
        queryset = ApiQuerySelector.module_coverage_scan().select_related("project_product", "project_product__project",
                                                                          "module")
        scan = ProductModuleService.with_full_paths(queryset, "module").get(id=scan_id)
        data = format_module_coverage_scan(scan)
        data["upload_status"] = ModuleCoverageService.upload_status(scan)
        return ok(data)

    @mcp.tool()
    def update_module_coverage_scan(
            scan_id: int,
            status: str = "completed",
            confirm_scope_reduction: bool = False,
    ) -> dict:
        """completed 应用校验通过的模块接口清单或完整分析；纯盘点不移除历史Case/接口、不算完整链路扫描。completed_with_gaps仅关闭分析审计。"""
        scan = ApiQuerySelector.module_coverage_scan().get(id=scan_id)
        if status == ModuleCoverageScanStatus.COMPLETED:
            scan = ModuleCoverageService.complete_scan(scan_id, confirm_scope_reduction)
        elif status == ModuleCoverageScanStatus.COMPLETED_WITH_GAPS:
            scan = ModuleCoverageService.complete_scan_with_gaps(scan_id)
        elif status == ModuleCoverageScanStatus.CANCELLED and scan.status == ModuleCoverageScanStatus.UPLOADING:
            scan.status = ModuleCoverageScanStatus.CANCELLED
            scan.save(update_fields=["status", "update_time"])
        else:
            raise AutoApiError(QUALITY_COVERAGE_TASK_STATUS_NOT_ALLOWED, value=(scan.status, status))
        return ok(format_module_coverage_scan(scan), "扫描状态已更新")

    @mcp.tool()
    def list_module_coverage_scans(
            project_product_id: int,
            module_id: int | None = None,
            status: str | None = None,
            scope_type: str | None = None,
            repository_key: str | None = None,
            branch: str | None = None,
            commit_sha: str | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询API自动化下的模块覆盖扫描。"""
        queryset = ApiQuerySelector.module_coverage_scan().select_related(
            "project_product", "project_product__project", "module", "target_interface",
        ).filter(project_product_id=project_product_id)
        queryset = ProductModuleService.with_full_paths(queryset, "module")
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if status:
            queryset = queryset.filter(status=status)
        if scope_type:
            queryset = queryset.filter(scope_type=scope_type)
        if repository_key:
            queryset = queryset.filter(repository_key=repository_key)
        if branch:
            queryset = queryset.filter(branch=branch)
        if commit_sha:
            queryset = queryset.filter(commit_sha=commit_sha)
        rows, count, page, page_size = paginate_queryset(queryset, page, page_size)
        return ok({
            "items": format_module_coverage_scan(rows, many=True),
            "count": count,
            "page": page,
            "page_size": page_size,
        })

    @mcp.tool()
    def list_module_coverage_cases(
            project_product_id: int,
            module_id: int | None = None,
            status: str | None = None,
            name: str | None = None,
            interface_name: str | None = None,
            repository_key: str | None = None,
            branch: str | None = None,
            change_status: str | None = None,
            coverage_validity: str | None = None,
            scenario_layer: int | None = None,
            scenario_type: int | None = None,
            scenario_tag: str | None = None,
            include_removed: bool = False,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询模块覆盖 Case；可按测试层级、验证类型、执行场景、扫描变更等条件过滤。"""
        queryset = ApiQuerySelector.module_coverage_case().filter(
            project_product_id=project_product_id,
            current_snapshot__isnull=False,
        ).select_related(
            "project_product", "project_product__project", "module", "api_case",
            "api_case_revision", "last_seen_scan", "current_snapshot",
            "last_reviewed_scan",
        )
        queryset = ProductModuleService.with_full_paths(queryset, "module")
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if not include_removed and change_status != ModuleCoverageCaseStatus.REMOVED:
            queryset = queryset.filter(removed_at__isnull=True)
        if status:
            queryset = queryset.filter(status=status)
        if name:
            queryset = queryset.filter(name__icontains=name)
        if interface_name:
            queryset = queryset.filter(interface_name__icontains=interface_name)
        if repository_key:
            queryset = queryset.filter(repository_key=repository_key)
        if branch:
            queryset = queryset.filter(branch=branch)
        if change_status == ModuleCoverageCaseStatus.REMOVED:
            queryset = queryset.filter(removed_at__isnull=False)
        elif change_status in ModuleCoverageSyncAction.values:
            queryset = queryset.filter(
                removed_at__isnull=True,
                current_snapshot__sync_action=change_status,
            )
        if coverage_validity:
            queryset = queryset.filter(coverage_validity=coverage_validity)
        if scenario_layer is not None:
            queryset = queryset.filter(scenario_layer=scenario_layer)
        if scenario_type is not None:
            queryset = queryset.filter(scenario_type=scenario_type)
        if scenario_tag:
            queryset = queryset.filter(scenario_tags__contains=[scenario_tag])
        rows, count, page, page_size = paginate_queryset(queryset, page, page_size)
        return ok({
            "items": format_module_coverage_case(rows, many=True),
            "count": count,
            "page": page,
            "page_size": page_size,
        })

    @mcp.tool()
    def list_module_coverage_interfaces(
            project_product_id: int,
            module_id: int | None = None,
            repository_key: str | None = None,
            branch: str | None = None,
            name: str | None = None,
            resolution_status: str | None = None,
            api_info_binding_status: str | None = None,
            include_removed: bool = False,
            page: int = 1,
            page_size: int = 20,
    ) -> dict:
        """按稳定接口身份聚合最新覆盖快照，返回ApiInfo绑定和Case覆盖统计。"""
        queryset = ApiQuerySelector.module_coverage_interface_snapshot().filter(
            project_product_id=project_product_id,
        ).select_related(
            "project_product", "project_product__project", "module", "scan",
            "api_info", "api_info__module", "api_info_revision", "module_interface",
        )
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if repository_key:
            queryset = queryset.filter(repository_key=repository_key)
        if branch:
            queryset = queryset.filter(branch=branch)
        queryset = ProductModuleService.with_full_paths(queryset, "module")
        queryset = ProductModuleService.with_full_paths(queryset, "api_info__module")
        if name:
            queryset = queryset.filter(Q(interface_name__icontains=name) | Q(url__icontains=name))
        if api_info_binding_status in ModuleCoverageApiInfoBindingStatus.values:
            queryset = queryset.filter(api_info_binding_status=api_info_binding_status)
        data = ModuleCoverageService.interface_page(
            queryset,
            page,
            page_size,
            include_removed,
            resolution_status,
        )
        data["items"] = format_module_coverage_interface(data["items"], many=True)
        return ok(data)

    @mcp.tool()
    def get_module_coverage_interface(
            coverage_interface_id: int,
            case_page: int = 1,
            case_page_size: int = 10,
    ) -> dict:
        """按当前接口快照ID查询调用全景图、ApiInfo绑定及场景Case。"""
        coverage_interface = ModuleCoverageService.get_current_interface_snapshot(coverage_interface_id)
        return ok(ModuleCoverageService.interface_detail(
            coverage_interface,
            None,
            case_page,
            case_page_size,
        ))

    @mcp.tool()
    def preview_module_coverage_interface_binding(
            coverage_interface_id: int,
            api_info_id: int,
            api_info_revision_id: int | None = None,
    ) -> dict:
        """预览已完成扫描的ApiInfo绑定修正；只校验变更，不改历史快照、Consumer或ApiInfo Owner。"""
        return ok(ModuleCoverageService.preview_interface_binding_correction(
            coverage_interface_id,
            api_info_id,
            api_info_revision_id,
        ))

    @mcp.tool()
    def update_module_coverage_interface_binding(
            coverage_interface_id: int,
            api_info_id: int,
            api_info_revision_id: int | None = None,
    ) -> dict:
        """通过新的单接口增量快照修正ApiInfo绑定；历史快照只读，重试不会重复生成快照。"""
        return ok(ModuleCoverageService.update_interface_binding(
            coverage_interface_id,
            api_info_id,
            api_info_revision_id,
            current_user().id,
        ), "ApiInfo绑定已通过增量快照修正")

    @mcp.tool()
    def list_module_coverage_interface_snapshots(
            coverage_interface_id: int,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询同一稳定接口身份的历次扫描快照。"""
        current = ApiQuerySelector.module_coverage_interface_snapshot().get(id=coverage_interface_id)
        queryset = ApiQuerySelector.module_coverage_interface_snapshot().filter(
            project_product_id=current.project_product_id,
            module_id=current.module_id,
            repository_key=current.repository_key,
            branch=current.branch,
            source_key_hash=current.source_key_hash,
        ).select_related("scan", "module", "api_info", "api_info_revision").order_by("-id")
        rows, count, page, page_size = paginate_queryset(queryset, page, page_size)
        return ok({
            "items": format_module_coverage_interface_snapshot(rows, many=True),
            "count": count,
            "page": page,
            "page_size": page_size,
        })

    @mcp.tool()
    def get_module_coverage_interface_diff(
            coverage_interface_id: int,
            current_snapshot_id: int | None = None,
            previous_snapshot_id: int | None = None,
    ) -> dict:
        """比较同一稳定接口身份的两个快照，返回原始快照和字段级结构化差异。"""
        current = ApiQuerySelector.module_coverage_interface_snapshot().get(id=coverage_interface_id)
        queryset = ApiQuerySelector.module_coverage_interface_snapshot().filter(
            project_product_id=current.project_product_id,
            module_id=current.module_id,
            repository_key=current.repository_key,
            branch=current.branch,
            source_key_hash=current.source_key_hash,
        ).select_related("scan")
        if current_snapshot_id and previous_snapshot_id:
            row_map = {row.id: row for row in queryset.filter(
                id__in=[current_snapshot_id, previous_snapshot_id],
            )}
            rows = [row_map.get(current_snapshot_id), row_map.get(previous_snapshot_id)]
        else:
            rows = list(queryset.order_by("-id")[:2])
        current_data = (
            format_module_coverage_interface_snapshot(rows[0])
            if rows and rows[0] else None
        )
        previous_data = (
            format_module_coverage_interface_snapshot(rows[1])
            if len(rows) > 1 and rows[1] else None
        )
        return ok({
            "current": current_data,
            "previous": previous_data,
            "diff": build_structured_diff(current_data, previous_data),
        })

    @mcp.tool()
    def list_module_coverage_interface_cases(
            coverage_interface_id: int,
            include_removed: bool = False,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询同一稳定接口身份下的扫描Case和ApiCase绑定。"""
        current = ApiQuerySelector.module_coverage_interface_snapshot().get(id=coverage_interface_id)
        queryset = ApiQuerySelector.module_coverage_case().filter(current_snapshot__isnull=False)
        if current.module_interface_id:
            queryset = queryset.filter(module_interface_id=current.module_interface_id)
        else:
            queryset = queryset.filter(
                project_product_id=current.project_product_id,
                module_id=current.module_id,
                repository_key=current.repository_key,
                branch=current.branch,
                interface_source_key_hash=current.source_key_hash,
            )
        queryset = queryset.select_related(
            "project_product", "project_product__project", "module", "api_case",
            "api_case_revision", "last_seen_scan", "current_snapshot", "module_interface",
        )
        if not include_removed:
            queryset = queryset.filter(removed_at__isnull=True)
        queryset = ProductModuleService.with_full_paths(queryset, "module")
        rows, count, page, page_size = paginate_queryset(queryset, page, page_size)
        return ok({
            "items": format_module_coverage_case(rows, many=True),
            "count": count,
            "page": page,
            "page_size": page_size,
        })

    @mcp.tool()
    def get_module_coverage_case(coverage_case_id: int) -> dict:
        """查询 Case 台账、测试场景、核心断言、代码证据、接口引用、覆盖路径和 ApiCase 绑定。"""
        queryset = ApiQuerySelector.module_coverage_case().filter(current_snapshot__isnull=False).select_related(
            "project_product", "project_product__project", "module", "api_case",
            "api_case_revision", "last_seen_scan", "current_snapshot",
        )
        item = ProductModuleService.with_full_paths(queryset, "module").get(id=coverage_case_id)
        data = format_module_coverage_case(item)
        data["current_snapshot_detail"] = format_module_coverage_case_snapshot(item.current_snapshot)
        return ok(data)

    @mcp.tool()
    def list_module_coverage_case_snapshots(
            coverage_case_id: int,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询一个模块覆盖 Case 的历次扫描快照。"""
        queryset = ApiQuerySelector.module_coverage_case_snapshot().filter(
            coverage_case_id=coverage_case_id,
        ).select_related("scan", "api_case", "api_case_revision").order_by("-id")
        rows, count, page, page_size = paginate_queryset(queryset, page, page_size)
        return ok({
            "items": format_module_coverage_case_snapshot(rows, many=True),
            "count": count,
            "page": page,
            "page_size": page_size,
        })

    @mcp.tool()
    def get_module_coverage_case_flow(coverage_case_id: int) -> dict:
        """查询 Case 所属接口的 Mermaid 全景图，以及该 Case 需要高亮的覆盖节点和分支。"""
        item = ApiQuerySelector.module_coverage_case().select_related(
            "current_snapshot",
        ).get(id=coverage_case_id)
        return ok(ModuleCoverageService.case_flow(item))

    @mcp.tool()
    def get_module_coverage_case_diff(coverage_case_id: int) -> dict:
        """查询 Case 最近两次快照，返回原始快照和字段级结构化差异。"""
        rows = list(ApiQuerySelector.module_coverage_case_snapshot().filter(
            coverage_case_id=coverage_case_id,
        ).select_related("scan", "api_case", "api_case_revision").order_by("-id")[:2])
        current_data = format_module_coverage_case_snapshot(rows[0]) if rows else None
        previous_data = format_module_coverage_case_snapshot(rows[1]) if len(rows) > 1 else None
        return ok({
            "current": current_data,
            "previous": previous_data,
            "diff": build_structured_diff(current_data, previous_data),
        })

    @mcp.tool()
    def update_module_coverage_case_binding(coverage_case_id: int, api_case_id: int) -> dict:
        """把覆盖 Case 绑定到同项目产品、同模块的已有 ApiCase。"""
        item = ModuleCoverageService.bind_api_case(coverage_case_id, api_case_id)
        return ok(format_module_coverage_case(item), "ApiCase 绑定已更新")

    @mcp.tool()
    def batch_archive_module_coverage_cases(coverage_case_ids: list[int]) -> dict:
        """归档覆盖 Case，不删除真实 ApiCase。"""
        count = ModuleCoverageService.archive_cases(coverage_case_ids)
        return ok({"archived": count}, "扫描 Case 已归档")

    @mcp.tool()
    def get_module_coverage_metrics(
            project_product_id: int,
            module_id: int | None = None,
            repository_key: str | None = None,
            branch: str | None = None,
    ) -> dict:
        """按模块、仓库和分支汇总 URL、Case、自动化完成率、执行通过率和测试归属。"""
        return ok(ModuleCoverageService.metrics(
            project_product_id,
            module_id,
            repository_key,
            branch,
        ))
