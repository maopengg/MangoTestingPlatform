# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/4/28 11:56
# @Author : 毛鹏
import copy
import random
import re
import traceback
import uuid

from django.core.exceptions import ObjectDoesNotExist
from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract
from mangotools.contracts import (
    UiEnvironmentContract,
    UiFlowRuntimeNodeContract,
    UiPublicVariableContract,
    UiStepDataContract,
)
from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum
from mangotools.mangos import build_decision_tree
from pydantic import ValidationError

from src.apps.auto_ui.enums import ElementOperationEnum, UiPublicTypeEnum
from src.apps.auto_ui.enums import UiAuthTypeEnum
from src.apps.auto_ui.exceptions import (
    AUTO_UI_TEST_CASE_TEST_CASE_STEP_PAGE_CONFIG_NODE_EXECUTION_INVALID,
    AUTO_UI_TEST_CASE_TEST_CASE_CASE_STEP_SAVE_INVALID,
    AutoUiError,
    UI_PAGE_STEPS_EMPTY,
    UI_CASE_STEPS_EMPTY,
    UI_EXECUTOR_EXECUTOR_EXECUTION_INVALID,
    UI_EXECUTOR_EXECUTOR_EXECUTION_INVALID_CODE_EXECUTOR_EXECUTION_INVALID,
    UI_EXECUTOR_EXECUTOR_TASK_EXECUTION_INVALID,
    UI_LIVE_NOT_FOUND,
    UI_LIVE_STEP_PAGE_ACCESS_DENIED,
    UI_LIVE_STEP_PAGE_INVALID,
    UI_STEP_STEP_PAGE_NODE_INVALID,
)
from src.apps.auto_ui.models import (
    Page,
    PageElement,
    PageSteps,
    PageStepsDetailed,
    UiCase,
    UiCaseStepsDetailed,
    UiElementSnapshot,
)
from src.apps.auto_ui.schemas.auth import (
    UiAuthCache,
)
from src.apps.auto_ui.schemas.element import (
    UiElementExecution,
    UiElementLocator,
)
from src.apps.auto_ui.schemas.execution import (
    UiCaseExecutionSchema,
    UiCasePageStepExecutionSchema,
    UiDebugPageStepExecutionSchema,
    UiPageStepExecutionSchema,
    UiElementCheckCommand,
    UiStepControlSchema,
)
from src.apps.auto_ui.services.cases.case_global_variable import UiCaseGlobalVariableService
from src.apps.auto_ui.services.elements.element_description import build_element_description
from src.apps.auto_ui.services.execution.executor_slot import ExecutorSlotLeaseService
from src.apps.auto_ui.services.execution.cases.case_data_factory import UiCaseDataFactory
from src.apps.auto_ui.services.authentication.ui_auth import UiAuthManager
from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
from src.apps.data_factory.models import DataFactoryCaseConfig
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver
from src.apps.data_factory.services.execution.runtime_cache import DataFactoryRuntimeCache
from src.apps.system.enums import ClientTypeEnum, ClientNameEnum
from src.apps.system.enums import ExecutorModeEnum, ExecutorTaskStatusEnum
from src.apps.system.enums import ServerUiCommandEnum
from src.apps.system.services.socket_link.connection_service import SocketConnectionService
from src.apps.system.services.socket_link.message_service import SocketMessageService
from src.apps.test_center.enums.environment import AutoTypeEnum
from src.apps.test_center.exceptions import (
    TEST_CASE_POST_SQL_EMPTY,
    TEST_CASE_PRE_KEY_VALUE_EMPTY,
    TEST_SUITE_KEY_EMPTY,
    TEST_CASE_PRE_SQL_REQUIRED,
    TEST_CASE_DELETED_PENDING_FAILED,
)
from src.apps.test_center.models import TestObject
from src.apps.test_center.services.datasource.factory import func_test_object_value
from src.common.exceptions import (
    MangoServerError,
)
from src.common.logging import log


