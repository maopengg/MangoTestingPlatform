# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023/4/28 11:56
# @Author : 毛鹏

from PyAutoTest.auto_test.auto_system.consumers import socket_conn
from PyAutoTest.auto_test.auto_system.data_consumer.update_test_suite import TestSuiteReportUpdate
from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_ui.models import UiPageStepsDetailed, UiCase, UiConfig, UiPageSteps, UiCaseStepsDetailed
from PyAutoTest.enums.actuator_api_enum import UiEnum
from PyAutoTest.enums.system_enum import ClientTypeEnum, AutoTestTypeEnum
from PyAutoTest.enums.system_enum import IsItEnabled, DevicePlatformEnum
from PyAutoTest.enums.ui_enum import DevicePlatform
from PyAutoTest.exceptions.ui_exception import UiConfigQueryIsNoneError
from PyAutoTest.models.socket_model import SocketDataModel, QueueModel
from PyAutoTest.models.socket_model.ui_model import *
from PyAutoTest.settings import DRIVER
from PyAutoTest.tools.snowflake import Snowflake


class RunApi:

    def __init__(self, user: dict = None):
        self.username = user.get("username")
        self.user_id = user.get("id")

    def steps(self, steps_id: int, test_obj: int, is_send: bool = True) -> tuple[
                                                                               PageStepsModel, bool] or PageStepsModel:
        """
        收集步骤数据
        @param steps_id: 步骤id
        @param test_obj: 测试对象
        @param is_send: 是否选择发送
        @return:
        """
        case_model = self.__data_ui_case(test_obj, steps_id)
        if self.username and is_send:
            return case_model, self.__socket_send(func_name=UiEnum.U_PAGE_STEPS.value, case_model=case_model)
        return case_model

    def case(self, case_id: int, test_obj: int, is_send: bool = True) -> tuple[CaseModel, bool] or CaseModel:
        """
        执行一个用例组
        @param case_id: 用例ID
        @param is_send: 是否发送
        @param test_obj: 测试对象
        @return:
        """
        case = UiCase.objects.get(pk=case_id)

        objects_filter = UiCaseStepsDetailed.objects.filter(case=case.id).order_by('case_sort')
        case_list = []
        case_cache_data = {}
        case_cache_ass = {}
        for i in objects_filter:
            case_list.append(self.__data_ui_case(test_obj, i.page_step.id))
            case_cache_data[i.page_step.name] = i.case_cache_data
            case_cache_ass[i.page_step.name] = i.case_cache_ass
        case_model = CaseModel(case_id=case.id,
                               case_name=case.name,
                               project=case.project.id,
                               module_name=case.module_name.name,
                               case_people=case.case_people.nickname,
                               case_cache_data=case_cache_data,
                               case_cache_ass=case_cache_ass,
                               case_list=case_list)
        if self.username and is_send:
            model = TestSuiteModel(id=Snowflake.generate_id(),
                                   type=AutoTestTypeEnum.UI.value,
                                   project=case.project.id,
                                   name=case.name,
                                   run_status=0,
                                   case_list=[])
            model.case_list.append(case_model)
            send_res = self.__socket_send(func_name=UiEnum.U_CASE_BATCH.value,
                                          case_model=model)
            if send_res:
                TestSuiteReportUpdate(model).update_test_suite_report()
            return case_model, send_res
        return case_model

    def case_batch(self, case_id_list: list, test_obj: int) -> tuple[list[CaseModel], bool]:
        """
        批量执行用例组用例
        @param case_id_list: 用例组的list或int
        @param test_obj:
        @return:
        """
        case_group_list: list[CaseModel] = []
        for case_id in case_id_list:
            case_group_list.append(self.case(case_id=case_id, test_obj=test_obj, is_send=False))
        model = TestSuiteModel(id=Snowflake.generate_id(),
                               type=AutoTestTypeEnum.UI.value,
                               project=case_group_list[0].project,
                               name=case_group_list[0].case_name,
                               run_status=0,
                               case_list=case_group_list)
        send_res = self.__socket_send(func_name=UiEnum.U_CASE_BATCH.value,
                                      case_model=model)
        if send_res:
            TestSuiteReportUpdate(model).update_test_suite_report()
        return case_group_list, send_res

    def __socket_send(self, case_model, func_name: str) -> bool:
        """
        发送给第三方工具方法
        @param case_model: 需要发送的json数据
        @param func_name: 需要执行的函数
        @return:
        """
        data = QueueModel(func_name=func_name, func_args=case_model)
        return socket_conn.active_send(SocketDataModel(
            code=200,
            msg=f'{DRIVER}：收到用例数据，准备开始执行自动化任务！',
            user=self.username,
            is_notice=ClientTypeEnum.ACTUATOR.value,
            data=data,
        ))

    def __data_ui_case(self, test_obj: int, page_steps_id: int) -> PageStepsModel:
        """
        根据test对象和步骤ID返回一个步骤测试对象
        @param test_obj: 测试环境id
        @param page_steps_id: 步骤id
        @return: 返回一个数据处理好的测试对象
        """
        step = UiPageSteps.objects.get(id=page_steps_id)
        case_model = PageStepsModel(
            page_steps_id=step.id,
            page_step_name=step.name,
            host=TestObject.objects.get(id=test_obj).value,
            url=step.page.url,
            type=step.page.type,
            config=
            self.__get_web_config() if step.page.type == DevicePlatform.WEB.value else self.__get_app_config()
        )

        step_sort_list: list[UiPageStepsDetailed] = UiPageStepsDetailed.objects.filter(page_step=step.id).order_by(
            'step_sort')
        for i in step_sort_list:
            ope_value = None
            if i.ope_value is not None:
                if isinstance(i.ope_value, dict):
                    ope_value = i.ope_value
                elif isinstance(i.ope_value, str):
                    ope_value = eval(i.ope_value)
            ass_value = None
            if i.ass_value is not None:
                if isinstance(i.ass_value, dict):
                    ass_value = i.ass_value
                elif isinstance(i.ass_value, str):
                    ass_value = eval(i.ass_value)
            case_model.pages_ele.append(ElementModel(
                type=i.type,
                ele_name_a=i.ele_name_a.name,
                ele_name_b=i.ele_name_b.name if i.ele_name_b else None,
                ele_loc_a=i.ele_name_a.loc,
                ele_loc_b=i.ele_name_b.loc if i.ele_name_b else None,
                ele_exp=i.ele_name_a.exp,
                ele_sleep=i.ele_name_a.sleep,
                ele_sub=i.ele_name_a.sub,
                ope_type=i.ope_type,
                ope_value=ope_value,
                ass_type=i.ass_type,
                ass_value=ass_value,
            ))
        return case_model

    def __get_web_config(self) -> WEBConfigModel:
        try:
            user_ui_config = UiConfig.objects.get(user_id=self.user_id,
                                                  status=IsItEnabled.right.value,
                                                  type=DevicePlatformEnum.WEB.value)
        except UiConfig.DoesNotExist:
            raise UiConfigQueryIsNoneError('web配置查询结果是空，请先进行配置')
        return WEBConfigModel(
            browser_port=user_ui_config.browser_port,
            browser_path=user_ui_config.browser_path,
            browser_type=user_ui_config.browser_type)

    def __get_app_config(self) -> AndroidConfigModel:
        user_ui_config = UiConfig.objects.get(user_id=self.user_id,
                                              status=IsItEnabled.right.value,
                                              type=DevicePlatformEnum.ANDROID.value)
        return AndroidConfigModel(equipment=user_ui_config.equipment)
