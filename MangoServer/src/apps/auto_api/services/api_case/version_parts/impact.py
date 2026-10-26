from copy import deepcopy
from typing import Any

from src.apps.auto_api.enums import ApiCaseReleaseStatusEnum
from src.apps.auto_api.exceptions import (
    API_VERSION_CASE_REVISION_NOT_FOUND,
    API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID,
    API_VERSION_API_INFO_VERSION_REQUIRED,
    AutoApiError,
)
from src.apps.auto_api.models import (
    ApiCase,
    ApiCaseDetailed,
    ApiCaseRelease,
    ApiCaseRevision,
    ApiInfo,
    ApiInfoRevision,
    ModuleCoverageModuleInterface,
)
from src.apps.auto_api.schemas.version import ApiCaseRevisionPayloadModel
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from ..snapshot import (
    ApiCasePublicationState,
    ApiExecutableSnapshotService,
)


class ApiCaseRevisionImpactMixin:
    @classmethod
    def inspect_checkout_impact(cls, case_id: int, revision_id: int) -> dict[str, Any]:
        revision = ApiCaseRevision.objects.filter(id=revision_id, api_case_id=case_id).first()
        if revision is None:
            raise AutoApiError(API_VERSION_CASE_REVISION_NOT_FOUND)
        cls.verify_revision(revision)
        payload = ApiCaseRevisionPayloadModel.from_payload(
            revision.payload if isinstance(revision.payload, dict) else {}
        )
        revision_ids = [item.api_info_revision_id for item in payload.api_case_detailed]
        revisions_by_id = {
            item.id: item
            for item in ApiInfoRevision.objects.filter(id__in=revision_ids).select_related('api_info')
        }
        from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
        items = []
        for index, step in enumerate(payload.api_case_detailed, start=1):
            live_revision = revisions_by_id.get(step.api_info_revision_id)
            live_available = bool(
                live_revision and
                live_revision.api_info_id == step.api_info_id and
                live_revision.checksum == ApiInfoRevisionService.checksum(live_revision.payload)
            )
            snapshot = step.api_info_snapshot if isinstance(step.api_info_snapshot, dict) else None
            snapshot_available = False
            snapshot_error = None
            if snapshot:
                try:
                    if (
                            snapshot.get('id') != step.api_info_id or
                            snapshot.get('revision_id') != step.api_info_revision_id or
                            not isinstance(snapshot.get('payload'), dict)
                    ):
                        raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
                    ApiInfoRevisionService.verify_snapshot_payload(
                        snapshot['payload'],
                        snapshot_schema_version=snapshot.get('snapshot_schema_version'),
                        checksum=snapshot.get('checksum'),
                        executable=True,
                    )
                    snapshot_available = True
                except AutoApiError as error:
                    snapshot_error = error.msg
            status = 'available' if live_available else ('restorable' if snapshot_available else 'blocked')
            reason = None
            if status == 'restorable':
                reason = '原接口或接口修订已删除，将从历史快照创建新接口和新修订'
            elif status == 'blocked':
                reason = snapshot_error or '旧版历史数据未保存完整接口快照，无法自动恢复'
            items.append({
                'step_index': index,
                'step_logical_id': step.logical_id,
                'api_info_id': step.api_info_id,
                'api_info_name': (snapshot or {}).get('name'),
                'api_info_revision_id': step.api_info_revision_id,
                'api_info_revision_no': (
                    live_revision.revision_no
                    if live_revision
                    else (snapshot or {}).get('revision_no')
                ),
                'status': status,
                'source_available': live_available,
                'snapshot_available': snapshot_available,
                'reason': reason,
            })
        return {
            'case_id': case_id,
            'revision_id': revision_id,
            'can_checkout': all(item['status'] != 'blocked' for item in items),
            'requires_restore': any(item['status'] == 'restorable' for item in items),
            'items': items,
        }

    @classmethod
    def find_api_info_history_references(
            cls,
            api_info_id: int,
            *,
            api_info_revision_id: int | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        self_contained = []
        legacy = []
        from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
        for revision in ApiQuerySelector.iter_api_case_revision_payloads():
            raw_payload = revision.payload if isinstance(revision.payload, dict) else {}
            try:
                payload = ApiCaseRevisionPayloadModel.from_payload(raw_payload)
            except (TypeError, ValueError):
                payload = None
            if payload is None or (
                    not payload.api_case_detailed and
                    isinstance(raw_payload.get('steps'), list)
            ):
                for step in raw_payload.get('steps') or []:
                    if not isinstance(step, dict):
                        continue
                    raw_api_info_id = step.get('api_info_id') or step.get('api_info')
                    raw_revision_id = step.get('api_info_revision_id')
                    if raw_api_info_id != api_info_id:
                        continue
                    if api_info_revision_id is not None and raw_revision_id != api_info_revision_id:
                        continue
                    legacy.append({
                        'case_id': revision.api_case_id,
                        'case_revision_id': revision.id,
                        'case_revision_no': revision.revision_no,
                        'step_logical_id': step.get('logical_id'),
                        'api_info_revision_id': raw_revision_id,
                    })
                continue
            for step in payload.api_case_detailed:
                if step.api_info_id != api_info_id:
                    continue
                if api_info_revision_id is not None and step.api_info_revision_id != api_info_revision_id:
                    continue
                item = {
                    'case_id': revision.api_case_id,
                    'case_revision_id': revision.id,
                    'case_revision_no': revision.revision_no,
                    'step_logical_id': step.logical_id,
                    'api_info_revision_id': step.api_info_revision_id,
                }
                snapshot_valid = False
                snapshot = step.api_info_snapshot
                if isinstance(snapshot, dict):
                    try:
                        if (
                                snapshot.get('id') != step.api_info_id or
                                snapshot.get('revision_id') != step.api_info_revision_id or
                                not isinstance(snapshot.get('payload'), dict)
                        ):
                            raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
                        ApiInfoRevisionService.verify_snapshot_payload(
                            snapshot['payload'],
                            snapshot_schema_version=snapshot.get('snapshot_schema_version'),
                            checksum=snapshot.get('checksum'),
                            executable=True,
                        )
                        snapshot_valid = True
                    except AutoApiError:
                        snapshot_valid = False
                if snapshot_valid:
                    self_contained.append(item)
                else:
                    legacy.append(item)
        self_contained.sort(key=lambda item: item['case_revision_no'], reverse=True)
        legacy.sort(key=lambda item: item['case_revision_no'], reverse=True)
        return {'self_contained': self_contained, 'legacy': legacy}

    @classmethod
    def inspect_api_info_delete_dependencies(cls, api_info_id: int) -> dict[str, Any]:
        editing_steps = list(
            ApiCaseDetailed.objects.select_related('case')
            .filter(api_info_id=api_info_id)
            .order_by('case_id', 'case_sort', 'id')
        )
        history = cls.find_api_info_history_references(api_info_id)
        module_coverage_consumers = list(
            ModuleCoverageModuleInterface.objects.filter(
                api_info_id=api_info_id,
                removed_at__isnull=True,
            ).select_related("module").order_by("module_id", "id")
        )
        blockers = []
        if editing_steps:
            blockers.append('接口仍被当前编辑态 API Case 步骤引用')
        if history['legacy']:
            blockers.append('接口仍被未内嵌完整接口配置的旧版 Case 快照引用')
        if module_coverage_consumers:
            blockers.append('接口仍被模块覆盖台账使用')
        return {
            'can_delete': not blockers,
            'editing_steps': editing_steps,
            'self_contained_history_references': history['self_contained'],
            'legacy_history_references': history['legacy'],
            'module_coverage_consumers': module_coverage_consumers,
            'blockers': blockers,
        }

    @classmethod
    def _restore_api_info_from_snapshot(
            cls,
            api_case: ApiCase,
            step_payload: dict[str, Any],
            *,
            operator_id: int | None,
    ) -> ApiInfoRevision:
        snapshot = step_payload.get('api_info_snapshot') or {}
        revision_payload = deepcopy(snapshot.get('payload'))
        if not isinstance(revision_payload, dict):
            raise AutoApiError(API_VERSION_API_INFO_VERSION_REQUIRED, value=(step_payload.get('logical_id'),))
        from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
        ApiInfoRevisionService.verify_snapshot_payload(
            revision_payload,
            snapshot_schema_version=snapshot.get('snapshot_schema_version'),
            checksum=snapshot.get('checksum'),
            executable=True,
        )
        runtime_payload = ApiInfoRuntimeService.normalize_payload(revision_payload)
        original_name = snapshot.get('name') or f'接口 {snapshot.get("id")}'
        api_info = ApiInfo.objects.create(
            project_product_id=snapshot.get('project_product_id') or api_case.project_product_id,
            module_id=snapshot.get('module_id') or api_case.module_id,
            update_user_id=operator_id,
            name=f'{original_name}（历史恢复）',
            url=runtime_payload.get('url') or '',
            protocol_type=runtime_payload.get('protocol_type') or 'http',
            posterior_json_path=deepcopy(runtime_payload.get('posterior_json_path') or []),
            posterior_re=deepcopy(runtime_payload.get('posterior_re') or []),
            posterior_func=runtime_payload.get('posterior_func'),
            status=2,
        )
        ApiInfoRuntimeService.apply_payload(api_info, revision_payload)
        api_info.update_user_id = operator_id
        api_info.save()
        ApiInfoRuntimeService.restore_mcp_binding(api_info)
        ApiInfoRuntimeService.restore_grpc_binding(api_info)
        ApiInfoRuntimeService.sync_protocol_config(api_info)
        restored_revision = ApiInfoRevisionService.record_current(
            api_info.id,
            operator_id=operator_id,
            source='case_history_restore',
            summary=(
                f'由 API Case {api_case.id} 历史快照恢复；'
                f'原接口 ID {snapshot.get("id")}，原修订 ID {snapshot.get("revision_id")}'
            ),
        )
        ApiInfoRevisionService.publish(
            api_info.id,
            restored_revision.id,
            publisher_id=operator_id,
            release_note='由 API Case 历史版本迁出恢复',
        )
        return restored_revision

    @classmethod
    def get_publication_state(cls, case_id: int) -> ApiCasePublicationState:
        current_revision = ApiCaseRevision.objects.filter(api_case_id=case_id).order_by('-revision_no').first()
        api_case = ApiCase.objects.filter(id=case_id).first()
        prepublication = ApiCaseRelease.objects.select_related('revision').filter(
            api_case_id=case_id,
            status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
        ).first()
        prepublished_revision = prepublication.revision if prepublication else None
        release = ApiQuerySelector.current_published_case_releases().filter(
            api_case_id=case_id,
        ).select_related('revision').order_by('-version_no').first()
        if release is None:
            return ApiCasePublicationState(
                publication_status=(
                    cls.PUBLICATION_PREPUBLISHED
                    if prepublished_revision is not None
                    else cls.PUBLICATION_UNPUBLISHED
                ),
                current_revision_id=current_revision.id if current_revision else None,
                current_revision_no=current_revision.revision_no if current_revision else None,
                published_release_id=None,
                published_revision_id=None,
                published_version_label=None,
                prepublished_revision_id=prepublished_revision.id if prepublished_revision else None,
                prepublished_revision_no=prepublished_revision.revision_no if prepublished_revision else None,
                has_unpublished_changes=False,
            )
        if api_case is None:
            has_unpublished_changes = False
        else:
            try:
                from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService

                payload = ApiExecutableSnapshotService.capture_case(
                    api_case,
                    lambda api_info: ApiInfoRevisionService.resolve_current_published(api_info.id),
                )
                has_unpublished_changes = cls.checksum(payload) != release.revision.checksum
            except AutoApiError:
                has_unpublished_changes = True
        return ApiCasePublicationState(
            publication_status=cls.PUBLICATION_PUBLISHED,
            current_revision_id=current_revision.id if current_revision else release.revision_id,
            current_revision_no=current_revision.revision_no if current_revision else release.revision.revision_no,
            published_release_id=release.id,
            published_revision_id=release.revision_id,
            published_version_label=release.version_label,
            prepublished_revision_id=prepublished_revision.id if prepublished_revision else None,
            prepublished_revision_no=prepublished_revision.revision_no if prepublished_revision else None,
            has_unpublished_changes=has_unpublished_changes,
        )
