from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from pydantic import ValidationError
from src.apps.auto_api.enums.module_coverage import ModuleCoverageInterfaceCoverageStatus as CoverageStatus, ModuleCoveragePolicy as Policy

from src.apps.auto_api.exceptions import (
    AutoApiError, MODULE_COVERAGE_POLICY_INPUT_INVALID,
    MODULE_COVERAGE_POLICY_REASON_REQUIRED, MODULE_COVERAGE_ANALYSIS_BLOCKED,
    QUALITY_COVERAGE_API_INFO_MODULE_NOT_FOUND,
)
from src.apps.auto_api.models import ModuleCoverageInterfaceSnapshot, ModuleCoverageModuleInterface
from src.apps.auto_api.schemas.module_coverage import ModuleCoveragePolicyUpdate
from src.apps.test_center.models import ProjectProduct
from src.apps.user.selectors.querysets import UserQuerySelector
from src.apps.user.services.permission import ProjectProductScopeService


class ModuleCoveragePolicyMixin:
    @classmethod
    def interface_coverage_status(cls, snapshot, target, completed, deferred):
        if target and completed == target:
            return CoverageStatus.COVERED
        if not target and deferred:
            return CoverageStatus.DEFERRED
        return CoverageStatus.PARTIAL if completed else CoverageStatus.UNCOVERED

    @staticmethod
    def interface_policy(snapshot) -> str:
        relation = getattr(snapshot, "module_interface", None)
        value = getattr(relation, "coverage_policy", None) if relation is not None else None
        return value if isinstance(value, str) else Policy.INCLUDED

    @classmethod
    def interface_is_excluded(cls, snapshot) -> bool:
        return cls.interface_policy(snapshot) == Policy.EXCLUDED

    @classmethod
    def interface_analysis_blocked(cls, snapshot) -> bool:
        return cls.interface_policy(snapshot) != Policy.INCLUDED

    @classmethod
    def interface_policy_fields(cls, snapshot):
        relation = getattr(snapshot, "module_interface", None)
        reason = getattr(relation, "coverage_reason", "") if relation is not None else ""
        return {"coverage_policy": cls.interface_policy(snapshot),
                "coverage_reason": reason if isinstance(reason, str) else ""}

    @classmethod
    def require_interface_included(cls, snapshot):
        if cls.interface_analysis_blocked(snapshot):
            raise AutoApiError(MODULE_COVERAGE_ANALYSIS_BLOCKED)

    @classmethod
    @transaction.atomic
    def update_interface_policy(cls, interface_ids, policy, reason, user_id):
        try:
            config = ModuleCoveragePolicyUpdate.model_validate({
                "interface_ids": interface_ids, "policy": policy, "reason": reason,
            })
        except ValidationError as error:
            raise AutoApiError(MODULE_COVERAGE_POLICY_INPUT_INVALID,
                               value=("请提供1～100个接口ID、有效覆盖策略和不超过2000字的原因",)) from error
        reason = config.reason.strip()
        if config.policy != Policy.INCLUDED and not reason:
            raise AutoApiError(MODULE_COVERAGE_POLICY_REASON_REQUIRED)
        ids = sorted(set(config.interface_ids))
        snapshots = list(ModuleCoverageInterfaceSnapshot.objects.filter(id__in=ids).filter(
            Q(module_interface__current_snapshot_id=F('id'))
            | Q(module_interface__isnull=True, is_current=True),
        ).select_related("scan", "module_interface"))
        actor = UserQuerySelector.user().filter(id=user_id).first()
        products = sorted({item.project_product_id for item in snapshots})
        if len(snapshots) != len(ids) or actor is None or any(
            not ProjectProductScopeService.has_project_product(actor, identity) for identity in products
        ):
            # 不区分不存在与越界ID，批量操作必须全部合法才能写入。
            raise AutoApiError(QUALITY_COVERAGE_API_INFO_MODULE_NOT_FOUND)
        list(ProjectProduct.objects.select_for_update().filter(id__in=products).order_by("id"))
        relations = []
        for snapshot in sorted(snapshots, key=lambda item: item.id):
            if snapshot.module_interface_id:
                relation = ModuleCoverageModuleInterface.objects.select_for_update().get(id=snapshot.module_interface_id)
            else:
                relation = cls.get_or_create_module_interface(
                    snapshot.scan, snapshot.module_id, snapshot.source_key, snapshot.source_key_hash,
                )
            relation = cls.adopt_legacy_module_interface_state(relation)
            if relation.current_snapshot_id != snapshot.id:
                raise AutoApiError(QUALITY_COVERAGE_API_INFO_MODULE_NOT_FOUND)
            relations.append(relation.id)
        updated = ModuleCoverageModuleInterface.objects.filter(id__in=relations).update(
            coverage_policy=config.policy,
            coverage_reason=reason,
            update_time=timezone.now(),
        )
        return {"updated": updated, "interface_ids": ids, "coverage_policy": config.policy, "coverage_reason": reason}
