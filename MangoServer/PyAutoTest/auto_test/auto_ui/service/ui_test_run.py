# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023/4/28 11:56
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_system.models import TasksRunCaseList
from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_system.service.socket_link.socket_user import SocketUser
from PyAutoTest.auto_test.auto_system.views.test_suite_report import TestSuiteReportCRUD
from PyAutoTest.auto_test.auto_ui.models import *
from PyAutoTest.auto_test.auto_user.tools.factory import func_mysql_config, func_test_object_value
from PyAutoTest.enums.socket_api_enum import UiSocketEnum
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.tools_enum import ClientTypeEnum, StatusEnum, ClientNameEnum, AutoTypeEnum
from PyAutoTest.enums.ui_enum import DriveTypeEnum
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.exceptions.error_msg import ERROR_MSG_0029, ERROR_MSG_0030, ERROR_MSG_0050, ERROR_MSG_0051
from PyAutoTest.exceptions.tools_exception import DoesNotExistError, SocketClientNotPresentError
from PyAutoTest.exceptions.ui_exception import UiConfigQueryIsNoneError
from PyAutoTest.exceptions.user_exception import UserIsNoneError
from PyAutoTest.models.socket_model import SocketDataModel, QueueModel
from PyAutoTest.models.socket_model.ui_model import *
from PyAutoTest.tools.view.snowflake import Snowflake

