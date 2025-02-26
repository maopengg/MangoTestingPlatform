# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-26 20:08
# @Author : 毛鹏
import asyncio

from mangokit import Mango

from src.consumer import UI


class LinuxLoop:

    def __init__(self):
        self.loop = Mango.t()

    def set_tips_info(self, value):
        print(value)


data = {"test_suite_details": None, "test_suite_id": None, "id": 2, "name": "鼠标悬停", "project_product": 1,
        "project_product_name": "百度", "module_name": "首页", "test_env": 2, "case_people": "admin",
        "front_custom": [], "front_sql": [], "posterior_sql": [], "parametrize": [], "steps": [
        {"id": 2, "name": "鼠标悬停", "project_product": 1, "project_product_name": "百度", "module_name": "首页",
         "type": 0, "url": "/", "element_list": [
            {"id": 3, "type": 0, "name": "设置", "loc": "//span[@name=\"tj_settingicon\"]", "exp": 0, "sleep": None,
             "sub": None, "is_iframe": 0, "ope_key": "w_hover", "ope_value": {"locating": ""}, "key_list": None,
             "sql": None, "key": None, "value": None}],
         "equipment_config": {"type": 0, "web_max": False, "web_recording": False, "web_parallel": 5, "web_type": 0,
                              "web_h5": None, "web_path": None, "web_headers": False, "and_equipment": None,
                              "host_list": None, "is_header_intercept": None},
         "environment_config": {"id": 1, "test_object_value": "https://www.baidu.com", "db_c_status": False,
                                "db_rud_status": False, "mysql_config": None}, "public_data_list": [],
         "case_step_details_id": 5, "case_data": [
            {"type": 0, "ope_key": "w_hover", "page_step_details_id": 3, "page_step_details_data": {},
             "page_step_details_name": "设置"}]}], "public_data_list": []}


async def run():
    loop = LinuxLoop()
    ui = UI()
    ui.parent = loop
    await ui.u_case(data)
    while True:
        await asyncio.sleep(0.1)


asyncio.run(run())
