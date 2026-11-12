from collections import defaultdict

from django.db.models import F, Q

from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.test_center.services.project.product_module import ProductModuleService
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService

from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageApiInfoBindingStatus,
    ModuleCoverageCaseStatus,
    ModuleCoverageInterfaceStatus,
    ModuleCoverageResolutionStatus,
    ModuleCoverageScanMode,
    ModuleCoverageScanScope,
    ModuleCoverageScanStatus,
    ModuleCoverageValidity,
    ModuleCoverageAnalysisStatus,
    ModuleCoveragePolicy,
    ModuleCoverageInterfaceCoverageStatus,
)


class ModuleCoverageOverviewMixin:
    @classmethod
    def analysis_metrics(cls, *, user, project_product_id=None, project_id=None,
                         module_id=None, repository_key=None, branch=None):
        products = TestCenterQuerySelector.project_product()
        if not (PermissionMenuService.is_effective_super_admin(user)
                or ProjectProductScopeService.can_view_all_project_data(user)):
            products = products.filter(id__in=ProjectProductScopeService.project_product_ids_for_user(user))
        if project_id is not None:
            products = products.filter(project_id=project_id)
        if project_product_id is not None:
            products = products.filter(id=project_product_id)
        product_ids = list(products.values_list("id", flat=True))
        modules = ProductModuleService.with_full_paths(
            TestCenterQuerySelector.product_module().filter(project_product_id__in=product_ids).order_by("id"),
        )
        interfaces = ApiQuerySelector.module_coverage_interface_snapshot().filter(project_product_id__in=product_ids)
        cases = ApiQuerySelector.module_coverage_case().filter(project_product_id__in=product_ids)
        scans = ApiQuerySelector.module_coverage_scan().filter(project_product_id__in=product_ids)
        selected_ids = None
        if module_id is not None:
            # 概览按整个模块子树统计，祖先扫描仍保留用于判断完整扫描基线。
            parents = dict(modules.values_list("id", "parent_id"))
            selected_ids = {module_id} if module_id in parents else set()
            pending = list(selected_ids)
            while pending:
                parent = pending.pop()
                for identity, parent_id in parents.items():
                    if parent_id == parent and identity not in selected_ids:
                        selected_ids.add(identity)
                        pending.append(identity)
        overview = cls.overview(
            modules=modules, interfaces=interfaces, cases=cases, scans=scans,
            repository_key=repository_key, branch=branch,
            # overview 的空集合表示全部；不存在或越权的模块必须明确返回空范围。
            module_ids=selected_ids if selected_ids else ([-1] if module_id is not None else None),
        )
        legacy = cls.metrics(project_product_id, module_id, repository_key, branch,
                             case_queryset=cases, scan_queryset=scans, interface_queryset=interfaces)
        summary = overview["summary"]
        summary["unbound_count"] = summary["interface_count"] - summary["bound_count"]
        summary["incomplete_case_count"] = summary["target_count"] - summary["completed_count"]
        summary["scenario_count"] = summary["target_count"] + summary["deferred_count"]
        scan_summary = overview["project_scan_summary"]
        scan_summary["scan_completion_rate"] = cls.overview_rate(
            scan_summary["scanned_count"], scan_summary["leaf_count"],
        )
        return {**legacy, "overview": {
            "scope": {"project_id": project_id, "project_product_id": project_product_id,
                      "module_id": module_id, "repository_key": repository_key, "branch": branch,
                      "visible_product_ids": product_ids, "authorized_products_only": True},
            "summary": summary, "project_scan_summary": scan_summary,
            "project_inventory_summary": overview["project_inventory_summary"],
            "modules": overview["modules"],
            "definitions": {
                "module_scan": "所选项目/产品/模块范围内的叶子模块；仅已生效的完整链路扫描计为完成，随模块筛选变化",
                "module_inventory": "第一阶段：完整模块接口清单已生效；包含纯盘点，零接口模块须有完整盘点证据；多仓库分别核实",
                "interface_analysis": "第二阶段：当前生效业务图和场景分析完整且修订匹配才算已分析；版本差异单列analysis_review_count，实际分析不完整列analysis_gap_count；排除项不计分母，暂缓单列；ApiInfo绑定不是分析完成",
                "interface_entry": "bound_count / interface_count；已正确绑定 ApiInfo 的当前有效接口；排除接口不计入",
                "interface_coverage": "covered_interface_count / interface_count；当前分析完成且全部目标场景有效完成才算覆盖；分析未完成但已有成果计为部分覆盖，保留Case和绑定；排除接口及其场景不计入",
                "automation": "completed_count / target_count；暂不处理单独统计；执行失败不影响有效覆盖完成状态",
                "rates": "百分比为 0–100；分母为零时为 null，不代表已完成；overview 为页面概览口径，顶层保留旧指标",
                "scope": "不传仓库或分支时汇总所选范围全部基线；项目统计仅含当前账号可见产品",
                "modules": "父模块已包含后代；模块行不可直接累加，请使用 summary；scan_completed 表示完整链路扫描而非纯接口盘点",
            },
        }}

    @classmethod
    def is_case_automation_completed(cls, item, interface):
        return bool(
            item.status == ModuleCoverageCaseStatus.COMPLETED and item.api_case_id is not None
            and item.coverage_validity == ModuleCoverageValidity.VALID
            and cls.case_coverage_assessment(item, interface)["status"] == ModuleCoverageValidity.VALID
        )

    @classmethod
    def interface_analysis_status(cls, interface, scenario_count, total_scenarios=None):
        return cls.interface_analysis_assessment(interface, scenario_count, total_scenarios)["analysis_status"]

    @classmethod
    def interface_analysis_assessment(cls, interface, scenario_count, total_scenarios=None):
        relation = getattr(interface, "module_interface", None)
        policy = getattr(relation, "coverage_policy", ModuleCoveragePolicy.INCLUDED)
        analysis_scan = interface.scan
        latest_scan = getattr(relation, "last_seen_scan", None)

        def result(status, reason):
            return {"analysis_status": status, "analysis_reason": reason,
                    "analysis_commit_sha": analysis_scan.commit_sha,
                    "latest_inventory_commit_sha": latest_scan.commit_sha if latest_scan else analysis_scan.commit_sha}

        if policy == ModuleCoveragePolicy.EXCLUDED:
            return result(ModuleCoverageAnalysisStatus.EXCLUDED, getattr(relation, "coverage_reason", "") or "已排除当前覆盖范围")
        if policy == ModuleCoveragePolicy.DEFERRED:
            return result(ModuleCoverageAnalysisStatus.DEFERRED, getattr(relation, "coverage_reason", "") or "已暂缓分析")
        if cls.is_inventory_scan(analysis_scan) or not interface.mermaid:
            return result(ModuleCoverageAnalysisStatus.PENDING, "仅完成接口盘点或尚无业务全景图")
        if (latest_scan and latest_scan.status == ModuleCoverageScanStatus.COMPLETED
                and latest_scan.commit_sha != analysis_scan.commit_sha):
            return result(ModuleCoverageAnalysisStatus.REVIEW,
                          f"已有分析版本 {analysis_scan.commit_sha} 与最新盘点版本 {latest_scan.commit_sha} 不同，需核实相关代码及依赖变化")
        if analysis_scan.status != ModuleCoverageScanStatus.COMPLETED:
            return result(ModuleCoverageAnalysisStatus.GAP, "分析扫描尚未完成并生效")
        if interface.gap_reason:
            return result(ModuleCoverageAnalysisStatus.GAP, interface.gap_reason)
        resolution = cls.interface_resolution(interface.mermaid, interface.node_ids)
        if resolution["status"] != ModuleCoverageResolutionStatus.RESOLVED:
            return result(ModuleCoverageAnalysisStatus.GAP, resolution["reason"] or "业务调用链尚未解析完整")
        if total_scenarios and scenario_count != total_scenarios:
            return result(ModuleCoverageAnalysisStatus.GAP, f"已登记 {total_scenarios} 个场景，其中 {scenario_count} 个分析有效，需补全或复核其余场景")
        if not scenario_count:
            return result(ModuleCoverageAnalysisStatus.PENDING, "已有全景图，但尚无有效场景分析")
        return result(ModuleCoverageAnalysisStatus.COMPLETED, "当前版本的全景图与已登记场景分析完整有效；不代表自动化已完成")

    @classmethod
    def case_analysis_complete(cls, item, interface):
        return (item.current_snapshot.scan.status == ModuleCoverageScanStatus.COMPLETED
                and cls.case_coverage_assessment(item, interface)["status"] == ModuleCoverageValidity.VALID)

    @classmethod
    def overview(cls, *, modules, interfaces, cases, scans, repository_key=None, branch=None, module_ids=None):
        # 全部数据按权限裁剪后批量读取，不能按每个模块重复查询。
        module_rows = list(modules.select_related("parent__parent", "project_product__project"))
        module_map = {item.id: item for item in module_rows}
        for field, value in (("repository_key", repository_key), ("branch", branch)):
            if value:
                interfaces = interfaces.filter(**{field: value})
                cases = cases.filter(**{field: value})
                scans = scans.filter(**{field: value})
        interfaces = list(interfaces.select_related("module_interface__last_seen_scan", "scan").filter(
            lifecycle_status=ModuleCoverageInterfaceStatus.ACTIVE, removed_at__isnull=True,
        ).filter(
            Q(module_interface__current_snapshot_id=F("id"))
            | Q(module_interface__isnull=True, is_current=True)
        ))
        cases = cls.active_cases(queryset=cases).select_related("current_snapshot__interface_snapshot", "current_snapshot__scan")
        case_groups = defaultdict(list)
        for item in cases:
            case_groups[(item.project_product_id, item.module_id, item.repository_key,
                         item.branch, item.interface_source_key_hash)].append(item)
        scan_rows = list(scans.order_by("-id"))
        scan_groups = defaultdict(list)
        for item in scan_rows:
            scan_groups[(item.project_product_id, item.module_id)].append(item)
        direct = defaultdict(lambda: {"interface_count": 0, "bound_count": 0, "target_count": 0,
                                      "completed_count": 0, "deferred_count": 0,
                                      "incomplete_interface_count": 0,
                                      "covered_interface_count": 0, "partial_interface_count": 0,
                                      "uncovered_interface_count": 0, "deferred_interface_count": 0,
                                      "excluded_interface_count": 0,
                                      "analyzed_interface_count": 0, "pending_analysis_count": 0,
                                      "analysis_gap_count": 0, "analysis_review_count": 0, "deferred_analysis_count": 0})
        gaps = []
        for interface in interfaces:
            if interface.module_id not in module_map:
                continue
            if cls.interface_is_excluded(interface):
                direct[interface.module_id]["excluded_interface_count"] += 1
                continue
            group = case_groups[(interface.project_product_id, interface.module_id,
                                 interface.repository_key, interface.branch, interface.source_key_hash)]
            scenario_count = sum(cls.case_analysis_complete(item, interface) for item in group)
            analysis_status = cls.interface_analysis_status(interface, scenario_count, len(group))
            for status, key in (
                (ModuleCoverageAnalysisStatus.COMPLETED, "analyzed_interface_count"),
                (ModuleCoverageAnalysisStatus.PENDING, "pending_analysis_count"),
                (ModuleCoverageAnalysisStatus.GAP, "analysis_gap_count"),
                (ModuleCoverageAnalysisStatus.REVIEW, "analysis_review_count"),
                (ModuleCoverageAnalysisStatus.DEFERRED, "deferred_analysis_count"),
            ):
                direct[interface.module_id][key] += int(analysis_status == status)
            targets = [item for item in group if item.status in (
                ModuleCoverageCaseStatus.PENDING_CREATE, ModuleCoverageCaseStatus.COMPLETED,
            )]
            resolved = cls.interface_resolution(interface.mermaid, interface.node_ids)["status"] == (
                ModuleCoverageResolutionStatus.RESOLVED
            )
            completed = sum(
                resolved and cls.is_case_automation_completed(item, interface)
                for item in targets
            )
            deferred = sum(item.status == ModuleCoverageCaseStatus.DEFERRED for item in group)
            bound = interface.api_info_id is not None and interface.api_info_binding_status == (
                ModuleCoverageApiInfoBindingStatus.BOUND
            )
            # 暂不处理不属于自动化目标；没有任何场景才视为待补场景。
            coverage_status = cls.interface_coverage_status(
                interface, len(targets), completed, deferred, analysis_status=analysis_status,
            )
            incomplete = coverage_status not in (
                ModuleCoverageInterfaceCoverageStatus.COVERED, ModuleCoverageInterfaceCoverageStatus.DEFERRED,
            )
            stats = direct[interface.module_id]
            if coverage_status == ModuleCoverageInterfaceCoverageStatus.COVERED:
                stats["covered_interface_count"] += 1
            elif coverage_status == ModuleCoverageInterfaceCoverageStatus.PARTIAL:
                stats["partial_interface_count"] += 1
            elif not targets and deferred:
                stats["deferred_interface_count"] += 1
            else:
                stats["uncovered_interface_count"] += 1
            for key, value in (("interface_count", 1), ("bound_count", int(bound)),
                               ("target_count", len(targets)), ("completed_count", completed),
                               ("deferred_count", deferred), ("incomplete_interface_count", int(incomplete))):
                stats[key] += value
            if not bound or incomplete:
                module = module_map[interface.module_id]
                gaps.append({"id": interface.id, "module_id": module.id,
                             "project_product_id": module.project_product_id,
                             "module_path": module.get_full_path(), "name": interface.interface_name,
                             "method": interface.method, "url": interface.url,
                             "bound": bound, "target_count": len(targets), "completed_count": completed,
                             "deferred_count": deferred, "incomplete": incomplete})

        def ancestors(module):
            result, visited = [], set()
            while module and module.id not in visited:
                visited.add(module.id)
                result.append(module.id)
                module = module_map.get(module.parent_id)
            return result

        descendants = defaultdict(set)
        for item in module_rows:
            for parent_id in ancestors(item):
                descendants[parent_id].add(item.id)
        selected = set(module_ids) if module_ids else set(module_map)
        rows = []
        project_scan_summary = {"leaf_count": 0, "scanned_count": 0, "unscanned_count": 0}
        project_inventory_summary = {"leaf_count": 0, "inventoried_count": 0, "uninventoried_count": 0}
        for module in module_rows:
            relevant = sorted(
                (scan for ancestor_id in ancestors(module)
                 for scan in scan_groups[(module.project_product_id, ancestor_id)]
                 if ancestor_id == module.id or scan.include_descendants),
                key=lambda scan: scan.id, reverse=True,
            )
            # 单接口、增量或未生效扫描不能证明整个模块已完整扫描。
            applied = next((scan for scan in relevant if scan.status == ModuleCoverageScanStatus.COMPLETED
                            and scan.scan_mode == ModuleCoverageScanMode.FULL
                            and scan.scope_type == ModuleCoverageScanScope.MODULE
                            and not cls.is_inventory_scan(scan)), None)
            # 每个已知仓库/分支均须有完整模块基线；单接口或部分仓库上传不能刷满模块进度。
            source_groups = defaultdict(list)
            for scan in relevant:
                source_groups[(scan.repository_key, scan.branch)].append(scan)
            inventory_scans = []
            for source_scans in source_groups.values():
                baseline = next((scan for scan in source_scans
                                 if scan.status == ModuleCoverageScanStatus.COMPLETED
                                 and scan.scan_mode == ModuleCoverageScanMode.FULL
                                 and scan.scope_type == ModuleCoverageScanScope.MODULE), None)
                latest_applied = next((scan for scan in source_scans
                                       if scan.status == ModuleCoverageScanStatus.COMPLETED), None)
                if baseline and latest_applied and baseline.commit_sha == latest_applied.commit_sha:
                    inventory_scans.append(baseline)
            inventoried = bool(source_groups) and len(inventory_scans) == len(source_groups)
            if module.id not in selected:
                continue
            if len(descendants[module.id]) == 1:
                project_scan_summary["leaf_count"] += 1
                project_scan_summary["scanned_count" if applied else "unscanned_count"] += 1
                project_inventory_summary["leaf_count"] += 1
                project_inventory_summary["inventoried_count" if inventoried else "uninventoried_count"] += 1
            scope = descendants[module.id] & selected
            totals = {key: sum(direct[item][key] for item in scope) for key in direct[module.id]}
            rows.append({"id": module.id, "parent_id": module.parent_id,
                         "project_product_id": module.project_product_id,
                         "product_name": module.project_product.name,
                         "project_name": module.project_product.project.name,
                         "full_path": module.get_full_path(), "name": module.name,
                         "is_leaf": len(descendants[module.id]) == 1,
                         "scan_completed": applied is not None,
                         "inventory_completed": inventoried,
                         "inventory_scan_ids": [scan.id for scan in inventory_scans],
                         "latest_scan_id": relevant[0].id if relevant else None,
                         "latest_scan_status": relevant[0].status if relevant else None,
                         "applied_scan_id": applied.id if applied else None,
                         **totals,
                         "analysis_rate": cls.overview_rate(totals["analyzed_interface_count"], totals["interface_count"]),
                         "binding_rate": cls.overview_rate(totals["bound_count"], totals["interface_count"]),
                         "interface_coverage_rate": cls.overview_rate(
                             totals["covered_interface_count"], totals["interface_count"]),
                         "automation_rate": cls.overview_rate(totals["completed_count"], totals["target_count"])})
        # 父模块已包含子模块数据，总览分子分母只按直接归属计算一次。
        totals = {key: sum(direct[item][key] for item in selected if item in module_map)
                  for key in ("interface_count", "bound_count", "target_count", "completed_count",
                              "deferred_count", "incomplete_interface_count", "covered_interface_count",
                              "partial_interface_count", "uncovered_interface_count", "deferred_interface_count",
                              "excluded_interface_count")}
        for key in ("analyzed_interface_count", "pending_analysis_count", "analysis_gap_count", "analysis_review_count", "deferred_analysis_count"):
            totals[key] = sum(direct[item][key] for item in selected if item in module_map)
        leaves = [row for row in rows if row["is_leaf"]]
        filtered_gaps = [row for row in gaps if row["module_id"] in selected]
        return {"modules": rows, "summary": {**totals, "module_count": len(rows),
                "leaf_count": len(leaves), "scanned_count": sum(row["scan_completed"] for row in leaves),
                "unscanned_count": sum(not row["scan_completed"] for row in leaves),
                "inventoried_count": sum(row["inventory_completed"] for row in leaves),
                "uninventoried_count": sum(not row["inventory_completed"] for row in leaves),
                "analysis_rate": cls.overview_rate(totals["analyzed_interface_count"], totals["interface_count"]),
                "binding_rate": cls.overview_rate(totals["bound_count"], totals["interface_count"]),
                "interface_coverage_rate": cls.overview_rate(
                    totals["covered_interface_count"], totals["interface_count"]),
                "automation_rate": cls.overview_rate(totals["completed_count"], totals["target_count"])},
                "project_scan_summary": project_scan_summary,
                "project_inventory_summary": {**project_inventory_summary, "inventory_rate": cls.overview_rate(
                    project_inventory_summary["inventoried_count"], project_inventory_summary["leaf_count"])},
                "interface_gaps": filtered_gaps[:20], "interface_gap_count": len(filtered_gaps)}

    @staticmethod
    def overview_rate(numerator, denominator):
        return round(numerator * 100 / denominator, 2) if denominator else None
