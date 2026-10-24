import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any

from django.db import models, transaction

from src.apps.auto_api.enums import ApiProtocolTypeEnum
from src.apps.auto_api.exceptions import (
    API_VERSION_API_INFO_NOT_FOUND,
    API_VERSION_API_INFO_REVISION_NOT_FOUND,
    API_VERSION_API_INFO_REVISION_CONFIG_FAILED,
    API_VERSION_API_INFO_VERSION_INVALID,
    API_VERSION_API_INFO_VERSION_UNSUPPORTED,
    API_VERSION_API_INFO_REVISION_CONFIG_EXECUTION_GENERATE_INVALID,
    API_VERSION_API_INFO_REVISION_DELETE_NOT_ALLOWED,
    AUTO_API_API_INFO_VERSION_REVISION_VERSION_DELETE_NOT_ALLOWED,
    AUTO_API_API_INFO_VERSION_STEP_REVISION_DELETE_NOT_ALLOWED,
    AUTO_API_API_INFO_VERSION_REVISION_DELETE_NOT_ALLOWED,
    AutoApiError,
    GRPC_API_API_INFO_BINDING_REQUIRED,
    MCP_API_API_INFO_VERSION_RECORD_EXECUTION_BINDING_REQUIRED,
)
from src.apps.auto_api.models import (
    ApiCaseDetailed,
    ApiInfo,
    ApiInfoGrpcConfig,
    ApiInfoHttpConfig,
    ApiInfoMcpBinding,
    ApiInfoMcpConfig,
    ApiInfoRelease,
    ApiInfoRevision,
    ApiInfoWebSocketConfig,
)
from src.apps.auto_api.schemas.version import ApiInfoRevisionPayloadModel


