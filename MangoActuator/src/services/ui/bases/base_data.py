# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-02-04 10:43
# @Author : 毛鹏
from typing import Optional

from PySide6.QtCore import QObject, Signal
from mangokit import MysqlConnect, MysqlConingModel
from playwright.async_api import Page, BrowserContext
from uiautomator2 import Device

from src.enums.tools_enum import StatusEnum
from src.enums.ui_enum import UiPublicTypeEnum
from src.exceptions import ToolsError, ERROR_MSG_0036, ERROR_MSG_0038
from src.models.ui_model import EnvironmentConfigModel, UiPublicModel, EquipmentModel
from src.tools.obtain_test_data import ObtainTestData


class BaseData(QObject):
    progress = Signal(object)
    finished = Signal(object)

    def __init__(self,
                 driver_object,
                 project_product_id,
                 equipment_config: None = None,
                 environment_config: None = None,
                 test_suite_id: int | None = None,
                 case_id: int | None = None,
                 case_step_details_id: int | None = None,
                 page_step_id: int | None = None,
                 is_step: bool = False) -> None:
        super().__init__()
        self.project_product_id = project_product_id
        self.test_suite_id: Optional[int | None] = test_suite_id
        self.case_id: Optional[int | None] = case_id
        self.case_step_details_id: Optional[int | None] = case_step_details_id
        self.page_step_id: Optional[int | None] = page_step_id
        self.is_step: bool = is_step
        self.equipment_config: Optional[EquipmentModel | None] = equipment_config
        self.environment_config: Optional[EnvironmentConfigModel | None] = environment_config

        from src.services.ui.bases.driver_object import DriverObject
        self.driver_object: DriverObject = driver_object

        self.test_case = ObtainTestData()
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

        self.package_name = None
        self.android = None
        self.mysql_connect = None
        self.mysql_config = None
        self.test_case = ObtainTestData()

    async def base_close(self):
        if self.context and isinstance(self.context, BrowserContext):
            await self.context.close()
        if self.page and isinstance(self.page, Page):
            await self.page.close()
        if self.driver_object.android.example_dict:
            for i in self.driver_object.android.example_dict:
                pass
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
                self.test_case.set_cache(cache_data.key, cache_data.value)
            elif cache_data.type == UiPublicTypeEnum.SQL.value:
                if self.mysql_connect:
                    sql = self.test_case.replace(cache_data.value)
                    result_list: list[dict] = self.mysql_connect.condition_execute(sql)
                    if isinstance(result_list, list):
                        for result in result_list:
                            try:
                                for value, key in zip(result, eval(cache_data.key)):
                                    self.test_case.set_cache(key, result.get(value))
                            except SyntaxError:
                                raise ToolsError(*ERROR_MSG_0038)

                        if not result_list:
                            raise ToolsError(*ERROR_MSG_0036, value=(sql,))
