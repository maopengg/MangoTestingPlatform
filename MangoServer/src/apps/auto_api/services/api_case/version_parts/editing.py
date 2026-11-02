from copy import deepcopy

from django.db import models, transaction

from src.apps.auto_api.enums import ApiCaseReleaseStatusEnum
from src.apps.auto_api.exceptions import (
    API_CASE_PREPUBLICATION_PRODUCT_CHANGE_NOT_ALLOWED,
    API_CASE_PREPUBLICATION_REVISION_DELETE_NOT_ALLOWED,
    API_VERSION_CASE_NOT_FOUND,
    API_VERSION_CASE_REVISION_NOT_FOUND,
    API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID,
    API_VERSION_API_INFO_VERSION_DELETE_INVALID,
    API_VERSION_API_INFO_VERSION_REQUIRED,
    AUTO_API_API_CASE_VERSION_PARTS_EDITING_REVISION_VERSION_DELETE_NOT_ALLOWED,
    AUTO_API_API_CASE_VERSION_PARTS_EDITING_REVISION_DELETE_NOT_ALLOWED,
    AUTO_API_API_CASE_VERSION_PARTS_EDITING_REVISION_TASK_DELETE_BINDING_NOT_ALLOWED,
    AutoApiError,
)
from src.apps.auto_api.models import (
    ApiCase,
    ApiCaseDetailed,
    ApiCaseDetailedParameter,
    ApiCaseRelease,
    ApiCaseRevision,
    ApiInfoRevision,
)
from src.apps.auto_api.schemas.config_fields import (
    API_CASE_CONFIG_FIELDS,
)
from src.apps.auto_api.schemas.version import ApiCaseRevisionPayloadModel