@dataclass(frozen=True)
class ApiInfoPublicationState:
    publication_status: str
    current_revision_id: int | None
    current_revision_no: int | None
    published_release_id: int | None
    published_revision_id: int | None
    published_version_label: str | None
    has_unpublished_changes: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ApiInfoRevisionService:
    PUBLICATION_UNPUBLISHED = 'unpublished'
    PUBLICATION_PUBLISHED = 'published'
    PUBLICATION_DRAFT_CHANGED = 'draft_changed'

    @staticmethod
    def checksum(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    @classmethod
    def ensure_current_editing_run_succeeded(cls, api_info_id: int):
        from mangotools.enums import StatusEnum
        from src.apps.test_center.models import ExecutionResult
        from src.apps.test_center.services.execution_result import ExecutionResultService

        api_info = ApiInfo.objects.filter(id=api_info_id).only('id', 'update_time').first()
        if api_info is None:
            raise AutoApiError(API_VERSION_API_INFO_NOT_FOUND, value=(api_info_id,))
        protocol_update_times = [
            model.objects.filter(api_info_id=api_info_id).values_list('update_time', flat=True).first()
            for model in (
                ApiInfoHttpConfig,
                ApiInfoWebSocketConfig,
                ApiInfoMcpBinding,
                ApiInfoMcpConfig,
                ApiInfoGrpcConfig,
            )
        ]
        config_update_time = max(
            value
            for value in (api_info.update_time, *protocol_update_times)
            if value is not None
        )
        latest = ExecutionResult.objects.filter(
            target_type=ExecutionResultService.TARGET_API_INFO,
            target_id=api_info_id,
            revision_id__isnull=True,
            release_id__isnull=True,
            source_type__in=[
                ExecutionResultService.SOURCE_PAGE,
                ExecutionResultService.SOURCE_MCP,
            ],
        ).order_by('-create_time', '-id').first()
        if (
                latest is None
                or latest.status != StatusEnum.SUCCESS.value
                or latest.create_time < config_update_time
        ):
            raise AutoApiError(API_VERSION_API_INFO_REVISION_CONFIG_EXECUTION_GENERATE_INVALID)

    @classmethod
    @transaction.atomic
    def record_current(
            cls,
            api_info_id: int,
            *,
            operator_id: int | None = None,
            source: str = 'system',
            summary: str | None = None,
    ) -> ApiInfoRevision:
        api_info = ApiInfo.objects.select_for_update().filter(id=api_info_id).first()
        if api_info is None:
            raise AutoApiError(API_VERSION_API_INFO_NOT_FOUND, value=(api_info_id,))
        from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
        payload = ApiInfoRuntimeService.capture_revision_payload(api_info)
        checksum = cls.checksum(payload)
        latest = ApiInfoRevision.objects.filter(api_info_id=api_info_id).order_by('-revision_no').first()
        if latest and latest.checksum == checksum:
            return latest
        return ApiInfoRevision.objects.create(
            api_info=api_info,
            revision_no=(latest.revision_no if latest else 0) + 1,
            parent_revision=latest,
            snapshot_schema_version=2,
            payload=payload,
            checksum=checksum,
            source=source,
            operator_id=operator_id,
            summary=summary,
        )

    @classmethod
    def verify_revision(cls, revision: ApiInfoRevision, *, executable: bool = False):
        cls.verify_snapshot_payload(
            revision.payload,
            snapshot_schema_version=revision.snapshot_schema_version,
            checksum=revision.checksum,
            executable=executable,
        )

    @classmethod
    def verify_snapshot_payload(
            cls,
            payload: dict,
            *,
            snapshot_schema_version: int,
            checksum: str,
            executable: bool = False,
    ):
        if snapshot_schema_version != 2:
            raise AutoApiError(API_VERSION_API_INFO_VERSION_UNSUPPORTED, value=(snapshot_schema_version,))
        try:
            parsed_payload = ApiInfoRevisionPayloadModel.from_payload(payload)
        except (TypeError, ValueError) as error:
            raise AutoApiError(API_VERSION_API_INFO_REVISION_CONFIG_FAILED, error=str(error)) from error
        if checksum != cls.checksum(payload):
            raise AutoApiError(API_VERSION_API_INFO_REVISION_CONFIG_FAILED)
        api_info_payload = parsed_payload.api_info if isinstance(parsed_payload.api_info, dict) else {}
        if executable and api_info_payload.get('protocol_type') == ApiProtocolTypeEnum.MCP.value:
            mcp_binding = api_info_payload.get('mcp_binding')
            if not isinstance(mcp_binding, dict) or not mcp_binding.get('tool_name') or not mcp_binding.get(
                    'tool_type'):
                raise AutoApiError(MCP_API_API_INFO_VERSION_RECORD_EXECUTION_BINDING_REQUIRED)
        if executable and api_info_payload.get('protocol_type') == ApiProtocolTypeEnum.GRPC.value:
            grpc_binding = api_info_payload.get('grpc_binding')
            if (
                    not isinstance(grpc_binding, dict)
                    or not grpc_binding.get('full_method')
                    or not grpc_binding.get('request_message')
                    or not grpc_binding.get('response_message')
            ):
                raise AutoApiError(GRPC_API_API_INFO_BINDING_REQUIRED)

    @classmethod
    @transaction.atomic
    def publish(
            cls,
            api_info_id: int,
            revision_id: int,
            *,
            publisher_id: int | None,
            release_note: str | None = None,
    ) -> ApiInfoRelease:
        api_info = ApiInfo.objects.select_for_update().filter(id=api_info_id).first()
        if api_info is None:
            raise AutoApiError(API_VERSION_API_INFO_NOT_FOUND, value=(api_info_id,))
        revision = ApiInfoRevision.objects.filter(id=revision_id, api_info_id=api_info_id).first()
        if revision is None:
            raise AutoApiError(API_VERSION_API_INFO_REVISION_NOT_FOUND)
        cls.verify_revision(revision, executable=True)
        releases = ApiInfoRelease.objects.select_for_update().filter(api_info_id=api_info_id)
        current = releases.filter(is_current=True).order_by('-version_no').first()
        if current and current.revision_id == revision.id and current.status == ApiInfoRelease.STATUS_PUBLISHED:
            return current
        version_no = releases.aggregate(max_version=models.Max('version_no'))['max_version'] or 0
        releases.filter(is_current=True).update(is_current=False)
        return ApiInfoRelease.objects.create(
            api_info=api_info,
            revision=revision,
            version_no=version_no + 1,
            version_label=f'V{version_no + 1}',
            status=ApiInfoRelease.STATUS_PUBLISHED,
            is_current=True,
            release_note=release_note,
            published_by_id=publisher_id,
            replaced_release=current,
        )

    @classmethod
    @transaction.atomic
    def checkout_to_editing(
            cls,
            api_info_id: int,
            revision_id: int,
            *,
            operator_id: int | None,
            summary: str | None = None,
    ) -> ApiInfo:
        api_info = ApiInfo.objects.select_for_update().filter(id=api_info_id).first()
        if api_info is None:
            raise AutoApiError(API_VERSION_API_INFO_NOT_FOUND, value=(api_info_id,))
        target = ApiInfoRevision.objects.filter(id=revision_id, api_info_id=api_info_id).first()
        if target is None:
            raise AutoApiError(API_VERSION_API_INFO_REVISION_NOT_FOUND)
        cls.verify_revision(target)
        from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
        ApiInfoRuntimeService.apply_payload(
            api_info,
            deepcopy(ApiInfoRevisionPayloadModel.from_payload(target.payload).api_info),
        )
        ApiInfoRuntimeService.restore_mcp_binding(api_info)
        ApiInfoRuntimeService.restore_grpc_binding(api_info)
        ApiInfoRuntimeService.sync_protocol_config(api_info)
        api_info.update_user_id = operator_id
        api_info.save()
        return api_info

    @classmethod
    def restore(
            cls,
            api_info_id: int,
            revision_id: int,
            *,
            operator_id: int | None,
            summary: str | None = None,
    ) -> ApiInfoRevision:
        cls.checkout_to_editing(
            api_info_id,
            revision_id,
            operator_id=operator_id,
            summary=summary,
        )
        return ApiInfoRevision.objects.get(id=revision_id, api_info_id=api_info_id)

    @classmethod
    def get_publication_state(cls, api_info_id: int) -> ApiInfoPublicationState:
        current_revision = ApiInfoRevision.objects.filter(api_info_id=api_info_id).order_by('-revision_no').first()
        release = ApiInfoRelease.objects.filter(
            api_info_id=api_info_id,
            is_current=True,
            status=ApiInfoRelease.STATUS_PUBLISHED,
        ).select_related('revision').order_by('-version_no').first()
        if release is None:
            return ApiInfoPublicationState(
                publication_status=cls.PUBLICATION_UNPUBLISHED,
                current_revision_id=current_revision.id if current_revision else None,
                current_revision_no=current_revision.revision_no if current_revision else None,
                published_release_id=None,
                published_revision_id=None,
                published_version_label=None,
                has_unpublished_changes=False,
            )
        api_info = ApiInfo.objects.filter(id=api_info_id).first()
        if api_info is None:
            changed = False
        else:
            from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
            changed = cls.checksum(
                ApiInfoRuntimeService.capture_revision_payload(api_info)) != release.revision.checksum
        return ApiInfoPublicationState(
            publication_status=cls.PUBLICATION_DRAFT_CHANGED if changed else cls.PUBLICATION_PUBLISHED,
            current_revision_id=current_revision.id if current_revision else release.revision_id,
            current_revision_no=current_revision.revision_no if current_revision else release.revision.revision_no,
            published_release_id=release.id,
            published_revision_id=release.revision_id,
            published_version_label=release.version_label,
            has_unpublished_changes=changed,
        )

    @classmethod
    def resolve_current_published(cls, api_info_id: int) -> ApiInfoRevision:
        release = ApiInfoRelease.objects.filter(
            api_info_id=api_info_id,
            is_current=True,
            status=ApiInfoRelease.STATUS_PUBLISHED,
        ).select_related('revision').first()
        if release is None:
            raise AutoApiError(API_VERSION_API_INFO_VERSION_INVALID)
        cls.verify_revision(release.revision, executable=True)
        return release.revision

    @classmethod
    @transaction.atomic
    def delete_unpublished_revision(cls, api_info_id: int, revision_id: int) -> dict:
        revision = ApiInfoRevision.objects.select_for_update().filter(
            id=revision_id,
            api_info_id=api_info_id,
        ).first()
        if revision is None:
            raise AutoApiError(API_VERSION_API_INFO_REVISION_NOT_FOUND)
        if ApiInfoRelease.objects.filter(revision_id=revision.id).exists():
            raise AutoApiError(AUTO_API_API_INFO_VERSION_REVISION_VERSION_DELETE_NOT_ALLOWED)
        if ApiCaseDetailed.objects.filter(pinned_api_info_revision_id=revision.id).exists():
            raise AutoApiError(AUTO_API_API_INFO_VERSION_STEP_REVISION_DELETE_NOT_ALLOWED)
        from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
        history = ApiCaseRevisionService.find_api_info_history_references(
            api_info_id,
            api_info_revision_id=revision.id,
        )
        if history['legacy']:
            raise AutoApiError(API_VERSION_API_INFO_REVISION_DELETE_NOT_ALLOWED,
                               value=(f'{len(history["legacy"])} 个旧版 Case 快照',),
                               )
        if ApiInfoRevision.objects.filter(parent_revision_id=revision.id).exists():
            raise AutoApiError(AUTO_API_API_INFO_VERSION_REVISION_DELETE_NOT_ALLOWED)
        deleted_id = revision.id
        revision_no = revision.revision_no
        revision.delete()
        return {'revision_id': deleted_id, 'revision_no': revision_no}
