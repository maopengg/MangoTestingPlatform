import hashlib
import json
import re
from collections import Counter

from pydantic import ValidationError

from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageErrorCodeEnum,
    ModuleCoverageInterfaceStatus,
    ModuleCoverageResolutionStatus,
    ModuleCoverageScanScope,
    ModuleCoverageValidity,
)
from src.apps.auto_api.exceptions import (
    AutoApiError,
    QUALITY_COVERAGE_PROJECT_PRODUCT_MODULE_INVALID,
    QUALITY_COVERAGE_FIELD_REQUIRED,
    QUALITY_COVERAGE_FIELD_INVALID,
    QUALITY_COVERAGE_UPLOAD_INVALID_CODE_UPLOAD_INVALID,
    QUALITY_COVERAGE_API_INFO_MODULE_NOT_FOUND,
)
from src.apps.auto_api.models import (
    ModuleCoverageCase,
    ModuleCoverageInterfaceSnapshot,
    ModuleCoverageScan,
)
from src.apps.auto_api.schemas.module_coverage import (
    ModuleCoverageCasePayload,
)
from src.apps.test_center.models import ProductModule


class ModuleCoverageFoundationMixin:
    @staticmethod
    def is_inventory_scan(scan: ModuleCoverageScan) -> bool:
        return scan.scope_type == ModuleCoverageScanScope.PROJECT or (scan.summary or {}).get("inventory_only") is True

    @staticmethod
    def get_current_interface_snapshot(interface_id: int) -> ModuleCoverageInterfaceSnapshot:
        try:
            snapshot = ModuleCoverageInterfaceSnapshot.objects.select_related(
                "project_product", "module", "scan", "api_info", "api_info_revision",
                "module_interface",
            ).get(id=interface_id)
            if snapshot.module_interface_id:
                if snapshot.module_interface.current_snapshot_id != snapshot.id:
                    raise ModuleCoverageInterfaceSnapshot.DoesNotExist
            elif not snapshot.is_current:
                raise ModuleCoverageInterfaceSnapshot.DoesNotExist
            return snapshot
        except ModuleCoverageInterfaceSnapshot.DoesNotExist as error:
            raise AutoApiError(QUALITY_COVERAGE_API_INFO_MODULE_NOT_FOUND,
                               error_code=ModuleCoverageErrorCodeEnum.INTERFACE_NOT_FOUND.value,
                               details={"coverage_interface_id": interface_id},
                               ) from error

    @classmethod
    def resolve_current_interface_snapshot(
            cls,
            interface_id: int,
    ) -> ModuleCoverageInterfaceSnapshot:
        """Resolve a historical snapshot ID to the current snapshot of the same stable interface."""
        snapshot = ModuleCoverageInterfaceSnapshot.objects.select_related(
            "module_interface",
        ).filter(id=interface_id).first()
        if snapshot is None:
            return cls.get_current_interface_snapshot(interface_id)
        if (
                snapshot.module_interface_id
                and snapshot.module_interface.current_snapshot_id
                and snapshot.module_interface.current_snapshot_id != snapshot.id
        ):
            return cls.get_current_interface_snapshot(
                snapshot.module_interface.current_snapshot_id,
            )
        return cls.get_current_interface_snapshot(snapshot.id)

    @staticmethod
    def canonical_hash(value: dict) -> str:
        body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    @classmethod
    def interface_semantic_hash(cls, payload: dict) -> str:
        topology = re.sub(r'"(?:\\.|[^"\\])*"', '""', payload["mermaid"])
        topology = re.sub(r"\|[^|\n]*\|", "||", topology)
        topology = topology.replace(";", "")
        topology = re.sub(r"\s+", "", topology)
        return cls.canonical_hash({
            "method": payload["method"].upper(),
            "url": payload["url"],
            "node_ids": sorted(payload["node_ids"]),
            "branch_ids": sorted(payload["branch_ids"]),
            "topology": topology,
        })

    @staticmethod
    def require_fields(data: dict, fields: tuple[str, ...]):
        missing = [field for field in fields if data.get(field) in (None, "")]
        if missing:
            raise AutoApiError(QUALITY_COVERAGE_FIELD_REQUIRED, value=(", ".join(missing),))

    @staticmethod
    def validate_choice(field: str, value: str, choices):
        if value not in choices.values:
            raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID, value=(field, value))
        return value

    @classmethod
    def validate_batch(cls, items: list[dict]):
        if not 1 <= len(items) <= cls.MAX_BATCH_SIZE:
            raise AutoApiError(QUALITY_COVERAGE_UPLOAD_INVALID_CODE_UPLOAD_INVALID,
                               value=(cls.MAX_BATCH_SIZE,),
                               )

    @staticmethod
    def parse_int(field: str, value, *, minimum: int | None = None) -> int:
        try:
            result = int(value)
        except (TypeError, ValueError) as error:
            raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID, value=(field, value)) from error
        if minimum is not None and result < minimum:
            raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID, value=(field, value))
        return result

    @staticmethod
    def normalized_text(field: str, value) -> str:
        result = str(value or "").strip()
        if not result:
            raise AutoApiError(QUALITY_COVERAGE_FIELD_REQUIRED, value=(field,))
        return result

    @classmethod
    def interface_resolution(cls, mermaid: str, node_ids: list[str] | None = None) -> dict:
        flow = str(mermaid or "")
        nodes = node_ids or []
        if not flow.strip() or not nodes:
            return {"status": "placeholder", "reason": "尚未分析代码链路"}
        route_only_unresolved = (
                len(nodes) <= 3
                and any(marker in flow for marker in cls.UNRESOLVED_FLOW_MARKERS)
                and re.search(r"controller|handler|控制器", flow, flags=re.IGNORECASE)
        )
        if any(marker in flow for marker in cls.PLACEHOLDER_FLOW_MARKERS) or route_only_unresolved:
            return {"status": "placeholder", "reason": "仅登记接口路由，Controller 后业务链路待补充"}
        if any(marker in flow for marker in cls.UNRESOLVED_FLOW_MARKERS):
            return {"status": "gap", "reason": "存在内部代码未解析边界"}
        return {"status": "resolved", "reason": ""}

    @classmethod
    def interface_resolution_summary(cls, snapshots, *, include_details: bool = False) -> dict:
        counts = Counter()
        unresolved = []
        for snapshot in snapshots:
            resolution = cls.interface_resolution(snapshot.mermaid, snapshot.node_ids)
            if resolution["status"] == ModuleCoverageResolutionStatus.GAP and snapshot.gap_reason:
                resolution["reason"] = snapshot.gap_reason
            counts[resolution["status"]] += 1
            if include_details and resolution["status"] != "resolved" and len(unresolved) < 20:
                unresolved.append({
                    "source_key": snapshot.source_key,
                    "status": resolution["status"],
                    "reason": resolution["reason"],
                    "next_action": snapshot.next_action,
                    "resumption_point": snapshot.resumption_point,
                })
        total = sum(counts.values())
        resolved = counts["resolved"]
        result = {
            "resolved_interface_count": resolved,
            "placeholder_interface_count": counts["placeholder"],
            "gap_interface_count": counts["gap"],
            "interface_resolution_rate": round(resolved * 100 / total, 2) if total else 0,
        }
        if include_details:
            result.update({
                "unresolved_interfaces": unresolved,
                "unresolved_interface_sample_limit": 20,
            })
        return result

    @classmethod
    def case_coverage_assessment(
            cls,
            coverage_case: ModuleCoverageCase,
            interface_snapshot: ModuleCoverageInterfaceSnapshot | None,
    ) -> dict:
        """Recalculate current Case validity from current schema and interface facts."""
        case_snapshot = coverage_case.current_snapshot
        if case_snapshot is None:
            return {"status": ModuleCoverageValidity.INVALID, "reason": "缺少当前Case快照"}
        try:
            payload = ModuleCoverageCasePayload.model_validate(case_snapshot.payload or {})
        except ValidationError as error:
            fields = sorted({str(item["loc"][0]) for item in error.errors() if item.get("loc")})
            detail = f"：{', '.join(fields[:8])}" if fields else ""
            return {
                "status": ModuleCoverageValidity.INVALID,
                "reason": f"当前Case快照不符合Schema v3{detail}",
            }
        if interface_snapshot is None:
            return {
                "status": ModuleCoverageValidity.PENDING_REVIEW,
                "reason": "Case尚未关联覆盖目标，不影响Case归属和接口调用",
            }
        if (
                coverage_case.module_interface_id is not None
                and coverage_case.module_interface_id != interface_snapshot.module_interface_id
        ):
            return {"status": ModuleCoverageValidity.INVALID, "reason": "Case与覆盖接口关系不一致"}
        if (
                (
                        interface_snapshot.module_interface_id
                        and interface_snapshot.module_interface.current_snapshot_id != interface_snapshot.id
                )
                or (not interface_snapshot.module_interface_id and not interface_snapshot.is_current)
                or interface_snapshot.lifecycle_status != ModuleCoverageInterfaceStatus.ACTIVE
                or interface_snapshot.removed_at is not None
        ):
            return {"status": ModuleCoverageValidity.INVALID, "reason": "当前接口已移除或未生效"}
        resolution = cls.interface_resolution(
            interface_snapshot.mermaid,
            interface_snapshot.node_ids,
        )
        if resolution["status"] != ModuleCoverageResolutionStatus.RESOLVED:
            return {
                "status": ModuleCoverageValidity.INVALID,
                "reason": f"接口代码链路未完整解析：{resolution['reason']}",
            }
        if hashlib.sha256(payload.interface_source_key.encode("utf-8")).hexdigest() != (
                interface_snapshot.source_key_hash
        ):
            return {"status": ModuleCoverageValidity.INVALID, "reason": "Case与当前接口身份不一致"}
        if (payload.method.upper(), payload.url) != (interface_snapshot.method, interface_snapshot.url):
            return {"status": ModuleCoverageValidity.INVALID, "reason": "Case与当前接口定义不一致"}
        missing_nodes = sorted(
            set(payload.covered_node_ids) - set(interface_snapshot.node_ids or []),
        )
        missing_branches = sorted(
            set(payload.covered_branch_ids) - set(interface_snapshot.branch_ids or []),
        )
        if missing_nodes or missing_branches:
            return {
                "status": ModuleCoverageValidity.INVALID,
                "reason": f"流程节点/分支已消失：nodes={missing_nodes}, branches={missing_branches}",
            }
        reviewed_interface = case_snapshot.interface_snapshot
        if reviewed_interface and reviewed_interface.id != interface_snapshot.id:
            same_semantics = bool(
                reviewed_interface.content_hash
                and interface_snapshot.content_hash
                and reviewed_interface.content_hash == interface_snapshot.content_hash
            )
            if not same_semantics:
                return {
                    "status": ModuleCoverageValidity.PENDING_REVIEW,
                    "reason": "接口流程已变更，需重新确认Case覆盖路径",
                }
        if getattr(coverage_case, 'api_case_id', None):
            from .binding import ModuleCoverageCaseBindingService
            try:
                ModuleCoverageCaseBindingService.validate(coverage_case.project_product_id,
                    coverage_case.module_id, coverage_case.api_case_id, coverage_case.api_case_revision_id,
                    interface=interface_snapshot, previous=coverage_case,
                    api_case=coverage_case.api_case, revision=coverage_case.api_case_revision)
            except AutoApiError as error:
                return {"status": ModuleCoverageValidity.INVALID, "reason": error.msg}
        return {"status": ModuleCoverageValidity.VALID, "reason": ""}

    @staticmethod
    def module_ids(module_id: int, include_descendants: bool) -> set[int]:
        ids = {int(module_id)}
        if not include_descendants:
            return ids
        pending = [int(module_id)]
        while pending:
            children = list(ProductModule.objects.filter(parent_id__in=pending).values_list("id", flat=True))
            new_ids = set(children) - ids
            if not new_ids:
                break
            ids.update(new_ids)
            pending = list(new_ids)
        return ids

    @classmethod
    def validate_module(cls, project_product_id: int, module_id: int):
        if not ProductModule.objects.filter(id=module_id, project_product_id=project_product_id).exists():
            raise AutoApiError(QUALITY_COVERAGE_PROJECT_PRODUCT_MODULE_INVALID)

    @classmethod
    def validate_module_scope(cls, scan: ModuleCoverageScan, module_id: int):
        cls.validate_module(scan.project_product_id, module_id)
        if module_id not in cls.module_ids(scan.module_id, scan.include_descendants):
            raise AutoApiError(QUALITY_COVERAGE_PROJECT_PRODUCT_MODULE_INVALID)
