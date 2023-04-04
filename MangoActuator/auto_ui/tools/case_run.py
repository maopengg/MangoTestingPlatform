# # -*- coding: utf-8 -*-
# # @Project: auto_test
# # @Description:
# # @Time   : 2023/3/8 15:17
# # @Author : 毛鹏
# # -*- coding: utf-8 -*-
# # @Project: auto_test
# # @Description: 用例类
# # @Time   : 2022-11-04 22:05
# # @Author : 毛鹏
# from DrissionPage.configs.chromium_options import ChromiumOptions
# from DrissionPage.web_page import WebPage
#
# # from utlis.log_control import ERROR
# from auto_ui.web_obj.web_page import WebPageObject
#
#
# class UiCaseRun(WebPageObject):
#
#     def __init__(self, web_page: WebPage, data: list):
#         super().__init__(web_page)
#         self.app = None
#         self.web = web_page
#         self.data = data
#
#     def case_main(self):
#         for case in self.data:
#             self.open_url(case['case_url'], case['case_id'])
#             self.case_along(case['case_data'])
#
#
# if __name__ == '__main__':
#     data1 = [
#         {'case_id': 1, 'case_name': '后台登录', 'case_url': 'https://mall-admin-pre.zalldata.cn/#/login', 'case_data': [
#             {'ope_type': 0, 'ass_type': 0, 'ope_value': None, 'ass_value': None, 'ele_name': 'url',
#              'ele_page_name': '登录',
#              'ele_exp': None, 'ele_loc': None, 'ele_sleep': 3, 'ele_sub': None},
#             {'ope_type': 2, 'ass_type': 1, 'ope_value': 'test', 'ass_value': None, 'ele_name': '账号',
#              'ele_page_name': '登录',
#              'ele_exp': 0, 'ele_loc': '.el-input__inner', 'ele_sleep': None, 'ele_sub': None},
#             {'ope_type': 2, 'ass_type': 2, 'ope_value': '123456', 'ass_value': None, 'ele_name': '密码',
#              'ele_page_name': '登录', 'ele_exp': 0, 'ele_loc': '.el-input__inner', 'ele_sleep': None, 'ele_sub': 1},
#             {'ope_type': 1, 'ass_type': 0, 'ope_value': None, 'ass_value': None, 'ele_name': '登录按钮',
#              'ele_page_name': '登录',
#              'ele_exp': 0, 'ele_loc': 'xpath://button[@type="button"]//span', 'ele_sleep': 1, 'ele_sub': None},
#             {'ope_type': 1, 'ass_type': 0, 'ope_value': None, 'ass_value': None, 'ele_name': '点击租户',
#              'ele_page_name': '登录',
#              'ele_exp': 0, 'ele_loc': '.el-input__inner', 'ele_sleep': 1, 'ele_sub': None},
#             {'ope_type': 1, 'ass_type': 0, 'ope_value': None, 'ass_value': None, 'ele_name': '切换租户',
#              'ele_page_name': '登录',
#              'ele_exp': 0, 'ele_loc': 'xpath://span[text()="常规测试商户"]', 'ele_sleep': 1, 'ele_sub': None},
#             {'ope_type': 1, 'ass_type': 0, 'ope_value': None, 'ass_value': None, 'ele_name': '进入后台',
#              'ele_page_name': '登录',
#              'ele_exp': 0, 'ele_loc': 'xpath://button[@type="button"]//span', 'ele_sleep': 1, 'ele_sub': None}]}]
#     do = ChromiumOptions(read_file=False).set_paths(
#         local_port='9222',
#         browser_path=r'C:\Users\毛鹏\AppData\Local\Google\Chrome\Application\chrome.exe')
#     do.set_argument('--remote-allow-origins=*')
#     page = WebPage(driver_or_options=do, session_or_options=False)
#     case = UiCaseRun(page, data1)
#     case.case_main()
