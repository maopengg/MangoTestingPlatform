from django.db import transaction

from src.apps.auto_api.exceptions import (
    API_VERSION_CASE_NOT_FOUND,
    API_VERSION_CASE_REVISION_NOT_FOUND,
    API_VERSION_CASE_VERSION_EXECUTION_INVALID,
    API_VERSION_CASE_VERSION_EXECUTION_INVALID_CODE_CASE_VERSION_EXECUTION_INVALID,
    API_VERSION_SELECTED_CASES_UNPUBLISHED,
    API_VERSION_VERSION_EXECUTION_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import (
    ApiCase,
    ApiCaseRelease,
    ApiCaseRevision,
)
from ..snapshot import (
    ApiCaseExecutionSelection,
)
from src.apps.auto_api.selectors.querysets import ApiQuerySelector


class ApiCaseRevisionSelectionMixin:
    @classmethod
    def resolve_current_published(cls, case_id: int) -> ApiCaseExecutionSelection:
        release = ApiQuerySelector.current_published_case_releases().filter(
            api_case_id=case_id,
        ).select_related('revision').order_by('-version_no').first()
        if release is None:
            raise AutoApiError(API_VERSION_CASE_VERSION_EXECUTION_INVALID)
        if release.revision.api_case_id != case_id:
            raise AutoApiError(API_VERSION_CASE_REVISION_NOT_FOUND)
        cls.verify_execution_revision(release.revision)
        if release.status != ApiCaseRelease.STATUS_PUBLISHED:
            raise AutoApiError(API_VERSION_CASE_VERSION_EXECUTION_INVALID_CODE_CASE_VERSION_EXECUTION_INVALID,
                               value=(release.status,))
        return ApiCaseExecutionSelection(
            case_id=case_id,
            case_revision_id=release.revision_id,
            case_revision_no=release.revision.revision_no,
            case_release_id=release.id,
            version_label=release.version_label,
            checksum=release.revision.checksum,
        )

    @classmethod
    def normalize_batch_execution_version(cls, execution_version: str | None) -> str:
        normalized = str(execution_version or cls.BATCH_EXECUTION_EDITING).strip().lower()
        if normalized not in (
                cls.BATCH_EXECUTION_EDITING,
                cls.BATCH_EXECUTION_PUBLISHED,
        ):
            raise AutoApiError(API_VERSION_VERSION_EXECUTION_INVALID, value=(execution_version,))
        return normalized

    @classmethod
    @transaction.atomic
    def resolve_batch_executions(
            cls,
            case_ids: list[int],
            *,
            execution_version: str | None,
            operator_id: int | None = None,
    ) -> dict[int, ApiCaseExecutionSelection]:
        """按用户选择执行当前编辑态，或固定当前发布版本。"""
        normalized_ids = list(dict.fromkeys(int(case_id) for case_id in case_ids))
        version = cls.normalize_batch_execution_version(execution_version)
        cases = {
            case.id: case
            for case in ApiCase.objects.select_for_update().filter(id__in=normalized_ids).only('id', 'name')
        }
        missing_case_ids = [case_id for case_id in normalized_ids if case_id not in cases]
        if missing_case_ids:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(', '.join(map(str, missing_case_ids)),))

        if version == cls.BATCH_EXECUTION_PUBLISHED:
            published_case_ids = set(
                ApiQuerySelector.current_published_case_releases().filter(
                    api_case_id__in=normalized_ids,
                ).values_list('api_case_id', flat=True)
            )
            unpublished = [
                f'{case_id}-{cases[case_id].name}'
                for case_id in normalized_ids
                if case_id not in published_case_ids
            ]
            if unpublished:
                raise AutoApiError(API_VERSION_SELECTED_CASES_UNPUBLISHED, value=('、'.join(unpublished),))
            return {
                case_id: cls.resolve_current_published(case_id)
                for case_id in normalized_ids
            }

        return {
            case_id: ApiCaseExecutionSelection(
                case_id=case_id,
                case_revision_id=None,
                case_revision_no=None,
                case_release_id=None,
                version_label='当前编辑态',
                checksum=None,
                execution_source='editing',
            )
            for case_id in normalized_ids
        }

    @classmethod
    @transaction.atomic
    def resolve_batch_execution(
            cls,
            case_id: int,
            *,
            execution_version: str | None = None,
            operator_id: int | None = None,
    ) -> ApiCaseExecutionSelection:
        """解析单个批量执行版本；调用方应显式指定编辑态或已发布。"""
        version = cls.normalize_batch_execution_version(execution_version)
        api_case = ApiCase.objects.select_for_update().filter(id=case_id).only('id').first()
        if api_case is None:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(case_id,))
        if version == cls.BATCH_EXECUTION_PUBLISHED:
            return cls.resolve_current_published(case_id)
        return ApiCaseExecutionSelection(
            case_id=case_id,
            case_revision_id=None,
            case_revision_no=None,
            case_release_id=None,
            version_label='当前编辑态',
            checksum=None,
            execution_source='editing',
        )

    @classmethod
    def resolve_release(cls, case_id: int, release_id: int) -> ApiCaseExecutionSelection:
        """解析页面或任务显式选择的发布版本，禁止退役版本进入新执行队列。"""
        cls.resolve_current_published(case_id)
        release = ApiCaseRelease.objects.filter(
            id=release_id,
            api_case_id=case_id,
        ).select_related('revision').first()
        if release is None or release.revision.api_case_id != case_id:
            raise AutoApiError(API_VERSION_CASE_REVISION_NOT_FOUND)
        if release.status != ApiCaseRelease.STATUS_PUBLISHED:
            raise AutoApiError(API_VERSION_CASE_VERSION_EXECUTION_INVALID_CODE_CASE_VERSION_EXECUTION_INVALID,
                               value=(release.status,))
        cls.verify_execution_revision(release.revision)
        return ApiCaseExecutionSelection(
            case_id=case_id,
            case_revision_id=release.revision_id,
            case_revision_no=release.revision.revision_no,
            case_release_id=release.id,
            version_label=release.version_label,
            checksum=release.revision.checksum,
        )

    @classmethod
    def resolve_revision(
            cls,
            case_id: int,
            revision_id: int,
            *,
            release_id: int | None = None,
    ) -> ApiCaseExecutionSelection:
        revision = ApiCaseRevision.objects.filter(
            id=revision_id,
            api_case_id=case_id,
        ).first()
        if revision is None:
            raise AutoApiError(API_VERSION_CASE_REVISION_NOT_FOUND)
        cls.verify_execution_revision(revision)
        if release_id is not None:
            release = ApiCaseRelease.objects.filter(
                id=release_id,
                api_case_id=case_id,
                revision_id=revision_id,
            ).first()
            if (
                    release is None or
                    release.status not in (
                    ApiCaseRelease.STATUS_PUBLISHED,
                    ApiCaseRelease.STATUS_DEPRECATED,
            )
            ):
                raise AutoApiError(API_VERSION_CASE_VERSION_EXECUTION_INVALID_CODE_CASE_VERSION_EXECUTION_INVALID,
                                   value=('release_mismatch',))
        else:
            release = ApiCaseRelease.objects.filter(
                api_case_id=case_id,
                revision_id=revision_id,
                status=ApiCaseRelease.STATUS_PUBLISHED,
            ).order_by('-version_no').first()
        return ApiCaseExecutionSelection(
            case_id=case_id,
            case_revision_id=revision.id,
            case_revision_no=revision.revision_no,
            case_release_id=release.id if release else None,
            version_label=release.version_label if release else None,
            checksum=revision.checksum,
        )
