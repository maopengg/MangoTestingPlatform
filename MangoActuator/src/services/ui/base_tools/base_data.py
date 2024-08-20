# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-02-04 10:43
# @Author : 毛鹏
from typing import Optional

from playwright.async_api import Page, BrowserContext
from uiautomator2 import Device

from src.enums.tools_enum import StatusEnum
from src.enums.ui_enum import UiPublicTypeEnum
from src.exceptions.error_msg import ERROR_MSG_0036, ERROR_MSG_0038
from src.exceptions.tools_exception import MysqlQueryIsNullError, SyntaxErrorError
from src.models.socket_model.ui_model import EnvironmentConfigModel, UiPublicModel
from src.models.tools_model import MysqlConingModel
from src.tools.data_processor import DataProcessor
from src.tools.database.mysql_connect import MysqlConnect


class BaseData:

    def __init__(self, project_product_id, driver_object) -> None:
        self.project_product_id: Optional[int | None] = project_product_id
        self.test_suite_id: Optional[int | None] = None
        self.case_id: Optional[int | None] = None
        self.case_step_details_id: Optional[int | None] = None
        self.page_step_id: Optional[int | None] = None

        from src.services.ui.base_tools.driver_object import DriverObject
        self.driver_object: Optional[DriverObject | None] = driver_object
        self.data_processor = DataProcessor(project_product_id)
        self.is_step: bool = False  # 判断是不是步骤，默认不是步骤是用例
        self.mysql_config: Optional[MysqlConingModel | None] = None  # mysql连接配置
        self.mysql_connect: Optional[MysqlConnect | None] = None  # mysql连接对象

        self.url: Optional[str | None] = None
        self.page: Optional[Page | None] = None
        self.context: Optional[BrowserContext | None] = None

        self.package_name: Optional[str | None] = None
        self.android: Optional[Device | None] = None

    async def setup(self) -> None:
        self.url = None
        self.page = None
        self.context = None

    async def base_close(self):
        if self.context and isinstance(self.context, BrowserContext):
            await self.context.close()
        if self.page and isinstance(self.page, Page):
            await self.page.close()
        if self.mysql_connect:
            self.mysql_connect.close()

    def set_mysql(self, run_config: EnvironmentConfigModel):
        self.mysql_config = run_config.mysql_config
        if StatusEnum.SUCCESS.value in [run_config.db_c_status, run_config.db_rud_status]:
            self.mysql_connect = MysqlConnect(run_config.mysql_config,
                                              bool(run_config.db_c_status),
                                              bool(run_config.db_rud_status))

    async def public_front(self, public_model: list[UiPublicModel]):
        for cache_data in public_model:
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
