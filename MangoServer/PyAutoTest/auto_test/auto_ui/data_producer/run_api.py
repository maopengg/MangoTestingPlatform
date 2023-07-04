# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/4/28 11:56
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.consumers import socket_conn
from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_ui.models import UiCaseGroup, RunSort, UiCase, UiConfig
from PyAutoTest.auto_test.auto_user.models import User
from PyAutoTest.base_data_model.system_data_model import SocketDataModel, QueueModel
from PyAutoTest.base_data_model.ui_data_model import CaseModel, ElementModel, CaseGroupModel
from PyAutoTest.enums.actuator_api_enum import UiApiEnum
from PyAutoTest.enums.system_enum import SocketEnum, DevicePlatformEnum
from PyAutoTest.enums.ui_enum import BrowserTypeEnum
from PyAutoTest.settings import DRIVER


class RunApi:

    def __init__(self, user: dict):
        self.username = user.get("username")
        self.user_id = user.get("user_id")

    def group_run(self, group_id: int, time=False):
        """
        执行一个用例组
        @param group_id: 用例组的ID
        @return:
        """
        case_group_data = UiCaseGroup.objects.get(pk=group_id)
        if time:
            data = CaseData(case_group_data.timing_actuator.id)
            case_json = data.group_cases(case_group_data)
            send_res = self.run_case_send(case_json=case_json,
                                          func_name=UiApiEnum.run_group_case.value)
        else:
            data = CaseData(User.objects.get(username=self.username).id)
            case_json = data.group_cases(case_group_data)
            send_res = self.run_case_send(case_json=case_json,
                                          func_name=UiApiEnum.run_group_case.value)
        return case_json, send_res

    def group_batch(self, group_id_list: list or int, time=False):
        """
        批量执行用例组用例
        @param group_id_list: 用例组的list或int
        @param time: 用来标识是不是定时任务
        @return:
        """
        case_group = []
        if isinstance(group_id_list, int):
            case_json, send_res = self.__group_run(group_id_list, time)
            case_group.append(case_json)
            if send_res:
                return case_group, True
        elif isinstance(group_id_list, list):
            for group_id in group_id_list:
                case_json, send_res = self.__group_run(group_id, time)
                case_group.append(case_json)
                if send_res:
                    return case_group, True
        return case_group, False

    def case_run(self, te: int, case_id: int, user_id):
        """
        调试用例单个执行
        """
        data = CaseData(user_id)
        case_data = data.data_ui_case(te, case_id)
        send_res = self.run_case_send(case_json=case_data,
                                      func_name=UiApiEnum.run_debug_case.value)
        return case_data, send_res

    def case_run_batch(self, case_list: int or list, te: int, user_id):
        """
        调试用例批量执行
        @param case_list: 用例id列表或者一个
        @param te: 测试环境
        @param user_id: user_id
        @return:
        """
        case_data = []
        if isinstance(case_list, int):
            case_json, send_res = self.__case_run(te, case_list, user_id)
            case_data.append(case_json)
            if send_res:
                return case_data, False
        elif isinstance(case_list, list):
            for case_id in case_list:
                case_json, send_res = self.__case_run(te, case_id, user_id)
                case_data.append(case_json)
                if send_res:
                    return case_data, False
        return case_data, True

    def __run_case_send(self, case_json, func_name: str) -> bool:
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
            client=SocketEnum.client_path.value,
            func=func_name,
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
            case_single.case_group.append(self.data_ui_case(group.test_obj.id, case_id))
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
