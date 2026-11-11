# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏
from datetime import datetime
from uuid import uuid4

from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceSourceType, ApiCaseTraceStepType
from src.apps.auto_api.services.execution_trace.recorder import trace_lifecycle
from src.apps.auto_api.exceptions import (
    API_VERSION_CASE_REVISION_CONFIG_FAILED,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCaseDetailed, ApiCase
from src.apps.auto_api.schemas.execution import (
    ApiStepExecutionContext,
    ApiCaseExecutionResult,
)
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.auto_api.services.base.api_base_test_setup import APIBaseTestSetup
from src.apps.auto_api.services.execution_trace import ApiCaseExecutionContext, ApiCaseExecutionTraceRecorder
from src.apps.auto_api.services.protocols.grpc import GrpcChannelManager
from src.apps.auto_api.services.protocols.mcp_session import McpSessionManager
from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
from src.apps.test_center.exceptions import (
    TEST_CASE_DELETED_PENDING_FAILED,
)
from src.apps.test_center.services.test_suite.update_test_suite import UpdateTestSuite
from ..step_debug import ApiCaseStepDebugState
from ...api_case.snapshot import ApiExecutableSnapshotService
from ...base.case_base import CaseBase


class ApiTestCaseLifecycleMixin:
    @trace_lifecycle(ApiCaseTraceStepType.CASE_START.value)
    def __init__(self,
                 user_id: int,
                 test_env: int,
                 case_id: int,
                 test_suite: int = None,
                 test_suite_details: int = None,
                 revision_id: int | None = None,
                 release_id: int | None = None,
                 config_checksum: str | None = None,
                 db_context=None,
                 trace_source_type: int | None = None,
                 update_case_status: bool = True):
        self.user_id = user_id
        self.test_env = test_env
        self.case_id = case_id
        self.test_suite = test_suite
        self.test_suite_details = test_suite_details
        self.trace_source_type = trace_source_type
        self.update_case_status = update_case_status
        self.is_step_debug = False
        self.current_step_execution_context: dict | None = None
        self.debug_context_state: ApiCaseStepDebugState | None = None
        self.revision_selection = None
        self.revision_aggregate = None

        self.trace_recorder = ApiCaseExecutionTraceRecorder()
        trace = self.trace_recorder.create_trace(ApiCaseExecutionContext(
            source_type=self.get_trace_source_type(), user_id=user_id, test_env=test_env,
            case_id=case_id, test_suite_id=test_suite, test_suite_detail_id=test_suite_details,
        ))

        self.test_setup = APIBaseTestSetup(db_context=db_context)
        if revision_id is not None or release_id is not None:
            if revision_id is not None:
                self.revision_selection = ApiCaseRevisionService.resolve_revision(
                    int(case_id),
                    int(revision_id),
                    release_id=int(release_id) if release_id is not None else None,
                )
            else:
                self.revision_selection = ApiCaseRevisionService.resolve_release(
                    int(case_id),
                    int(release_id),
                )
            if config_checksum is not None and config_checksum != self.revision_selection.checksum:
                raise AutoApiError(API_VERSION_CASE_REVISION_CONFIG_FAILED)
            self.revision_aggregate = ApiCaseRevisionService.load_execution_revision(
                self.revision_selection.case_revision_id,
            )
            self.api_case = self.revision_aggregate.api_case
        else:
            try:
                self.api_case: ApiCase = ApiCase.objects.get(id=case_id)
            except ApiCase.DoesNotExist:
                if self.test_suite_details:
                    UpdateTestSuite.update_test_suite_details_status(
                        self.test_suite_details,
                        StatusEnum.FAIL.value,
                        TEST_CASE_DELETED_PENDING_FAILED.message
                    )
                raise AutoApiError(TEST_CASE_DELETED_PENDING_FAILED)
            ApiExecutableSnapshotService.apply_case_execution_config(
                self.api_case,
                ApiExecutableSnapshotService.current_case_config(
                    self.api_case.id,
                    self.api_case.project_product_id,
                ),
            )
        if self.api_case.callback_checks:
            from src.apps.auto_api.services.callback import ApiCallbackService
            ApiCallbackService.validate_execution(
                self.api_case.callback_checks, list(self.get_case_detailed_queryset(self.api_case.id, None)),
            )
        case_data_factory_configs = None
        if self.revision_aggregate is not None:
            case_data_factory_configs = self.revision_aggregate.data_factory_configs_for(
                DataFactoryCaseSourceTypeEnum.API_CASE.value,
                self.api_case.id,
            )
        self.case_base = CaseBase(
            self.test_setup,
            self.api_case,
            test_env=self.test_env,
            user_id=self.user_id,
            data_factory_configs=case_data_factory_configs,
        )

        if self.update_case_status:
            self.api_case.status = TaskEnum.PROCEED.value
            self.update_test_case(self.case_id, TaskEnum.PROCEED.value)
        self.api_case_result = ApiCaseExecutionResult(
            id=case_id,
            name=self.api_case.name,
            project_product_name=self.api_case.project_product.name,
            test_env=self.test_env,
            user_id=self.user_id,
            status=StatusEnum.FAIL.value,
            test_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            case_revision_id=(self.revision_selection.case_revision_id if self.revision_selection else None),
            case_revision_no=(self.revision_selection.case_revision_no if self.revision_selection else None),
            case_release_id=(self.revision_selection.case_release_id if self.revision_selection else None),
            version_label=(self.revision_selection.version_label if self.revision_selection else None),
            config_checksum=(self.revision_selection.checksum if self.revision_selection else None),
        )
        self.trace_recorder.update_metadata(self.api_case.name, {
            'project_product_id': self.api_case.project_product_id,
            'project_product_name': self.api_case.project_product.name,
            'case_revision_id': self.api_case_result.case_revision_id,
            'case_revision_no': self.api_case_result.case_revision_no,
            'case_release_id': self.api_case_result.case_release_id,
            'version_label': self.api_case_result.version_label,
            'config_checksum': self.api_case_result.config_checksum,
            'api_revision_dependencies': (
                list(self.revision_aggregate.api_revision_dependencies)
                if self.revision_aggregate is not None
                else []
            ),
        })
        if trace:
            self.api_case_result.trace_id = trace.trace_id
        self.execution_context_id = self.api_case_result.trace_id or uuid4().hex
        self.api_case_result.execution_context_id = self.execution_context_id
        self.test_setup.mcp_session_manager = McpSessionManager(self.trace_recorder)
        self.test_setup.grpc_channel_manager = GrpcChannelManager(self.trace_recorder)
        self.test_setup.trace_recorder = self.trace_recorder
        self.resource_cleanup_manager = None
        if getattr(self.api_case, 'resource_cleanup', None):
            from src.apps.auto_api.services.resource_cleanup import ApiResourceCleanupService, ApiResourceExecutionManager
            rules = ApiResourceCleanupService.validate_config(
                self.api_case.resource_cleanup, self.api_case.project_product_id)
            from src.apps.auto_api.schemas.resource_cleanup import ApiResourceCleanupRule
            ApiResourceCleanupService.validate_steps([ApiResourceCleanupRule.model_validate(rule) for rule in rules],
                                                     list(self.get_case_detailed_queryset(self.api_case.id, None)))
            self.resource_cleanup_manager = ApiResourceExecutionManager(self.api_case, trace, self.test_setup, rules)
            self.test_setup.resource_cleanup_manager = self.resource_cleanup_manager

    def get_trace_source_type(self) -> int:
        if self.trace_source_type is not None:
            return self.trace_source_type
        if not self.test_suite_details:
            return ApiCaseTraceSourceType.SINGLE_CASE
        from src.apps.test_center.models import TestSuite
        is_timing_task = TestSuite.objects.filter(
            id=self.test_suite,
            tasks_id__isnull=False,
        ).exists()
        return ApiCaseTraceSourceType.TIMING_TASK if is_timing_task else ApiCaseTraceSourceType.TEST_SUITE

    def build_step_execution_context(
            self,
            case_detailed: ApiCaseDetailed,
            parent_snapshot_id: str | None,
    ) -> dict:
        return ApiStepExecutionContext(
            context_id=self.execution_context_id,
            snapshot_id=uuid4().hex,
            parent_snapshot_id=parent_snapshot_id,
            case_id=self.api_case.id,
            case_detailed_id=case_detailed.id,
            case_sort=case_detailed.case_sort,
            test_env=self.test_env,
            user_id=self.user_id,
            trace_id=self.api_case_result.trace_id,
            executed_at=datetime.now().astimezone().isoformat(),
        ).model_dump()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
