# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-26 20:08
# @Author : 毛鹏
import asyncio

from mangokit import Mango

from src import test_process
from src.consumer import SocketConsumer
from src.models.socket_model import QueueModel
from src.network import HTTP
from src.settings import settings


class LinuxLoop:

    def __init__(self):
        self.loop = Mango.t()

    def set_tips_info(self, value):
        print(value)


data = {"func_name": "u_case",
        "func_args": {"test_suite_details": None, "test_suite_id": None, "id": 2, "name": "鼠标悬停",
                      "project_product": 1,
                      "project_product_name": "百度", "module_name": "首页", "test_env": 2, "case_people": "admin",
                      "front_custom": [], "front_sql": [], "posterior_sql": [], "parametrize": [], "steps": [
                {"id": 2, "name": "鼠标悬停", "project_product": 1, "project_product_name": "百度",
                 "module_name": "首页",
                 "type": 0, "url": "/", "element_list": [
                    {"id": 3, "type": 0, "name": "设置", "loc": "//span[@name=\"tj_settingicon\"]", "exp": 0,
                     "sleep": None,
                     "sub": None, "is_iframe": 0, "ope_key": "w_hover", "ope_value": {"locating": ""}, "key_list": None,
                     "sql": None, "key": None, "value": None}],
                 "equipment_config": {"type": 0, "web_max": False, "web_recording": False, "web_parallel": 5,
                                      "web_type": 0,
                                      "web_h5": None, "web_path": None, "web_headers": False, "and_equipment": None,
                                      "host_list": None, "is_header_intercept": None},
                 "environment_config": {"id": 1, "test_object_value": "https://www.baidu.com", "db_c_status": False,
                                        "db_rud_status": False, "mysql_config": None}, "public_data_list": [],
                 "case_step_details_id": 5, "case_data": [
                    {"type": 0, "ope_key": "w_hover", "page_step_details_id": 3, "page_step_details_data": {},
                     "page_step_details_name": "设置"}]}], "public_data_list": []}}


# async def test_process(parent):
#     try:
#         SocketConsumer.parent = parent
#         CaseFlow.parent = parent
#         consumer_task = asyncio.create_task(SocketConsumer.process_tasks())
#         case_flow_task = asyncio.create_task(CaseFlow.process_tasks())
#         # 不等待任务完成，只创建任务
#     except Exception as error:
#         traceback.print_exc()
#         log.error(f"启动永久循环协程任务时出现异常：{error}")
#         await asyncio.sleep(5)
#         await process(parent)


async def run():
    loop = LinuxLoop()
    settings.IP = '121.37.174.56'
    settings.PORT = '8000'
    settings.IS_DEBUG = True
    settings.USERNAME = 'admin'
    settings.PASSWORD = '123456'
    HTTP.api.public.set_host(settings.IP, settings.PORT)
    await test_process(loop)
    await SocketConsumer.add_task(QueueModel(**data))
    while True:
        await asyncio.sleep(0.1)


asyncio.run(run())
