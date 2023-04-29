# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏

from auto_ui.test_runner.case_distribution import CaseDistribution
from enum_class.ui_enum import DevicePlatform
from utlis.ope_win.cmd import cmd


class ExternalAPI:

    def start_up(self, func, *args, **kwargs):
        getattr(self, func)(*args, **kwargs)

    @staticmethod
    def cmd(cmd_data):
        return cmd(cmd_data)

    def new_web_obj(self, original_data: dict):
        # self.case = MainTest()
        if original_data['type'] == DevicePlatform.WEB.value:
            CaseDistribution.new_case_obj(_type=original_data['type'],
                                          local_port=original_data['local_port'],
                                          browser_path=original_data['browser_path'])
        elif original_data['type'] == DevicePlatform.ANDROID.value:
            CaseDistribution.new_case_obj(_type=original_data['type'],
                                          equipment=original_data['equipment'],
                                          package=original_data['package'])

    def ui_case_run(self, original_data: list[dict]):
        CaseDistribution.case_run(original_data)


if __name__ == '__main__':
    local_port = '9222'
    browser_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    r = ExternalAPI()
    data11 = {
        "code": 200,
        "msg": "测试客户端已收到用例，正在执行中...",
        "data": [
            {'type': 0,
             'local_port': local_port,
             'browser_path': browser_path,
             "case_id": 1,
             "case_name": "后台登录",
             "case_url": "http://mall-tenant.zalldata.cn/#/login",
             "case_data": [
                 {
                     "ope_type": 0,
                     "ass_type": 0,
                     "ope_value": None,
                     "ass_value": None,
                     "ele_name": "url",
                     "ele_page_name": "登录",
                     "ele_exp": None,
                     "ele_loc": None,
                     "ele_sleep": 3,
                     "ele_sub": None
                 },
                 {
                     "ope_type": 2,
                     "ass_type": 1,
                     "ope_value": "test",
                     "ass_value": None,
                     "ele_name": "账号",
                     "ele_page_name": "登录",
                     "ele_exp": 0,
                     "ele_loc": ".el-input__inner",
                     "ele_sleep": None,
                     "ele_sub": None
                 },
                 {
                     "ope_type": 2,
                     "ass_type": 2,
                     "ope_value": "123456",
                     "ass_value": None,
                     "ele_name": "密码",
                     "ele_page_name": "登录",
                     "ele_exp": 0,
                     "ele_loc": ".el-input__inner",
                     "ele_sleep": None,
                     "ele_sub": 1
                 },
                 {
                     "ope_type": 1,
                     "ass_type": 0,
                     "ope_value": None,
                     "ass_value": None,
                     "ele_name": "登录按钮",
                     "ele_page_name": "登录",
                     "ele_exp": 0,
                     "ele_loc": "xpath://button[@type=\"button\"]//span",
                     "ele_sleep": 1,
                     "ele_sub": None
                 },
                 {
                     "ope_type": 1,
                     "ass_type": 0,
                     "ope_value": None,
                     "ass_value": None,
                     "ele_name": "点击租户",
                     "ele_page_name": "登录",
                     "ele_exp": 0,
                     "ele_loc": "xpath://input[@readonly=\"readonly\"]",
                     "ele_sleep": 1,
                     "ele_sub": None
                 },
                 {
                     "ope_type": 1,
                     "ass_type": 0,
                     "ope_value": None,
                     "ass_value": None,
                     "ele_name": "切换租户",
                     "ele_page_name": "登录",
                     "ele_exp": 0,
                     "ele_loc": "xpath://span[text()=\"常规测试商户\"]",
                     "ele_sleep": 1,
                     "ele_sub": None
                 },
                 {
                     "ope_type": 1,
                     "ass_type": 0,
                     "ope_value": None,
                     "ass_value": None,
                     "ele_name": "进入后台",
                     "ele_page_name": "登录",
                     "ele_exp": 0,
                     "ele_loc": "xpath://button[@type=\"button\"]//span",
                     "ele_sleep": 1,
                     "ele_sub": None
                 }
             ]
             }
        ]
    }
    r.web_case_run(data11)
