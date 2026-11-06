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
from src.interfaces.mcp.common import current_user, ok, paginate_list, paginate_queryset


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
            coverage_policy: str | None = None,
            resolution_statuses: list[str] | None = None,
            coverage_statuses: list[str] | None = None,
            analysis_statuses: list[str] | None = None,
            methods: list[str] | None = None,
            sync_actions: list[str] | None = None,
            coverage_reason: str | None = None,
            api_info_id: int | None = None,
            page: int = 1,
            page_size: int = 20,
    ) -> dict:
        """按稳定接口身份分页查询，先筛选再分页。analysis_statuses多选completed/pending/gap/deferred/excluded，与接口分析图同口径；仅有图、没有完整场景不算已分析。支持链路、覆盖、方法、变更及ApiInfo筛选。coverage_policy为included/deferred/excluded；后两者仅盘点，不生成图或Case，仅excluded排除分母。"""
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
            coverage_policy,
            resolution_statuses=resolution_statuses,
            coverage_statuses=coverage_statuses,
            analysis_statuses=analysis_statuses,
            methods=methods,
            sync_actions=sync_actions,
            coverage_reason=coverage_reason,
            api_info_id=api_info_id,
        )
        data["items"] = format_module_coverage_interface(data["items"], many=True)
        return ok(data)

    @mcp.tool()
    def update_module_coverage_interface_policy(
            coverage_interface_id: int, policy: str, reason: str = "",
    ) -> dict:
        """设置覆盖策略included(纳入)/deferred(暂不处理)/excluded(排除)。后两者必填原因。按产品、模块、仓库、分支持久生效，不删除真实资产或历史，也不改自动计算的覆盖进度；扫描不会自动恢复。"""
        return ok(ModuleCoverageService.update_interface_policy(
            [coverage_interface_id], policy, reason, current_user().id,
        ), "接口覆盖策略已更新")

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
            project_product_id: int | None = None,
            module_id: int | None = None,
            repository_key: str | None = None,
            branch: str | None = None,
            project_id: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分析一个项目或产品的自动化覆盖完成率、未完成模块和主要缺口。

        当用户询问“这个项目/产品完成了多少、哪些模块还没完成、接口是否已录入、
        Case 覆盖得怎么样”时使用。只读统计，不执行 Case，也不修改覆盖状态。

        范围：project_id 是项目ID（汇总其下可见产品），project_product_id 是产品ID；
        同传取交集，均不传查账号可见范围。module_id 限定模块及子模块的覆盖概览。
        repository_key/branch 限定代码基线，不传则聚合；不能将聚合结果冒充单一分支结论。

        AI 分析优先读取与页面同口径的 overview，而非顶层兼容旧指标：
        - project_scan_summary：全部叶子模块的已完整扫描/未完整扫描数量、scan_completion_rate；
          此项始终按项目/产品统计，不随 module_id 变化，纯接口盘点不算完整链路扫描。
        - project_inventory_summary：①模块接口盘点进度，inventoried_count/leaf_count与inventory_rate；
          完整模块清单生效即完成，包含inventory_only，不要求图或Case；modules.inventory_completed用于阶段一验收。
        - summary.analysis_rate：②接口业务图和场景分析进度；analyzed_interface_count、pending_analysis_count、
          analysis_gap_count、deferred_analysis_count分别为已分析/待分析/缺口/暂缓，排除项不进分母。
        - summary.binding_rate：接口录入比例；bound_count/interface_count 为正确绑定 ApiInfo 数/接口数。
        - summary.interface_coverage_rate：接口覆盖率；全部目标场景有效完成才算已覆盖；
          同时返回已覆盖、部分覆盖、未覆盖、暂不处理及已排除数量。
        - summary.automation_rate：目标 Case 场景完成率；completed_count/target_count；
          incomplete_case_count 为未完成数，deferred_count 为暂不处理数。
        - modules：分页模块进度（items/count/page/page_size，默认10条），用于定位落后模块；
          需要完整排名或缺口清单须翻完各页。父模块包含后代，禁止累加父子行重复统计。

        按①模块接口盘点、②接口分析、③场景自动化、④接口覆盖顺序报告；ApiInfo绑定另列，不合成未经定义的总完成率。
        排除接口及其场景不参与覆盖统计；暂不处理单独列示。执行通过率不等于覆盖完成率，
        执行失败不直接代表覆盖未完成。百分比为0–100，零分母返回null，不能视为100%完成。
        汇总不受明细分页影响；definitions 提供口径，scope 标明范围，仅反映账号可见数据。
        """
        result = ModuleCoverageService.analysis_metrics(
            user=current_user(), project_product_id=project_product_id, project_id=project_id,
            module_id=module_id, repository_key=repository_key, branch=branch,
        )
        rows, count, page, page_size = paginate_list(result["overview"]["modules"], page, page_size)
        result["overview"]["modules"] = {"items": rows, "count": count, "page": page, "page_size": page_size}
        return ok(result)
