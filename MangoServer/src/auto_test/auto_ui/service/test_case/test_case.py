# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023/4/28 11:56
# @Author : 毛鹏
import copy
import random
import traceback

from mangotools.mangos import build_decision_tree
from pydantic import ValidationError

from src.auto_test.auto_system.consumers import ChatConsumer
from src.auto_test.auto_system.models import TestObject
from src.auto_test.auto_system.service.factory import func_mysql_config, func_test_object_value
from src.auto_test.auto_system.service.socket_link.socket_user import SocketUser
from src.auto_test.auto_ui.models import *
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
        try:
            case = UiCase.objects.get(id=case_id)
        except UiCase.DoesNotExist:
            raise UiError(*ERROR_MSG_0057)
        case.status = TaskEnum.PROCEED.value
        case.save()
        case_steps_detailed = UiCaseStepsDetailed.objects.filter(case=case.id).order_by('case_sort')
        try:
            if not case_steps_detailed:
                raise UiError(*ERROR_MSG_0042)
            for i in case.front_custom:
                if not i.get('key') or not i.get('value'):
                    raise UiError(*ERROR_MSG_0029)
            for i in case.front_sql:
                if not i.get('sql_list') or not i.get('sql'):
                    raise UiError(*ERROR_MSG_0036)
            for i in case.posterior_sql:
                if not i.get('sql'):
                    raise UiError(*ERROR_MSG_0026)
            for i in case.parametrize:
                for e in i.get('parametrize'):
                    if not e.get('key') or not e.get('value'):
                        raise UiError(*ERROR_MSG_0032)
        except Exception as error:
            case.status = TaskEnum.FAIL.value
            case.save()
            raise error
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
            steps=[self.steps_model(i.page_step.id, i, bool(i.switch_step_open_url)) for i in case_steps_detailed],
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
        try:
            page_steps_model = self.steps_model(steps_id)
            self.__socket_send(func_name=UiSocketEnum.PAGE_STEPS.value, data_model=page_steps_model)
            return page_steps_model
        except Exception as error:
            page_steps = PageSteps.objects.get(id=steps_id)
            page_steps.status = TaskEnum.FAIL.value
            page_steps.save()
            raise error

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
                    page_steps_id: int,
                    case_steps_detailed: UiCaseStepsDetailed | None = None,
                    switch_step_open_url=False) -> PageStepsModel:
        page_steps = PageSteps.objects.get(id=page_steps_id)
        page_steps_element = PageStepsDetailed.objects.filter(page_step=page_steps.id)
        if not page_steps_element:
            raise UiError(*ERROR_MSG_0041)
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
            switch_step_open_url=switch_step_open_url,
            environment_config=self.__environment_config(page_steps.project_product.id),
            public_data_list=self.__public_data(page_steps.project_product_id),
            flow_data=build_decision_tree(page_steps.flow_data)
        )
        if case_steps_detailed:
            page_steps_model.case_steps_id = case_steps_detailed.id
            case_steps_detailed.status = TaskEnum.PROCEED.value
            case_steps_detailed.save()
            page_steps_model.error_retry = case_steps_detailed.error_retry
            try:
                page_steps_model.case_data = [StepsDataModel(**i) for i in case_steps_detailed.case_data]
            except ValidationError:
                log.ui.debug(f'{traceback.print_exc()}')
                raise UiError(401, f'请刷新这个用例步骤的数据，这个数据我之前在保存的时候，有一些问题，请刷新后重试')
        page_steps_model.element_list = [self.element_model(i) for i in page_steps_element]
        return page_steps_model

    @classmethod
    def element_model(cls,
                      steps_element: PageStepsDetailed | PageElement,
                      is_test_element: bool = False,
                      data: dict = None) -> ElementModel:
        if not is_test_element and data is None:
            element_model = ElementModel(
                id=steps_element.id,
                type=steps_element.type,
                name=steps_element.ele_name.name if steps_element.ele_name else None,
                sleep=steps_element.ele_name.sleep if steps_element.ele_name else None,
                ope_key=steps_element.ope_key,
                ope_value=steps_element.ope_value if steps_element.ope_value is not None else [],
                sql_execute=steps_element.sql_execute,
                custom=steps_element.custom,
                condition_value=steps_element.condition_value,
                func=steps_element.func
            )
            if steps_element.ele_name:
                element_model.elements.append(ElementListModel(
                    exp=steps_element.ele_name.exp,
                    loc=steps_element.ele_name.loc,
                    sub=steps_element.ele_name.sub,
                    is_iframe=steps_element.ele_name.is_iframe,
                    prompt=steps_element.ele_name.prompt or f'查找元素：{steps_element.ele_name.name}'
                ))
                if steps_element.ele_name.loc2 is not None and steps_element.ele_name.exp2 is not None:
                    element_model.elements.append(ElementListModel(
                        exp=steps_element.ele_name.exp2,
                        loc=steps_element.ele_name.loc2,
                        sub=steps_element.ele_name.sub2,
                        is_iframe=steps_element.ele_name.is_iframe,
                        prompt=steps_element.ele_name.prompt or f'查找元素：{steps_element.ele_name.name}'
                    ))
                if steps_element.ele_name.loc3 is not None and steps_element.ele_name.exp3 is not None:
                    element_model.elements.append(ElementListModel(
                        exp=steps_element.ele_name.exp3,
                        loc=steps_element.ele_name.loc3,
                        sub=steps_element.ele_name.sub3,
                        is_iframe=steps_element.ele_name.is_iframe,
                        prompt=steps_element.ele_name.prompt or f'查找元素：{steps_element.ele_name.name}'
                    ))
        else:
            element_model = ElementModel(
                id=steps_element.id,
                type=data.get('type'),
                name=steps_element.name,
                sleep=steps_element.sleep,
                ope_key=data.get('ope_key'),
                ope_value=data.get('ope_value') if data.get('ope_value') is not None else [],
            )
            element_model.elements.append(
                ElementListModel(exp=steps_element.exp, loc=steps_element.loc, sub=steps_element.sub,
                                 is_iframe=steps_element.is_iframe,
                                 prompt=steps_element.prompt or f'查找元素：{steps_element.name}'))
            if steps_element.loc2 is not None and steps_element.exp2 is not None:
                element_model.elements.append(
                    ElementListModel(exp=steps_element.exp2, loc=steps_element.loc2, sub=steps_element.sub2,
                                     is_iframe=steps_element.is_iframe,
                                     prompt=steps_element.prompt or f'查找元素：{steps_element.name}'))
            if steps_element.loc3 is not None and steps_element.exp3 is not None:
                element_model.elements.append(
                    ElementListModel(exp=steps_element.exp3, loc=steps_element.loc3, sub=steps_element.sub3,
                                     is_iframe=steps_element.is_iframe,
                                     prompt=steps_element.prompt or f'查找元素：{steps_element.name}'))
        return element_model

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
                if error.code == 1028 and is_open and user_list:
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
