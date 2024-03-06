# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023/4/28 11:56
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_system.models import TasksRunCaseList
from PyAutoTest.auto_test.auto_system.models import TestObject, User
from PyAutoTest.auto_test.auto_system.service.get_common_parameters import GetCommonParameters
from PyAutoTest.auto_test.auto_system.service.get_database import GetDataBase
from PyAutoTest.auto_test.auto_system.service.update_test_suite import TestSuiteReportUpdate
from PyAutoTest.auto_test.auto_ui.models import UiCase, UiPageSteps, UiPageStepsDetailed, UiCaseStepsDetailed, \
    UiElement, UiConfig, UiPage
from PyAutoTest.enums.socket_api_enum import UiSocketEnum
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.tools_enum import ClientTypeEnum, StatusEnum, ClientNameEnum
from PyAutoTest.enums.ui_enum import DriveTypeEnum
from PyAutoTest.exceptions.tools_exception import DoesNotExistError
from PyAutoTest.exceptions.ui_exception import UiConfigQueryIsNoneError
from PyAutoTest.models.socket_model import SocketDataModel, QueueModel
from PyAutoTest.models.socket_model.ui_model import *
from PyAutoTest.tools.view_utils.error_msg import ERROR_MSG_0029, ERROR_MSG_0030
from PyAutoTest.tools.view_utils.snowflake import Snowflake


