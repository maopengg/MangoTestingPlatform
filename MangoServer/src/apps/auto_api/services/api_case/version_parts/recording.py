import hashlib
import json
from typing import Any

from django.db import models, transaction
from mangotools.enums import TaskEnum

from src.apps.auto_api.enums import ApiCaseReleaseStatusEnum
from src.apps.auto_api.exceptions import (
    API_CASE_REVISION_SUMMARY_INVALID,
    API_CASE_PREPUBLICATION_ALREADY_EXISTS,
    API_CASE_PREPUBLICATION_APPROVAL_FORBIDDEN,
    API_CASE_PREPUBLICATION_CURRENT_REVISION_NOT_ALLOWED,
    API_CASE_PREPUBLICATION_NOT_FOUND,
    API_CASE_PREPUBLICATION_OWNER_REQUIRED,
    API_CASE_PREPUBLICATION_REVISION_FROZEN,
    API_CASE_REVISION_NOT_ACTIVE_CANDIDATE,
    API_CASE_PUBLICATION_REQUIRES_PASSED,
    API_VERSION_CASE_NOT_FOUND,
    API_VERSION_CASE_REVISION_NOT_FOUND,
    API_VERSION_CASE_REVISION_CONFIG_FAILED,
    API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID,
    API_VERSION_API_INFO_VERSION_INVALID,
    API_VERSION_CASE_REVISION_INVALID,
    API_VERSION_CASE_VERSION_UNSUPPORTED,
    API_VERSION_DEPENDENCY_FREEZE_UNSUPPORTED,
    API_VERSION_CASE_VERSION_INVALID,
    API_VERSION_VERSION_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import (
    ApiCase,
    ApiCaseRelease,
    ApiCaseRevision,
    ApiInfo,
    ApiInfoRevision,
)
from src.apps.auto_api.schemas.version import ApiCaseRevisionPayloadModel
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.logging import log
from ..snapshot import (
    ApiExecutableSnapshotService,
)


class ApiCaseRevisionRecordingMixin:
    @staticmethod
    def _schedule_prepublication_todo_sync(project_product_id: int) -> None:
        def reconcile() -> None:
            try:
                from src.apps.task_center.services.workbench.todo import WorkbenchTodoService

                WorkbenchTodoService.reconcile_api_case_prepublication_todos(
                    project_product_ids={project_product_id},
                )
            except Exception as error:
                log.system.error(
                    '同步 API Case 预发布审核待办失败，不影响版本流转：'
                    f'project_product_id={project_product_id}, error={error}'
                )

        transaction.on_commit(reconcile)

    @staticmethod
    def checksum(payload: dict[str, Any]) -> str:
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(',', ':'),
        )
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    @classmethod
    @transaction.atomic
    def record_current(
            cls,
            case_id: int,
            *,
            operator_id: int | None = None,
            source: str = 'system',
            summary: str | None = None,
            change_group_id: str | None = None,
    ) -> ApiCaseRevision:
        summary_limit = ApiCaseRevision._meta.get_field('summary').max_length
        if summary is not None and (not isinstance(summary, str) or len(summary) > summary_limit):
            raise AutoApiError(API_CASE_REVISION_SUMMARY_INVALID, value=(summary_limit,))
        api_case = ApiCase.objects.select_for_update().filter(id=case_id).first()
        if api_case is None:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(case_id,))
        if ApiCaseRelease.objects.filter(
                api_case_id=case_id,
                status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
        ).exists():
            raise AutoApiError(API_CASE_PREPUBLICATION_REVISION_FROZEN)

        def resolve_api_revision(api_info: ApiInfo) -> ApiInfoRevision:
            from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
            try:
                return ApiInfoRevisionService.resolve_current_published(api_info.id)
            except AutoApiError as error:
                if error.code == API_VERSION_API_INFO_VERSION_INVALID.code:
                    raise AutoApiError(API_VERSION_CASE_REVISION_INVALID,
                                       value=(f'接口 {api_info.id} 没有已发布版本',),
                                       ) from error
                raise

        payload = ApiExecutableSnapshotService.capture_case(api_case, resolve_api_revision)
        checksum = cls.checksum(payload)
        latest = ApiCaseRevision.objects.select_for_update().filter(
            api_case_id=case_id,
        ).order_by('-revision_no').first()
        if latest and latest.checksum == checksum:
            return latest

        return ApiCaseRevision.objects.create(
            api_case=api_case,
            revision_no=(latest.revision_no if latest else 0) + 1,
            parent_revision=latest,
            snapshot_schema_version=ApiExecutableSnapshotService.SNAPSHOT_SCHEMA_VERSION,
            payload=payload,
            checksum=checksum,
            source=source,
            operator_id=operator_id,
            summary=summary,
            change_group_id=change_group_id,
        )

    @classmethod
    @transaction.atomic
    def record_execution_snapshot(
            cls,
            case_id: int,
            *,
            operator_id: int | None = None,
    ) -> ApiCaseRevision:
        """冻结当前编辑态供测试报告执行，不改变 Case 或接口的发布状态。"""
        api_case = ApiCase.objects.select_for_update().filter(id=case_id).first()
        if api_case is None:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(case_id,))

        def resolve_api_revision(api_info: ApiInfo) -> ApiInfoRevision:
            from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
            return ApiInfoRevisionService.record_current(
                api_info.id,
                operator_id=operator_id,
                source='batch_execution_snapshot',
                summary=f'API Case {case_id} 批量执行编辑态快照',
            )

        payload = ApiExecutableSnapshotService.capture_case(
            api_case,
            resolve_api_revision,
            require_published_api_revisions=False,
        )
        checksum = cls.checksum(payload)
        latest = ApiCaseRevision.objects.filter(api_case_id=case_id).order_by('-revision_no').first()
        if latest and latest.checksum == checksum:
            return latest
        return ApiCaseRevision.objects.create(
            api_case=api_case,
            revision_no=(latest.revision_no if latest else 0) + 1,
            parent_revision=latest,
            snapshot_schema_version=ApiExecutableSnapshotService.SNAPSHOT_SCHEMA_VERSION,
            payload=payload,
            checksum=checksum,
            source='batch_execution_snapshot',
            operator_id=operator_id,
            summary='批量执行时冻结当前编辑态，不改变发布状态',
        )

    @classmethod
    @transaction.atomic
    def _publish_revision(
            cls,
            case_id: int,
            revision_id: int,
            *,
            publisher_id: int | None,
            release_note: str | None = None,
    ) -> ApiCaseRelease:
        api_case = ApiCase.objects.select_for_update().filter(id=case_id).first()
        if api_case is None:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(case_id,))
        if api_case.status != TaskEnum.SUCCESS.value:
            raise AutoApiError(API_CASE_PUBLICATION_REQUIRES_PASSED)
        revision = ApiCaseRevision.objects.filter(id=revision_id, api_case_id=case_id).first()
        if revision is None:
            raise AutoApiError(API_VERSION_CASE_REVISION_NOT_FOUND)
        cls.verify_execution_revision(revision)
        cls.verify_publishable_revision(revision)

        releases = ApiCaseRelease.objects.select_for_update().filter(api_case_id=case_id)
        current = releases.filter(is_current=True).order_by('-version_no').first()
        if (
                current and
                current.revision_id == revision.id and
                current.status == ApiCaseRelease.STATUS_PUBLISHED
        ):
            return current
        prepublication = releases.filter(
            revision_id=revision.id,
            status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
        ).first()
        version_no = releases.aggregate(max_version=models.Max('version_no'))['max_version'] or 0
        releases.filter(is_current=True).update(is_current=False)
        if prepublication is not None:
            prepublication.status = ApiCaseReleaseStatusEnum.PUBLISHED.value
            prepublication.is_current = True
            prepublication.release_note = release_note
            prepublication.published_by_id = publisher_id
            prepublication.replaced_release = current or prepublication.replaced_release
            prepublication.save(update_fields=[
                'status',
                'is_current',
                'release_note',
                'published_by',
                'replaced_release',
            ])
            return prepublication
        return ApiCaseRelease.objects.create(
            api_case=api_case,
            revision=revision,
            version_no=version_no + 1,
            version_label=f'V{version_no + 1}',
            status=ApiCaseReleaseStatusEnum.PUBLISHED.value,
            is_current=True,
            release_note=release_note,
            published_by_id=publisher_id,
            replaced_release=current,
        )

    @classmethod
    @transaction.atomic
    def submit_prepublication(cls, case_id: int, revision_id: int) -> ApiCaseRelease:
        api_case = ApiCase.objects.select_for_update().filter(id=case_id).first()
        if api_case is None:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(case_id,))
        if api_case.status != TaskEnum.SUCCESS.value:
            raise AutoApiError(API_CASE_PUBLICATION_REQUIRES_PASSED)
        if ApiCaseRelease.objects.filter(
                api_case_id=case_id,
                status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
        ).exists():
            raise AutoApiError(API_CASE_PREPUBLICATION_ALREADY_EXISTS)
        revision = ApiCaseRevision.objects.select_for_update().filter(
            id=revision_id,
            api_case_id=case_id,
        ).first()
        if revision is None:
            raise AutoApiError(API_VERSION_CASE_REVISION_NOT_FOUND)
        if ApiCaseRelease.objects.filter(
                api_case_id=case_id,
                revision_id=revision_id,
                is_current=True,
                status=ApiCaseRelease.STATUS_PUBLISHED,
        ).exists():
            raise AutoApiError(API_CASE_PREPUBLICATION_CURRENT_REVISION_NOT_ALLOWED)
        latest_revision_id = ApiCaseRevision.objects.filter(
            api_case_id=case_id,
        ).order_by('-revision_no').values_list('id', flat=True).first()
        if revision.id != latest_revision_id or ApiCaseRelease.objects.filter(
                revision_id=revision.id,
        ).exists():
            raise AutoApiError(API_CASE_REVISION_NOT_ACTIVE_CANDIDATE)
        if not TestCenterQuerySelector.has_project_product_owner(api_case.project_product_id):
            raise AutoApiError(API_CASE_PREPUBLICATION_OWNER_REQUIRED)
        cls.verify_execution_revision(revision)
        cls.verify_publishable_revision(revision)
        version_no = (
                             ApiCaseRelease.objects.filter(api_case_id=case_id).aggregate(
                                 max_version=models.Max('version_no'),
                             )['max_version']
                             or 0
                     ) + 1
        current = ApiCaseRelease.objects.select_for_update().filter(
            api_case_id=case_id, is_current=True, status=ApiCaseRelease.STATUS_PUBLISHED,
        ).order_by('-version_no').first()
        ApiCaseRelease.objects.filter(api_case_id=case_id, is_current=True).update(is_current=False)
        release = ApiCaseRelease.objects.create(
            api_case=api_case,
            revision=revision,
            version_no=version_no,
            version_label=f'V{version_no}',
            status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
            is_current=False,
            replaced_release=current,
        )
        cls._schedule_prepublication_todo_sync(api_case.project_product_id)
        return release

    @classmethod
    @transaction.atomic
    def approve_prepublication(
            cls,
            case_id: int,
            *,
            operator_id: int | None,
            release_note: str | None = None,
    ) -> ApiCaseRelease:
        api_case = ApiCase.objects.select_for_update().filter(id=case_id).first()
        if api_case is None:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(case_id,))
        cls._verify_product_owner(api_case, operator_id)
        prepublication = ApiCaseRelease.objects.select_for_update().select_related('revision').filter(
            api_case_id=case_id,
            status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
        ).first()
        if prepublication is None:
            raise AutoApiError(API_CASE_PREPUBLICATION_NOT_FOUND)
        release = cls._publish_revision(
            case_id,
            prepublication.revision_id,
            publisher_id=operator_id,
            release_note=release_note,
        )
        cls._schedule_prepublication_todo_sync(api_case.project_product_id)
        return release

    @classmethod
    @transaction.atomic
    def revert_prepublication(cls, case_id: int, *, operator_id: int | None) -> ApiCaseRevision:
        api_case = ApiCase.objects.select_for_update().filter(id=case_id).first()
        if api_case is None:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(case_id,))
        prepublication = ApiCaseRelease.objects.select_for_update().select_related('revision').filter(
            api_case_id=case_id,
            status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
        ).first()
        if prepublication is None:
            raise AutoApiError(API_CASE_PREPUBLICATION_NOT_FOUND)
        revision = prepublication.revision
        # 退回后保持未发布，也清除旧流程遗留的当前版本标记，不恢复历史版本。
        ApiCaseRelease.objects.filter(api_case_id=case_id, is_current=True).update(is_current=False)
        prepublication.delete()
        cls._schedule_prepublication_todo_sync(api_case.project_product_id)
        return revision

    @staticmethod
    def _verify_product_owner(api_case: ApiCase, operator_id: int | None) -> None:
        if not TestCenterQuerySelector.is_project_product_owner(
                api_case.project_product_id,
                operator_id,
        ):
            raise AutoApiError(API_CASE_PREPUBLICATION_APPROVAL_FORBIDDEN)

    @classmethod
    def verify_product_owner(cls, case_id: int, operator_id: int | None) -> None:
        api_case = ApiCase.objects.filter(id=case_id).first()
        if api_case is None:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(case_id,))
        cls._verify_product_owner(api_case, operator_id)

    @classmethod
    @transaction.atomic
    def unpublish(cls, case_id: int, release_id: int) -> ApiCaseRelease:
        api_case = ApiCase.objects.select_for_update().filter(id=case_id).first()
        if api_case is None:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(case_id,))

        release = ApiCaseRelease.objects.select_for_update().filter(
            id=release_id,
            api_case_id=case_id,
        ).first()
        if release is None:
            raise AutoApiError(API_VERSION_CASE_VERSION_INVALID)
        if not release.is_current or release.status != ApiCaseRelease.STATUS_PUBLISHED:
            raise AutoApiError(API_VERSION_VERSION_INVALID)

        updated = ApiCaseRelease.objects.filter(
            id=release.id,
            api_case_id=case_id,
            is_current=True,
            status=ApiCaseRelease.STATUS_PUBLISHED,
        ).update(
            is_current=False,
            status=ApiCaseRelease.STATUS_DEPRECATED,
        )
        if updated != 1:
            raise AutoApiError(API_VERSION_VERSION_INVALID)
        release.refresh_from_db()
        return release

    @classmethod
    def verify_revision(cls, revision: ApiCaseRevision):
        if revision.snapshot_schema_version != ApiExecutableSnapshotService.SNAPSHOT_SCHEMA_VERSION:
            raise AutoApiError(API_VERSION_CASE_VERSION_UNSUPPORTED, value=(revision.snapshot_schema_version,))
        if revision.checksum != cls.checksum(revision.payload):
            raise AutoApiError(API_VERSION_CASE_REVISION_CONFIG_FAILED)

    @classmethod
    def verify_publishable_revision(cls, revision: ApiCaseRevision):
        payload = ApiCaseRevisionPayloadModel.from_payload(
            revision.payload if isinstance(revision.payload, dict) else {}
        )
        step_payloads = payload.api_case_detailed
        if not isinstance(step_payloads, list) or not step_payloads:
            raise AutoApiError(API_VERSION_CASE_REVISION_INVALID, value=('至少需要一个接口步骤',))
        if payload.runtime.missing_front_header_ids:
            raise AutoApiError(API_VERSION_CASE_REVISION_INVALID,
                               value=(f'用例请求头不存在：{payload.runtime.missing_front_header_ids}',),
                               )
        for index, step_payload in enumerate(step_payloads, start=1):
            parameter_payloads = step_payload.api_case_detailed_parameter
            if not isinstance(parameter_payloads, list) or not parameter_payloads:
                raise AutoApiError(API_VERSION_CASE_REVISION_INVALID, value=(f'第 {index} 个步骤至少需要一个场景',))
            for parameter_index, parameter_payload in enumerate(parameter_payloads, start=1):
                if parameter_payload.missing_header_ids:
                    raise AutoApiError(API_VERSION_CASE_REVISION_INVALID,
                                       value=(
                                           f'第 {index} 个步骤的第 {parameter_index} 个场景请求头不存在：'
                                           f'{parameter_payload.missing_header_ids}',
                                       ),
                                       )

    @classmethod
    def verify_execution_revision(cls, revision: ApiCaseRevision):
        cls.verify_revision(revision)
        payload = ApiCaseRevisionPayloadModel.from_payload(
            revision.payload if isinstance(revision.payload, dict) else {}
        )
        unsupported_dependency_types = payload.runtime.unsupported_dependency_types or []
        if unsupported_dependency_types:
            raise AutoApiError(API_VERSION_DEPENDENCY_FREEZE_UNSUPPORTED,
                               value=(', '.join(sorted(set(unsupported_dependency_types))),),
                               )
        step_payloads = payload.api_case_detailed
        if not isinstance(step_payloads, list):
            raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
        legacy_revision_ids = [
            step_payload.api_info_revision_id
            for step_payload in step_payloads
            if not step_payload.api_info_snapshot
        ]
        revisions = ApiInfoRevision.objects.filter(id__in=legacy_revision_ids)
        revisions_by_id = {item.id: item for item in revisions}
        from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
        for step_payload in step_payloads:
            if not step_payload.api_info_revision_id:
                raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
            if step_payload.api_info_snapshot:
                snapshot = step_payload.api_info_snapshot
                if (
                        snapshot.get('id') != step_payload.api_info_id or
                        snapshot.get('revision_id') != step_payload.api_info_revision_id or
                        not isinstance(snapshot.get('payload'), dict)
                ):
                    raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
                ApiInfoRevisionService.verify_snapshot_payload(
                    snapshot['payload'],
                    snapshot_schema_version=snapshot.get('snapshot_schema_version'),
                    checksum=snapshot.get('checksum'),
                    executable=True,
                )
                continue
            api_revision = revisions_by_id.get(step_payload.api_info_revision_id)
            if api_revision is None or api_revision.api_info_id != step_payload.api_info_id:
                raise AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID)
            ApiInfoRevisionService.verify_revision(api_revision, executable=True)
