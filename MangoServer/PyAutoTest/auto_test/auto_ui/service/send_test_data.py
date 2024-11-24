# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023/4/28 11:56
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_system.service.socket_link.socket_user import SocketUser
from PyAutoTest.auto_test.auto_system.views.test_suite_report import TestSuiteReportCRUD
from PyAutoTest.auto_test.auto_ui.models import *
from PyAutoTest.auto_test.auto_user.tools.factory import func_mysql_config, func_test_object_value
from PyAutoTest.enums.socket_api_enum import UiSocketEnum
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.tools_enum import ClientTypeEnum, StatusEnum, ClientNameEnum, AutoTypeEnum
from PyAutoTest.enums.ui_enum import DriveTypeEnum

from PyAutoTest.exceptions import *
from PyAutoTest.models.socket_model import SocketDataModel, QueueModel
from PyAutoTest.models.ui_model import *
from PyAutoTest.tools.view.snowflake import Snowflake


class SendTestData:

    def __init__(self,
                 user_id: int,
                 test_env: int,
                 case_executor: list | None = None,
                 tasks_id: int = None,
                 is_notice: int = 0,
                 is_send: bool = True):
        self.user_id = user_id
        self.test_env = test_env
        self.case_executor = self.__get_case_executor(case_executor)
        self.tasks_id = tasks_id
        self.is_notice = is_notice
        self.is_send = is_send
        self.username = User.objects.get(id=user_id).username

    def test_case_batch(self, case_id_list: list) -> None:
        test_suite_id = Snowflake.generate_id()
        if self.case_executor:
            max_len = max(len(case_id_list), len(self.case_executor))
            for i in range(max_len):
                case_id = case_id_list[i % len(case_id_list)]
                username = self.case_executor[i % len(self.case_executor)]
                case_model = self.test_case(case_id, test_suite_id)
                self.__socket_send(func_name=UiSocketEnum.CASE_BATCH.value,
                                   data_model=case_model,
                                   username=username)
        else:
            for case_id in case_id_list:
                case_model = self.test_case(case_id, test_suite_id)
                self.__socket_send(func_name=UiSocketEnum.CASE_BATCH.value,
                                   data_model=case_model)
        TestSuiteReportCRUD.inside_post({
            'id': test_suite_id,
            'type': AutoTestTypeEnum.UI.value,
            'test_env': self.test_env,
            'error_message': None,
            'run_status': StatusEnum.FAIL.value,
            'status': None,
            'case_list': case_id_list,
            'is_notice': self.is_notice,
            'user': self.user_id,
            'project_product': UiCase.objects.get(id=case_id_list[0]).project_product_id,
        })

    def test_case(self, case_id: int, test_suite_id) -> CaseModel:
        case = UiCase.objects.get(id=case_id)
        objects_filter = UiCaseStepsDetailed.objects.filter(case=case.id).order_by('case_sort')
        return CaseModel(
            test_suite_id=test_suite_id,
            id=case.id,
            name=case.name,
            module_name=case.module.name,
            project_product=case.project_product.id,
            case_people=case.case_people.nickname,
            front_custom=case.front_custom,
            front_sql=case.front_sql,
            posterior_sql=case.posterior_sql,
            steps=[self.steps_model(i.page_step.id, i.id) for i in objects_filter],
            public_data_list=self.__public_data(case.project_product_id)
        )

    def test_steps(self, steps_id: int) -> PageStepsModel:
        page_steps_model = self.steps_model(steps_id)
        self.__socket_send(func_name=UiSocketEnum.PAGE_STEPS.value, data_model=page_steps_model)
        return page_steps_model

    def test_element(self, data: dict) -> None:
        try:
            page = UiPage.objects.get(id=data['page_id'])
        except UiPage.DoesNotExist as error:
            raise UiError(*ERROR_MSG_0030, error=error)
        element_obj = UiElement.objects.get(id=data['id'])
        page_steps_model = PageStepsModel(
            id=page.id,
            name=page.name,
            project_product=page.project_product.id,
            module_name=page.module.name,
            type=page.project_product.client_type,
            url=page.url,
            element_list=[self.element_model(element_obj, True, data)],
            equipment_config=self.__equipment_config(page.project_product.client_type),
            environment_config=self.__environment_config(page.project_product.id),
            public_data_list=self.__public_data(page.project_product_id),
        )
        self.__socket_send(func_name=UiSocketEnum.PAGE_STEPS.value, data_model=page_steps_model)

    def steps_model(self,
                    page_steps_id: id,
                    case_step_details_id: int | None = None) -> PageStepsModel:
        page_steps = UiPageSteps.objects.get(id=page_steps_id)
        page_steps_model = PageStepsModel(
            id=page_steps.id,
            name=page_steps.name,
            project_product=page_steps.project_product.id,
            module_name=page_steps.module.name,
            type=page_steps.project_product.client_type,
            url=page_steps.page.url,
            equipment_config=self.__equipment_config(page_steps.project_product.client_type),
            environment_config=self.__environment_config(page_steps.project_product.id),
            public_data_list=self.__public_data(page_steps.project_product_id),
            case_step_details_id=case_step_details_id,

        )
        if case_step_details_id:
            for case_data in UiCaseStepsDetailed.objects.get(id=case_step_details_id).case_data:
                page_steps_model.case_data.append(StepsDataModel(**case_data))

        page_steps_element: list[UiPageStepsDetailed] = UiPageStepsDetailed \
            .objects.filter(page_step=page_steps.id).order_by('step_sort')
        for i in page_steps_element:
            page_steps_model.element_list.append(self.element_model(i))
        return page_steps_model

    @classmethod
    def element_model(cls,
                      steps_element: UiPageStepsDetailed | UiElement,
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
                ope_key=data['ope_key'],
                ope_value=data['ope_value'],
                is_iframe=steps_element.is_iframe,
            )

    def __socket_send(self, data_model, func_name: str, username: str = None) -> None:
        if self.is_send:
            data = QueueModel(func_name=func_name, func_args=data_model)
            ChatConsumer.active_send(SocketDataModel(
                code=200,
                msg=f'{ClientNameEnum.DRIVER.value}：收到用例数据，准备开始执行自动化任务！',
                user=username if username else self.username,
                is_notice=ClientTypeEnum.ACTUATOR.value,
                data=data,
            ))

    @classmethod
    def __get_case_executor(cls, case_executor):
        error = None
        if case_executor:
            case_executor = []
            for nickname in case_executor:
                try:
                    user_obj = User.objects.get(nickname=nickname)
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

    def __equipment_config(self, _type: int) -> EquipmentModel:
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
            mysql_config = func_mysql_config(self.test_env)
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
