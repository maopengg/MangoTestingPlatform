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
from src.enums.tools_enum import StatusEnum, AutoTypeEnum
from src.enums.ui_enum import DriveTypeEnum
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
        self.username = username
        self.test_env = test_env
        self.tasks_id = tasks_id
        self.is_send = is_send

    def test_case(self,
                  case_id: int,
                  case_name: str = None,
                  test_suite: int | None = None,
                  test_suite_details: int | None = None,
                  parametrize: list[dict] | list = None) -> CaseModel:
        case = UiCase.objects.get(id=case_id)
        objects_filter = UiCaseStepsDetailed.objects.filter(case=case.id).order_by('case_sort')
        case_model = CaseModel(
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
            steps=[self.steps_model(i.page_step.id, i.id) for i in objects_filter],
            public_data_list=self.__public_data(case.project_product_id),
            switch_step_open_url=True if case.switch_step_open_url else False
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
            element_list=[self.element_model(element_obj, True, data)],
            # equipment_config=self.__equipment_config(page.project_product.ui_client_type),
            environment_config=self.__environment_config(page.project_product.id),
            public_data_list=self.__public_data(page.project_product_id),
        )
        self.__socket_send(func_name=UiSocketEnum.PAGE_STEPS.value, data_model=page_steps_model)

    def steps_model(self,
                    page_steps_id: id,
                    case_step_details_id: int | None = None) -> PageStepsModel:
        page_steps = PageSteps.objects.get(id=page_steps_id)
        page_steps_model = PageStepsModel(
            id=page_steps.id,
            name=page_steps.name,
            project_product=page_steps.project_product.id,
            project_product_name=page_steps.project_product.name,
            module_name=page_steps.module.name,
            type=page_steps.project_product.ui_client_type,
            url=page_steps.page.url,
            # equipment_config=self.__equipment_config(page_steps.project_product.ui_client_type),
            environment_config=self.__environment_config(page_steps.project_product.id),
            public_data_list=self.__public_data(page_steps.project_product_id),
            case_step_details_id=case_step_details_id,
        )
        if case_step_details_id:
            for case_data in UiCaseStepsDetailed.objects.get(id=case_step_details_id).case_data:
                try:
                    page_steps_model.case_data.append(StepsDataModel(**case_data))
                except ValidationError:
                    raise UiError(401, f'请刷新这个用例步骤的数据，这个数据我之前在保存的时候，有一些问题，请刷新后重试')
        page_steps_element: list[PageStepsDetailed] = PageStepsDetailed \
            .objects.filter(page_step=page_steps.id).order_by('step_sort')
        for i in page_steps_element:
            page_steps_model.element_list.append(self.element_model(i))
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
        try:
            if self.is_send:
                data = QueueModel(func_name=func_name, func_args=data_model)
                ChatConsumer.active_send(SocketDataModel(
                    code=200,
                    msg=f'{ClientNameEnum.DRIVER.value}：收到用例数据，准备开始执行自动化任务！',
                    user=self.username,
                    is_notice=ClientTypeEnum.ACTUATOR,
                    data=data,
                ))
        except MangoServerError as error:
            user_list = []
            for i in SocketUser.user:
                if i.is_open:
                    user_list.append(i.username)
            if error.code == 328 and is_open and user_list:
                if self.is_send:
                    data = QueueModel(func_name=func_name, func_args=data_model)
                    ChatConsumer.active_send(SocketDataModel(
                        code=200,
                        msg=f'{ClientNameEnum.DRIVER.value}：收到用例数据，准备开始执行自动化任务！',
                        user=user_list[random.randint(0, len(user_list) - 1)],
                        is_notice=ClientTypeEnum.ACTUATOR,
                        data=data,
                    ))
            else:
                raise error

    @classmethod
    def __get_case_executor(cls, case_executor):
        error = None
        if case_executor:
            case_executor = []
            for name in case_executor:
                try:
                    user_obj = User.objects.get(name=name)
                except User.DoesNotExist:
                    raise UiError(*ERROR_MSG_0050)
                try:
                    SocketUser.get_user_client_obj(user_obj.username)
                except UiError as error:
                    error = error
                else:
                    case_executor.append(user_obj.username)
            if case_executor:
                return case_executor
            else:
                raise error

    def inspect_environment_config(self, case_id: int) -> bool:
        objects_filter = UiCaseStepsDetailed.objects.filter(case=case_id).first()
        if objects_filter:
            try:
                page_steps = PageSteps.objects.get(id=objects_filter.page_step.id)
                # self.__equipment_config(page_steps.project_product.ui_client_type)
            except UiError:
                return False
            else:
                return True
        else:
            return False

    def __equipment_config(self, _type: int):
        try:
            if _type == DriveTypeEnum.WEB.value:
                user_ui_config = UiConfig.objects.get(user_id=self.user_id,
                                                      status=StatusEnum.SUCCESS.value,
                                                      type=DriveTypeEnum.WEB.value)
            elif _type == DriveTypeEnum.ANDROID.value:
                user_ui_config = UiConfig.objects.get(user_id=self.user_id,
                                                      status=StatusEnum.SUCCESS.value,
                                                      type=DriveTypeEnum.ANDROID.value)
            elif _type == DriveTypeEnum.DESKTOP.value:
                raise UiError(*ERROR_MSG_0040)
            else:
                raise UiError(*ERROR_MSG_0040)
            if user_ui_config.config is None:
                raise UiError(*ERROR_MSG_0055)
            return EquipmentModel(type=user_ui_config.type, **user_ui_config.config)
        except UiConfig.DoesNotExist:
            raise UiError(*ERROR_MSG_0029)

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
