import hashlib

from pydantic import ValidationError

from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageApiInfoBindingStatus, ModuleCoverageInterfaceStatus, ModuleCoveragePolicy,
)
from src.apps.auto_api.enums import MethodEnum
from src.apps.auto_api.exceptions import (
    AutoApiError, MODULE_COVERAGE_CASE_NOT_FOUND, MODULE_COVERAGE_CASE_PRODUCT_MISMATCH,
    MODULE_COVERAGE_CASE_MODULE_MISMATCH, MODULE_COVERAGE_CASE_REVISION_MISMATCH,
    MODULE_COVERAGE_CASE_TARGET_MISMATCH,
)
from src.apps.auto_api.models import ApiCase, ApiCaseRevision, ModuleCoverageModuleInterface
from src.apps.auto_api.schemas.module_coverage import ModuleCoverageCasePayload


class ModuleCoverageCaseBindingService:
    @classmethod
    def validate(cls, product_id, module_id, case_id, revision_id, *, interface=None, previous=None,
                 api_case=None, revision=None, coverage_payload=None):
        if not case_id:
            if revision_id:
                raise AutoApiError(MODULE_COVERAGE_CASE_REVISION_MISMATCH, value=(case_id, revision_id))
            return None, None
        api_case = api_case or ApiCase.objects.filter(id=case_id).first()
        if api_case is None:
            raise AutoApiError(MODULE_COVERAGE_CASE_NOT_FOUND, value=(case_id,))
        if api_case.project_product_id != product_id:
            raise AutoApiError(MODULE_COVERAGE_CASE_PRODUCT_MISMATCH, value=(case_id, product_id))
        if revision_id:
            revision = revision or ApiCaseRevision.objects.filter(id=revision_id, api_case_id=case_id).first()
            if revision is None or revision.api_case_id != case_id or revision.id != revision_id:
                raise AutoApiError(MODULE_COVERAGE_CASE_REVISION_MISMATCH, value=(case_id, revision_id))
        if api_case.module_id == module_id:
            return api_case, revision

        def reject(reason):
            raise AutoApiError(MODULE_COVERAGE_CASE_MODULE_MISMATCH,
                value=(module_id, case_id, api_case.module_id, reason))

        if not revision_id:
            reject('复用绑定缺少精确修订，请指定已核验的修订，平台不会自动选择最新版本')
        historical = bool(previous is not None and previous.removed_at is None
                and previous.project_product_id == product_id and previous.module_id == module_id
                and previous.api_case_id == case_id
                and previous.api_case_revision_id in (None, revision_id))
        if not (interface is not None and interface.project_product_id == product_id
                and interface.module_id == module_id and interface.api_info_id
                and interface.lifecycle_status == ModuleCoverageInterfaceStatus.ACTIVE
                and interface.removed_at is None
                and interface.api_info_binding_status == ModuleCoverageApiInfoBindingStatus.BOUND
                and interface.api_info.project_product_id == product_id):
            reject('覆盖目标缺少已确认的同产品接口绑定')
        if previous is not None and (
                previous.project_product_id != product_id or previous.module_id != module_id
                or interface.repository_key != previous.repository_key or interface.branch != previous.branch
                or interface.source_key_hash != previous.interface_source_key_hash):
            reject('消费场景与目标接口的产品、模块或稳定身份不一致')
        api_info = interface.api_info
        owner_or_consumer = api_case.module_id in (module_id, api_info.module_id) or ModuleCoverageModuleInterface.objects.filter(
            project_product_id=product_id, module_id=api_case.module_id,
            module__project_product_id=product_id, api_info_id=api_info.id,
            repository_key=interface.repository_key, branch=interface.branch,
            lifecycle_status=ModuleCoverageInterfaceStatus.ACTIVE, removed_at__isnull=True,
            current_snapshot__api_info_id=api_info.id, current_snapshot__module_id=api_case.module_id,
            current_snapshot__project_product_id=product_id,
            current_snapshot__api_info_binding_status=ModuleCoverageApiInfoBindingStatus.BOUND,
            current_snapshot__lifecycle_status=ModuleCoverageInterfaceStatus.ACTIVE,
            current_snapshot__removed_at__isnull=True, api_info_binding_status=ModuleCoverageApiInfoBindingStatus.BOUND,
            coverage_policy=ModuleCoveragePolicy.INCLUDED,
        ).exists()
        if not owner_or_consumer:
            reject('Case模块没有该接口的有效Owner/Consumer关系')
        if not historical:
            cls.validate_consumer_evidence(coverage_payload, interface, reject)
        payload = revision.payload if revision is not None and isinstance(revision.payload, dict) else {}
        steps = payload.get('api_case_detailed')
        targets = [step for step in steps if isinstance(step, dict)
                   and step.get('api_info_id') == api_info.id] if isinstance(steps, list) else []
        if not targets:
            raise AutoApiError(MODULE_COVERAGE_CASE_TARGET_MISMATCH,
                              value=(case_id, revision_id, api_info.id))
        if not historical:
            # 覆盖绑定到 Case 修订，多次调用可共同覆盖，但不能跳过其中任何调用的身份核验。
            for target in targets:
                frozen = target.get('api_info_snapshot')
                frozen = frozen if isinstance(frozen, dict) else {}
                frozen_payload = frozen.get('payload')
                config = frozen_payload.get('api_info') if isinstance(frozen_payload, dict) else None
                if not (isinstance(config, dict) and frozen.get('id') == api_info.id
                        and frozen.get('project_product_id') == product_id
                        and target.get('api_info_revision_id')
                        and frozen.get('revision_id') == target.get('api_info_revision_id')
                        and config.get('protocol_type') == api_info.protocol_type
                        and config.get('url') == interface.url
                        and MethodEnum.obj().get(config.get('method')) == interface.method):
                    reject('目标接口调用的冻结快照与消费接口的产品、协议、方法或URL不一致，请选择匹配的Case精确修订')
        return api_case, revision

    @staticmethod
    def validate_consumer_evidence(payload, interface, reject):
        try:
            evidence = ModuleCoverageCasePayload.model_validate(payload or {})
        except ValidationError:
            reject('消费场景缺少有效的场景、核心断言或覆盖路径证据，请先上传并核验该模块自己的场景')
        if (hashlib.sha256(evidence.interface_source_key.encode('utf-8')).hexdigest() != interface.source_key_hash
                or evidence.method != interface.method or evidence.url != interface.url
                or not set(evidence.covered_node_ids).issubset(interface.node_ids or [])
                or not set(evidence.covered_branch_ids).issubset(interface.branch_ids or [])):
            reject('消费场景的接口身份、请求定义或覆盖节点/分支与目标接口不一致，请重新核验，不能沿用其他模块的完成状态')
