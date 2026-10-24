import hashlib
import re
from collections import Counter

from django.db import IntegrityError, transaction
from django.db.models import F, Max, Min, Q
from django.utils import timezone
from pydantic import ValidationError

from src.apps.auto_api.enums import ApiProtocolTypeEnum, MethodEnum
from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageApiInfoBindingStatus,
    ModuleCoverageCaseStatus,
    ModuleCoverageExecutionResult,
    ModuleCoverageInterfaceStatus,
    ModuleCoverageResolutionStatus,
    ModuleCoverageScanMode,
    ModuleCoverageScanScope,
    ModuleCoverageScanStatus,
    ModuleCoverageSyncAction,
)
from src.apps.auto_api.exceptions import (
    AutoApiError,
    QUALITY_COVERAGE_MODULE_NOT_FOUND,
    QUALITY_COVERAGE_MODULE_UPLOAD_NOT_ALLOWED,
    QUALITY_COVERAGE_UPLOAD_INVALID,
    QUALITY_COVERAGE_EXECUTION_INVALID,
    QUALITY_COVERAGE_PROJECT_PRODUCT_BINDING_NOT_FOUND,
    QUALITY_COVERAGE_INVALID,
    QUALITY_COVERAGE_FIELD_INVALID,
    QUALITY_COVERAGE_SCAN_UPLOAD_INCOMPLETE,
    QUALITY_COVERAGE_CONTENT_HASH_MISMATCH,
    QUALITY_COVERAGE_MODULE_INVALID,
    QUALITY_COVERAGE_CODE_PARSE_NOT_ALLOWED,
    QUALITY_COVERAGE_API_INFO_INVALID,
    QUALITY_COVERAGE_API_INFO_UPLOAD_INVALID,
)
from src.apps.auto_api.models import ApiCase, ApiCaseRevision, ApiInfo, ApiInfoRevision
from src.apps.auto_api.models import (
    ModuleCoverageCase,
    ModuleCoverageCaseSnapshot,
    ModuleCoverageInterfaceSnapshot,
    ModuleCoverageModuleInterface,
    ModuleCoverageScan,
)
from src.apps.auto_api.schemas.module_coverage import (
    ModuleCoverageCasePayload,
    ModuleCoverageInterfacePayload,
)
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import ProjectProduct


