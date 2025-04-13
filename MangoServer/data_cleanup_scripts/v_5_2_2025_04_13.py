# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-01-24 11:36
# @Author : 毛鹏

from src.auto_test.auto_ui.models import UiCaseStepsDetailed

data = [{"type": 0, "ope_key": "w_input", "page_step_details_id": 1,
         "page_step_details_data": {"input_value": "芒果测试平台"},
         "page_step_details_name": "输入框"},
        {"type": 0, "ope_key": "w_click", "page_step_details_id": 2, "page_step_details_data": {},
         "page_step_details_name": "搜索"}]
for i in data:
    pass

# def ui_case_steps_detailed():
#     for i in UiCaseStepsDetailed.objects.all():
#
#         for key, value in i.case_data.items():
#
#         i.case_data = replace_json_field(i.case_data)
#         i.save()
#
#
# def main_4_7():
#     api_case()
#     api_case_detailed()
#     api_info()
#     api_public()
#     page_element()
#     page_steps_detailed()
#     ui_case()
#     ui_case_steps_detailed()
