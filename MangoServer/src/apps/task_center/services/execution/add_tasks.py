# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-11-24 20:26
# @Author : 毛鹏
from mangotools.enums import StatusEnum, TaskEnum

from src.apps.auto_api.exceptions import (
    API_VERSION_CASE_REVISION_NOT_FOUND,
    API_VERSION_CASE_REVISION_CONFIG_FAILED,
    API_VERSION_CASE_VERSION_EXECUTION_INVALID_CODE_CASE_VERSION_EXECUTION_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCase, ApiCaseRelease, ApiCaseRevision
from src.apps.auto_api.schemas.version import ApiCaseRevisionPayloadModel
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_ui.models import UiCase
from src.apps.task_center.enums.execution import AutomationExecutionScopeEnum
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.services.test_suite.create import TestSuiteCreateService
from src.apps.test_center.services.testcounter import TestCounter
from src.common.logging import log
from src.common.utils.snowflake import Snowflake


class AddTasks:
    def __init__(
            self,
            project_product: int,
            test_env: int,
            is_notice: int,
            user_id: int,
            tasks_id: int | None = None,
            module_id: int | None = None,
            execution_name: str | None = None,
            api_concurrency_limit: int | None = None,
            execution_scenes: list[str] | None = None,
            execution_scope: str = AutomationExecutionScopeEnum.UNCLASSIFIED.value,
    ):
        self.test_suite_id = Snowflake.generate_id()
        self.project_product = project_product
        self.test_env = test_env
        self.is_notice = is_notice
        self.user_id = user_id
        self.tasks_id = tasks_id
        self.module_id = module_id
        self.execution_name = execution_name.strip() if execution_name else None
        self.execution_scenes = list(execution_scenes or [])
        self.execution_scope = execution_scope
        self.api_concurrency_limit = ApiConcurrencyService.resolve_report_limit(api_concurrency_limit)
        self.add_test_suite()

    def add_test_suite(self):
        TestSuiteCreateService.create_suite(
            suite_id=self.test_suite_id,
            project_product_id=self.project_product,
            module_id=self.module_id,
            test_env=self.test_env,
            execution_scenes=self.execution_scenes,
            execution_scope=self.execution_scope,
            user_id=self.user_id,
            status=TaskEnum.STAY_BEGIN.value,
            is_notice=StatusEnum.FAIL.value,
            task_id=self.tasks_id,
            execution_name=self.execution_name,
            api_concurrency_limit=self.api_concurrency_limit,
        )

    def add_test_suite_details(
            self,
            case_id: int,
            _type: TestCaseTypeEnum,
            *,
            api_case_revision_id: int | None = None,
            api_case_release_id: int | None = None,
            bound_checksum: str | None = None,
    ):
        def set_task(case_id, case_name, project_product, case_sum, parametrize=None):
            TestSuiteCreateService.create_detail(
                suite_id=self.test_suite_id,
                case_type=_type.value,
                project_product_id=project_product,
                test_env=self.test_env,
                case_id=case_id,
                case_name=case_name,
                parametrize=parametrize if parametrize else [],
                status=TaskEnum.STAY_BEGIN.value,
                retry=0 if self.tasks_id else 2,
                case_sum=case_sum,
                api_case_revision_id=api_case_revision_id,
                api_case_release_id=api_case_release_id,
                config_checksum=bound_checksum,
            )

        if _type == TestCaseTypeEnum.UI:
            case = UiCase.objects.get(id=case_id)
            if case.parametrize:
                for i in case.parametrize:
                    set_task(case.id,
                             f'{case.name} - {i.get("name")}',
                             case.project_product.id,
                             TestCounter.case_ui(case_id),
                             i.get('parametrize'))
            else:
                set_task(case.id, case.name, case.project_product.id, TestCounter.case_ui(case_id))
        elif _type == TestCaseTypeEnum.API:
            case = ApiCase.objects.get(id=case_id)
            if self.tasks_id:
                ApiCaseRevisionService.resolve_current_published(case_id)
            if api_case_revision_id is not None:
                revision = ApiCaseRevision.objects.filter(
                    id=api_case_revision_id,
                    api_case_id=case_id,
                ).first()
                if revision is None:
                    raise AutoApiError(API_VERSION_CASE_REVISION_NOT_FOUND)
                ApiCaseRevisionService.verify_execution_revision(revision)
                if bound_checksum is not None and bound_checksum != revision.checksum:
                    raise AutoApiError(API_VERSION_CASE_REVISION_CONFIG_FAILED)
                if api_case_release_id is not None:
                    release = ApiCaseRelease.objects.filter(
                        id=api_case_release_id,
                        api_case_id=case_id,
                        revision_id=revision.id,
                    ).first()
                    if release is None:
                        raise AutoApiError(API_VERSION_CASE_REVISION_NOT_FOUND)
                    if release.status not in (
                            ApiCaseRelease.STATUS_PUBLISHED,
                            ApiCaseRelease.STATUS_DEPRECATED,
                    ):
                        raise AutoApiError(
                            API_VERSION_CASE_VERSION_EXECUTION_INVALID_CODE_CASE_VERSION_EXECUTION_INVALID,
                            value=(release.status,))
                payload = ApiCaseRevisionPayloadModel.from_payload(revision.payload)
                case_payload = payload.api_case
                case_name = case_payload.get('name', case.name)
                project_product_id = case_payload.get('project_product', case.project_product_id)
                parametrize = case_payload.get('parametrize') or []
                case_sum = sum(
                    len(step.api_case_detailed_parameter or [])
                    for step in payload.api_case_detailed
                )
            else:
                case_name = case.name
                project_product_id = case.project_product_id
                parametrize = case.parametrize or []
                case_sum = TestCounter.case_api(case_id)

            if parametrize:
                for i in parametrize:
                    set_task(case.id,
                             f'{case_name} - {i.get("name")}',
                             project_product_id,
                             case_sum,
                             i.get('parametrize'))
            else:
                set_task(case.id, case_name, project_product_id, case_sum)
        else:
            case = PytestCase.objects.get(id=case_id)
            set_task(case.id, case.name, case.project_product.project_product.id, TestCounter.case_pytest(case_id))
        if _type in (TestCaseTypeEnum.UI, TestCaseTypeEnum.PYTEST):
            self.notify_actuator_task_available(_type)

    def notify_actuator_task_available(self, task_type: TestCaseTypeEnum):
        try:
            from src.apps.system.services.socket_link.message_service import SocketMessageService
            from src.apps.user.models import User
            from src.apps.system.enums import ServerToolsCommandEnum
            from src.apps.system.enums import ClientTypeEnum
            from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract

            user = User.objects.get(id=self.user_id)
            SocketMessageService.send_socket_data(SocketEnvelopeContract(
                code=200,
                msg='有新的执行任务可拉取',
                user=user.username,
                is_notice=ClientTypeEnum.ACTUATOR,
                data=SocketCommandContract(
                    func_name=ServerToolsCommandEnum.TASK_AVAILABLE.value,
                    func_args={'task_type': 'ui' if task_type == TestCaseTypeEnum.UI else 'pytest'}
                ),
            ))
        except Exception as error:
            log.system.debug(f'通知执行器拉取任务失败，可等待执行器轮询拉取，详情：{error}')
