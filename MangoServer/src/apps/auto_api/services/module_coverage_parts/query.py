from collections import defaultdict

from django.db.models import Count, F, Min, Q

from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageApiInfoBindingStatus,
    ModuleCoverageCaseStatus,
    ModuleCoverageExecutionResult,
    ModuleCoverageInterfaceStatus,
    ModuleCoverageResolutionStatus,
    ModuleCoverageScanStatus,
    ModuleCoverageValidity,
    ModuleCoveragePolicy,
    ModuleCoverageInterfaceCoverageStatus,
    ModuleCoverageSyncAction,
    ModuleCoverageAnalysisStatus,
)
from src.apps.auto_api.models import (
    ModuleCoverageCase,
    ModuleCoverageInterfaceSnapshot,
    ModuleCoverageScan,
)


class ModuleCoverageQueryMixin:
    @staticmethod
    def active_cases(
            project_product_id: int | None = None,
            module_id: int | None = None,
            repository_key: str | None = None,
            branch: str | None = None,
            queryset=None,
            include_excluded=False,
    ):
        queryset = (queryset if queryset is not None else ModuleCoverageCase.objects.all()).filter(
            removed_at__isnull=True,
            current_snapshot__isnull=False,
        )
        if not include_excluded:
            queryset = queryset.filter(~Q(module_interface__coverage_policy=ModuleCoveragePolicy.EXCLUDED))
        if project_product_id:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id:
            queryset = queryset.filter(module_id=module_id)
        if repository_key:
            queryset = queryset.filter(repository_key=repository_key)
        if branch:
            queryset = queryset.filter(branch=branch)
        return queryset

    @classmethod
    def interface_page(
            cls,
            queryset,
            page: int = 1,
            page_size: int = 20,
            include_removed: bool = False,
            resolution_status: str | None = None,
            coverage_policy: str | None = None,
            resolution_statuses: list[str] | None = None,
            coverage_statuses: list[str] | None = None,
            methods: list[str] | None = None,
            sync_actions: list[str] | None = None,
            coverage_reason: str | None = None,
            api_info_id: int | None = None,
            analysis_statuses: list[str] | None = None,
    ) -> dict:
        page = max(1, int(page))
        page_size = min(100, max(1, int(page_size)))
        resolution_statuses = resolution_statuses or ([resolution_status] if resolution_status else [])
        for values, choices, field in (
            (resolution_statuses, ModuleCoverageResolutionStatus, "resolution_status"),
            (coverage_statuses or [], ModuleCoverageInterfaceCoverageStatus, "coverage_status"),
            (sync_actions or [], ModuleCoverageSyncAction, "sync_action"),
            (analysis_statuses or [], ModuleCoverageAnalysisStatus, "analysis_status"),
        ):
            for value in values:
                cls.validate_choice(field, value, choices)
        if methods:
            queryset = queryset.filter(method__in=methods)
        if sync_actions:
            queryset = queryset.filter(sync_action__in=sync_actions)
        if coverage_reason:
            queryset = queryset.filter(module_interface__coverage_reason__icontains=coverage_reason)
        if api_info_id is not None:
            queryset = queryset.filter(api_info_id=api_info_id)
        queryset = queryset.filter(
            Q(module_interface__current_snapshot_id=F("id"))
            | Q(module_interface__isnull=True, is_current=True)
        )
        if coverage_policy:
            cls.validate_choice("coverage_policy", coverage_policy, ModuleCoveragePolicy)
            policy_scope = Q(module_interface__coverage_policy=coverage_policy)
            if coverage_policy == ModuleCoveragePolicy.INCLUDED:
                policy_scope |= Q(module_interface__isnull=True)
            queryset = queryset.filter(policy_scope)
        if not include_removed:
            queryset = queryset.filter(
                lifecycle_status=ModuleCoverageInterfaceStatus.ACTIVE,
                removed_at__isnull=True,
            )
        queryset = queryset.order_by(
            "project_product_id", "module_id", "method", "url", "id",
        )
        queryset = queryset.select_related("scan", "module_interface__last_seen_scan")
        if resolution_statuses or coverage_statuses or analysis_statuses:
            matched_interfaces = [
                item for item in queryset
                if not resolution_statuses or cls.interface_resolution(item.mermaid, item.node_ids)["status"]
                   in resolution_statuses
            ]
            count = len(matched_interfaces)
            interfaces = matched_interfaces if coverage_statuses or analysis_statuses else matched_interfaces[(page - 1) * page_size:page * page_size]
        else:
            count = queryset.count()
            interfaces = list(queryset[(page - 1) * page_size:page * page_size])
        case_group_fields = (
            "project_product_id", "module_id", "repository_key", "branch",
            "interface_source_key_hash",
        )
        case_scope = Q(pk__in=[])
        identity_scope = Q(pk__in=[])
        for item in interfaces:
            case_scope |= Q(
                project_product_id=item.project_product_id,
                module_id=item.module_id,
                repository_key=item.repository_key,
                branch=item.branch,
                interface_source_key_hash=item.source_key_hash,
            )
            identity_scope |= Q(
                project_product_id=item.project_product_id,
                module_id=item.module_id,
                repository_key=item.repository_key,
                branch=item.branch,
                source_key_hash=item.source_key_hash,
            )
        case_stats = {
            tuple(row[field] for field in case_group_fields): row
            for row in cls.active_cases(include_excluded=True).filter(case_scope).values(*case_group_fields).annotate(
                case_count=Count("id"),
                target_case_count=Count(
                    "id",
                    filter=Q(status__in=[
                        ModuleCoverageCaseStatus.PENDING_CREATE,
                        ModuleCoverageCaseStatus.COMPLETED,
                    ]),
                ),
                completed_case_count=Count(
                    "id",
                    filter=Q(
                        status=ModuleCoverageCaseStatus.COMPLETED,
                        api_case__isnull=False,
                    ),
                ),
                effective_completed_case_count=Count(
                    "id",
                    filter=Q(
                        status=ModuleCoverageCaseStatus.COMPLETED,
                        api_case__isnull=False,
                        coverage_validity=ModuleCoverageValidity.VALID,
                        current_snapshot__payload__has_keys=cls.REQUIRED_CURRENT_CASE_PAYLOAD_KEYS,
                    ),
                ),
                deferred_case_count=Count(
                    "id",
                    filter=Q(status=ModuleCoverageCaseStatus.DEFERRED),
                ),
                api_case_count=Count("api_case_id", distinct=True),
                valid_case_count=Count(
                    "id", filter=Q(coverage_validity=ModuleCoverageValidity.VALID),
                ),
                effective_valid_case_count=Count(
                    "id",
                    filter=Q(
                        coverage_validity=ModuleCoverageValidity.VALID,
                        current_snapshot__payload__has_keys=cls.REQUIRED_CURRENT_CASE_PAYLOAD_KEYS,
                    ),
                ),
                pending_review_case_count=Count(
                    "id", filter=Q(coverage_validity=ModuleCoverageValidity.PENDING_REVIEW),
                ),
                invalid_case_count=Count(
                    "id", filter=Q(coverage_validity=ModuleCoverageValidity.INVALID),
                ),
            )
        }
        first_scan_ids = {
            (
                row["project_product_id"], row["module_id"], row["repository_key"],
                row["branch"], row["source_key_hash"],
            ): row["first_scan_id"]
            for row in ModuleCoverageInterfaceSnapshot.objects.filter(identity_scope).values(
                "project_product_id", "module_id", "repository_key", "branch", "source_key_hash",
            ).annotate(first_scan_id=Min("scan_id"))
        }
        analysis_cases = defaultdict(list)
        for case in cls.active_cases(include_excluded=True).filter(case_scope).select_related(
                "current_snapshot__scan", "current_snapshot__interface_snapshot"):
            analysis_cases[tuple(getattr(case, field) for field in case_group_fields)].append(case)
        rows = []
        for item in interfaces:
            identity = (
                item.project_product_id, item.module_id, item.repository_key,
                item.branch, item.source_key_hash,
            )
            stats = case_stats.get(identity, {})
            case_count = stats.get("case_count", 0)
            target = stats.get("target_case_count", 0)
            completed = stats.get("completed_case_count", 0)
            resolution = cls.interface_resolution(item.mermaid, item.node_ids)
            effective_completed = (
                stats.get("effective_completed_case_count", 0)
                if resolution["status"] == ModuleCoverageResolutionStatus.RESOLVED
                else 0
            )
            effective_valid = (
                stats.get("effective_valid_case_count", 0)
                if resolution["status"] == ModuleCoverageResolutionStatus.RESOLVED
                else 0
            )
            effective_pending_review = (
                stats.get("pending_review_case_count", 0)
                if resolution["status"] == ModuleCoverageResolutionStatus.RESOLVED
                else 0
            )
            effective_invalid = max(
                case_count - effective_valid - effective_pending_review,
                0,
            )
            deferred = stats.get("deferred_case_count", 0)
            row = {
                "id": item.id,
                "key": item.id,
                "project_product": item.project_product,
                "module": item.module,
                "repository_key": item.repository_key,
                "branch": item.branch,
                "interface_source_key": item.source_key,
                "interface_source_key_hash": item.source_key_hash,
                "interface_name": item.interface_name,
                "method": item.method,
                "url": item.url,
                "case_count": case_count,
                "target_case_count": target,
                "completed_case_count": completed,
                "effective_completed_case_count": effective_completed,
                "deferred_case_count": deferred,
                "api_case_count": stats.get("api_case_count", 0),
                "valid_case_count": stats.get("valid_case_count", 0),
                "effective_valid_case_count": effective_valid,
                "pending_review_case_count": stats.get("pending_review_case_count", 0),
                "invalid_case_count": stats.get("invalid_case_count", 0),
                "effective_pending_review_case_count": effective_pending_review,
                "effective_invalid_case_count": effective_invalid,
                "first_scan_id": first_scan_ids.get(identity),
                "latest_scan_id": item.scan_id,
                "latest_commit_sha": item.scan.commit_sha,
                "sync_action": item.sync_action,
                "update_time": item.create_time,
                "resolution_status": resolution["status"],
                "analysis_status": cls.interface_analysis_status(
                    item, sum(cls.case_analysis_complete(case, item) for case in analysis_cases[identity]),
                    len(analysis_cases[identity])),
                "resolution_reason": resolution["reason"],
                "gap_reason": item.gap_reason,
                "next_action": item.next_action,
                "resumption_point": item.resumption_point,
                "lifecycle_status": item.lifecycle_status,
                **cls.interface_policy_fields(item),
                "removed_at": item.removed_at,
                "api_info_id": item.api_info_id,
                "api_info_revision_id": item.api_info_revision_id,
                "api_info_binding_status": item.api_info_binding_status,
                "api_info_binding_reason": item.api_info_binding_reason,
                "module_interface_id": item.module_interface_id,
                "owner_module": item.api_info.module if item.api_info_id else None,
                "is_cross_module_reuse": bool(
                    item.api_info_id and item.api_info.module_id != item.module_id
                ),
                "coverage_rate": (
                    round(effective_completed * 100 / target, 2) if target else 0
                ),
            }
            row["coverage_status"] = cls.interface_coverage_status(item, target, effective_completed, row["deferred_case_count"])
            rows.append(row)
        if coverage_statuses or analysis_statuses:
            rows = [row for row in rows
                    if (not coverage_statuses or row["coverage_status"] in coverage_statuses)
                    and (not analysis_statuses or row["analysis_status"] in analysis_statuses)]
            count = len(rows)
            rows = rows[(page - 1) * page_size:page * page_size]
        return {
            "items": rows,
            "count": count,
            "page": page,
            "page_size": page_size,
        }

    @classmethod
    def interface_detail(
            cls,
            interface_snapshot: ModuleCoverageInterfaceSnapshot,
            case_queryset=None,
            case_page: int = 1,
            case_page_size: int = 100,
    ) -> dict:
        cases = (
            case_queryset if case_queryset is not None else ModuleCoverageCase.objects.all()
        )
        if interface_snapshot.module_interface_id:
            cases = cases.filter(
                module_interface_id=interface_snapshot.module_interface_id,
                current_snapshot__isnull=False,
            )
        else:
            cases = cases.filter(
                project_product_id=interface_snapshot.project_product_id,
                module_id=interface_snapshot.module_id,
                repository_key=interface_snapshot.repository_key,
                branch=interface_snapshot.branch,
                interface_source_key_hash=interface_snapshot.source_key_hash,
                current_snapshot__isnull=False,
            )
        if interface_snapshot.lifecycle_status == ModuleCoverageInterfaceStatus.ACTIVE:
            cases = cases.filter(removed_at__isnull=True)
        cases = list(cases.select_related(
            "api_case", "last_seen_scan", "current_snapshot",
            "current_snapshot__interface_snapshot",
        ).order_by("name", "id"))
        resolution = cls.interface_resolution(
            interface_snapshot.mermaid, interface_snapshot.node_ids,
        )
        assessments = {
            item.id: cls.case_coverage_assessment(item, interface_snapshot)
            for item in cases
        }
        target = sum(item.status in {
            ModuleCoverageCaseStatus.PENDING_CREATE,
            ModuleCoverageCaseStatus.COMPLETED,
        } for item in cases)
        completed = sum(
            item.status == ModuleCoverageCaseStatus.COMPLETED
            and item.api_case_id is not None
            and assessments[item.id]["status"] == ModuleCoverageValidity.VALID
            for item in cases
        )
        case_page = max(1, int(case_page))
        case_page_size = min(100, max(1, int(case_page_size)))
        page_cases = cases[(case_page - 1) * case_page_size:case_page * case_page_size]
        if interface_snapshot.module_interface_id:
            first_scan_id = interface_snapshot.module_interface.first_seen_scan_id
        else:
            first_scan_id = ModuleCoverageInterfaceSnapshot.objects.filter(
                project_product_id=interface_snapshot.project_product_id,
                module_id=interface_snapshot.module_id,
                repository_key=interface_snapshot.repository_key,
                branch=interface_snapshot.branch,
                source_key_hash=interface_snapshot.source_key_hash,
            ).aggregate(value=Min("scan_id"))["value"]
        return {
            "id": interface_snapshot.id,
            "source_key": interface_snapshot.source_key,
            "source_key_hash": interface_snapshot.source_key_hash,
            "project_product_id": interface_snapshot.project_product_id,
            "module_id": interface_snapshot.module_id,
            "module": {
                "id": interface_snapshot.module_id,
                "name": interface_snapshot.module.name,
                "full_path": interface_snapshot.module.get_full_path(),
            } if interface_snapshot.module_id else None,
            "lifecycle_status": interface_snapshot.lifecycle_status,
            **cls.interface_policy_fields(interface_snapshot),
            "coverage_status": cls.interface_coverage_status(
                interface_snapshot, target, completed,
                sum(item.status == ModuleCoverageCaseStatus.DEFERRED for item in cases),
            ),
            "first_scan_id": first_scan_id,
            "latest_scan_id": interface_snapshot.scan_id,
            "latest_commit_sha": interface_snapshot.scan.commit_sha,
            "current_snapshot_id": interface_snapshot.id,
            "interface_name": interface_snapshot.interface_name,
            "method": interface_snapshot.method,
            "url": interface_snapshot.url,
            "repository_key": interface_snapshot.repository_key,
            "branch": interface_snapshot.branch,
            "case_count": len(cases),
            "target_case_count": target,
            "completed_case_count": completed,
            "coverage_rate": round(completed * 100 / target, 2) if target else 0,
            "mermaid": interface_snapshot.mermaid,
            "node_ids": interface_snapshot.node_ids,
            "branch_ids": interface_snapshot.branch_ids,
            "flow_scan_id": interface_snapshot.scan_id,
            "resolution_status": resolution["status"],
            "resolution_reason": resolution["reason"],
            "gap_reason": interface_snapshot.gap_reason,
            "next_action": interface_snapshot.next_action,
            "resumption_point": interface_snapshot.resumption_point,
            "api_info_id": interface_snapshot.api_info_id,
            "api_info_revision_id": interface_snapshot.api_info_revision_id,
            "api_info_binding_status": interface_snapshot.api_info_binding_status,
            "api_info_binding_reason": interface_snapshot.api_info_binding_reason,
            "module_interface_id": interface_snapshot.module_interface_id,
            "owner_module": (
                {
                    "id": interface_snapshot.api_info.module_id,
                    "name": interface_snapshot.api_info.module.name,
                    "full_path": interface_snapshot.api_info.module.get_full_path(),
                }
                if interface_snapshot.api_info_id else None
            ),
            "is_cross_module_reuse": bool(
                interface_snapshot.api_info_id
                and interface_snapshot.api_info.module_id != interface_snapshot.module_id
            ),
            "cases": [
                {
                    "id": item.id,
                    "name": item.name,
                    "status": item.status,
                    "execution_result": item.execution_result,
                    "coverage_validity": assessments[item.id]["status"],
                    "coverage_validity_reason": assessments[item.id]["reason"],
                    "test_ownership": item.test_ownership,
                    "scenario_layer": item.scenario_layer,
                    "scenario_type": item.scenario_type,
                    "scenario_tags": item.scenario_tags,
                    "api_case": item.api_case_id,
                    "api_case_name": item.api_case.name if item.api_case_id else None,
                    "test_scenario": (item.current_snapshot.payload or {}).get("test_scenario"),
                    "core_assertion": (item.current_snapshot.payload or {}).get("core_assertion"),
                    "legacy_scenario_assertion": (
                            item.current_snapshot.payload or {}
                    ).get("scenario_assertion"),
                    "remark": (item.current_snapshot.payload or {}).get("remark"),
                    "node_ids": (item.current_snapshot.payload or {}).get("covered_node_ids", []),
                    "branch_ids": (item.current_snapshot.payload or {}).get("covered_branch_ids", []),
                }
                for item in page_cases
            ],
            "case_page": case_page,
            "case_page_size": case_page_size,
        }

    @staticmethod
    def case_flow(item: ModuleCoverageCase) -> dict:
        interface_snapshot = (
            item.module_interface.current_snapshot
            if item.module_interface_id else ModuleCoverageInterfaceSnapshot.objects.filter(
                project_product_id=item.project_product_id,
                module_id=item.module_id,
                repository_key=item.repository_key,
                branch=item.branch,
                source_key_hash=item.interface_source_key_hash,
                is_current=True,
            ).first()
        )
        payload = item.current_snapshot.payload or {}
        return {
            "interface_source_key": item.interface_source_key,
            "mermaid": interface_snapshot.mermaid if interface_snapshot else "",
            "node_ids": interface_snapshot.node_ids if interface_snapshot else [],
            "branch_ids": interface_snapshot.branch_ids if interface_snapshot else [],
            "selected_node_ids": payload.get("covered_node_ids", []),
            "selected_branch_ids": payload.get("covered_branch_ids", []),
            "flow_scan_id": interface_snapshot.scan_id if interface_snapshot else None,
            "coverage_interface_id": interface_snapshot.id if interface_snapshot else None,
            "coverage_validity": item.coverage_validity,
            "coverage_validity_reason": item.coverage_validity_reason,
        }

    @classmethod
    def metrics(
            cls,
            project_product_id: int | None = None,
            module_id: int | None = None,
            repository_key: str | None = None,
            branch: str | None = None,
            case_queryset=None,
            scan_queryset=None,
            interface_queryset=None,
    ) -> dict:
        queryset = cls.active_cases(
            project_product_id,
            module_id,
            repository_key,
            branch,
            queryset=case_queryset,
        )
        total = queryset.count()
        target = queryset.filter(status__in=[
            ModuleCoverageCaseStatus.PENDING_CREATE,
            ModuleCoverageCaseStatus.COMPLETED,
        ]).count()
        completed = queryset.filter(
            status=ModuleCoverageCaseStatus.COMPLETED,
            api_case__isnull=False,
        ).count()
        executed = queryset.exclude(
            execution_result__in=[
                ModuleCoverageExecutionResult.NOT_EXECUTED,
                ModuleCoverageExecutionResult.NOT_APPLICABLE,
            ],
        ).count()
        passed = queryset.filter(execution_result=ModuleCoverageExecutionResult.PASSED).count()
        interfaces = (
            interface_queryset
            if interface_queryset is not None
            else ModuleCoverageInterfaceSnapshot.objects.all()
        ).filter(
            lifecycle_status=ModuleCoverageInterfaceStatus.ACTIVE,
            removed_at__isnull=True,
        ).filter(
            Q(module_interface__current_snapshot_id=F("id"))
            | Q(module_interface__isnull=True, is_current=True)
        )
        if project_product_id:
            interfaces = interfaces.filter(project_product_id=project_product_id)
        if module_id:
            interfaces = interfaces.filter(module_id=module_id)
        if repository_key:
            interfaces = interfaces.filter(repository_key=repository_key)
        if branch:
            interfaces = interfaces.filter(branch=branch)
        excluded_interface_count = interfaces.filter(module_interface__coverage_policy=ModuleCoveragePolicy.EXCLUDED).count()
        interfaces = interfaces.exclude(module_interface__coverage_policy=ModuleCoveragePolicy.EXCLUDED)
        current_interfaces = list(interfaces)
        interface_usage_total = len(current_interfaces)
        if module_id:
            api_total = interface_usage_total
            bound_api_info_count = sum(
                item.api_info_binding_status == ModuleCoverageApiInfoBindingStatus.BOUND
                and item.api_info_id is not None
                for item in current_interfaces
            )
        else:
            unique_interfaces = {
                ("api_info", item.api_info_id)
                if (
                        item.api_info_binding_status == ModuleCoverageApiInfoBindingStatus.BOUND
                        and item.api_info_id is not None
                ) else (
                    "source", item.project_product_id, item.repository_key,
                    item.branch, item.source_key_hash,
                )
                for item in current_interfaces
            }
            api_total = len(unique_interfaces)
            bound_api_info_count = len({
                item.api_info_id for item in current_interfaces
                if (
                        item.api_info_binding_status == ModuleCoverageApiInfoBindingStatus.BOUND
                        and item.api_info_id is not None
                )
            })
        ambiguous_api_info_count = interfaces.filter(
            api_info_binding_status=ModuleCoverageApiInfoBindingStatus.AMBIGUOUS,
        ).count()
        mismatch_api_info_count = interfaces.filter(
            api_info_binding_status=ModuleCoverageApiInfoBindingStatus.MISMATCH,
        ).count()
        resolution = cls.interface_resolution_summary(current_interfaces)
        resolved_case_scope = Q(pk__in=[])
        for interface in current_interfaces:
            if cls.interface_resolution(interface.mermaid, interface.node_ids)["status"] != (
                    ModuleCoverageResolutionStatus.RESOLVED
            ):
                continue
            resolved_case_scope |= Q(
                project_product_id=interface.project_product_id,
                module_id=interface.module_id,
                repository_key=interface.repository_key,
                branch=interface.branch,
                interface_source_key_hash=interface.source_key_hash,
            )
        effective_cases = queryset.filter(
            resolved_case_scope,
            coverage_validity=ModuleCoverageValidity.VALID,
            current_snapshot__payload__has_keys=cls.REQUIRED_CURRENT_CASE_PAYLOAD_KEYS,
        )
        effective_completed = effective_cases.filter(
            status=ModuleCoverageCaseStatus.COMPLETED,
            api_case__isnull=False,
        ).count()
        effective_valid = effective_cases.count()
        effective_pending_review = queryset.filter(
            resolved_case_scope,
            coverage_validity=ModuleCoverageValidity.PENDING_REVIEW,
            current_snapshot__payload__has_keys=cls.REQUIRED_CURRENT_CASE_PAYLOAD_KEYS,
        ).count()
        effective_invalid = max(total - effective_valid - effective_pending_review, 0)
        effective_executed = effective_cases.exclude(
            execution_result__in=[
                ModuleCoverageExecutionResult.NOT_EXECUTED,
                ModuleCoverageExecutionResult.NOT_APPLICABLE,
            ],
        ).count()
        effective_passed = effective_cases.filter(
            execution_result=ModuleCoverageExecutionResult.PASSED,
        ).count()
        current_interface_case_scope = Q(pk__in=[])
        for interface in current_interfaces:
            current_interface_case_scope |= Q(
                project_product_id=interface.project_product_id,
                module_id=interface.module_id,
                repository_key=interface.repository_key,
                branch=interface.branch,
                interface_source_key_hash=interface.source_key_hash,
            )
        entered_api_total = queryset.filter(
            current_interface_case_scope,
            api_case__isnull=False,
        ).values(
            "project_product_id", "module_id", "repository_key", "branch", "interface_source_key_hash",
        ).distinct().count()
        ownership = {
            row["test_ownership"]: row["count"]
            for row in queryset.values("test_ownership").annotate(count=Count("id"))
        }
        latest_scan = (
            scan_queryset if scan_queryset is not None else ModuleCoverageScan.objects.all()
        ).filter(status=ModuleCoverageScanStatus.COMPLETED)
        if project_product_id:
            latest_scan = latest_scan.filter(project_product_id=project_product_id)
        if module_id:
            latest_scan = latest_scan.filter(module_id=module_id)
        if repository_key:
            latest_scan = latest_scan.filter(repository_key=repository_key)
        if branch:
            latest_scan = latest_scan.filter(branch=branch)
        latest_scan = latest_scan.order_by("-id").first()
        return {
            "case_total": total,
            "excluded_interface_count": excluded_interface_count,
            "target_case_count": target,
            "pending_case_count": queryset.filter(
                status=ModuleCoverageCaseStatus.PENDING_CREATE,
            ).count(),
            "deferred_case_count": queryset.filter(
                status=ModuleCoverageCaseStatus.DEFERRED,
            ).count(),
            "valid_case_count": queryset.filter(
                coverage_validity=ModuleCoverageValidity.VALID,
            ).count(),
            "effective_valid_case_count": effective_valid,
            "pending_review_case_count": queryset.filter(
                coverage_validity=ModuleCoverageValidity.PENDING_REVIEW,
            ).count(),
            "effective_pending_review_case_count": effective_pending_review,
            "invalid_case_count": queryset.filter(
                coverage_validity=ModuleCoverageValidity.INVALID,
            ).count(),
            "effective_invalid_case_count": effective_invalid,
            "completed_case_count": completed,
            "api_case_completion_rate": round(completed * 100 / target, 2) if target else 0,
            "effective_completed_case_count": effective_completed,
            "effective_coverage_rate": (
                round(effective_completed * 100 / target, 2) if target else 0
            ),
            "executed_case_count": executed,
            "passed_case_count": passed,
            "failed_case_count": queryset.filter(execution_result=ModuleCoverageExecutionResult.FAILED).count(),
            "partial_case_count": queryset.filter(execution_result=ModuleCoverageExecutionResult.PARTIAL).count(),
            "execution_pass_rate": round(passed * 100 / executed, 2) if executed else 0,
            "effective_executed_case_count": effective_executed,
            "effective_passed_case_count": effective_passed,
            "effective_execution_pass_rate": (
                round(effective_passed * 100 / effective_executed, 2)
                if effective_executed else 0
            ),
            "api_total": api_total,
            "interface_usage_total": interface_usage_total,
            "bound_api_info_count": bound_api_info_count,
            "unbound_api_info_count": max(api_total - bound_api_info_count, 0),
            "ambiguous_api_info_count": ambiguous_api_info_count,
            "mismatch_api_info_count": mismatch_api_info_count,
            "api_info_binding_rate": (
                round(bound_api_info_count * 100 / api_total, 2) if api_total else 0
            ),
            "entered_api_total": entered_api_total,
            "api_entry_rate": round(entered_api_total * 100 / api_total, 2) if api_total else 0,
            **resolution,
            "ownership": ownership,
            "latest_scan_id": latest_scan.id if latest_scan else None,
            "latest_commit_sha": latest_scan.commit_sha if latest_scan else None,
        }