class UiTestRun:

    def __init__(self,
                 user_id: int,
                 test_obj_id: int,
                 tasks_id: int = None,
                 is_notice: bool = False,
                 spare_test_object_id: int = None,
                 concurrent: int = None
                 ):
        self.user_obj = User.objects.get(id=user_id)
        self.test_object = TestObject.objects.get(id=test_obj_id)
        self.user_id = user_id
        self.test_object_id = test_obj_id
        self.tasks_id = tasks_id
        self.is_notice = is_notice
        self.spare_test_object_id = spare_test_object_id
        self.concurrent = concurrent

    def steps(self, steps_id: int, is_send: bool = True) -> PageStepsModel:
        """
        收集步骤数据
        @param steps_id: 步骤id
        @param is_send: 是否选择发送
        @return:
        """
        case_model = self.__data_ui_case(steps_id)
        if is_send:
            self.__socket_send(func_name=UiSocketEnum.PAGE_STEPS.value, case_model=case_model)
        return case_model

    def case(self, case_id: int, is_send: bool = True, is_batch: bool = False) -> CaseModel:
        """
        执行一个用例组
        @param case_id: 用例ID
        @param is_send: 是否发送
        @param is_batch: 是否是批量发送
        @return:
        """
        if self.tasks_id:
            tasks_run_case = TasksRunCaseList.objects.get(task=self.tasks_id, case=case_id)
            self.test_object_id = tasks_run_case.test_object.id if tasks_run_case.test_object else\
                self.spare_test_object_id
        case = UiCase.objects.get(id=case_id)
        objects_filter = UiCaseStepsDetailed.objects.filter(case=case.id).order_by('case_sort')
        case_model = CaseModel(
            id=case.id,
            name=case.name,
            is_batch=StatusEnum.SUCCESS.value if is_batch else StatusEnum.FAIL.value,
            project=case.project.id,
            module_name=case.module_name.name,
            case_people=case.case_people.nickname,
            front_custom=case.front_custom,
            front_sql=case.front_sql,
            posterior_sql=case.posterior_sql,
            run_config=self.__get_run_config(),
            case_list=[self.__data_ui_case(i.page_step.id, i.id, False) for i in objects_filter],
        )
        if is_send:
            model = TestSuiteModel(id=Snowflake.generate_id(),
                                   type=AutoTestTypeEnum.UI.value,
                                   project=case.project.id,
                                   test_object=self.test_object_id,
                                   error_message=None,
                                   run_status=0,
                                   case_list=[])
            model.case_list.append(case_model)
            self.__socket_send(func_name=UiSocketEnum.CASE_BATCH.value,
                               case_model=model)
            TestSuiteReportUpdate(model).add_test_suite_report()
        return case_model

    def case_batch(self, case_id_list: list) -> list[CaseModel]:
        """
        批量执行用例组用例
        @param case_id_list: 用例组的list或int
        @return:
        """
        test_suite_id = Snowflake.generate_id()
        case_group_list: list[CaseModel] = []
        for index, case_id in enumerate(case_id_list):
            is_last = (index == len(case_id_list) - 1)
            if is_last:
                case_group_list.append(self.case(case_id=case_id, is_send=False, is_batch=True))
            else:
                case_group_list.append(self.case(case_id=case_id, is_send=False))

        model = TestSuiteModel(id=test_suite_id,
                               type=AutoTestTypeEnum.UI.value,
                               project=case_group_list[0].project,
                               test_object=self.test_object_id,
                               is_notice=self.is_notice,
                               error_message=None,
                               run_status=0,
                               concurrent=self.concurrent,
                               case_list=case_group_list)
        self.__socket_send(func_name=UiSocketEnum.CASE_BATCH.value,
                           case_model=model)
        TestSuiteReportUpdate(model).add_test_suite_report()

        return case_group_list

    def __socket_send(self, case_model, func_name: str) -> None:
        """
        发送给第三方工具方法
        @param case_model: 需要发送的json数据
        @param func_name: 需要执行的函数
        @return:
        """
        data = QueueModel(func_name=func_name, func_args=case_model)
        ChatConsumer.active_send(SocketDataModel(
            code=200,
            msg=f'{ClientNameEnum.DRIVER.value}：收到用例数据，准备开始执行自动化任务！',
            user=self.user_obj.username,
            is_notice=ClientTypeEnum.ACTUATOR.value,
            data=data,
        ))

    def __data_ui_case(self,
                       page_steps_id: int,
                       case_step_details_id: int | None = None,
                       is_page_step: bool = True) -> PageStepsModel:
        """
        根据test对象和步骤ID返回一个步骤测试对象
        @param page_steps_id: 步骤id
        @return: 返回一个数据处理好的测试对象
        """
        step = UiPageSteps.objects.get(id=page_steps_id)
        page_steps_model = PageStepsModel(
            id=step.id,
            name=step.name,
            case_step_details_id=case_step_details_id,
            project=step.project.id,
            test_object_value=self.test_object.value,
            url=step.page.url,
            type=step.page.type,
            equipment_config=self.__get_web_config(
                self.test_object.value) if step.page.type == DriveTypeEnum.WEB.value else self.__get_app_config(),
            run_config=self.__get_run_config()
        )
        if not is_page_step:
            for case_data in UiCaseStepsDetailed.objects.get(id=case_step_details_id).case_data:
                page_steps_model.case_data.append(StepsDataModel(**case_data))
        step_sort_list: list[UiPageStepsDetailed] = UiPageStepsDetailed.objects.filter(page_step=step.id).order_by(
            'step_sort')
        for i in step_sort_list:
            page_steps_model.element_list.append(ElementModel(
                id=i.id,
                type=i.type,
                ele_name_a=i.ele_name_a.name if i.ele_name_a else None,
                ele_name_b=i.ele_name_b.name if i.ele_name_b else None,
                ele_loc_a=i.ele_name_a.loc if i.ele_name_a else None,
                locator=i.ele_name_a.locator if i.ele_name_a else None,
                ele_loc_b=i.ele_name_b.loc if i.ele_name_b else None,
                ele_exp=i.ele_name_a.exp if i.ele_name_a else None,
                ele_sleep=i.ele_name_a.sleep if i.ele_name_a else None,
                ele_sub=i.ele_name_a.sub if i.ele_name_a else None,
                ope_type=i.ope_type,
                ope_value=i.ope_value,
                ass_type=i.ass_type,
                ass_value=i.ass_value,
                is_iframe=i.ele_name_a.is_iframe if i.ele_name_a else None,
            ))
        return page_steps_model

    def element(self, data: dict) -> None:
        try:
            page_obj = UiPage.objects.get(id=data['page_id'])
        except UiPage.DoesNotExist as error:
            raise DoesNotExistError(*ERROR_MSG_0030, error=error)
        element_obj = UiElement.objects.get(id=data['id'])
        page_steps_model = PageStepsModel(
            id=None,
            name=f'测试元素-{element_obj.name}',
            case_step_details_id=None,
            project=data['project_id'],
            test_object_value=self.test_object.value,
            url=page_obj.url,
            type=page_obj.type,
            equipment_config=self.__get_web_config(
                self.test_object.value) if page_obj.type == DriveTypeEnum.WEB.value else self.__get_app_config(),
        )
        page_steps_model.element_list.append(ElementModel(
            id=element_obj.id,
            type=data['type'],
            ele_name_a=element_obj.name,
            ele_name_b=None,
            ele_loc_a=element_obj.loc,
            locator=element_obj.locator,
            ele_loc_b=None,
            ele_exp=element_obj.exp,
            ele_sleep=element_obj.sleep,
            ele_sub=element_obj.sub,
            ope_type=data['ope_type'] if data.get('ope_type') else None,
            ope_value=data['ope_value'] if data.get('ope_value') else None,
            ass_type=data['ass_type'] if data.get('ass_type') else None,
            ass_value=data['ass_value'] if data.get('ass_value') else None,
            is_iframe=element_obj.is_iframe,
        ))
        self.__socket_send(func_name=UiSocketEnum.PAGE_STEPS.value, case_model=page_steps_model)

    def __get_web_config(self, host: str) -> WEBConfigModel:
        try:
            user_ui_config = UiConfig.objects.get(user_id=self.user_id,
                                                  status=StatusEnum.SUCCESS.value,
                                                  type=DriveTypeEnum.WEB.value)
        except UiConfig.DoesNotExist:
            raise UiConfigQueryIsNoneError(*ERROR_MSG_0029)
        return WEBConfigModel(
            browser_port=user_ui_config.browser_port,
            browser_path=user_ui_config.browser_path,
            browser_type=user_ui_config.browser_type,
            is_headless=user_ui_config.is_headless,
            host=host)

    def __get_app_config(self) -> AndroidConfigModel:
        user_ui_config = UiConfig.objects.get(user_id=self.user_id,
                                              status=StatusEnum.SUCCESS.value,
                                              type=DriveTypeEnum.ANDROID.value)
        return AndroidConfigModel(equipment=user_ui_config.equipment)

    def __get_run_config(self) -> RunConfigModel:
        mysql_config = None
        if StatusEnum.SUCCESS.value in [self.test_object.db_c_status, self.test_object.db_rud_status]:
            mysql_config = GetDataBase.get_mysql_config(self.test_object_id)
        return RunConfigModel(
            db_c_status=bool(self.test_object.db_c_status),
            db_rud_status=bool(self.test_object.db_rud_status),
            mysql_config=mysql_config,
            public_data_list=GetCommonParameters.get_ui_args(self.test_object_id)
        )
