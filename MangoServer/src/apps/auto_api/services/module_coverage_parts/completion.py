import hashlib
from collections import Counter

from django.db import transaction
from django.utils import timezone

from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageCaseStatus,
    ModuleCoverageInterfaceStatus,
    ModuleCoverageScanMode,
    ModuleCoverageScanScope,
    ModuleCoverageScanStatus,
    ModuleCoverageSyncAction,
    ModuleCoverageValidity,
    ModuleCoveragePolicy,
)
from src.apps.auto_api.exceptions import (
    AutoApiError,
    QUALITY_COVERAGE_MODULE_NOT_ALLOWED,
    QUALITY_COVERAGE_INVALID_CODE_INVALID,
    QUALITY_COVERAGE_MODULE_INVALID,
)
from src.apps.auto_api.models import ApiCaseRevision
from src.apps.test_center.models import ProjectProduct
from src.apps.auto_api.models import (
    ModuleCoverageCase,
    ModuleCoverageInterfaceSnapshot,
    ModuleCoverageModuleInterface,
    ModuleCoverageScan,
)


class ModuleCoverageCompletionMixin:
    @classmethod
    @transaction.atomic
    def complete_scan(cls, scan_id: int, confirm_scope_reduction: bool = False) -> ModuleCoverageScan:
        scan = cls.get_locked_uploading_scan(scan_id)
        ProjectProduct.objects.select_for_update().get(id=scan.project_product_id)
        inventory = cls.is_inventory_scan(scan)
        cls.link_pending_case_snapshots(scan)
        validation = cls.validation(scan)
        if not validation["valid"]:
            raise AutoApiError(QUALITY_COVERAGE_MODULE_INVALID,
                               value=("；".join(validation["errors"]),),
                               )
        snapshots = list(scan.case_snapshots.select_related(
            "coverage_case__module_interface", "interface_snapshot__module_interface", "api_case", "api_case_revision",
        ))
        interface_snapshots = list(scan.interface_snapshots.select_related(
            "api_info", "api_info_revision", "module_interface",
        ))
        skipped_interface_count = 0 if inventory else sum(cls.interface_analysis_blocked(item) for item in interface_snapshots)
        if not inventory:
            interface_snapshots = [item for item in interface_snapshots if not cls.interface_analysis_blocked(item)]
        snapshots = [item for item in snapshots if not (
            (item.interface_snapshot_id and cls.interface_analysis_blocked(item.interface_snapshot))
            or cls.interface_analysis_blocked(item.coverage_case)
        )]
        if scan.scope_type == ModuleCoverageScanScope.INTERFACE:
            cls.require_interface_included(scan.target_interface)
            newer_scan_exists = ModuleCoverageModuleInterface.objects.filter(
                id=scan.target_interface.module_interface_id,
                last_seen_scan_id__gt=scan.id,
            ).exists()
        elif inventory:
            newer_relations = ModuleCoverageModuleInterface.objects.filter(
                project_product_id=scan.project_product_id,
                repository_key=scan.repository_key,
                branch=scan.branch,
                last_seen_scan_id__gt=scan.id,
            )
            if scan.module_id is not None:
                newer_relations = newer_relations.filter(
                    module_id__in=cls.module_ids(scan.module_id, scan.include_descendants),
                )
            newer_scan_exists = newer_relations.exists()
        else:
            module_ids = cls.module_ids(scan.module_id, scan.include_descendants)
            newer_scan_exists = ModuleCoverageScan.objects.filter(
                project_product_id=scan.project_product_id,
                module_id=scan.module_id,
                repository_key=scan.repository_key,
                branch=scan.branch,
                include_descendants=scan.include_descendants,
                status=ModuleCoverageScanStatus.COMPLETED,
                scope_type=ModuleCoverageScanScope.MODULE,
                id__gt=scan.id,
            ).exists()
            newer_scan_exists = newer_scan_exists or ModuleCoverageModuleInterface.objects.filter(
                project_product_id=scan.project_product_id,
                module_id__in=module_ids,
                repository_key=scan.repository_key,
                branch=scan.branch,
                last_seen_scan_id__gt=scan.id,
            ).exists()
        if newer_scan_exists:
            raise AutoApiError(QUALITY_COVERAGE_MODULE_NOT_ALLOWED)
        module_ids = cls.module_ids(scan.module_id, scan.include_descendants) if scan.module_id is not None else set()
        current_relations = ModuleCoverageModuleInterface.objects.select_for_update().filter(
            project_product_id=scan.project_product_id,
            repository_key=scan.repository_key,
            branch=scan.branch,
            lifecycle_status=ModuleCoverageInterfaceStatus.ACTIVE,
            removed_at__isnull=True,
            current_snapshot__isnull=False,
        ).filter(coverage_policy=ModuleCoveragePolicy.INCLUDED).select_related("current_snapshot")
        if scan.scope_type == ModuleCoverageScanScope.INTERFACE:
            current_relations = current_relations.filter(id=scan.target_interface.module_interface_id)
        elif scan.module_id is not None:
            current_relations = current_relations.filter(module_id__in=module_ids)
        current_relation_ids = set(current_relations.values_list("id", flat=True))
        current_scope = ModuleCoverageCase.objects.filter(
            project_product_id=scan.project_product_id,
            module_id__in=module_ids,
            repository_key=scan.repository_key,
            branch=scan.branch,
            removed_at__isnull=True,
            current_snapshot__isnull=False,
        ).exclude(module_interface__coverage_policy__in=[ModuleCoveragePolicy.DEFERRED, ModuleCoveragePolicy.EXCLUDED])
        if scan.scope_type == ModuleCoverageScanScope.INTERFACE:
            current_scope = current_scope.filter(
                module_interface_id=scan.target_interface.module_interface_id,
            )
        removed_ids: set[int] = set()
        submitted_relation_ids = {item.module_interface_id for item in interface_snapshots}
        previous_relation_ids = current_relation_ids
        removed_interface_count = 0
        if not inventory and scan.scan_mode == ModuleCoverageScanMode.FULL:
            submitted_ids = {item.coverage_case_id for item in snapshots}
            if scan.scope_type == ModuleCoverageScanScope.MODULE:
                removed_ids = set(
                    current_scope.exclude(id__in=submitted_ids).values_list("id", flat=True),
                )
            previous_total = current_scope.count()
            case_scope_reduced = (
                    scan.scope_type == ModuleCoverageScanScope.MODULE
                    and previous_total
                    and len(snapshots) < previous_total * 0.5
            )
            interface_scope_reduced = (
                    scan.scope_type == ModuleCoverageScanScope.MODULE
                    and bool(previous_relation_ids)
                    and len(submitted_relation_ids) < len(previous_relation_ids) * 0.5
            )
            if (case_scope_reduced or interface_scope_reduced) and not confirm_scope_reduction:
                raise AutoApiError(QUALITY_COVERAGE_INVALID_CODE_INVALID)
            if scan.scope_type == ModuleCoverageScanScope.MODULE:
                removed_interface_count = len(previous_relation_ids - submitted_relation_ids)

        submitted_case_ids = {item.coverage_case_id for item in snapshots}
        changed_interfaces: list[ModuleCoverageInterfaceSnapshot] = []
        for interface_snapshot in interface_snapshots:
            module_interface = interface_snapshot.module_interface
            if not inventory and cls.interface_analysis_blocked(interface_snapshot):
                module_interface.last_seen_scan = scan
                module_interface.save(update_fields=["last_seen_scan", "update_time"])
                continue
            if (inventory and module_interface.current_snapshot_id and module_interface.removed_at is None
                    and module_interface.module_id == interface_snapshot.module_id):
                # 盘点只更新发现记录，不能将旧链路的源码证据冒充本次修订的分析结果。
                module_interface.last_seen_scan = scan
                module_interface.save(update_fields=["last_seen_scan", "update_time"])
                continue
            if module_interface.current_snapshot_id != interface_snapshot.id:
                ModuleCoverageInterfaceSnapshot.objects.filter(
                    id=module_interface.current_snapshot_id,
                ).update(is_current=False)
            interface_snapshot.is_current = True
            interface_snapshot.lifecycle_status = ModuleCoverageInterfaceStatus.ACTIVE
            interface_snapshot.removed_at = None
            interface_snapshot.save(update_fields=["is_current", "lifecycle_status", "removed_at"])
            module_interface.source_key = interface_snapshot.source_key
            module_interface.module_id = interface_snapshot.module_id
            module_interface.api_info = interface_snapshot.api_info
            module_interface.api_info_revision = interface_snapshot.api_info_revision
            module_interface.api_info_binding_status = interface_snapshot.api_info_binding_status
            module_interface.api_info_binding_reason = interface_snapshot.api_info_binding_reason
            module_interface.current_snapshot = interface_snapshot
            module_interface.last_seen_scan = scan
            module_interface.lifecycle_status = ModuleCoverageInterfaceStatus.ACTIVE
            module_interface.removed_at = None
            module_interface.save(update_fields=[
                "source_key", "module", "api_info", "api_info_revision", "api_info_binding_status",
                "api_info_binding_reason", "current_snapshot", "last_seen_scan",
                "lifecycle_status", "removed_at", "update_time",
            ])
            if not inventory and interface_snapshot.sync_action == ModuleCoverageSyncAction.UPDATED:
                changed_interfaces.append(interface_snapshot)

        applied_interfaces = {interface.id: interface for interface in interface_snapshots}
        for snapshot in snapshots:
            if snapshot.interface_snapshot_id in applied_interfaces:
                snapshot.interface_snapshot = applied_interfaces[snapshot.interface_snapshot_id]
            if ((snapshot.interface_snapshot_id and cls.interface_analysis_blocked(snapshot.interface_snapshot))
                    or cls.interface_analysis_blocked(snapshot.coverage_case)):
                continue
            payload = snapshot.payload
            item = snapshot.coverage_case
            item.interface_source_key = payload["interface_source_key"]
            item.interface_source_key_hash = hashlib.sha256(
                payload["interface_source_key"].encode("utf-8"),
            ).hexdigest()
            item.module_interface = (
                snapshot.interface_snapshot.module_interface
                if snapshot.interface_snapshot_id else None
            )
            item.name = payload["case_title"]
            item.interface_name = payload["interface_name"]
            item.method = payload["method"].upper()
            item.url = payload["url"]
            item.test_ownership = payload["test_ownership"]
            item.scenario_layer = payload["scenario_layer"]
            item.scenario_type = payload["scenario_type"]
            item.scenario_tags = payload["scenario_tags"]
            item.status = payload["current_status"]
            item.execution_result = payload["execution_result"]
            item.api_case = snapshot.api_case
            item.api_case_revision = snapshot.api_case_revision
            if snapshot.api_case_id:
                latest_result, executed_revision_id = cls.latest_api_case_execution(
                    snapshot.api_case_id,
                )
                if latest_result:
                    item.execution_result = latest_result
                if executed_revision_id:
                    item.api_case_revision = ApiCaseRevision.objects.filter(
                        id=executed_revision_id,
                        api_case_id=snapshot.api_case_id,
                    ).first() or item.api_case_revision
            item.last_reviewed_scan = scan
            item.last_seen_scan = scan
            item.current_snapshot = snapshot
            item.removed_at = None
            assessment = cls.case_coverage_assessment(item, snapshot.interface_snapshot)
            item.coverage_validity = assessment["status"]
            item.coverage_validity_reason = assessment["reason"]
            item.save(update_fields=[
                "interface_source_key", "interface_source_key_hash", "name",
                "interface_name", "method", "url", "test_ownership",
                "scenario_layer", "scenario_type", "scenario_tags",
                "status", "execution_result", "api_case",
                "api_case_revision", "coverage_validity",
                "coverage_validity_reason", "last_reviewed_scan", "last_seen_scan",
                "current_snapshot", "module_interface", "removed_at", "update_time",
            ])

        if scan.scan_mode == ModuleCoverageScanMode.INCREMENTAL:
            for interface_snapshot in changed_interfaces:
                omitted_cases = ModuleCoverageCase.objects.filter(
                    module_interface=interface_snapshot.module_interface,
                    removed_at__isnull=True,
                    current_snapshot__isnull=False,
                ).exclude(id__in=submitted_case_ids).select_related("current_snapshot")
                for item in omitted_cases:
                    payload = item.current_snapshot.payload or {}
                    missing_nodes = sorted(
                        set(payload.get("covered_node_ids", [])) - set(interface_snapshot.node_ids),
                    )
                    missing_branches = sorted(
                        set(payload.get("covered_branch_ids", [])) - set(interface_snapshot.branch_ids),
                    )
                    if missing_nodes or missing_branches:
                        item.coverage_validity = ModuleCoverageValidity.INVALID
                        item.coverage_validity_reason = (
                            f"流程节点/分支已消失：nodes={missing_nodes}, branches={missing_branches}"
                        )
                    else:
                        item.coverage_validity = ModuleCoverageValidity.PENDING_REVIEW
                        item.coverage_validity_reason = "接口流程已变更，需重新确认Case覆盖路径"
                    item.save(update_fields=[
                        "coverage_validity", "coverage_validity_reason", "update_time",
                    ])

        if (not inventory and scan.scan_mode == ModuleCoverageScanMode.FULL
                and scan.scope_type == ModuleCoverageScanScope.MODULE):
            removed_relation_ids = previous_relation_ids - submitted_relation_ids
            if removed_relation_ids:
                removal_time = timezone.now()
                for relation in list(current_relations.filter(id__in=removed_relation_ids)):
                    previous = relation.current_snapshot
                    if previous is None:
                        continue
                    previous.is_current = False
                    previous.save(update_fields=["is_current"])
                    removed_snapshot = ModuleCoverageInterfaceSnapshot.objects.create(
                        scan=scan,
                        project_product=previous.project_product,
                        module=previous.module,
                        module_interface=relation,
                        repository_key=previous.repository_key,
                        branch=previous.branch,
                        source_key=previous.source_key,
                        source_key_hash=previous.source_key_hash,
                        interface_name=previous.interface_name,
                        method=previous.method,
                        url=previous.url,
                        mermaid=previous.mermaid,
                        node_ids=previous.node_ids,
                        branch_ids=previous.branch_ids,
                        resolution_status=previous.resolution_status,
                        resolution_reason=previous.resolution_reason,
                        gap_reason=previous.gap_reason,
                        next_action=previous.next_action,
                        resumption_point=previous.resumption_point,
                        api_info=previous.api_info,
                        api_info_revision=previous.api_info_revision,
                        api_info_binding_status=previous.api_info_binding_status,
                        api_info_binding_reason=previous.api_info_binding_reason,
                        content_hash=previous.content_hash,
                        submitted_hash=cls.canonical_hash({
                            "removed_from_snapshot_id": previous.id,
                            "scan_id": scan.id,
                        }),
                        sync_action=ModuleCoverageSyncAction.REMOVED,
                        lifecycle_status=ModuleCoverageInterfaceStatus.REMOVED,
                        is_current=True,
                        removed_at=removal_time,
                    )
                    relation.current_snapshot = removed_snapshot
                    relation.last_seen_scan = scan
                    relation.lifecycle_status = ModuleCoverageInterfaceStatus.REMOVED
                    relation.removed_at = removal_time
                    relation.save(update_fields=[
                        "current_snapshot", "last_seen_scan", "lifecycle_status",
                        "removed_at", "update_time",
                    ])
        if removed_ids:
            ModuleCoverageCase.objects.filter(id__in=removed_ids).update(
                status=ModuleCoverageCaseStatus.REMOVED,
                removed_at=timezone.now(),
            )
        actions = Counter(item.sync_action for item in snapshots)
        interface_actions = Counter(item.sync_action for item in interface_snapshots)
        scan.summary = {
            "applied": True,
            "inventory_only": inventory,
            "case_count": len(snapshots),
            "created": actions[ModuleCoverageSyncAction.CREATED],
            "updated": actions[ModuleCoverageSyncAction.UPDATED],
            "unchanged": actions[ModuleCoverageSyncAction.UNCHANGED],
            "removed": len(removed_ids),
            "interface_count": len(interface_snapshots),
            "skipped_interface_count": skipped_interface_count,
            "interface_created": interface_actions[ModuleCoverageSyncAction.CREATED],
            "interface_updated": interface_actions[ModuleCoverageSyncAction.UPDATED],
            "interface_unchanged": interface_actions[ModuleCoverageSyncAction.UNCHANGED],
            "interface_removed": removed_interface_count,
            "resolved_interface_count": validation["resolved_interface_count"],
            "placeholder_interface_count": validation["placeholder_interface_count"],
            "gap_interface_count": validation["gap_interface_count"],
            "interface_resolution_rate": validation["interface_resolution_rate"],
        }
        scan.status = ModuleCoverageScanStatus.COMPLETED
        scan.finished_at = timezone.now()
        scan.save(update_fields=["summary", "status", "finished_at", "update_time"])
        return scan
