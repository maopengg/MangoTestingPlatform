from django.db import transaction

from src.apps.auto_api.exceptions import AutoApiError, API_VERSION_CASE_NOT_FOUND
from src.apps.auto_api.exceptions.definitions import API_CASE_LIST_VERSION_CHANGED, API_CASE_LIST_ALREADY_RUNNING
from src.apps.auto_api.exceptions.definitions import API_CASE_LIST_TRACE_UNAVAILABLE
from src.apps.auto_api.models import ApiCase
from src.apps.auto_api.selectors.case_list_execution import ApiCaseListExecutionSelector
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.auto_api.services.execution.cases.test_case import TestCase


class ApiCaseListExecutionService:
    @staticmethod
    @transaction.atomic
    def prepare(*, case_id, test_env, version_token, user_id):
        # 同一 Case 的并发提交串行检查并创建 Trace；真正请求在提交事务之后执行。
        case = ApiCase.objects.select_for_update().filter(pk=case_id).first()
        if case is None:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(case_id,))
        row = ApiCaseListExecutionSelector.annotate(ApiCase.objects.filter(pk=case_id), test_env).get()
        if ApiCaseListExecutionSelector.token(row) != version_token:
            raise AutoApiError(API_CASE_LIST_VERSION_CHANGED)
        if row.list_active:
            raise AutoApiError(API_CASE_LIST_ALREADY_RUNNING)
        if row.list_revision_id is None:
            revision = ApiCaseRevisionService.record_execution_snapshot(case_id, operator_id=user_id)
            if ApiCaseListExecutionSelector.editing_fingerprints([case_id]).get(case_id) != row.list_fingerprint:
                raise AutoApiError(API_CASE_LIST_VERSION_CHANGED)
            revision_id, release_id = revision.id, None
        else:
            revision_id = row.list_revision_id
            release_id = row.list_release_id if row.list_version == 'published' else None
        runner = TestCase(user_id=user_id, test_env=test_env, case_id=case_id,
                          revision_id=revision_id, release_id=release_id)
        if runner.trace_recorder.trace is None:
            raise AutoApiError(API_CASE_LIST_TRACE_UNAVAILABLE)
        runner.trace_recorder.update_metadata(case.name, {
            'execution_source': 'editing' if row.list_version == 'unpublished' else row.list_version,
            'editing_fingerprint': row.list_fingerprint if row.list_version == 'unpublished' else None,
        })
        return runner, revision_id, release_id
