# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/4/28 11:56
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.consumers import socket_conn
from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_ui.models import UiCaseGroup, RunSort, UiCase, UiConfig
from PyAutoTest.base_data_model.system_data_model import SocketDataModel, QueueModel
from PyAutoTest.base_data_model.ui_data_model import CaseModel, ElementModel, CaseGroupModel, CaseGroupListModel
from PyAutoTest.enums.actuator_api_enum import UiApiEnum
from PyAutoTest.enums.system_enum import SocketEnum, DevicePlatformEnum, ClientTypeEnum
from PyAutoTest.enums.ui_enum import BrowserTypeEnum
from PyAutoTest.settings import DRIVER


class RunApi:

    def __init__(self, user: dict = None):
        self.username = user.get("username")
        self.user_id = user.get("id")

    def group_one(self, group_id: int, send: bool) -> tuple[CaseGroupModel, bool] or bool:
        """
        执行一个用例组
        @param group_id: 用例组的ID
        @param send: 用例组的ID
        @return:
        """
        case_group_data = UiCaseGroup.objects.get(pk=group_id)
        if send:
            self.username = case_group_data.timing_actuator.username
            self.user_id = case_group_data.case_people.id
        case_json = self.__group_cases(case_group_data)
        if self.username and send:
            return case_json, self.__socket_send(func_name=UiApiEnum.run_group_case.value,
                                                 case_json=case_json)
        return case_json

    def group_batch(self, group_id_list: list or int, time: bool = False) -> tuple[CaseGroupListModel, bool]:
        """
        批量执行用例组用例
        @param group_id_list: 用例组的list或int
        @param time: 定时
        @return:
        """
        case_group_list = CaseGroupListModel(list=[])
        if isinstance(group_id_list, int):
            case_group_list.list.append(self.group_one(group_id_list, time))
        elif isinstance(group_id_list, list):
            for group_id in group_id_list:
                case_group_list.list.append(self.group_one(group_id, time))
        return case_group_list, self.__socket_send(func_name=UiApiEnum.run_group_case.value,
                                                   case_json=case_group_list)

    def case_noe(self, case_id: int, test_obj: int, send: bool = False) -> tuple[CaseModel, bool] or bool:
        """
        调试用例单个执行
        """
        case_json = self.__data_ui_case(test_obj, case_id)
        if self.username and send:
            return case_json, self.__socket_send(func_name=UiApiEnum.run_debug_case.value, case_json=case_json)
        return case_json

    def case_batch(self, case_list: int or list, test_obj: int) -> tuple[list[CaseModel], bool]:
        """
        调试用例批量执行
        @param case_list: 用例id列表或者一个
        @param test_obj: 测试环境
        @return:
        """
        case_data = []
        if isinstance(case_list, int):
            case_data.append(self.case_noe(test_obj, case_list))
        elif isinstance(case_list, list):
            for case_id in case_list:
                case_data.append(self.case_noe(test_obj, case_id))
        return case_data, self.__socket_send(func_name=UiApiEnum.run_group_case.value,
                                             case_json=case_data)

    def __socket_send(self, case_json, func_name: str) -> bool:
        """
        发送给第三方工具方法
        @param case_json: 需要发送的json数据
        @param func_name: 需要执行的函数
        @return:
        """

        return socket_conn.active_send(SocketDataModel(
            code=200,
            msg=f'{DRIVER}：收到用例数据，准备开始执行自动化任务！',
            user=self.username,
            is_notice=ClientTypeEnum.ACTUATOR.value,
            data=QueueModel(func_name=func_name, func_args=case_json),
        ))

    def __group_cases(self, group: UiCaseGroup) -> CaseGroupModel:
        """
        根据用例组的列表，返回所有的测试对象
        @param group: UiCaseGroup对象，一条数据
        @return:
        """
        case_single = CaseGroupModel(group_name=group.name, case_group=[])
        for case_id in eval(group.case_id):
            case_single.case_group.append(self.__data_ui_case(group.test_obj.id, case_id))
        return case_single

    def __data_ui_case(self, test_obj: int, case_id: int) -> CaseModel:
        """
        根据test对象和用例ID返回一个UI测试对象回去
        @param test_obj: 测试环境id
        @param case_id: 用例id
        @return: 返回一个数据处理好的测试对象
        """
        case_ = UiCase.objects.get(id=case_id)
        case_model = CaseModel.create_empty()
        case_model.case_id = case_.id
        case_model.case_name = case_.name
        run_sort = RunSort.objects.filter(case=case_.id).order_by('run_sort')
        # 如果是web用例，则写入浏览器的端口，浏览器打开地址，type 执行用例url和浏览器的类型
        if case_.case_type == DevicePlatformEnum.WEB.value:
            case_model.local_port, case_model.browser_path = self.__get_web_config()
            case_model.type = DevicePlatformEnum.WEB.value
            case_model.browser_type = BrowserTypeEnum.CHROMIUM.value
            case_model.case_url = TestObject.objects.get(id=test_obj).value + run_sort[0].el_page.url

            # if self.group_id == 4 and case_.name == 'shop商城使用管理员登录并切换到妮维雅租户' or case_.name == '获取首页周日数据':
            #     case_model.case_url = 'http://mall-tenant.zalldata.cn' + run_sort[0].el_page.url
            # elif self.group_id == 4 and case_.name == '登录GrowKnows租户：妮维雅' or case_.name == '查询昨日支付订单的支付订单金额':
            #     case_model.case_url = 'https://cdxp.growknows.cn' + run_sort[0].el_page.url
            # else:
        # 如果是安卓用例，则写入设备，app和type
        elif case_.case_type == DevicePlatformEnum.ANDROID.value:
            case_model.equipment = self.__get_app_config()
            case_model.package = run_sort[0].el_page.url
            case_model.type = DevicePlatformEnum.ANDROID.value
        elif case_.case_type == DevicePlatformEnum.IOS.value:
            pass
        elif case_.case_type == DevicePlatformEnum.DESKTOP.value:
            pass
        for i in run_sort:
            if i.el_name is not None:
                case_model.case_data.append(ElementModel(
                    ope_type=i.ope_type,
                    ass_type=i.ass_type,
                    ope_value=eval(i.ope_value) if i.ope_value else None,
                    ass_value=eval(i.ass_value) if i.ass_value else None,
                    ele_name_a=i.el_name.name if i.el_name else None,
                    ele_name_b=i.el_name_b.name if i.el_name_b else None,
                    ele_page_name=i.el_page.name,
                    ele_exp=i.el_name.exp,
                    ele_loc=i.el_name.loc if i.el_name else None,
                    ele_loc_b=i.el_name_b.loc if i.el_name_b else None,
                    ele_sleep=i.el_name.sleep,
                    ele_sub=i.el_name.sub,
                    ope_value_key=i.ope_value_key
                ))
        return case_model

    def __get_web_config(self) -> tuple:
        user_ui_config = UiConfig.objects.get(user_id=self.user_id)
        return user_ui_config.local_port, user_ui_config.browser_path

    def __get_app_config(self) -> tuple:
        user_ui_config = UiConfig.objects.get(user_id=self.user_id)
        return user_ui_config.equipment
