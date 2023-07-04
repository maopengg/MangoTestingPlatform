# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 处理所有用例的数据
# @Time   : 2023-03-12 10:54
# @Author : 毛鹏

from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_ui.models import UiCase, RunSort, UiConfig
from PyAutoTest.auto_test.auto_ui.models import UiCaseGroup
from PyAutoTest.enums.system_enum import DevicePlatformEnum
from PyAutoTest.enums.ui_enum import BrowserTypeEnum


class CaseData:

    def __init__(self, user):
        self.user = user
        self.group_id = 0
        self.sum = 0

    def group_cases(self, group: UiCaseGroup) -> dict:
        """
        根据用例组的列表，返回所有的测试对象
        @param group: UiCaseGroup对象，一条数据
        @return:
        """
        self.group_id = group.id
        case_single = {'group_name': group.name,
                       'case_group': []}
        for case_id in eval(group.case_id):
            case_single['case_group'].append(self.data_ui_case(group.test_obj.id, case_id))
            # case_single.get(group.name).append()
        return case_single

    def data_ui_case(self, test_obj: int, case_id: int) -> dict:
        """
        根据test对象和用例ID返回一个UI测试对象回去
        @param test_obj: 测试环境id
        @param case_id: 用例id
        @return: 返回一个数据处理好的测试对象
        """
        case_ = UiCase.objects.get(id=case_id)
        run_sort = RunSort.objects.filter(case=case_.id).order_by('run_sort')
        case_strip = {'case_id': case_.id, 'case_name': case_.name, }
        if case_.case_type == DevicePlatformEnum.WEB.value:
            # 如果是web用例，则写入浏览器的端口，浏览器打开地址，type 执行用例url和浏览器的类型
            case_strip['local_port'], case_strip['browser_path'] = self.__get_web_config()
            case_strip['type'] = DevicePlatformEnum.WEB.value
            if self.group_id == 4 and case_.name == 'shop商城使用管理员登录并切换到妮维雅租户' or case_.name == '获取首页周日数据':
                case_strip['case_url'] = 'http://mall-tenant.zalldata.cn' + run_sort[0].el_page.url
            elif self.group_id == 4 and case_.name == '登录GrowKnows租户：妮维雅' or case_.name == '查询昨日支付订单的支付订单金额':
                case_strip['case_url'] = 'https://cdxp.growknows.cn' + run_sort[0].el_page.url
            else:
                case_strip['case_url'] = TestObject.objects.get(id=test_obj).value + run_sort[0].el_page.url
            case_strip['browser_type'] = BrowserTypeEnum.CHROMIUM.value
        elif case_.case_type == DevicePlatformEnum.ANDROID.value:
            # 如果是安卓用例，则写入设备，app和type
            case_strip['equipment'] = self.__get_app_config()
            case_strip['package'] = run_sort[0].el_page.url
            case_strip['type'] = DevicePlatformEnum.ANDROID.value
        elif case_.case_type == DevicePlatformEnum.IOS.value:
            pass
        elif case_.case_type == DevicePlatformEnum.DESKTOP.value:
            pass
        case_data = []
        for i in run_sort:
            if i.el_name is not None:
                case_data.append({
                    'ope_type': i.ope_type,
                    'ass_type': i.ass_type,
                    'ope_value': eval(i.ope_value) if i.ope_value else None,
                    'ass_value': eval(i.ass_value) if i.ass_value else None,
                    'ele_name_a': i.el_name.name if i.el_name else None,
                    'ele_name_b': i.el_name_b.name if i.el_name_b else None,
                    'ele_page_name': i.el_page.name,
                    'ele_exp': i.el_name.exp,
                    'ele_loc': i.el_name.loc if i.el_name else None,
                    'ele_loc_b': i.el_name_b.loc if i.el_name_b else None,
                    'ele_sleep': i.el_name.sleep,
                    'ele_sub': i.el_name.sub,
                    'ope_value_key': i.ope_value_key
                })
        case_strip['case_data'] = case_data
        return case_strip

    def __get_web_config(self) -> tuple:

        user_ui_config = UiConfig.objects.get(user_id=self.user)
        return user_ui_config.local_port, user_ui_config.browser_path

    def __get_app_config(self) -> tuple:
        user_ui_config = UiConfig.objects.get(user_id=self.user)
        return user_ui_config.equipment
