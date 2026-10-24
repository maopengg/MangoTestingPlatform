from copy import deepcopy
from types import MappingProxyType

from src.apps.auto_api.exceptions import (
    API_VERSION_CASE_REVISION_NOT_FOUND,
    API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import (
    ApiCase,
    ApiCaseDetailed,
    ApiCaseDetailedParameter,
    ApiCaseRevision,
    ApiInfo,
    ApiInfoRevision,
)
from src.apps.auto_api.schemas.version import ApiCaseRevisionPayloadModel
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from ..snapshot import (
    ApiCaseExecutionAggregate,
    ApiExecutableSnapshotService,
)


class ApiCaseRevisionLoadingMixin:
    @classmethod
    def load_execution_revision(cls, revision_id: int) -> ApiCaseExecutionAggregate:
        revision = ApiCaseRevision.objects.filter(id=revision_id).first()
        if revision is None:
            raise AutoApiError(API_VERSION_CASE_REVISION_NOT_FOUND)
        cls.verify_execution_revision(revision)
        payload = ApiCaseRevisionPayloadModel.from_payload(
            revision.payload if isinstance(revision.payload, dict) else {}
        )
        step_payloads = [
            item.model_dump()
            for item in payload.api_case_detailed
        ]
        if not isinstance(step_payloads, list):
            raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)

        revision_ids = [
            step_payload.get('api_info_revision_id')
            for step_payload in step_payloads
            if isinstance(step_payload, dict)
        ]
        api_revisions = ApiInfoRevision.objects.filter(id__in=revision_ids)
        api_revisions_by_id = {item.id: item for item in api_revisions}
        api_infos_by_id = {
            item.id: item
            for item in ApiInfo.objects.filter(id__in={revision.api_info_id for revision in api_revisions})
        }
        api_case = ApiExecutableSnapshotService.hydrate_model(ApiCase, payload.api_case)
        ApiExecutableSnapshotService.apply_case_execution_config(api_case, payload.api_case)
        resolved_front_headers = payload.runtime.resolved_front_headers
        if not isinstance(resolved_front_headers, dict):
            raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
        api_case._revision_front_headers = MappingProxyType(deepcopy(resolved_front_headers))
        gray_configs = payload.runtime.gray_configs
        if not isinstance(gray_configs, list):
            raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
        api_case._revision_gray_configs = tuple(deepcopy(gray_configs))
        api_case._revision_dependency_freeze_level = payload.runtime.dependency_freeze_level
        steps = []
        api_revision_dependencies = []
        parameters_by_step = {}
        for step_payload in step_payloads:
            if not isinstance(step_payload, dict):
                raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
            logical_id = step_payload.get('logical_id')
            api_revision_id = step_payload.get('api_info_revision_id')
            api_revision = api_revisions_by_id.get(api_revision_id)
            api_info_id = step_payload.get('api_info_id')
            api_info_snapshot = step_payload.get('api_info_snapshot')
            if not logical_id:
                raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
            if isinstance(api_info_snapshot, dict):
                revision_payload = api_info_snapshot.get('payload')
                if (
                        api_info_snapshot.get('id') != api_info_id or
                        api_info_snapshot.get('revision_id') != api_revision_id or
                        not isinstance(revision_payload, dict)
                ):
                    raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
                api_info = ApiInfo(
                    id=api_info_snapshot.get('id'),
                    project_product_id=api_info_snapshot.get('project_product_id'),
                    module_id=api_info_snapshot.get('module_id'),
                    name=api_info_snapshot.get('name') or f'接口 {api_info_id}',
                    url='',
                )
                api_info = ApiInfoRuntimeService.apply_payload(api_info, revision_payload)
                dependency_checksum = api_info_snapshot.get('checksum')
            else:
                if (
                        api_revision is None or
                        api_revision.api_info_id != api_info_id or
                        api_revision.checksum != cls.checksum(api_revision.payload)
                ):
                    raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
                api_info = api_infos_by_id.get(api_revision.api_info_id)
                if api_info is None:
                    raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
                api_info = ApiInfoRuntimeService.apply_payload(deepcopy(api_info), api_revision.payload)
                dependency_checksum = api_revision.checksum
            step_payload['api_info_id'] = api_info_id
            step = ApiExecutableSnapshotService.hydrate_model(ApiCaseDetailed, step_payload)
            step.api_info = api_info
            parameter_payloads = step_payload.get('api_case_detailed_parameter')
            if not isinstance(parameter_payloads, list):
                raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
            parameters = []
            for item in parameter_payloads:
                if not isinstance(item, dict):
                    raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
                resolved_headers = item.get('resolved_headers')
                if resolved_headers is not None and not isinstance(resolved_headers, dict):
                    raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
                parameter = ApiExecutableSnapshotService.hydrate_model(
                    ApiCaseDetailedParameter,
                    item,
                )
                parameter._revision_headers = (
                    None
                    if resolved_headers is None
                    else MappingProxyType(deepcopy(resolved_headers))
                )
                parameter_gray_configs = item.get('gray_configs')
                if not isinstance(parameter_gray_configs, list):
                    raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
                parameter._revision_gray_configs = tuple(deepcopy(parameter_gray_configs))
                parameters.append(parameter)
            parameters = tuple(parameters)
            if len(parameters) != len(parameter_payloads):
                raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
            steps.append(step)
            api_revision_dependencies.append({
                'step_logical_id': logical_id,
                'api_info_id': api_info_id,
                'api_info_revision_id': api_revision_id,
                'checksum': dependency_checksum,
            })
            parameters_by_step[step.id] = parameters
        data_factory_configs = payload.dependencies.data_factory_configs or []
        if not isinstance(data_factory_configs, list):
            raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
        return ApiCaseExecutionAggregate(
            revision_id=revision.id,
            revision_no=revision.revision_no,
            checksum=revision.checksum,
            api_case=api_case,
            steps=tuple(steps),
            api_revision_dependencies=tuple(api_revision_dependencies),
            data_factory_configs=tuple(deepcopy(data_factory_configs)),
            _parameters_by_step=MappingProxyType(parameters_by_step),
        )