class ApiCaseRevisionEditingMixin:
    @classmethod
    @transaction.atomic
    def checkout_to_editing(
            cls,
            case_id: int,
            revision_id: int,
            *,
            operator_id: int | None,
            restore_missing_dependencies: bool = False,
    ) -> ApiCase:
        api_case = ApiCase.objects.select_for_update().filter(id=case_id).first()
        if api_case is None:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(case_id,))
        revision = ApiCaseRevision.objects.filter(id=revision_id, api_case_id=case_id).first()
        if revision is None:
            raise AutoApiError(API_VERSION_CASE_REVISION_NOT_FOUND)
        cls.verify_revision(revision)
        payload = deepcopy(revision.payload)
        if not isinstance(payload, dict):
            raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
        snapshot = ApiCaseRevisionPayloadModel.from_payload(payload)
        case_payload = snapshot.api_case
        target_project_product_id = case_payload.get('project_product')
        if (
                ApiCaseRelease.objects.filter(
                    api_case_id=api_case.id,
                    status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
                ).exists()
                and target_project_product_id is not None
                and int(target_project_product_id) != api_case.project_product_id
        ):
            raise AutoApiError(API_CASE_PREPUBLICATION_PRODUCT_CHANGE_NOT_ALLOWED)
        step_payloads = [
            item.model_dump()
            for item in snapshot.api_case_detailed
        ]
        if not isinstance(step_payloads, list):
            raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
        impact = cls.inspect_checkout_impact(case_id, revision_id)
        blocked = [item for item in impact['items'] if item['status'] == 'blocked']
        if blocked:
            labels = ', '.join(
                item.get('api_info_name') or f'步骤 {item["step_index"]}'
                for item in blocked[:10]
            )
            raise AutoApiError(API_VERSION_API_INFO_VERSION_REQUIRED, value=(labels,))
        restorable = [item for item in impact['items'] if item['status'] == 'restorable']
        if restorable and not restore_missing_dependencies:
            labels = ', '.join(
                item.get('api_info_name') or f'步骤 {item["step_index"]}'
                for item in restorable[:10]
            )
            raise AutoApiError(API_VERSION_API_INFO_VERSION_DELETE_INVALID, value=(labels,))
        api_revision_ids = [
            step_payload.get('api_info_revision_id')
            for step_payload in step_payloads
            if isinstance(step_payload, dict) and step_payload.get('api_info_revision_id')
        ]
        api_revisions_by_id = {
            api_revision.id: api_revision
            for api_revision in ApiInfoRevision.objects.filter(id__in=api_revision_ids)
        }
        impact_by_logical_id = {
            item['step_logical_id']: item
            for item in impact['items']
        }
        for index, step_payload in enumerate(step_payloads, start=1):
            if not isinstance(step_payload, dict):
                continue
            api_revision_id = step_payload.get('api_info_revision_id')
            api_revision = api_revisions_by_id.get(api_revision_id)
            dependency = impact_by_logical_id.get(step_payload.get('logical_id')) or {}
            if dependency.get('status') == 'restorable':
                api_revision = cls._restore_api_info_from_snapshot(
                    api_case,
                    step_payload,
                    operator_id=operator_id,
                )
                api_revisions_by_id[api_revision_id] = api_revision

        case_field_map = {
            'project_product': 'project_product_id',
            'module': 'module_id',
            'case_people': 'case_people_id',
        }
        for field in (
                'name',
                'case_flow',
                'parametrize',
                'level',
                'scenario_description',
                *API_CASE_CONFIG_FIELDS,
        ):
            case_field_map[field] = field
        for source_field in case_field_map:
            target_field = case_field_map[source_field]
            if source_field in case_payload:
                setattr(api_case, target_field, deepcopy(case_payload[source_field]))
        api_case.update_user_id = operator_id
        api_case.save()

        for step in ApiCaseDetailed.objects.filter(case_id=api_case.id):
            step.delete()

        restored_step_keys = {}
        for index, step_payload in enumerate(step_payloads, start=1):
            if not isinstance(step_payload, dict):
                continue
            api_revision_id = step_payload.get('api_info_revision_id')
            api_revision = api_revisions_by_id.get(api_revision_id)
            step = ApiCaseDetailed.objects.create(
                case=api_case,
                api_info_id=api_revision.api_info_id,
                pinned_api_info_revision=api_revision,
                case_sort=step_payload.get('case_sort') or index,
                execution_config=step_payload.get('execution_config', {}),
                update_user_id=operator_id,
            )
            restored_step_keys[step_payload.get('logical_id') or f"step-{step_payload['id']}"] = f'step-{step.id}'
            for parameter_payload in step_payload.get('api_case_detailed_parameter') or []:
                if not isinstance(parameter_payload, dict):
                    continue
                values = {}
                excluded = {
                    'id',
                    'create_time',
                    'update_time',
                    'case_detailed',
                    'update_user',
                    'update_user_id',
                    'status',
                    'resolved_headers',
                    'missing_header_ids',
                    'gray_configs',
                }
                for field in ApiCaseDetailedParameter._meta.concrete_fields:
                    if field.name in excluded:
                        continue
                    key = field.attname if isinstance(field, models.ForeignKey) else field.name
                    if key in parameter_payload:
                        values[key] = deepcopy(parameter_payload[key])
                    elif field.name in parameter_payload:
                        values[key] = deepcopy(parameter_payload[field.name])
                ApiCaseDetailedParameter.objects.create(
                    case_detailed=step,
                    update_user_id=operator_id,
                    **values,
                )
        api_case.callback_checks = deepcopy(case_payload.get('callback_checks') or [])
        for rule in api_case.callback_checks:
            rule['trigger_step_key'] = restored_step_keys[rule['trigger_step_key']]
        api_case.save(update_fields=['callback_checks'])
        from src.apps.auto_api.services.api_case.mutation import ApiCaseAggregateMutationService
        ApiCaseAggregateMutationService.rebuild_case_flow(api_case.id)
        api_case.refresh_from_db()
        return api_case

    @classmethod
    @transaction.atomic
    def delete_unpublished_revision(cls, case_id: int, revision_id: int) -> dict:
        revision = ApiCaseRevision.objects.select_for_update().filter(
            id=revision_id,
            api_case_id=case_id,
        ).first()
        if revision is None:
            raise AutoApiError(API_VERSION_CASE_REVISION_NOT_FOUND)
        if ApiCaseRelease.objects.filter(
                revision_id=revision.id,
                status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
        ).exists():
            raise AutoApiError(API_CASE_PREPUBLICATION_REVISION_DELETE_NOT_ALLOWED)
        if ApiCaseRelease.objects.filter(revision_id=revision.id).exists():
            raise AutoApiError(AUTO_API_API_CASE_VERSION_PARTS_EDITING_REVISION_VERSION_DELETE_NOT_ALLOWED)
        if ApiCaseRevision.objects.filter(parent_revision_id=revision.id).exists():
            raise AutoApiError(AUTO_API_API_CASE_VERSION_PARTS_EDITING_REVISION_DELETE_NOT_ALLOWED)
        from src.apps.task_center.models import TasksDetails
        from src.apps.test_center.models import TestSuiteDetails
        if TasksDetails.objects.filter(api_case_revision_id=revision.id).exists():
            raise AutoApiError(AUTO_API_API_CASE_VERSION_PARTS_EDITING_REVISION_TASK_DELETE_BINDING_NOT_ALLOWED)
        detached_report_detail_count = TestSuiteDetails.objects.filter(
            api_case_revision_id=revision.id,
        ).update(
            api_case_revision_id=None,
            config_checksum=None,
        )
        deleted_id = revision.id
        revision_no = revision.revision_no
        revision.delete()
        return {
            'revision_id': deleted_id,
            'revision_no': revision_no,
            'detached_report_detail_count': detached_report_detail_count,
        }

    @classmethod
    def detach_report_references_for_case(cls, case_id: int) -> int:
        """删除 Case 前解除历史报告对版本表的可选追溯链接。"""
        from src.apps.test_center.models import TestSuiteDetails

        return TestSuiteDetails.objects.filter(
            models.Q(api_case_revision__api_case_id=case_id)
            | models.Q(api_case_release__api_case_id=case_id)
        ).update(
            api_case_revision_id=None,
            api_case_release_id=None,
            config_checksum=None,
        )
