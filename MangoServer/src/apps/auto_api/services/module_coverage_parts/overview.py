from collections import defaultdict

from django.db.models import F, Q

from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageApiInfoBindingStatus,
    ModuleCoverageCaseStatus,
    ModuleCoverageInterfaceStatus,
    ModuleCoverageResolutionStatus,
    ModuleCoverageScanMode,
    ModuleCoverageScanScope,
    ModuleCoverageScanStatus,
    ModuleCoverageValidity,
)


class ModuleCoverageOverviewMixin:
    @classmethod
    def is_case_automation_completed(cls, item, interface):
        return bool(
            item.status == ModuleCoverageCaseStatus.COMPLETED and item.api_case_id is not None
            and item.coverage_validity == ModuleCoverageValidity.VALID
            and cls.case_coverage_assessment(item, interface)["status"] == ModuleCoverageValidity.VALID
        )

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
        interfaces = list(interfaces.select_related("module_interface").filter(
            lifecycle_status=ModuleCoverageInterfaceStatus.ACTIVE, removed_at__isnull=True,
        ).filter(
            Q(module_interface__current_snapshot_id=F("id"))
            | Q(module_interface__isnull=True, is_current=True)
        ))
        cases = cls.active_cases(queryset=cases).select_related("current_snapshot__interface_snapshot")
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
                                      "uncovered_interface_count": 0, "deferred_interface_count": 0})
        gaps = []
        for interface in interfaces:
            if interface.module_id not in module_map:
                continue
            group = case_groups[(interface.project_product_id, interface.module_id,
                                 interface.repository_key, interface.branch, interface.source_key_hash)]
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
            incomplete = completed < len(targets) if targets else not deferred
            stats = direct[interface.module_id]
            if targets and completed == len(targets):
                stats["covered_interface_count"] += 1
            elif completed:
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
            if len(descendants[module.id]) == 1:
                project_scan_summary["leaf_count"] += 1
                project_scan_summary["scanned_count" if applied else "unscanned_count"] += 1
            if module.id not in selected:
                continue
            scope = descendants[module.id] & selected
            totals = {key: sum(direct[item][key] for item in scope) for key in direct[module.id]}
            rows.append({"id": module.id, "parent_id": module.parent_id,
                         "project_product_id": module.project_product_id,
                         "product_name": module.project_product.name,
                         "project_name": module.project_product.project.name,
                         "full_path": module.get_full_path(), "name": module.name,
                         "is_leaf": len(descendants[module.id]) == 1,
                         "scan_completed": applied is not None,
                         "latest_scan_id": relevant[0].id if relevant else None,
                         "latest_scan_status": relevant[0].status if relevant else None,
                         "applied_scan_id": applied.id if applied else None,
                         **totals,
                         "binding_rate": cls.overview_rate(totals["bound_count"], totals["interface_count"]),
                         "interface_coverage_rate": cls.overview_rate(
                             totals["covered_interface_count"], totals["interface_count"]),
                         "automation_rate": cls.overview_rate(totals["completed_count"], totals["target_count"])})
        # 父模块已包含子模块数据，总览分子分母只按直接归属计算一次。
        totals = {key: sum(direct[item][key] for item in selected if item in module_map)
                  for key in ("interface_count", "bound_count", "target_count", "completed_count",
                              "deferred_count", "incomplete_interface_count", "covered_interface_count",
                              "partial_interface_count", "uncovered_interface_count", "deferred_interface_count")}
        leaves = [row for row in rows if row["is_leaf"]]
        filtered_gaps = [row for row in gaps if row["module_id"] in selected]
        return {"modules": rows, "summary": {**totals, "module_count": len(rows),
                "leaf_count": len(leaves), "scanned_count": sum(row["scan_completed"] for row in leaves),
                "unscanned_count": sum(not row["scan_completed"] for row in leaves),
                "binding_rate": cls.overview_rate(totals["bound_count"], totals["interface_count"]),
                "interface_coverage_rate": cls.overview_rate(
                    totals["covered_interface_count"], totals["interface_count"]),
                "automation_rate": cls.overview_rate(totals["completed_count"], totals["target_count"])},
                "project_scan_summary": project_scan_summary,
                "interface_gaps": filtered_gaps[:20], "interface_gap_count": len(filtered_gaps)}

    @staticmethod
    def overview_rate(numerator, denominator):
        return round(numerator * 100 / denominator, 2) if denominator else None