class ModuleCoverageScanMixin:
    @staticmethod
    def get_or_create_module_interface(
            scan: ModuleCoverageScan,
            module_id: int | None,
            source_key: str,
            source_key_hash: str,
    ) -> ModuleCoverageModuleInterface:
        identity = {
            "project_product_id": scan.project_product_id,
            "module_id": module_id,
            "repository_key": scan.repository_key,
            "branch": scan.branch,
            "source_key_hash": source_key_hash,
        }
        # NULL 模块的唯一约束不能防止并发重复；同产品的身份认领在此串行化。
        ProjectProduct.objects.select_for_update().get(id=scan.project_product_id)
        candidates = ModuleCoverageModuleInterface.objects.select_for_update().filter(
            **{key: value for key, value in identity.items() if key != "module_id"},
        )
        if scan.scope_type == ModuleCoverageScanScope.PROJECT:
            existing = candidates.order_by("id").first()
        else:
            existing = candidates.filter(module_id=module_id).first() or candidates.filter(module__isnull=True).first()
        if existing:
            return existing
        try:
            with transaction.atomic():
                relation, _ = ModuleCoverageModuleInterface.objects.select_for_update().get_or_create(
                    **identity,
                    defaults={
                        "source_key": source_key,
                        "first_seen_scan": scan,
                        "last_seen_scan": scan,
                    },
                )
                return relation
        except IntegrityError:
            return ModuleCoverageModuleInterface.objects.select_for_update().get(**identity)

    @staticmethod
    def adopt_legacy_module_interface_state(
            relation: ModuleCoverageModuleInterface,
    ) -> ModuleCoverageModuleInterface:
        legacy_snapshots = ModuleCoverageInterfaceSnapshot.objects.select_for_update().filter(
            project_product_id=relation.project_product_id,
            module_id=relation.module_id,
            repository_key=relation.repository_key,
            branch=relation.branch,
            source_key_hash=relation.source_key_hash,
            module_interface__isnull=True,
        )
        scan_bounds = legacy_snapshots.aggregate(first_scan_id=Min("scan_id"), last_scan_id=Max("scan_id"))
        current_snapshots = list(legacy_snapshots.filter(is_current=True).order_by("-scan_id", "-id")[:2])
        if len(current_snapshots) > 1:
            raise AutoApiError(QUALITY_COVERAGE_INVALID,
                               value=("稳定接口身份存在多个当前快照，请先执行历史数据修复",),
                               )
        legacy_snapshots.update(module_interface=relation)
        ModuleCoverageCase.objects.filter(
            project_product_id=relation.project_product_id,
            module_id=relation.module_id,
            repository_key=relation.repository_key,
            branch=relation.branch,
            interface_source_key_hash=relation.source_key_hash,
            module_interface__isnull=True,
        ).update(module_interface=relation)
        if current_snapshots and relation.current_snapshot_id is None:
            current = current_snapshots[0]
            relation.source_key = current.source_key
            relation.api_info = current.api_info
            relation.api_info_revision = current.api_info_revision
            relation.api_info_binding_status = current.api_info_binding_status
            relation.api_info_binding_reason = current.api_info_binding_reason
            relation.current_snapshot = current
            relation.first_seen_scan_id = min(
                relation.first_seen_scan_id,
                scan_bounds["first_scan_id"] or current.scan_id,
            )
            relation.last_seen_scan_id = max(
                relation.last_seen_scan_id,
                scan_bounds["last_scan_id"] or current.scan_id,
            )
            relation.lifecycle_status = current.lifecycle_status
            relation.removed_at = current.removed_at
            relation.save(update_fields=[
                "source_key", "api_info", "api_info_revision", "api_info_binding_status",
                "api_info_binding_reason", "current_snapshot", "first_seen_scan",
                "last_seen_scan", "lifecycle_status", "removed_at", "update_time",
            ])
        return relation

    @classmethod
    @transaction.atomic
    def create_scan(cls, data: dict, user_id: int | None = None) -> ModuleCoverageScan:
        cls.require_fields(data, cls.REQUIRED_SCAN_FIELDS)
        scan_mode = cls.validate_choice(
            "scan_mode", data.get("scan_mode") or ModuleCoverageScanMode.FULL,
            ModuleCoverageScanMode,
        )
        scope_type = cls.validate_choice(
            "scope_type", data.get("scope_type") or ModuleCoverageScanScope.MODULE,
            ModuleCoverageScanScope,
        )
        inventory_only = data.get("inventory_only", False)
        if not isinstance(inventory_only, bool):
            raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID, value=("inventory_only", inventory_only))
        inventory_only = inventory_only or scope_type == ModuleCoverageScanScope.PROJECT
        if inventory_only and scope_type == ModuleCoverageScanScope.INTERFACE:
            raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID, value=("scope_type", scope_type))
        expected_case_count = cls.parse_int("expected_case_count", data["expected_case_count"], minimum=0)
        expected_interface_count = cls.parse_int(
            "expected_interface_count", data["expected_interface_count"], minimum=0,
        )
        if inventory_only and expected_case_count:
            raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID, value=("expected_case_count", expected_case_count))
        project_product_id = cls.parse_int("project_product_id", data["project_product_id"], minimum=1)
        module_id = data.get("module_id")
        if scope_type == ModuleCoverageScanScope.PROJECT:
            if module_id is not None or expected_case_count or data.get("include_descendants"):
                raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID, value=("scope_type", scope_type))
        else:
            module_id = cls.parse_int("module_id", module_id, minimum=1)
            cls.validate_module(project_product_id, module_id)
        target_interface = None
        target_interface_id = data.get("target_interface_id")
        if scope_type == ModuleCoverageScanScope.INTERFACE:
            if expected_interface_count != 1 or not target_interface_id:
                raise AutoApiError(QUALITY_COVERAGE_API_INFO_INVALID)
            target_interface = ModuleCoverageInterfaceSnapshot.objects.filter(
                id=cls.parse_int("target_interface_id", target_interface_id, minimum=1),
                project_product_id=project_product_id,
                repository_key=cls.normalized_text("repository_key", data["repository_key"]),
                branch=cls.normalized_text("branch", data["branch"]),
                lifecycle_status=ModuleCoverageInterfaceStatus.ACTIVE,
                removed_at__isnull=True,
            ).filter(
                Q(module_interface__current_snapshot_id=F("id"))
                | Q(module_interface__isnull=True, is_current=True)
            ).first()
            if target_interface is None:
                raise AutoApiError(QUALITY_COVERAGE_API_INFO_INVALID)
            if target_interface.module_id not in cls.module_ids(module_id,
                                                                bool(data.get("include_descendants", False))):
                raise AutoApiError(QUALITY_COVERAGE_API_INFO_INVALID)
        elif target_interface_id:
            raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID, value=("target_interface_id", target_interface_id))
        test_env = data.get("test_env")
        if test_env is not None:
            test_env = cls.parse_int("test_env", test_env)
        if test_env is not None and test_env not in EnvironmentEnum.obj():
            raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID, value=("test_env", test_env))
        schema_version = cls.parse_int("schema_version", data.get("schema_version") or 3, minimum=1)
        if schema_version != 3:
            raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID, value=("schema_version", schema_version))

        identity = {
            "project_product_id": project_product_id,
            "module_id": module_id,
            "repository_key": cls.normalized_text("repository_key", data["repository_key"]),
            "branch": cls.normalized_text("branch", data["branch"]),
            "commit_sha": cls.normalized_text("commit_sha", data["commit_sha"]),
            "scan_mode": scan_mode,
            "scope_type": scope_type,
            "target_interface_id": target_interface.id if target_interface else None,
            "expected_case_count": expected_case_count,
            "expected_interface_count": expected_interface_count,
            "include_descendants": bool(data.get("include_descendants", False)),
            "base_commit_sha": (
                cls.normalized_text("base_commit_sha", data["base_commit_sha"])
                if data.get("base_commit_sha") else None
            ),
            "test_env": test_env,
            "schema_version": schema_version,
        }
        if not re.fullmatch(r"[0-9a-fA-F]{40}", identity["commit_sha"]):
            raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID,
                               value=("commit_sha", identity["commit_sha"]),
                               )
        if identity["base_commit_sha"] and not re.fullmatch(
                r"[0-9a-fA-F]{40}", identity["base_commit_sha"],
        ):
            raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID,
                               value=("base_commit_sha", identity["base_commit_sha"]),
                               )
        existing = ModuleCoverageScan.objects.filter(idempotency_key=str(data["idempotency_key"])).first()
        if existing:
            existing_identity = {key: getattr(existing, key) for key in identity}
            if existing_identity != identity or cls.is_inventory_scan(existing) != inventory_only:
                raise AutoApiError(QUALITY_COVERAGE_UPLOAD_INVALID)
            return existing

        if scan_mode == ModuleCoverageScanMode.INCREMENTAL:
            if scope_type == ModuleCoverageScanScope.INTERFACE:
                latest_commit = target_interface.scan.commit_sha
            else:
                latest_scans = ModuleCoverageScan.objects.filter(
                    project_product_id=project_product_id,
                    module_id=module_id,
                    repository_key=identity["repository_key"],
                    branch=identity["branch"],
                    include_descendants=identity["include_descendants"],
                    status=ModuleCoverageScanStatus.COMPLETED,
                    scope_type=scope_type,
                )
                if inventory_only:
                    latest_scans = latest_scans.filter(summary__inventory_only=True)
                else:
                    latest_scans = latest_scans.filter(
                        Q(summary__inventory_only=False) | Q(summary__inventory_only__isnull=True),
                    )
                latest = latest_scans.order_by("-id").first()
                latest_commit = latest.commit_sha if latest else None
            if identity["base_commit_sha"] != latest_commit:
                raise AutoApiError(QUALITY_COVERAGE_EXECUTION_INVALID)

        return ModuleCoverageScan.objects.create(
            **identity,
            repository_name=str(data.get("repository_name") or data["repository_key"]).strip(),
            idempotency_key=str(data["idempotency_key"]),
            skill_name=data.get("skill_name") or "mango-code-driven-api-case-builder",
            skill_version=str(data.get("skill_version") or "1"),
            created_by_id=user_id,
            started_at=timezone.now(),
            summary={"inventory_only": inventory_only},
        )

    @staticmethod
    def get_uploading_scan(scan_id: int) -> ModuleCoverageScan:
        scan = ModuleCoverageScan.objects.filter(id=scan_id).first()
        if scan is None:
            raise AutoApiError(QUALITY_COVERAGE_MODULE_NOT_FOUND)
        if scan.status != ModuleCoverageScanStatus.UPLOADING:
            raise AutoApiError(QUALITY_COVERAGE_MODULE_UPLOAD_NOT_ALLOWED)
        return scan

    @staticmethod
    def get_locked_uploading_scan(scan_id: int) -> ModuleCoverageScan:
        scan = ModuleCoverageScan.objects.select_for_update().filter(id=scan_id).first()
        if scan is None:
            raise AutoApiError(QUALITY_COVERAGE_MODULE_NOT_FOUND)
        if scan.status != ModuleCoverageScanStatus.UPLOADING:
            raise AutoApiError(QUALITY_COVERAGE_MODULE_UPLOAD_NOT_ALLOWED)
        return scan

    @classmethod
    def validate_api_case(
            cls, scan: ModuleCoverageScan, module_id: int, api_case_id: int | None,
            api_case_revision_id: int | None,
    ) -> tuple[ApiCase | None, ApiCaseRevision | None]:
        if not api_case_id:
            if api_case_revision_id:
                raise AutoApiError(QUALITY_COVERAGE_PROJECT_PRODUCT_BINDING_NOT_FOUND)
            return None, None
        api_case = ApiCase.objects.filter(id=api_case_id, project_product_id=scan.project_product_id).first()
        if api_case is None or api_case.module_id != module_id:
            raise AutoApiError(QUALITY_COVERAGE_PROJECT_PRODUCT_BINDING_NOT_FOUND)
        revision = None
        if api_case_revision_id:
            revision = ApiCaseRevision.objects.filter(id=api_case_revision_id, api_case=api_case).first()
            if revision is None:
                raise AutoApiError(QUALITY_COVERAGE_PROJECT_PRODUCT_BINDING_NOT_FOUND)
        return api_case, revision

    @classmethod
    def resolve_api_info_binding(
            cls,
            scan: ModuleCoverageScan,
            module_id: int,
            payload: dict,
            previous: ModuleCoverageInterfaceSnapshot | None,
    ) -> tuple[ApiInfo | None, ApiInfoRevision | None, str, str]:
        """只匹配或校验既有 ApiInfo，扫描上传不得绕过正式接口的重复校验创建资产。"""
        method_value = {value: key for key, value in MethodEnum.obj().items()}.get(payload["method"])
        if method_value is None:
            return None, None, ModuleCoverageApiInfoBindingStatus.MISMATCH, "ApiInfo不支持该请求方法"

        explicit_id = payload.get("api_info_id")
        explicit_revision_id = payload.get("api_info_revision_id")
        if explicit_id:
            candidates = ApiInfo.objects.filter(
                id=explicit_id,
                project_product_id=scan.project_product_id,
            )
        else:
            candidates = ApiInfo.objects.filter(
                project_product_id=scan.project_product_id,
                protocol_type=ApiProtocolTypeEnum.HTTP.value,
                http_config__method=method_value,
                http_config__url=payload["url"],
            )

        matched: list[ApiInfo] = []
        for item in candidates:
            try:
                runtime = ApiInfoRuntimeService.resolve_runtime(
                    item.id,
                    allow_draft=True,
                    revision_id=explicit_revision_id if explicit_id and explicit_revision_id else None,
                )
            except Exception:
                continue
            if (
                    runtime.protocol_type == ApiProtocolTypeEnum.HTTP.value
                    and runtime.method == method_value
                    and runtime.url == payload["url"]
            ):
                matched.append(item)

        if explicit_id:
            if len(matched) != 1:
                raise AutoApiError(QUALITY_COVERAGE_INVALID,
                                   value=("api_info_id 与接口的项目产品、协议、Method或URL不一致",),
                                   )
            api_info = matched[0]
            if explicit_revision_id:
                revision = ApiInfoRevision.objects.filter(
                    id=explicit_revision_id, api_info=api_info,
                ).first()
                if revision is None:
                    raise AutoApiError(QUALITY_COVERAGE_INVALID,
                                       value=("api_info_revision_id 不属于指定 ApiInfo",),
                                       )
            else:
                revision = api_info.revisions.order_by("-revision_no").first()
            return api_info, revision, ModuleCoverageApiInfoBindingStatus.BOUND, ""

        if len(matched) == 1:
            api_info = matched[0]
            return (
                api_info,
                api_info.revisions.order_by("-revision_no").first(),
                ModuleCoverageApiInfoBindingStatus.BOUND,
                "按项目产品、协议、Method和URL自动匹配",
            )
        if len(matched) > 1:
            previous_match = next(
                (item for item in matched if previous and item.id == previous.api_info_id),
                None,
            )
            if previous_match is not None:
                return (
                    previous_match,
                    previous_match.revisions.order_by("-revision_no").first(),
                    ModuleCoverageApiInfoBindingStatus.BOUND,
                    "存在多个候选，保留当前已验证的ApiInfo绑定",
                )
            return (
                None,
                None,
                ModuleCoverageApiInfoBindingStatus.AMBIGUOUS,
                f"匹配到多个ApiInfo候选：{','.join(str(item.id) for item in matched)}",
            )

        if previous and previous.api_info_id:
            try:
                runtime = ApiInfoRuntimeService.resolve_runtime(previous.api_info_id, allow_draft=True)
            except Exception:
                runtime = None
            if runtime and (
                    runtime.project_product_id == scan.project_product_id
                    and runtime.protocol_type == ApiProtocolTypeEnum.HTTP.value
                    and runtime.method == method_value
                    and runtime.url == payload["url"]
            ):
                return (
                    previous.api_info,
                    previous.api_info.revisions.order_by("-revision_no").first(),
                    ModuleCoverageApiInfoBindingStatus.MISMATCH,
                    "保留原ApiInfo关联，当前接口定义待确认",
                )
        return None, None, ModuleCoverageApiInfoBindingStatus.UNBOUND, "未找到唯一匹配的ApiInfo"

    @staticmethod
    def interface_binding_payload(
            snapshot: ModuleCoverageInterfaceSnapshot,
            api_info_id: int,
            api_info_revision_id: int | None = None,
    ) -> dict:
        return {
            "interface_name": snapshot.interface_name,
            "method": snapshot.method,
            "url": snapshot.url,
            "mermaid": snapshot.mermaid,
            "node_ids": snapshot.node_ids,
            "branch_ids": snapshot.branch_ids,
            "gap_reason": snapshot.gap_reason or None,
            "next_action": snapshot.next_action or None,
            "resumption_point": snapshot.resumption_point or None,
            "api_info_id": api_info_id,
            "api_info_revision_id": api_info_revision_id,
        }

    @classmethod
    def preview_interface_binding_correction(
            cls,
            coverage_interface_id: int,
            api_info_id: int,
            api_info_revision_id: int | None = None,
    ) -> dict:
        """Validate a binding correction without mutating the immutable scan history."""
        current = cls.resolve_current_interface_snapshot(coverage_interface_id)
        payload = cls.interface_binding_payload(
            current,
            cls.parse_int("api_info_id", api_info_id, minimum=1),
            (
                cls.parse_int("api_info_revision_id", api_info_revision_id, minimum=1)
                if api_info_revision_id is not None else None
            ),
        )
        target, target_revision, binding_status, binding_reason = cls.resolve_api_info_binding(
            current.scan,
            current.module_id,
            payload,
            current,
        )
        same_binding = (
                current.api_info_id == target.id
                and (
                        api_info_revision_id is None
                        or current.api_info_revision_id == target_revision.id
                )
                and current.api_info_binding_status == ModuleCoverageApiInfoBindingStatus.BOUND
        )
        return {
            "coverage_interface_id": current.id,
            "module_interface_id": current.module_interface_id,
            "consumer_module_id": current.module_id,
            "source_key": current.source_key,
            "method": current.method,
            "url": current.url,
            "current_binding": {
                "api_info_id": current.api_info_id,
                "api_info_revision_id": current.api_info_revision_id,
                "owner_module_id": current.api_info.module_id if current.api_info_id else None,
                "status": current.api_info_binding_status,
            },
            "target_binding": {
                "api_info_id": target.id,
                "api_info_revision_id": target_revision.id if target_revision else None,
                "owner_module_id": target.module_id,
                "status": binding_status,
                "reason": binding_reason,
            },
            "changed": not same_binding,
            "history_snapshot_mutated": False,
            "api_info_owner_mutated": False,
            "will_create_incremental_snapshot": not same_binding,
        }

    @classmethod
    @transaction.atomic
    def update_interface_binding(
            cls,
            coverage_interface_id: int,
            api_info_id: int,
            api_info_revision_id: int | None = None,
            user_id: int | None = None,
    ) -> dict:
        """Apply a binding correction through an auditable single-interface scan."""
        ModuleCoverageInterfaceSnapshot.objects.select_for_update().filter(
            id=coverage_interface_id,
        ).first()
        current = cls.resolve_current_interface_snapshot(coverage_interface_id)
        if current.module_interface_id:
            ModuleCoverageModuleInterface.objects.select_for_update().get(
                id=current.module_interface_id,
            )
        preview = cls.preview_interface_binding_correction(
            coverage_interface_id,
            api_info_id,
            api_info_revision_id,
        )
        current = cls.resolve_current_interface_snapshot(coverage_interface_id)
        if not preview["changed"]:
            return {
                **preview,
                "applied": False,
                "scan_id": current.scan_id,
                "new_coverage_interface_id": current.id,
            }

        revision_key = api_info_revision_id or "current"
        idempotency_key = (
            f"coverage-binding:{current.id}:{api_info_id}:{revision_key}"
        )
        scan = cls.create_scan({
            "project_product_id": current.project_product_id,
            "module_id": current.module_id,
            "repository_key": current.repository_key,
            "repository_name": current.scan.repository_name,
            "branch": current.branch,
            "commit_sha": current.scan.commit_sha,
            "base_commit_sha": current.scan.commit_sha,
            "idempotency_key": idempotency_key,
            "expected_case_count": 0,
            "expected_interface_count": 1,
            "scan_mode": ModuleCoverageScanMode.INCREMENTAL,
            "scope_type": ModuleCoverageScanScope.INTERFACE,
            "target_interface_id": current.id,
            "include_descendants": False,
            "test_env": current.scan.test_env,
            "schema_version": current.scan.schema_version,
            "skill_name": current.scan.skill_name,
            "skill_version": current.scan.skill_version,
        }, user_id)
        if scan.status == ModuleCoverageScanStatus.UPLOADING:
            cls.upload_interfaces(scan.id, [{
                "source_key": current.source_key,
                "module_id": current.module_id,
                "payload": cls.interface_binding_payload(
                    current,
                    api_info_id,
                    api_info_revision_id,
                ),
            }])
            cls.complete_scan(scan.id)

        new_snapshot = scan.interface_snapshots.select_related("module_interface").get()
        relation = ModuleCoverageModuleInterface.objects.select_related(
            "current_snapshot", "api_info", "api_info_revision",
        ).get(id=new_snapshot.module_interface_id)
        return {
            **preview,
            "applied": True,
            "scan_id": scan.id,
            "new_coverage_interface_id": relation.current_snapshot_id,
            "target_binding": {
                "api_info_id": relation.api_info_id,
                "api_info_revision_id": relation.api_info_revision_id,
                "owner_module_id": relation.api_info.module_id if relation.api_info_id else None,
                "status": relation.api_info_binding_status,
                "reason": relation.api_info_binding_reason,
            },
        }

    @classmethod
    @transaction.atomic
    def upload_interfaces(cls, scan_id: int, items: list[dict]) -> dict:
        scan = cls.get_locked_uploading_scan(scan_id)
        cls.validate_batch(items)
        result = Counter()
        for raw in items:
            cls.require_fields(raw, ("source_key", "payload"))
            inventory = cls.is_inventory_scan(scan)
            module_id = raw.get("module_id") or scan.module_id
            if module_id is not None:
                module_id = cls.parse_int("module_id", module_id, minimum=1)
                if scan.scope_type == ModuleCoverageScanScope.PROJECT:
                    cls.validate_module(scan.project_product_id, module_id)
                else:
                    cls.validate_module_scope(scan, module_id)
            elif not inventory:
                raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID, value=("module_id", module_id))
            try:
                payload = ModuleCoverageInterfacePayload.model_validate(raw["payload"]).model_dump(mode="json")
            except ValidationError as error:
                raise AutoApiError(QUALITY_COVERAGE_INVALID, value=(str(error),)) from error
            if (not inventory and not payload["mermaid"]) or (inventory and payload["mermaid"]):
                raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID, value=("mermaid", payload["mermaid"]))
            source_key = cls.normalized_text("source_key", raw["source_key"])
            source_key_hash = hashlib.sha256(source_key.encode("utf-8")).hexdigest()
            if (
                    scan.scope_type == ModuleCoverageScanScope.INTERFACE
                    and source_key_hash != scan.target_interface.source_key_hash
            ):
                raise AutoApiError(QUALITY_COVERAGE_API_INFO_UPLOAD_INVALID)
            content_hash = cls.interface_semantic_hash(payload)
            submitted_hash = cls.canonical_hash({"module_id": module_id, "payload": payload})
            if raw.get("content_hash") and raw["content_hash"] != content_hash:
                raise AutoApiError(QUALITY_COVERAGE_CONTENT_HASH_MISMATCH)
            existing_rows = ModuleCoverageInterfaceSnapshot.objects.filter(
                scan=scan,
                source_key_hash=source_key_hash,
            )
            if scan.scope_type != ModuleCoverageScanScope.PROJECT:
                existing_rows = existing_rows.filter(module_id=module_id)
            existing = existing_rows.first()
            if existing:
                if existing.submitted_hash != submitted_hash:
                    raise AutoApiError(QUALITY_COVERAGE_UPLOAD_INVALID)
                result[ModuleCoverageSyncAction.UNCHANGED] += 1
                continue
            module_interface = cls.get_or_create_module_interface(
                scan,
                module_id,
                source_key,
                source_key_hash,
            )
            module_interface = cls.adopt_legacy_module_interface_state(module_interface)
            previous = module_interface.current_snapshot
            if scan.scope_type == ModuleCoverageScanScope.PROJECT:
                module_id = module_interface.module_id
            if scan.scope_type == ModuleCoverageScanScope.INTERFACE:
                if previous is None or previous.id != scan.target_interface_id:
                    raise AutoApiError(QUALITY_COVERAGE_API_INFO_UPLOAD_INVALID)
            if previous and (
                    previous.method != payload["method"] or previous.url != payload["url"]
            ):
                raise AutoApiError(QUALITY_COVERAGE_INVALID,
                                   value=("接口 Method 或 URL 已变化，必须使用新的接口 source_key",),
                                   )
            action = (
                ModuleCoverageSyncAction.CREATED if previous is None or previous.removed_at is not None
                else ModuleCoverageSyncAction.UNCHANGED
                if previous.content_hash == content_hash and previous.module_id == module_id
                else ModuleCoverageSyncAction.UPDATED
            )
            resolution = cls.interface_resolution(payload["mermaid"], payload["node_ids"])
            if resolution["status"] == ModuleCoverageResolutionStatus.GAP:
                resolution["reason"] = payload["gap_reason"]
            if inventory and previous:
                api_info, api_info_revision = previous.api_info, previous.api_info_revision
                binding_status, binding_reason = previous.api_info_binding_status, previous.api_info_binding_reason
            else:
                api_info, api_info_revision, binding_status, binding_reason = cls.resolve_api_info_binding(
                    scan, module_id, payload, previous,
                )
            ModuleCoverageInterfaceSnapshot.objects.create(
                scan=scan,
                project_product_id=scan.project_product_id,
                module_id=module_id,
                module_interface=module_interface,
                repository_key=scan.repository_key,
                branch=scan.branch,
                source_key=source_key,
                source_key_hash=source_key_hash,
                interface_name=payload["interface_name"],
                method=payload["method"],
                url=payload["url"],
                mermaid=payload["mermaid"],
                node_ids=payload["node_ids"],
                branch_ids=payload["branch_ids"],
                resolution_status=resolution["status"],
                resolution_reason=resolution["reason"],
                gap_reason=payload["gap_reason"] or "",
                next_action=payload["next_action"] or "",
                resumption_point=payload["resumption_point"] or "",
                api_info=api_info,
                api_info_revision=api_info_revision,
                api_info_binding_status=binding_status,
                api_info_binding_reason=binding_reason,
                content_hash=content_hash,
                submitted_hash=submitted_hash,
                sync_action=action,
            )
            result[action] += 1
        return {
            "accepted": sum(result.values()),
            "created": result[ModuleCoverageSyncAction.CREATED],
            "updated": result[ModuleCoverageSyncAction.UPDATED],
            "unchanged": result[ModuleCoverageSyncAction.UNCHANGED],
        }

    @classmethod
    @transaction.atomic
    def upload_cases(cls, scan_id: int, items: list[dict]) -> dict:
        scan = cls.get_locked_uploading_scan(scan_id)
        if cls.is_inventory_scan(scan):
            raise AutoApiError(QUALITY_COVERAGE_FIELD_INVALID, value=("scope_type", scan.scope_type))
        cls.validate_batch(items)
        result = Counter()
        for raw in items:
            cls.require_fields(raw, ("source_key", "payload"))
            module_id = cls.parse_int("module_id", raw.get("module_id") or scan.module_id, minimum=1)
            cls.validate_module_scope(scan, module_id)
            try:
                payload = ModuleCoverageCasePayload.model_validate(raw["payload"]).model_dump(mode="json")
            except ValidationError as error:
                raise AutoApiError(QUALITY_COVERAGE_INVALID, value=(str(error),)) from error
            cls.validate_choice("current_status", payload["current_status"], ModuleCoverageCaseStatus)
            cls.validate_choice(
                "execution_result", payload["execution_result"],
                ModuleCoverageExecutionResult,
            )
            interface_source_key = payload["interface_source_key"]
            interface_source_key_hash = hashlib.sha256(interface_source_key.encode("utf-8")).hexdigest()
            interface_snapshot = ModuleCoverageInterfaceSnapshot.objects.filter(
                scan=scan,
                module_id=module_id,
                source_key_hash=interface_source_key_hash,
            ).first()
            if interface_snapshot is not None and (
                    payload["method"] != interface_snapshot.method
                    or payload["url"] != interface_snapshot.url
                    or payload["interface_name"] != interface_snapshot.interface_name
                    or not set(payload["covered_node_ids"]).issubset(interface_snapshot.node_ids)
                    or not set(payload["covered_branch_ids"]).issubset(interface_snapshot.branch_ids)
            ):
                raise AutoApiError(QUALITY_COVERAGE_INVALID,
                                   value=(f"Case 与接口 {interface_source_key} 的定义或覆盖路径不一致",),
                                   )
            api_case, api_case_revision = cls.validate_api_case(
                scan, module_id, raw.get("api_case_id"), raw.get("api_case_revision_id"),
            )
            is_completed = payload["current_status"] == ModuleCoverageCaseStatus.COMPLETED
            if is_completed != (api_case is not None):
                raise AutoApiError(QUALITY_COVERAGE_INVALID,
                                   value=("current_status=completed 必须且只能在绑定 ApiCase 时提交",),
                                   )
            content_hash = cls.canonical_hash({"module_id": module_id, "payload": payload})
            if raw.get("content_hash") and raw["content_hash"] != content_hash:
                raise AutoApiError(QUALITY_COVERAGE_CONTENT_HASH_MISMATCH)
            submitted_hash = cls.canonical_hash({
                "content_hash": content_hash,
                "api_case_id": api_case.id if api_case else None,
                "api_case_revision_id": api_case_revision.id if api_case_revision else None,
            })
            source_key = cls.normalized_text("source_key", raw["source_key"])
            source_key_hash = hashlib.sha256(source_key.encode("utf-8")).hexdigest()
            coverage_case = ModuleCoverageCase.objects.filter(
                project_product_id=scan.project_product_id,
                module_id=module_id,
                repository_key=scan.repository_key,
                branch=scan.branch,
                source_key_hash=source_key_hash,
            ).first()
            created = coverage_case is None
            if coverage_case is None:
                coverage_case = ModuleCoverageCase.objects.create(
                    project_product_id=scan.project_product_id,
                    module_id=module_id,
                    module_interface=(
                        interface_snapshot.module_interface if interface_snapshot else None
                    ),
                    repository_key=scan.repository_key,
                    branch=scan.branch,
                    source_key=source_key,
                    source_key_hash=source_key_hash,
                    interface_source_key=interface_source_key,
                    interface_source_key_hash=interface_source_key_hash,
                    name=payload["case_title"],
                    interface_name=payload["interface_name"],
                    method=payload["method"].upper(),
                    url=payload["url"],
                    test_ownership=payload["test_ownership"],
                    scenario_layer=payload["scenario_layer"],
                    scenario_type=payload["scenario_type"],
                    scenario_tags=payload["scenario_tags"],
                    status=ModuleCoverageCaseStatus.PENDING_CREATE,
                    execution_result=ModuleCoverageExecutionResult.NOT_EXECUTED,
                    first_seen_scan=scan,
                    last_seen_scan=scan,
                )
            existing = ModuleCoverageCaseSnapshot.objects.filter(scan=scan, coverage_case=coverage_case).first()
            if existing:
                if existing.submitted_hash != submitted_hash:
                    raise AutoApiError(QUALITY_COVERAGE_UPLOAD_INVALID)
                if existing.interface_snapshot_id is None and interface_snapshot is not None:
                    existing.interface_snapshot = interface_snapshot
                    existing.save(update_fields=["interface_snapshot"])
                result[ModuleCoverageSyncAction.UNCHANGED] += 1
                continue
            current = coverage_case.current_snapshot
            action = (
                ModuleCoverageSyncAction.CREATED if created or coverage_case.removed_at is not None
                else ModuleCoverageSyncAction.UNCHANGED
                if current and current.content_hash == content_hash
                else ModuleCoverageSyncAction.UPDATED
            )
            ModuleCoverageCaseSnapshot.objects.create(
                scan=scan,
                coverage_case=coverage_case,
                interface_snapshot=interface_snapshot,
                content_hash=content_hash,
                submitted_hash=submitted_hash,
                payload=payload,
                api_case=api_case,
                api_case_revision=api_case_revision,
                sync_action=action,
            )
            result[action] += 1
        return {
            "accepted": sum(result.values()),
            "created": result[ModuleCoverageSyncAction.CREATED],
            "updated": result[ModuleCoverageSyncAction.UPDATED],
            "unchanged": result[ModuleCoverageSyncAction.UNCHANGED],
        }

    @staticmethod
    def upload_status(scan: ModuleCoverageScan, page: int = 1, page_size: int = 100) -> dict:
        page = max(1, int(page))
        page_size = min(500, max(1, int(page_size)))
        queryset = scan.case_snapshots.select_related("coverage_case").order_by("id")
        count = queryset.count()
        rows = queryset[(page - 1) * page_size:page * page_size]
        interface_queryset = scan.interface_snapshots.exclude(
            sync_action=ModuleCoverageSyncAction.REMOVED,
        ).order_by("id")
        interface_count = interface_queryset.count()
        interface_rows = interface_queryset[(page - 1) * page_size:page * page_size]
        return {
            "items": [
                {
                    "source_key": row.coverage_case.source_key,
                    "submitted_hash": row.submitted_hash,
                    "sync_action": row.sync_action,
                }
                for row in rows
            ],
            "count": count,
            "expected_count": scan.expected_case_count,
            "interface_items": [
                {
                    "source_key": row.source_key,
                    "submitted_hash": row.submitted_hash,
                    "sync_action": row.sync_action,
                }
                for row in interface_rows
            ],
            "interface_count": interface_count,
            "expected_interface_count": scan.expected_interface_count,
            "complete": (
                    count == scan.expected_case_count
                    and interface_count == scan.expected_interface_count
            ),
            "page": page,
            "page_size": page_size,
        }

    @classmethod
    def validation(cls, scan: ModuleCoverageScan) -> dict:
        received = scan.case_snapshots.count()
        uploaded_interfaces = scan.interface_snapshots.exclude(
            sync_action=ModuleCoverageSyncAction.REMOVED,
        )
        received_interfaces = uploaded_interfaces.count()
        resolution = cls.interface_resolution_summary(
            uploaded_interfaces.only(
                "source_key", "mermaid", "node_ids", "gap_reason",
                "next_action", "resumption_point",
            ),
            include_details=True,
        )
        blocking_errors = []
        gap_errors = []
        if received != scan.expected_case_count:
            blocking_errors.append(
                QUALITY_COVERAGE_SCAN_UPLOAD_INCOMPLETE.message.format("Case", scan.expected_case_count, received),
            )
        if received_interfaces != scan.expected_interface_count:
            blocking_errors.append(
                QUALITY_COVERAGE_SCAN_UPLOAD_INCOMPLETE.message.format(
                    "接口", scan.expected_interface_count, received_interfaces,
                ),
            )
        if not cls.is_inventory_scan(scan) and resolution["placeholder_interface_count"]:
            blocking_errors.append(QUALITY_COVERAGE_CODE_PARSE_NOT_ALLOWED.message.format(
                resolution["resolved_interface_count"],
                resolution["placeholder_interface_count"],
                0,
            ))
        if not cls.is_inventory_scan(scan) and resolution["gap_interface_count"]:
            gap_errors.append(QUALITY_COVERAGE_CODE_PARSE_NOT_ALLOWED.message.format(
                resolution["resolved_interface_count"],
                0,
                resolution["gap_interface_count"],
            ))
        interface_snapshot_ids = set(uploaded_interfaces.values_list("id", flat=True))
        invalid_case_snapshot_count = 0
        for snapshot in scan.case_snapshots.select_related(
                "coverage_case", "interface_snapshot",
        ):
            interface_snapshot = snapshot.interface_snapshot
            payload = snapshot.payload or {}
            if interface_snapshot is not None and (
                    interface_snapshot.id not in interface_snapshot_ids
                    or (
                            snapshot.coverage_case.module_interface_id is not None
                            and snapshot.coverage_case.module_interface_id
                            != interface_snapshot.module_interface_id
                    )
                    or snapshot.coverage_case.interface_source_key_hash
                    != interface_snapshot.source_key_hash
                    or not set(payload.get("covered_node_ids", [])).issubset(interface_snapshot.node_ids)
                    or not set(payload.get("covered_branch_ids", [])).issubset(interface_snapshot.branch_ids)
            ):
                invalid_case_snapshot_count += 1
        if invalid_case_snapshot_count:
            blocking_errors.append(f"{invalid_case_snapshot_count} 个Case快照未正确关联本次接口快照或覆盖路径无效")
        target_mismatch_count = 0
        if scan.scope_type == ModuleCoverageScanScope.INTERFACE:
            target_mismatch_count = uploaded_interfaces.exclude(
                source_key_hash=scan.target_interface.source_key_hash,
            ).count()
            if target_mismatch_count:
                blocking_errors.append("单接口扫描上传了目标接口之外的接口快照")
        errors = blocking_errors + gap_errors
        return {
            "valid": not errors,
            "inventory_only": cls.is_inventory_scan(scan),
            "valid_with_gaps": not blocking_errors and bool(resolution["gap_interface_count"]),
            "expected_case_count": scan.expected_case_count,
            "received_case_count": received,
            "expected_interface_count": scan.expected_interface_count,
            "received_interface_count": received_interfaces,
            **resolution,
            "invalid_case_snapshot_count": invalid_case_snapshot_count,
            "target_mismatch_count": target_mismatch_count,
            "blocking_errors": blocking_errors,
            "gap_errors": gap_errors,
            "errors": errors,
        }

    @classmethod
    @transaction.atomic
    def complete_scan_with_gaps(cls, scan_id: int) -> ModuleCoverageScan:
        """Close a fully uploaded audit without applying unresolved snapshots as current assets."""
        scan = cls.get_locked_uploading_scan(scan_id)
        validation = cls.validation(scan)
        if not validation["valid_with_gaps"]:
            raise AutoApiError(QUALITY_COVERAGE_MODULE_INVALID,
                               value=("；".join(validation["errors"] or ["扫描中不存在可登记的未解析Gap"]),),
                               )
        actions = Counter(scan.case_snapshots.values_list("sync_action", flat=True))
        interface_actions = Counter(
            scan.interface_snapshots.exclude(
                sync_action=ModuleCoverageSyncAction.REMOVED,
            ).values_list("sync_action", flat=True),
        )
        scan.summary = {
            "applied": False,
            "case_count": validation["received_case_count"],
            "created": actions[ModuleCoverageSyncAction.CREATED],
            "updated": actions[ModuleCoverageSyncAction.UPDATED],
            "unchanged": actions[ModuleCoverageSyncAction.UNCHANGED],
            "removed": 0,
            "interface_count": validation["received_interface_count"],
            "interface_created": interface_actions[ModuleCoverageSyncAction.CREATED],
            "interface_updated": interface_actions[ModuleCoverageSyncAction.UPDATED],
            "interface_unchanged": interface_actions[ModuleCoverageSyncAction.UNCHANGED],
            "interface_removed": 0,
            "resolved_interface_count": validation["resolved_interface_count"],
            "placeholder_interface_count": validation["placeholder_interface_count"],
            "gap_interface_count": validation["gap_interface_count"],
            "interface_resolution_rate": validation["interface_resolution_rate"],
            "gap_details": validation["unresolved_interfaces"],
        }
        scan.status = ModuleCoverageScanStatus.COMPLETED_WITH_GAPS
        scan.finished_at = timezone.now()
        scan.save(update_fields=["summary", "status", "finished_at", "update_time"])
        return scan
