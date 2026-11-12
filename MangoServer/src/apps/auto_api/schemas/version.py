from copy import deepcopy
from typing import Any

from pydantic import Field

from src.common.schemas import OpenSchema, StrictSchema
from src.apps.auto_api.enums.case import ApiRevisionUnsupportedDependencyEnum


class ApiCaseDetailedParameterSnapshotModel(OpenSchema):
    allow_failure: bool = False
    resolved_headers: dict[str, Any] | None = None
    missing_header_ids: list[Any] = Field(default_factory=list)


class ApiCaseDetailedSnapshotModel(OpenSchema):
    logical_id: str
    api_info_id: int
    api_info_revision_id: int
    api_info_snapshot: dict[str, Any] | None = None
    api_case_detailed_parameter: list[ApiCaseDetailedParameterSnapshotModel] = Field(default_factory=list)


class ApiCaseRevisionRuntimeSnapshotModel(StrictSchema):
    resolved_front_headers: dict[str, Any] = Field(default_factory=dict)
    missing_front_header_ids: list[Any] = Field(default_factory=list)
    dependency_freeze_level: str | None = None
    unsupported_dependency_types: list[str] = Field(default_factory=list)


class ApiCaseRevisionDependenciesSnapshotModel(StrictSchema):
    data_factory_configs: list[dict[str, Any]] = Field(default_factory=list)
    api_revision_dependencies: list[dict[str, Any]] = Field(default_factory=list)


class ApiCaseRevisionPayloadModel(StrictSchema):
    api_case: dict[str, Any] = Field(default_factory=dict)
    api_case_detailed: list[ApiCaseDetailedSnapshotModel] = Field(default_factory=list)
    runtime: ApiCaseRevisionRuntimeSnapshotModel = Field(default_factory=ApiCaseRevisionRuntimeSnapshotModel)
    dependencies: ApiCaseRevisionDependenciesSnapshotModel = Field(
        default_factory=ApiCaseRevisionDependenciesSnapshotModel)

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> 'ApiCaseRevisionPayloadModel':
        value = deepcopy(payload or {})
        runtime = value.setdefault('runtime', {})
        retired = bool(runtime.pop('gray_configs', []))
        for step in value.get('api_case_detailed') or []:
            for parameter in step.get('api_case_detailed_parameter') or []:
                retired = bool(parameter.pop('gray_configs', [])) or retired
        if retired:
            unsupported = runtime.setdefault('unsupported_dependency_types', [])
            marker = ApiRevisionUnsupportedDependencyEnum.RETIRED_GRAY.label
            if marker not in unsupported:
                unsupported.append(marker)
        return cls.model_validate(value)


class ApiInfoRevisionRuntimeSnapshotModel(OpenSchema):
    pass


class ApiInfoRevisionPayloadModel(StrictSchema):
    api_info: dict[str, Any] = Field(default_factory=dict)
    runtime: ApiInfoRevisionRuntimeSnapshotModel = Field(default_factory=ApiInfoRevisionRuntimeSnapshotModel)

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> 'ApiInfoRevisionPayloadModel':
        return cls.model_validate(deepcopy(payload or {}))