class TestCase:
    PUBLIC_VALUE_MAX_LENGTH = 100000
    PUBLIC_VALUE_STORAGE_NOISE = (
        '__tea_',
        'text.',
        'localStorage',
        'sessionStorage',
        'storage_state',
        'policy-sdk-config-',
    )

    @staticmethod
    def _frame_locator_list(value) -> list[dict]:
        if isinstance(value, dict):
            value = value.get('frames')
        return [item for item in (value or []) if isinstance(item, dict)]

    def __init__(self,
                 user_id: int,
                 username: str,
                 test_env: int,
                 tasks_id: int = None,
                 is_send: bool = False,
                 actuator_username: str | None = None):
        self.user_id = user_id
        self.send_user = username
        self.actuator_user = actuator_username or username
        self.actuator_user_explicit = bool(actuator_username)
        self.test_env = test_env
        self.tasks_id = tasks_id
        self.is_send = is_send
        self.test_data = None
        self.case_data_factory: UiCaseDataFactory | None = None
        self._snapshot_baseline_cache: dict[int, bool] = {}
        self.last_executor_task = None

    def test_case(self,
                  case_id: int,
                  case_name: str = None,
                  test_suite: int | None = None,
                  test_suite_details: int | None = None,
                  parametrize: list[dict] | list = None,
                  send_case_user: str = None) -> UiCaseExecutionSchema:
        try:
            case = UiCase.objects.get(id=case_id)
        except UiCase.DoesNotExist:
            raise AutoUiError(TEST_CASE_DELETED_PENDING_FAILED)
        case.status = TaskEnum.PROCEED.value
        case.save(update_fields=['status'])
        case_steps_detailed = UiCaseStepsDetailed.objects.filter(case=case.id).order_by('case_sort')
        try:
            if not case_steps_detailed:
                raise AutoUiError(UI_CASE_STEPS_EMPTY)
            self._reset_case_step_runtime_status(case.id)
            for i in case.front_custom:
                if not i.get('key') or not i.get('value'):
                    raise AutoUiError(TEST_CASE_PRE_KEY_VALUE_EMPTY)
            for i in case.front_sql:
                if not i.get('sql'):
                    raise AutoUiError(TEST_CASE_PRE_SQL_REQUIRED)
            for i in case.posterior_sql:
                if not i.get('sql'):
                    raise AutoUiError(TEST_CASE_POST_SQL_EMPTY)
            for i in case.parametrize:
                for e in i.get('parametrize'):
                    if not e.get('key'):
                        raise AutoUiError(TEST_SUITE_KEY_EMPTY)
            case_model = None
            if case.parametrize and test_suite is None:
                for i in case.parametrize:
                    case_model_1 = self.__case_model(
                        case,
                        case_steps_detailed,
                        f'{case.name} - {i.get("name")}',
                        test_suite,
                        test_suite_details,
                        i.get('parametrize'),
                        send_case_user,
                    )
                    case_model = copy.deepcopy(case_model_1)
                    self.__socket_send(func_name=ServerUiCommandEnum.CASE_BATCH.value,
                                       data_model=case_model_1, is_open=True)
            elif test_suite and test_suite_details and parametrize:
                case_model = self.__case_model(
                    case,
                    case_steps_detailed,
                    case_name,
                    test_suite,
                    test_suite_details,
                    parametrize,
                    send_case_user,
                )
                self.__socket_send(func_name=ServerUiCommandEnum.CASE_BATCH.value,
                                   data_model=case_model, is_open=True)
            else:
                case_model = self.__case_model(
                    case,
                    case_steps_detailed,
                    case_name,
                    test_suite,
                    test_suite_details,
                    case.parametrize,
                    send_case_user,
                )
                self.__socket_send(func_name=ServerUiCommandEnum.CASE_BATCH.value,
                                   data_model=case_model, is_open=True)
            return case_model
        except Exception as error:
            self.__cleanup_case_data_factory()
            case.status = TaskEnum.FAIL.value
            case.save(update_fields=['status'])
            raise error

    @staticmethod
    def _reset_case_step_runtime_status(case_id: int) -> None:
        """A new execution must not inherit step states from the previous run."""
        UiCaseStepsDetailed.objects.filter(case_id=case_id).update(
            status=TaskEnum.STAY_BEGIN.value,
            error_message=None,
        )

    def __case_model(self,
                     case: UiCase,
                     case_steps_detailed,
                     case_name: str | None,
                     test_suite: int | None,
                     test_suite_details: int | None,
                     parametrize: list[dict] | list | None,
                     send_case_user: str | None) -> UiCaseExecutionSchema:
        ui_auth_cache = self.__ui_auth_cache(case.project_product_id, case.front_auth_config)
        ui_auth_config = UiAuthManager.get_enabled_auth_configs(
            case.project_product_id,
            self.test_env,
            case.front_auth_config,
        ).filter(auth_type=UiAuthTypeEnum.PAGE_STEP.value, page_step_id__isnull=False).first()
        self.__run_case_data_factory(case, parametrize, test_suite=test_suite, test_suite_details=test_suite_details)
        steps = [
            self.case_steps_model(
                i.page_step.id,
                i,
                bool(i.switch_step_open_url),
                front_public_ids=case.front_public,
            )
            for i in case_steps_detailed
        ]
        if ui_auth_config:
            if ui_auth_config.auth_type == UiAuthTypeEnum.PAGE_STEP.value and ui_auth_config.page_step_id:
                steps.insert(0, self.case_steps_model(
                    ui_auth_config.page_step_id,
                    is_auth_step=True,
                    front_public_ids=case.front_public,
                ))
        execution_id = str(uuid.uuid4())
        for step in steps:
            step.execution_id = execution_id
        return UiCaseExecutionSchema(
            execution_id=execution_id,
            send_user=send_case_user if send_case_user else self.send_user,
            test_suite_details=test_suite_details,
            test_suite_id=test_suite,
            id=case.id,
            name=case_name if case_name else case.name,
            module_name=self.__module_name(case),
            project_product=case.project_product.id,
            project_product_name=case.project_product.name,
            test_env=self.test_env,
            case_people=case.case_people.name,
            front_custom=case.front_custom,
            front_sql=case.front_sql,
            posterior_sql=case.posterior_sql,
            parametrize=parametrize or [],
            data_factory_cache_data=self.test_data.get_data_factory_all() if self.test_data else {},
            data_factory_execution_ids=self.case_data_factory.runner.execution_ids
            if self.case_data_factory and self.case_data_factory.runner else [],
            data_factory_auto_cleanup_execution_ids=self.case_data_factory.runner.auto_cleanup_execution_ids
            if self.case_data_factory and self.case_data_factory.runner else [],


            ui_auth_cache=ui_auth_cache,
            steps=steps,
        )

    def __ui_auth_cache(self, project_product_id: int, front_auth_config_ids=None) -> UiAuthCache | None:
        ui_auth_configs = list(UiAuthManager.get_enabled_auth_configs(
            project_product_id,
            self.test_env,
            front_auth_config_ids,
        ))
        if not ui_auth_configs:
            return None
        cache_data = {
            'cookies': [],
            'local_storage': [],
            'session_storage': [],
            'headers': {},
        }
        cache_found = False
        for ui_auth_config in ui_auth_configs:
            if ui_auth_config.auth_type not in [
                UiAuthTypeEnum.MANUAL.value,
                UiAuthTypeEnum.AUTO.value,
                UiAuthTypeEnum.API.value,
            ]:
                continue
            UiAuthManager.ensure_cache_available(ui_auth_config)
            normalized = UiAuthManager.normalize_cache_data(
                ui_auth_config.cache_data,
                UiAuthManager.resolve_origin(ui_auth_config),
            )
            cache_data['cookies'].extend(normalized.get('cookies') or [])
            cache_data['local_storage'].extend(normalized.get('local_storage') or [])
            cache_data['session_storage'].extend(normalized.get('session_storage') or [])
            cache_data['headers'].update(normalized.get('headers') or {})
            if normalized.get('storage_state'):
                cache_data['storage_state'] = normalized.get('storage_state')
            cache_found = True
        if not cache_found:
            return None
        return UiAuthCache(**cache_data)

    def ui_auth_cache(self, project_product_id: int, front_auth_config_ids=None) -> UiAuthCache | None:
        return self.__ui_auth_cache(project_product_id, front_auth_config_ids)

    def __run_case_data_factory(self, case: UiCase, parametrize: list[dict] | list | None = None,
                                *, test_suite=None, test_suite_details=None):
        self.test_data = None
        self.case_data_factory = None
        if not isinstance(case, UiCase):
            return
        if not DataFactoryCaseConfig.objects.filter(
                source_type=DataFactoryCaseSourceTypeEnum.UI_CASE.value,
                source_id=case.id,
                stage=1,
                status=StatusEnum.SUCCESS.value,
        ).exists():
            return
        test_object = func_test_object_value(self.test_env, case.project_product_id, AutoTypeEnum.UI.value)
        self.test_data = DataFactoryRuntimeCache.build_test_data(
            case.project_product_id,
            self.test_env,
            ui_public_ids=case.front_public,
        )
        for custom in case.front_custom:
            if not self.__matches_test_environment(custom):
                continue
            self.test_data.set_cache(custom.get('key'), self.test_data.replace(custom.get('value')))
        self.__set_parametrize_cache(parametrize)
        self.case_data_factory = UiCaseDataFactory(test_object.id, self.test_data, case, user_id=self.user_id)
        from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService
        from src.apps.test_center.enums import TestCaseTypeEnum
        with DataFactoryCleanupScheduleService.report_scope(
                test_suite_details, suite_id=test_suite, case_id=case.id, case_type=TestCaseTypeEnum.UI.value):
            self.case_data_factory.run_front()

    def __set_parametrize_cache(self, parametrize: list[dict] | list | None):
        if not self.test_data or not parametrize:
            return
        for item in parametrize:
            if not self.__matches_test_environment(item):
                continue
            key = item.get('key')
            if not key:
                continue
            value = item.get('value')
            self.test_data.set_cache(key, self.test_data.replace(value) if value is not None else value)

    def __matches_test_environment(self, item: dict) -> bool:
        configured_environments = item.get('test_envs') or []
        return not configured_environments or self.test_env in configured_environments

    def __cleanup_case_data_factory(self):
        if self.case_data_factory:
            self.case_data_factory.cleanup()

    def test_steps(
            self,
            steps_id: int,
            workspace_id: str | None = None,
            step_control: dict | None = None,
            page_step_detail_id: int | None = None,
    ) -> UiDebugPageStepExecutionSchema:
        try:
            self.__bind_live_workspace(steps_id, workspace_id)
            page_steps_model = self.debug_steps_model(
                steps_id,
                page_step_detail_id=page_step_detail_id,
            )
            if page_step_detail_id is not None:
                selected_element = next((
                    item for item in page_steps_model.element_list
                    if item.id == page_step_detail_id
                ), None)
                if selected_element is None:
                    raise AutoUiError(UI_STEP_STEP_PAGE_NODE_INVALID)
                page_steps_model.element_list = [selected_element]
                page_steps_model.flow_data = UiFlowRuntimeNodeContract(
                    id=selected_element.id,
                    type=selected_element.type,
                    children=[],
                )
            page_steps_model.ui_auth_cache = self.__ui_auth_cache(page_steps_model.project_product)
            page_steps_model.workspace_id = workspace_id
            page_steps_model.step_control = UiStepControlSchema(**(step_control or {}))
            self.__socket_send(func_name=ServerUiCommandEnum.PAGE_STEPS.value, data_model=page_steps_model)
            return page_steps_model
        except Exception as error:
            page_steps = PageSteps.objects.get(id=steps_id)
            page_steps.status = TaskEnum.FAIL.value
            page_steps.save(update_fields=['status'])
            raise error

    def __bind_live_workspace(self, steps_id: int, workspace_id: str | None) -> None:
        if not workspace_id:
            return
        from src.apps.auto_ui.enums.live_stream import LiveStreamExecutionType
        from src.apps.auto_ui.services.live_stream.workspace_service import LiveWorkspaceService

        workspace = LiveWorkspaceService.get_workspace(str(workspace_id))
        if workspace is None:
            raise AutoUiError(UI_LIVE_NOT_FOUND)
        if workspace.username != self.send_user:
            raise AutoUiError(UI_LIVE_STEP_PAGE_ACCESS_DENIED)
        if (
                workspace.workspace_type != LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value
                or workspace.resource_id != int(steps_id)
        ):
            raise AutoUiError(UI_LIVE_STEP_PAGE_INVALID)
        self.actuator_user = workspace.executor_username
        self.actuator_user_explicit = True

    def check_element(self, element_id: int, check_id: str, workspace_id: str | None = None,
                      check_mode: str = 'normal',
                      runtime_variables: dict | None = None) -> UiElementCheckCommand:
        element_obj = PageElement.objects.select_related('page__project_product').get(id=element_id)
        page = element_obj.page
        runtime_variables = runtime_variables if check_mode == 'deep' and isinstance(runtime_variables, dict) else {}

        def runtime_value(value):
            if not isinstance(value, str):
                return value

            def replace_match(match):
                key = str(match.group(1) or '').strip()
                replacement = runtime_variables.get(key)
                return match.group(0) if replacement in (None, '') else str(replacement)

            return re.sub(r'\$\{\{([\s\S]*?)\}\}', replace_match, value)

        expected_event = element_obj.expected_event or {}
        element_description = build_element_description(
            name=element_obj.name,
            category=element_obj.category,
            location_description=getattr(element_obj, 'location_description', None),
            surrounding_text=getattr(element_obj, 'surrounding_text', None),
            legacy_prompt=element_obj.prompt,
        )
        ope_key = expected_event.get('ope_key') or 'w_get_text'
        ope_value = [
            {'f': 'locating', 'd': False},
            *[item for item in (expected_event.get('ope_value') or []) if item.get('f') != 'locating'],
        ]
        self.__cache_snapshot_baselines([element_obj.id])
        element_model = UiElementExecution(
            id=element_obj.id,
            element_id=element_obj.id,
            type=ElementOperationEnum.OPE,
            name=runtime_value(element_obj.name),
            category=element_obj.category,
            ai_heal_status=element_obj.ai_heal_status,
            element_version=getattr(element_obj, 'locator_version', 1),
            description_template=element_description,
            page_url=page.url,
            frame_path=self._frame_locator_list(getattr(element_obj, 'frame_path', None)),
            collect_snapshot=self.__should_collect_snapshot(element_obj.id),
            sleep=element_obj.sleep,
            ope_key=ope_key,
            ope_value=ope_value,
        )
        locator_slots = (
            (element_obj.exp, element_obj.loc, element_obj.sub),
            (element_obj.exp2, element_obj.loc2, element_obj.sub2),
            (element_obj.exp3, element_obj.loc3, element_obj.sub3),
        )
        for slot, (exp, loc, sub) in enumerate(locator_slots, start=1):
            if exp is None or not loc:
                if check_mode == 'deep':
                    element_model.elements.append(UiElementLocator(
                        exp=9,
                        loc=f'[data-mango-deep-check-empty-slot="{slot}"]',
                        is_iframe=element_obj.is_iframe,
                        prompt=runtime_value(element_description),
                        slot=slot,
                        is_placeholder=True,
                    ))
                continue
            element_model.elements.append(UiElementLocator(
                exp=exp,
                loc=runtime_value(loc),
                sub=sub,
                is_iframe=element_obj.is_iframe,
                prompt=runtime_value(element_description),
                slot=slot,
            ))
        if not element_model.elements:
            element_model.elements.append(UiElementLocator(
                prompt=runtime_value(element_description),
                slot=1,
                is_placeholder=True,
            ))
        check_model = UiElementCheckCommand(
            check_id=check_id,
            check_mode=check_mode,
            send_user=self.send_user,
            id=page.id,
            name=page.name,
            project_product=page.project_product.id,
            project_product_name=page.project_product.name,
            module_name=self.__module_name(page),
            test_env=self.test_env,
            type=page.project_product.ui_client_type,
            url=runtime_value(page.url),
            switch_step_open_url=False,
            error_retry=None,
            element_list=[element_model],
            environment_config=self.__environment_config(page.project_product.id),
            public_data_list=self.__public_data(page.project_product_id, self.test_env),
            ui_auth_cache=self.__ui_auth_cache(page.project_product_id),
        )
        check_model.workspace_id = workspace_id
        self.__socket_send(func_name=ServerUiCommandEnum.ELEMENT_CHECK.value, data_model=check_model)
        return check_model

    def debug_steps_model(
            self,
            page_steps_id: int,
            mark_running: bool = True,
            page_step_detail_id: int | None = None,
    ) -> UiDebugPageStepExecutionSchema:
        return self.steps_model(
            page_steps_id,
            model_class=UiDebugPageStepExecutionSchema,
            mark_running=mark_running,
            page_step_detail_id=page_step_detail_id,
        )

    def workspace_page_model(self, page_id: int) -> UiDebugPageStepExecutionSchema:
        page = Page.objects.select_related('project_product', 'module').get(id=page_id)
        return UiDebugPageStepExecutionSchema(
            send_user=self.send_user,
            id=page.id,
            name=page.name,
            project_product=page.project_product.id,
            project_product_name=page.project_product.name,
            module_name=self.__module_name(page),
            test_env=self.test_env,
            type=page.project_product.ui_client_type,
            url=page.url,
            switch_step_open_url=False,
            error_retry=None,
            element_list=[],
            environment_config=self.__environment_config(page.project_product.id),
            public_data_list=self.__public_data(page.project_product_id, self.test_env),
            flow_data=None,
            ui_auth_cache=self.__ui_auth_cache(page.project_product_id),
        )

    def open_page_step_browser(self, page_steps_id: int) -> UiDebugPageStepExecutionSchema:
        page_steps = PageSteps.objects.select_related('page').get(id=page_steps_id)
        page_model = self.workspace_page_model(page_steps.page_id)
        page_model.id = page_steps.id
        page_model.name = page_steps.name
        self.__socket_send(
            func_name=ServerUiCommandEnum.OPEN_TARGET_PAGE.value,
            data_model=page_model,
            mark_running=False,
        )
        return page_model

    def open_page_browser(self, page_id: int) -> UiDebugPageStepExecutionSchema:
        page_model = self.workspace_page_model(page_id)
        self.__socket_send(
            func_name=ServerUiCommandEnum.OPEN_TARGET_PAGE.value,
            data_model=page_model,
            mark_running=False,
        )
        return page_model

    def case_steps_model(self,
                         page_steps_id: int,
                         case_steps_detailed: UiCaseStepsDetailed | None = None,
                         switch_step_open_url=False,
                         is_auth_step: bool = False,
                         front_public_ids=None) -> UiCasePageStepExecutionSchema:
        return self.steps_model(
            page_steps_id,
            case_steps_detailed=case_steps_detailed,
            switch_step_open_url=switch_step_open_url,
            is_auth_step=is_auth_step,
            front_public_ids=front_public_ids,
            model_class=UiCasePageStepExecutionSchema,
        )

    def steps_model(self,
                    page_steps_id: int,
                    case_steps_detailed: UiCaseStepsDetailed | None = None,
                    switch_step_open_url=False,
                    is_auth_step: bool = False,
                    front_public_ids=None,
                    mark_running: bool = True,
                    model_class=UiPageStepExecutionSchema,
                    page_step_detail_id: int | None = None) -> UiPageStepExecutionSchema:
        page_steps = PageSteps.objects.get(id=page_steps_id)
        page_steps_element = list(
            PageStepsDetailed.objects.filter(page_step=page_steps.id).select_related('ele_name')
        )
        if not page_steps_element:
            raise AutoUiError(UI_PAGE_STEPS_EMPTY)
        selected_page_step_element = None
        if page_step_detail_id is not None:
            selected_page_step_element = next((
                item for item in page_steps_element
                if item.id == page_step_detail_id
            ), None)
            if selected_page_step_element is None:
                raise AutoUiError(UI_STEP_STEP_PAGE_NODE_INVALID)
            page_steps_element = [selected_page_step_element]
        self.__cache_snapshot_baselines([
            item.ele_name_id for item in page_steps_element if item.ele_name_id
        ])
        if selected_page_step_element is None:
            self.__validate_flow_data(page_steps.flow_data)
            runtime_flow_data = build_decision_tree(page_steps.flow_data)
        else:
            runtime_flow_data = UiFlowRuntimeNodeContract(
                id=selected_page_step_element.id,
                type=selected_page_step_element.type,
                children=[],
            )
        if mark_running and case_steps_detailed is None and not is_auth_step:
            page_steps.status = TaskEnum.PROCEED.value
            page_steps.save(update_fields=['status'])
        model_values = dict(
            id=page_steps.id,
            name=page_steps.name,
            project_product=page_steps.project_product.id,
            project_product_name=page_steps.project_product.name,
            module_name=self.__module_name(page_steps, page_steps.page),
            test_env=self.test_env,
            type=page_steps.project_product.ui_client_type,
            url=page_steps.page.url,
            switch_step_open_url=switch_step_open_url,
            environment_config=self.__environment_config(page_steps.project_product.id),
            public_data_list=self.__public_data(page_steps.project_product_id, self.test_env, front_public_ids),
            flow_data=runtime_flow_data,
            is_auth_step=is_auth_step,
            config_version=page_steps.config_version,
            goal=page_steps.goal,
            entry_criteria=page_steps.entry_criteria,
            success_criteria=page_steps.success_criteria,
            healing_enabled=page_steps.healing_enabled,
            healing_policy=page_steps.healing_policy,
        )
        if issubclass(model_class, UiDebugPageStepExecutionSchema):
            model_values['send_user'] = self.send_user
        page_steps_model = model_class(**model_values)
        if case_steps_detailed:
            page_steps_model.case_steps_id = case_steps_detailed.id
            page_steps_model.error_retry = case_steps_detailed.error_retry
            try:
                page_steps_model.case_data = [UiStepDataContract(**i) for i in case_steps_detailed.case_data]
            except ValidationError:
                log.ui.debug(f'{traceback.print_exc()}')
                raise AutoUiError(AUTO_UI_TEST_CASE_TEST_CASE_CASE_STEP_SAVE_INVALID)
        page_steps_model.element_list = [self.element_model(i) for i in page_steps_element]
        return page_steps_model

    @classmethod
    def __module_name(cls, *objects) -> str:
        for obj in objects:
            try:
                module = getattr(obj, 'module', None)
                if module:
                    return module.name
            except ObjectDoesNotExist:
                continue
        return ''

    @classmethod
    def __validate_flow_data(cls, flow_data: dict):
        nodes = flow_data.get('nodes') if isinstance(flow_data, dict) else None
        if not nodes:
            raise AutoUiError(UI_PAGE_STEPS_EMPTY)
        invalid_nodes = [
            node.get('label') or node.get('id') or '未命名节点'
            for node in nodes
            if not isinstance(node.get('config'), dict) or not node.get('config', {}).get('id')
        ]
        if invalid_nodes:
            raise AutoUiError(AUTO_UI_TEST_CASE_TEST_CASE_STEP_PAGE_CONFIG_NODE_EXECUTION_INVALID,
                              value=('、'.join(invalid_nodes),))

    def element_model(self, steps_element: PageStepsDetailed) -> UiElementExecution:
        element = steps_element.ele_name
        element_id = element.id if element else None
        element_description = build_element_description(
            name=element.name if element else None,
            category=element.category if element else None,
            location_description=getattr(element, 'location_description', None) if element else None,
            surrounding_text=getattr(element, 'surrounding_text', None) if element else None,
            legacy_prompt=element.prompt if element else None,
        )
        element_model = UiElementExecution(
            id=steps_element.id,
            element_id=element_id,
            type=steps_element.type,
            name=element.name if element else None,
            category=element.category if element else None,
            ai_heal_status=element.ai_heal_status if element else 0,
            element_version=element.locator_version if element else None,
            description_template=element_description,
            page_url=element.page.url if element else None,
            frame_path=self._frame_locator_list(element.frame_path) if element else [],
            collect_snapshot=self.__should_collect_snapshot(element_id),
            sleep=element.sleep if element else None,
            ope_key=steps_element.ope_key,
            ope_value=steps_element.ope_value if steps_element.ope_value is not None else [],
            sql_execute=steps_element.sql_execute,
            custom=steps_element.custom,
            condition_value=steps_element.condition_value,
            func=steps_element.func,
            precondition=getattr(steps_element, 'precondition', None),
            postcondition=getattr(steps_element, 'postcondition', None),
        )
        if element:
            for exp, loc, sub in (
                    (element.exp, element.loc, element.sub),
                    (element.exp2, element.loc2, element.sub2),
                    (element.exp3, element.loc3, element.sub3)):
                if exp is None or not loc:
                    continue
                element_model.elements.append(UiElementLocator(
                    exp=exp,
                    loc=loc,
                    sub=sub,
                    is_iframe=element.is_iframe,
                    prompt=element_description,
                ))
            if not element_model.elements:
                element_model.elements.append(UiElementLocator(
                    prompt=element_description,
                    is_placeholder=True,
                ))
        return element_model

    def __cache_snapshot_baselines(self, element_ids: list[int]) -> None:
        unresolved_ids = {
            element_id for element_id in element_ids
            if element_id and element_id not in self._snapshot_baseline_cache
        }
        if not unresolved_ids:
            return
        baseline_ids = set(
            UiElementSnapshot.objects.filter(
                element_id__in=unresolved_ids,
                test_env=self.test_env,
                status=1,
            ).values_list('element_id', flat=True)
        )
        for element_id in unresolved_ids:
            self._snapshot_baseline_cache[element_id] = element_id in baseline_ids

    def __should_collect_snapshot(self, element_id: int | None) -> bool:
        if not element_id:
            return False
        self.__cache_snapshot_baselines([element_id])
        return not self._snapshot_baseline_cache[element_id]

    def __socket_send(
            self,
            data_model,
            func_name: str,
            is_open=False,
            mark_running: bool = True,
    ):
        if self.is_send:
            target_user = self.actuator_user
            workspace_id = self.__value(data_model, 'workspace_id')
            executor_mode = (
                ExecutorModeEnum.WORKSPACE.value
                if workspace_id
                else ExecutorModeEnum.SPECIFIED.value
                if self.actuator_user_explicit
                else ExecutorModeEnum.SELF.value
            )
            send_data = SocketEnvelopeContract(
                code=200,
                msg=f'{ClientNameEnum.DRIVER.value}：收到用例数据，准备开始执行自动化任务！',
                user=target_user,
                is_notice=ClientTypeEnum.ACTUATOR,
                data=SocketCommandContract(func_name=func_name, func_args=data_model),
            )
            failed_dispatch_recorded = False
            try:
                connection = SocketConnectionService.require_actuator(target_user)
                lease = self.__bind_executor_slot(data_model, connection, func_name)
                self.last_executor_task = SocketMessageService.send_socket_data(
                    send_data,
                    executor_mode=executor_mode,
                    ttl_seconds=0,
                    created_by=self.user_id,
                )
                if self.last_executor_task.status == ExecutorTaskStatusEnum.FAILED.value:
                    failed_dispatch_recorded = True
                    raise AutoUiError(UI_EXECUTOR_EXECUTOR_TASK_EXECUTION_INVALID)
                if mark_running:
                    ExecutorSlotLeaseService.set_running(
                        str(connection.connection_id),
                        lease["slot_id"],
                        True,
                        execution_id=self.__execution_key(data_model),
                    )
            except MangoServerError as error:
                log.ui.debug(f'发送ui测试数据报错-1:{error}')
                if error.code != 1028:
                    raise error
                if is_open and not self.actuator_user_explicit:
                    usernames = SocketConnectionService.list_open_actuator_usernames()
                    random.shuffle(usernames)
                    for username in usernames:
                        try:
                            connection = SocketConnectionService.require_actuator(username)
                            lease = self.__bind_executor_slot(data_model, connection, func_name)
                            send_data.user = connection.user.username
                            self.last_executor_task = SocketMessageService.send_socket_data(
                                send_data,
                                executor_mode=ExecutorModeEnum.SPECIFIED.value,
                                ttl_seconds=0,
                                created_by=self.user_id,
                            )
                            if self.last_executor_task.status == ExecutorTaskStatusEnum.FAILED.value:
                                failed_dispatch_recorded = True
                                continue
                            if mark_running:
                                ExecutorSlotLeaseService.set_running(
                                    str(connection.connection_id),
                                    lease["slot_id"],
                                    True,
                                    execution_id=self.__execution_key(data_model),
                                )
                            log.pytest.debug(f'发送ui测试数据重试成功-2:{send_data.user}')
                            return self.last_executor_task
                        except MangoServerError:
                            continue
                # 保留失败任务用于审计，但交互请求必须立即返回执行器不可用，
                # 不能把“任务记录创建成功”误报成“已发送执行器”。
                virtual_slot = f'task-{send_data.message_id}'
                if isinstance(data_model, dict):
                    data_model.setdefault('slot_id', virtual_slot)
                elif getattr(data_model, 'slot_id', None) is None:
                    data_model.slot_id = virtual_slot
                if not failed_dispatch_recorded:
                    self.last_executor_task = SocketMessageService.send_socket_data(
                        send_data,
                        executor_mode=executor_mode,
                        ttl_seconds=0,
                        created_by=self.user_id,
                    )
                if self.actuator_user_explicit:
                    raise AutoUiError(UI_EXECUTOR_EXECUTOR_EXECUTION_INVALID_CODE_EXECUTOR_EXECUTION_INVALID,
                                      value=(target_user,),
                                      )
                raise AutoUiError(UI_EXECUTOR_EXECUTOR_EXECUTION_INVALID)
            return self.last_executor_task

    @staticmethod
    def __value(data_model, key: str):
        if isinstance(data_model, dict):
            return data_model.get(key)
        return getattr(data_model, key, None)

    def __bind_executor_slot(self, data_model, connection, func_name: str) -> dict:
        lease = ExecutorSlotLeaseService.acquire(
            user={"id": self.user_id, "username": self.send_user},
            connection=connection,
            runtime_type=func_name,
            resource_id=getattr(data_model, "execution_id", None) or getattr(data_model, "id", None),
        )
        if isinstance(data_model, dict):
            data_model["slot_id"] = lease["slot_id"]
            data_model["executor_connection_id"] = str(connection.connection_id)
        else:
            data_model.slot_id = lease["slot_id"]
            data_model.executor_connection_id = str(connection.connection_id)
        return lease

    @staticmethod
    def __execution_key(data_model) -> str:
        getter = data_model.get if isinstance(data_model, dict) else lambda key: getattr(data_model, key, None)
        return str(
            getter("execution_id")
            or getter("workspace_id")
            or getter("check_id")
            or getter("id")
            or uuid.uuid4()
        )

    def __environment_config(self, project_product_id: int, ) -> UiEnvironmentContract:
        test_object: TestObject = func_test_object_value(self.test_env, project_product_id, AutoTypeEnum.UI.value)
        return UiEnvironmentContract(
            id=test_object.id,
            test_object_value=test_object.value,
            target_config=(test_object.target_config or None) if not test_object.value else None,
        )

    @classmethod
    def __public_data(cls, project_product_id, test_env, front_public_ids=None) -> list[UiPublicVariableContract]:
        ui_public_list = UiCaseGlobalVariableService.list_public(project_product_id, test_env, front_public_ids)
        public_data = []
        for item in ui_public_list:
            if cls.__is_noisy_public_value(item.value):
                log.ui.warning(f'跳过异常大的UI公共变量：id={item.id}，key={item.key}，长度={len(str(item.value or ""))}')
                continue
            if item.type == UiPublicTypeEnum.SQL.value:
                DataFactoryDatasourceResolver.require_sql_public_alias(
                    item.datasource_alias,
                    project_product_id,
                )
            public_data.append(
                UiPublicVariableContract(
                    id=item.id,
                    type=item.type,
                    key=item.key,
                    value=item.value,
                    datasource_alias=item.datasource_alias_id,
                )
            )
        return public_data

    @classmethod
    def __is_noisy_public_value(cls, value) -> bool:
        text = str(value or '')
        if len(text) <= cls.PUBLIC_VALUE_MAX_LENGTH:
            return False
        return any(keyword in text for keyword in cls.PUBLIC_VALUE_STORAGE_NOISE)
