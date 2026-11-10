from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageApiInfoBindingStatus, ModuleCoverageInterfaceStatus, ModuleCoveragePolicy,
)
from src.apps.auto_api.exceptions import (
    AutoApiError, MODULE_COVERAGE_CASE_NOT_FOUND, MODULE_COVERAGE_CASE_PRODUCT_MISMATCH,
    MODULE_COVERAGE_CASE_MODULE_MISMATCH, MODULE_COVERAGE_CASE_REVISION_MISMATCH,
    MODULE_COVERAGE_CASE_TARGET_MISMATCH,
)
from src.apps.auto_api.models import ApiCase, ApiCaseRevision, ModuleCoverageModuleInterface


class ModuleCoverageCaseBindingService:
    @classmethod
    def validate(cls, product_id, module_id, case_id, revision_id, *, interface=None, previous=None,
                 api_case=None, revision=None):
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
            reject('跨模块历史绑定缺少精确修订，请明确原验证修订后重新上传，平台不会自动选择最新版本')
        # 只保留原覆盖场景的精确绑定，不将历史兼容变成任意跨模块新建入口。
        if not (previous is not None and previous.removed_at is None
                and previous.project_product_id == product_id and previous.module_id == module_id
                and previous.api_case_id == case_id
                and previous.api_case_revision_id in (None, revision_id)):
            reject('仅允许保留已有Case及精确修订，不允许借此新增或更换跨模块绑定')
        if not (interface is not None and interface.project_product_id == product_id
                and interface.module_id == module_id and interface.api_info_id
                and interface.repository_key == previous.repository_key and interface.branch == previous.branch
                and interface.source_key_hash == previous.interface_source_key_hash
                and interface.lifecycle_status == ModuleCoverageInterfaceStatus.ACTIVE
                and interface.removed_at is None
                and interface.api_info_binding_status == ModuleCoverageApiInfoBindingStatus.BOUND
                and interface.api_info.project_product_id == product_id):
            reject('覆盖目标缺少已确认的同产品接口绑定')
        api_info = interface.api_info
        owner_or_consumer = api_case.module_id == api_info.module_id or ModuleCoverageModuleInterface.objects.filter(
            project_product_id=product_id, module_id=api_case.module_id,
            module__project_product_id=product_id, api_info_id=api_info.id,
            repository_key=previous.repository_key, branch=previous.branch,
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
        payload = revision.payload if revision is not None and isinstance(revision.payload, dict) else {}
        steps = payload.get('api_case_detailed')
        if not (isinstance(steps, list) and any(isinstance(step, dict)
                and step.get('api_info_id') == api_info.id for step in steps)):
            raise AutoApiError(MODULE_COVERAGE_CASE_TARGET_MISMATCH,
                              value=(case_id, revision_id, api_info.id))
        return api_case, revision