class UiTestRun:

    def __init__(self,
                 user_id: int,
                 test_env: int,
                 case_executor: list | None = None,
                 tasks_id: int = None,
                 is_notice: int = 0,
                 is_send=True,
                 ):
        self.user_id = user_id
        self.username = User.objects.get(id=user_id).username
        self.test_env = test_env
        self.tasks_id = tasks_id
        self.is_notice = is_notice
        self.is_send = is_send
        self.case_executor = case_executor
        if self.case_executor:
            username_list = []
            for nickname in self.case_executor:
                try:
                    user_obj = User.objects.get(nickname=nickname)
                except User.DoesNotExist:
                    raise UserIsNoneError(*ERROR_MSG_0050)
                try:
                    SocketUser.get_user_client_obj(user_obj.username)
                except SocketClientNotPresentError as error:
                    self.error = error
                else:
                    username_list.append(user_obj.username)
            if username_list:
                self.case_executor = username_list
            else:
                raise self.error

    def case_batch(self, case_id_list: list) -> None:

        test_suite_id = Snowflake.generate_id()
        try:
            if self.case_executor:
                max_len = max(len(case_id_list), len(self.case_executor))
                for i in range(max_len):
                    case_id = case_id_list[i % len(case_id_list)]
                    username = self.case_executor[i % len(self.case_executor)]
                    case_model = self.send_case(case_id, test_suite_id)
                    self.__socket_send(func_name=UiSocketEnum.CASE_BATCH.value,
                                       case_model=case_model,
                                       username=username)
            else:
                for case_id in case_id_list:
                    case_model = self.send_case(case_id, test_suite_id)
                    self.__socket_send(func_name=UiSocketEnum.CASE_BATCH.value,
                                       case_model=case_model)
        except MangoServerError as error:
            raise error
        else:
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
            # with open(r'D:\GitCode\MangoTestingPlatform\MangoServer\test.json', 'w') as f:
            #     json.dump(case_model_list, f, indent=4, ensure_ascii=False)

    def send_case(self, case_id: int, test_suite_id) -> CaseModel:
        if self.tasks_id:
            tasks_run_case = TasksRunCaseList.objects.get(task=self.tasks_id, case=case_id)
            # self.test_object_id = tasks_run_case \
            #     .test_object \
            #     .id if tasks_run_case \
            #     .test_object else \
            #     self.spare_test_object_id

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
            steps=[self.__page_steps(i.page_step.id, i.id) for i in objects_filter],
            public_data_list=self.__public_data(case.project_product_id)
        )

    def steps(self, steps_id: int, is_send: bool = True) -> PageStepsModel:

        case_model = self.__page_steps(steps_id)
        if is_send:
            self.__socket_send(func_name=UiSocketEnum.PAGE_STEPS.value, case_model=case_model)
        return case_model

    def element(self, data: dict) -> None:
        try:
            page_obj = UiPage.objects.get(id=data['page_id'])
        except UiPage.DoesNotExist as error:
            raise DoesNotExistError(*ERROR_MSG_0030, error=error)
        element_obj = UiElement.objects.get(id=data['id'])
        test_object: TestObject = func_test_object_value(self.test_env,
                                                         element_obj.page.project_product_id,
                                                         AutoTypeEnum.UI.value)
        page_steps_model = PageStepsModel(
            id=None,
            name=f'测试元素-{element_obj.name}',
            case_step_details_id=None,
            project_product=data['project_product_id'],
            url=page_obj.url,
            type=page_obj.project_product.client_type,
            equipment_config=self.__get_web_config() if page_obj.project_product.client_type == DriveTypeEnum.WEB.value else self.__get_app_config(),
            environment_config=self.__environment_config(test_object, page_obj.project_product_id)
        )
        page_steps_model.element_list.append(ElementModel(
            id=element_obj.id,
            type=data['type'],
            name=element_obj.name,
            loc=element_obj.loc,
            exp=element_obj.exp,
            sleep=element_obj.sleep,
            sub=element_obj.sub,
            ope_key=data['ope_type'] if data.get('ope_type') else data.get('ass_type'),
            ope_value=data['ope_value'] if data.get('ope_value') else None,
            ass_value=data['ass_value'] if data.get('ass_value') else None,
            is_iframe=element_obj.is_iframe,
        ))
        self.__socket_send(func_name=UiSocketEnum.PAGE_STEPS.value, case_model=page_steps_model)

    def __socket_send(self, case_model, func_name: str, username: str = None) -> None:
        if self.is_send:
            data = QueueModel(func_name=func_name, func_args=case_model)
            ChatConsumer.active_send(SocketDataModel(
                code=200,
                msg=f'{ClientNameEnum.DRIVER.value}：收到用例数据，准备开始执行自动化任务！',
                user=username if username else self.username,
                is_notice=ClientTypeEnum.ACTUATOR.value,
                data=data,
            ))

    def __page_steps(self,
                     page_steps_id: int,
                     case_step_details_id: int | None = None) -> PageStepsModel:

        step = UiPageSteps.objects.get(id=page_steps_id)
        test_object: TestObject = func_test_object_value(self.test_env,
                                                         step.project_product_id,
                                                         AutoTypeEnum.UI.value)
        page_steps_model = PageStepsModel(
            id=step.id,
            name=step.name,
            case_step_details_id=case_step_details_id,
            project_product=step.project_product.id,
            test_object_value=test_object.value,
            url=step.page.url,
            type=step.project_product.client_type,
            equipment_config=self.__get_web_config() if step.project_product.client_type == DriveTypeEnum.WEB.value else self.__get_app_config(),
            environment_config=self.__environment_config(test_object, step.project_product_id)
        )
        if case_step_details_id:
            for case_data in UiCaseStepsDetailed.objects.get(id=case_step_details_id).case_data:
                page_steps_model.case_data.append(StepsDataModel(**case_data))
        else:
            page_steps_model.public_data_list = self.__public_data(step.project_product_id)

        step_sort_list: list[UiPageStepsDetailed] = UiPageStepsDetailed.objects.filter(page_step=step.id).order_by(
            'step_sort')
        for i in step_sort_list:
            page_steps_model.element_list.append(ElementModel(
                id=i.id,
                type=i.type,
                name=i.ele_name.name if i.ele_name else None,
                loc=i.ele_name.loc if i.ele_name else None,
                exp=i.ele_name.exp if i.ele_name else None,
                sleep=i.ele_name.sleep if i.ele_name else None,
                sub=i.ele_name.sub if i.ele_name else None,
                ope_key=i.ope_key,
                ope_value=i.ope_value,
                is_iframe=i.ele_name.is_iframe if i.ele_name else None,
                key_list=i.key_list,
                sql=i.sql,
                key=i.key,
                value=i.value
            ))
        return page_steps_model

    def __get_equipment_config(self):
        pass

    def __get_web_config(self) -> EquipmentModel:
        try:
            user_ui_config = UiConfig.objects.get(user_id=self.user_id,
                                                  status=StatusEnum.SUCCESS.value,
                                                  type=DriveTypeEnum.WEB.value)
        except UiConfig.DoesNotExist:
            raise UiConfigQueryIsNoneError(*ERROR_MSG_0029)
        return EquipmentModel(type=user_ui_config.type, **user_ui_config.config)

    def __get_app_config(self) -> EquipmentModel:
        try:
            user_ui_config = UiConfig.objects.get(user_id=self.user_id,
                                                  status=StatusEnum.SUCCESS.value,
                                                  type=DriveTypeEnum.ANDROID.value)
        except UiConfig.DoesNotExist:
            raise UiConfigQueryIsNoneError(*ERROR_MSG_0051)
        return EquipmentModel(type=user_ui_config.type, **user_ui_config.config)

    def __environment_config(self, test_object: TestObject, project_product_id) -> EnvironmentConfigModel:
        mysql_config = None
        if StatusEnum.SUCCESS.value in [test_object.db_c_status, test_object.db_rud_status]:
            mysql_config = func_mysql_config(self.test_env, project_product_id)
        return EnvironmentConfigModel(
            test_object_value=test_object.value,
            db_c_status=bool(test_object.db_c_status),
            db_rud_status=bool(test_object.db_rud_status),
            mysql_config=mysql_config,
        )

    @classmethod
    def __public_data(cls, project_product_id) -> list[UiPublicModel]:
        ui_public_list = UiPublic.objects \
            .filter(project_product=project_product_id, status=StatusEnum.SUCCESS.value) \
            .order_by('type')
        return [UiPublicModel(type=i.type,
                              key=i.key,
                              value=i.value) for i in ui_public_list]
