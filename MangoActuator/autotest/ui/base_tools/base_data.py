# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-02-04 10:43
# @Author : 毛鹏
from typing import Optional

from playwright.async_api import Page, BrowserContext
from uiautomator2 import Device

from enums.tools_enum import StatusEnum
from enums.ui_enum import UiPublicTypeEnum
from exceptions.tools_exception import MysqlQueryIsNullError, SyntaxErrorError
from models.socket_model.ui_model import RunConfigModel
from models.tools_model import MysqlConingModel
from tools.data_processor import DataProcessor
from tools.database.mysql_connect import MysqlConnect
from tools.message.error_msg import ERROR_MSG_0036, ERROR_MSG_0037, ERROR_MSG_0038, ERROR_MSG_0039


class BaseData:

    def __init__(self,
                 project_id: int,
                 test_suite_id: int | None = None,
                 case_step_details_id: int = None,
                 page_step_id: int = None,
                 case_id: int | None = None,

                 is_step: bool = False,
                 page: Page = None,
                 context: BrowserContext = None,
                 android: Device = None
                 ) -> None:
        self.project_id = project_id
        self.test_suite_id = test_suite_id
        self.case_step_details_id = case_step_details_id
        self.page_step_id = page_step_id
        self.case_id = case_id
        self.data_processor = DataProcessor(project_id)

        self.is_step: bool = is_step  # 判断是不是步骤，默认不是步骤是用例
        self.test_object_value = ''  # 浏览器url
        self.is_url = False  # 判断是否需要重新加载url

        self.page: Optional[Page] = page  # 页面对象
        self.context: Optional[BrowserContext] = context  # 浏览器上下文对象

        self.mysql_config: Optional[MysqlConingModel] = None  # mysql连接配置
        self.mysql_connect: Optional[MysqlConnect] = None  # mysql连接对象

        self.android: Device = android

    def set_mysql(self, run_config: RunConfigModel):
        self.mysql_config = run_config.mysql_config
        if StatusEnum.SUCCESS.value in [run_config.db_c_status, run_config.db_rud_status]:
            self.mysql_connect = MysqlConnect(run_config.mysql_config,
                                              bool(run_config.db_c_status),
                                              bool(run_config.db_rud_status))

    async def base_close(self):
        if self.context and isinstance(self.context, BrowserContext):
            await self.context.close()
        if self.page and isinstance(self.page, Page):
            await self.page.close()
        if self.mysql_connect:
            self.mysql_connect.close()

    async def public_front(self, run_config: RunConfigModel):

        self.set_mysql(run_config)
        if run_config.public_data_list:
            for cache_data in run_config.public_data_list:
                if cache_data.type == UiPublicTypeEnum.CUSTOM.value:
                    self.data_processor.set_cache(cache_data.key, cache_data.value)
                elif cache_data.type == UiPublicTypeEnum.SQL.value:
                    if self.mysql_connect:
                        sql = self.data_processor.replace(cache_data.value)
                        result_list: list[dict] = self.mysql_connect.condition_execute(sql)
                        if isinstance(result_list, list):
                            for result in result_list:
                                try:
                                    for value, key in zip(result, eval(cache_data.key)):
                                        self.data_processor.set_cache(key, result.get(value))
                                except SyntaxError:
                                    raise SyntaxErrorError(*ERROR_MSG_0038)

                            if not result_list:
                                raise MysqlQueryIsNullError(*ERROR_MSG_0036, value=(sql,))

    async def case_front(self, front_custom: list[dict], front_sql: list[dict]):
        for i in front_custom:
            self.data_processor.set_cache(i.get('key'), i.get('value'))
        for i in front_sql:
            if self.mysql_connect:
                sql = self.data_processor.replace(i.get('sql'))
                result_list: list[dict] = self.mysql_connect.condition_execute(sql)
                if isinstance(result_list, list):
                    for result in result_list:
                        try:
                            for value, key in zip(result, eval(i.get('key_list'))):
                                self.data_processor.set_cache(key, result.get(value))
                        except SyntaxError:
                            raise SyntaxErrorError(*ERROR_MSG_0039)
                    if not result_list:
                        raise MysqlQueryIsNullError(*ERROR_MSG_0037, value=(sql,))

    async def case_posterior(self, posterior_sql: list[dict]):
        for sql in posterior_sql:
            self.mysql_connect.condition_execute(sql.get('sql'))
