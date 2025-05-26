# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023/4/28 11:56
# @Author : 毛鹏
import copy
import random

from pydantic import ValidationError

from src.auto_test.auto_system.consumers import ChatConsumer
from src.auto_test.auto_system.models import TestObject
from src.auto_test.auto_system.service.socket_link.socket_user import SocketUser
from src.auto_test.auto_ui.models import *
from src.auto_test.auto_user.tools.factory import func_mysql_config, func_test_object_value
from src.enums.socket_api_enum import UiSocketEnum
from src.enums.system_enum import ClientTypeEnum, ClientNameEnum
from src.enums.tools_enum import StatusEnum, AutoTypeEnum, TaskEnum
from src.exceptions import *
from src.models.socket_model import SocketDataModel, QueueModel
from src.models.ui_model import *


class TestCase:

    def __init__(self,
                 user_id: int,
                 username: str,
                 test_env: int,
                 tasks_id: int = None,
                 is_send: bool = False):
        self.user_id = user_id
        self.send_user = username
        self.test_env = test_env
        self.tasks_id = tasks_id
        self.is_send = is_send

    def test_case(self,
                  case_id: int,
                  case_name: str = None,
                  test_suite: int | None = None,
                  test_suite_details: int | None = None,
                  parametrize: list[dict] | list = None,
                  send_case_user: str = None) -> CaseModel:
        case = UiCase.objects.get(id=case_id)
        case.status = TaskEnum.PROCEED.value
        case.save()
        case_steps_detailed = UiCaseStepsDetailed.objects.filter(case=case.id).order_by('case_sort')
        case_model = CaseModel(
            send_user=send_case_user if send_case_user else self.send_user,
            test_suite_details=test_suite_details,
            test_suite_id=test_suite,
            id=case.id,
            name=case_name if case_name else case.name,
            module_name=case.module.name,
            project_product=case.project_product.id,
            project_product_name=case.project_product.name,
            test_env=self.test_env,
            case_people=case.case_people.name,
            front_custom=case.front_custom,
            front_sql=case.front_sql,
            posterior_sql=case.posterior_sql,
            parametrize=case.parametrize,
            steps=[self.steps_model(i.page_step.id, i) for i in case_steps_detailed],
            public_data_list=self.__public_data(case.project_product_id),
        )
        if case.parametrize and test_suite is None:
            for i in case.parametrize:
                case_model_1 = copy.deepcopy(case_model)
                case_model_1.parametrize = i.get('parametrize')
                case_model_1.name = f'{case.name} - {i.get("name")}'
                self.__socket_send(func_name=UiSocketEnum.CASE_BATCH.value,
                                   data_model=case_model_1, is_open=True)
        elif test_suite and test_suite_details and parametrize:
            case_model.parametrize = parametrize
            self.__socket_send(func_name=UiSocketEnum.CASE_BATCH.value,
                               data_model=case_model, is_open=True)
        else:
            self.__socket_send(func_name=UiSocketEnum.CASE_BATCH.value,
                               data_model=case_model, is_open=True)
        return case_model

    def test_steps(self, steps_id: int) -> PageStepsModel:
        page_steps_model = self.steps_model(steps_id)
        self.__socket_send(func_name=UiSocketEnum.PAGE_STEPS.value, data_model=page_steps_model)
        return page_steps_model

    def test_page_steps(self, page_steps_detailed_id: id) -> PageStepsModel:
        page_steps_detailed = PageStepsDetailed.objects.get(id=page_steps_detailed_id)
        page_steps_model = PageStepsModel(
            id=page_steps_detailed.id,
            name=page_steps_detailed.page_step.name,
            project_product=page_steps_detailed.page_step.project_product.id,
            project_product_name=page_steps_detailed.page_step.project_product.name,
            module_name=page_steps_detailed.page_step.module.name,
            type=page_steps_detailed.page_step.project_product.ui_client_type,
            url=page_steps_detailed.ele_name.page.url,
            switch_step_open_url=True,
            error_retry=None,
            element_list=[self.element_model(page_steps_detailed, )],
            # equipment_config=self.__equipment_config(page_steps_detailed.page_step.project_product.ui_client_type),
            environment_config=self.__environment_config(page_steps_detailed.page_step.project_product.id),
            public_data_list=self.__public_data(page_steps_detailed.page_step.project_product.id),
        )
        self.__socket_send(func_name=UiSocketEnum.PAGE_STEPS.value, data_model=page_steps_model)
        return page_steps_model

    def test_element(self, data: dict) -> None:
        try:
            page = Page.objects.get(id=data['page_id'])
        except Page.DoesNotExist as error:
            raise UiError(*ERROR_MSG_0030, error=error)
        element_obj = PageElement.objects.get(id=data['id'])
        page_steps_model = PageStepsModel(
            id=page.id,
            name=page.name,
            project_product=page.project_product.id,
            project_product_name=page.project_product.name,
            module_name=page.module.name,
            type=page.project_product.ui_client_type,
            url=page.url,
            switch_step_open_url=False,
            error_retry=None,
            element_list=[self.element_model(element_obj, True, data)],
            # equipment_config=self.__equipment_config(page.project_product.ui_client_type),
            environment_config=self.__environment_config(page.project_product.id),
            public_data_list=self.__public_data(page.project_product_id),
        )
        self.__socket_send(func_name=UiSocketEnum.PAGE_STEPS.value, data_model=page_steps_model)

    def steps_model(self,
                    page_steps_id: id,
                    case_steps_detailed: UiCaseStepsDetailed | None = None) -> PageStepsModel:
        page_steps = PageSteps.objects.get(id=page_steps_id)
        page_steps.status = TaskEnum.PROCEED.value
        page_steps.save()
        page_steps_model = PageStepsModel(
            id=page_steps.id,
            name=page_steps.name,
            project_product=page_steps.project_product.id,
            project_product_name=page_steps.project_product.name,
            module_name=page_steps.module.name,
            type=page_steps.project_product.ui_client_type,
            url=page_steps.page.url,
            switch_step_open_url=False,
            error_retry=None,
            environment_config=self.__environment_config(page_steps.project_product.id),
            public_data_list=self.__public_data(page_steps.project_product_id),
            case_step_details_id=case_steps_detailed.id if case_steps_detailed else None,
        )
        if case_steps_detailed:
            case_steps_detailed.status = TaskEnum.PROCEED.value
            case_steps_detailed.save()
            page_steps_model.switch_step_open_url = bool(case_steps_detailed.switch_step_open_url)
            page_steps_model.error_retry = case_steps_detailed.error_retry
            try:
                page_steps_model.case_data = [StepsDataModel(**i) for i in case_steps_detailed.case_data]
            except ValidationError:
                raise UiError(401, f'请刷新这个用例步骤的数据，这个数据我之前在保存的时候，有一些问题，请刷新后重试')
        page_steps_element = PageStepsDetailed.objects.filter(page_step=page_steps.id).order_by('step_sort')
        page_steps_model.element_list = [self.element_model(i) for i in page_steps_element]
        return page_steps_model

    @classmethod
    def element_model(cls,
                      steps_element: PageStepsDetailed | PageElement,
                      is_test_element: bool = False,
                      data: dict = None) -> ElementModel:
        if not is_test_element and data is None:
            return ElementModel(
                id=steps_element.id,
                type=steps_element.type,
                name=steps_element.ele_name.name if steps_element.ele_name else None,
                loc=steps_element.ele_name.loc if steps_element.ele_name else None,
                exp=steps_element.ele_name.exp if steps_element.ele_name else None,
                sleep=steps_element.ele_name.sleep if steps_element.ele_name else None,
                sub=steps_element.ele_name.sub if steps_element.ele_name else None,
                ope_key=steps_element.ope_key,
                ope_value=steps_element.ope_value,
                is_iframe=steps_element.ele_name.is_iframe if steps_element.ele_name else None,
                key_list=steps_element.key_list,
                sql=steps_element.sql,
                key=steps_element.key,
                value=steps_element.value
            )
        else:
            return ElementModel(
                id=steps_element.id,
                type=data.get('type'),
                name=steps_element.name,
                loc=steps_element.loc,
                exp=steps_element.exp,
                sleep=steps_element.sleep,
                sub=steps_element.sub,
                ope_key=data.get('ope_key'),
                ope_value=data.get('ope_value'),
                is_iframe=steps_element.is_iframe,
            )

    def __socket_send(self, data_model, func_name: str, is_open=False) -> None:
        if self.is_send:
            send_data = SocketDataModel(
                code=200,
                msg=f'{ClientNameEnum.DRIVER.value}：收到用例数据，准备开始执行自动化任务！',
                user=self.send_user,
                is_notice=ClientTypeEnum.ACTUATOR,
                data=QueueModel(func_name=func_name, func_args=data_model),
            )
            try:
                ChatConsumer.active_send(send_data)
            except MangoServerError as error:
                user_list = [i.username for i in SocketUser.user if i.is_open]
                if error.code == 328 and is_open and user_list:
                    send_data.user = user_list[random.randint(0, len(user_list) - 1)]
                    ChatConsumer.active_send(send_data)
                else:
                    raise error

    def __environment_config(self, project_product_id: int, ) -> EnvironmentConfigModel:
        test_object: TestObject = func_test_object_value(self.test_env, project_product_id, AutoTypeEnum.UI.value)
        mysql_config = None
        if StatusEnum.SUCCESS.value in [test_object.db_c_status, test_object.db_rud_status]:
            mysql_config = func_mysql_config(test_object.id)
        return EnvironmentConfigModel(
            id=test_object.id,
            test_object_value=test_object.value,
            db_c_status=bool(test_object.db_c_status),
            db_rud_status=bool(test_object.db_rud_status),
            mysql_config=mysql_config,
        )

    @classmethod
    def __public_data(cls, project_product_id) -> list[UiPublicModel]:
        ui_public_list = UiPublic \
            .objects \
            .filter(project_product=project_product_id, status=StatusEnum.SUCCESS.value) \
            .order_by('type')
        return [UiPublicModel(type=i.type, key=i.key, value=i.value) for i in ui_public_list]
