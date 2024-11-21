# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-07-15 11:57
# @Author : 毛鹏
from src.enums.tools_enum import StatusEnum
from src.enums.ui_enum import ElementOperationEnum, DriveTypeEnum
from src.exceptions import *
from src.models.ui_model import ElementResultModel, ElementModel, ElementDataModel
from src.services.ui.bases.android import AndroidDriver
from src.services.ui.bases.web import WebDevice
from src.tools.decorator.memory import async_memory
from src.tools.log_collector import log


class ElementMain(WebDevice, AndroidDriver):
    element_test_result: ElementResultModel = None
    element_model: ElementModel = None
    element_data: dict = None
    ope_name: str = None
    drive_type: int = None

    async def element_setup(self, element_model: ElementModel, element_data: dict, drive_type: int):
        self.element_model = element_model
        self.element_data = element_data
        self.drive_type = drive_type
        self.ope_name = element_model.name if element_model.name else element_model.ope_key
        self.element_test_result = ElementResultModel(
            test_suite_id=self.test_suite_id,
            case_id=self.case_id,
            page_step_id=self.page_step_id,
            ele_name=self.ope_name,
            element_data=ElementDataModel(
                type=self.element_model.type,
                exp=element_model.exp,
                sub=element_model.sub,
                sleep=element_model.sleep,
                ope_key=element_model.ope_key,
                ope_value=element_model.ope_key,
                status=StatusEnum.FAIL.value,
                ele_quantity=0,
                key_list=element_model.key_list,
                sql=element_model.sql,
                key=element_model.key,
                value=element_model.value,
            )
        )
        try:
            for key, value in self.element_model:
                value = self.test_case.replace(value)
                setattr(self.element_model, key, value)
        except MangoActuatorError as error:
            raise error

    @async_memory
    async def element_main(self) -> None:
        if self.element_model.type == ElementOperationEnum.OPE.value:
            await self.__ope()
        elif self.element_model.type == ElementOperationEnum.ASS.value:
            await self.__ass()
        elif self.element_model.type == ElementOperationEnum.SQL.value:
            await self.__sql()
        elif self.element_model.type == ElementOperationEnum.CUSTOM.value:
            await self.__custom()
        else:
            raise UiError(*ERROR_MSG_0015)
        self.element_test_result.element_data.status = StatusEnum.SUCCESS.value

    async def action_element(self):
        if self.drive_type == DriveTypeEnum.WEB.value:
            await self.web_action_element()
        elif self.drive_type == DriveTypeEnum.ANDROID.value:
            self.a_action_element()
        elif self.drive_type == DriveTypeEnum.IOS.value:
            pass
        elif self.drive_type == DriveTypeEnum.DESKTOP.value:
            pass
        else:
            log.error('不存在的设备类型')
            raise Exception('不存在的设备类型')

    async def assertion_element(self):
        if self.drive_type == DriveTypeEnum.WEB.value:
            await self.web_assertion_element()
        elif self.drive_type == DriveTypeEnum.ANDROID.value:
            self.a_assertion_element()
        elif self.drive_type == DriveTypeEnum.IOS.value:
            pass
        elif self.drive_type == DriveTypeEnum.DESKTOP.value:
            pass
        else:
            log.error('不存在的设备类型')
            raise Exception('不存在的设备类型')

    async def __ope(self):
        try:
            for key, value in self.element_model.ope_value.items():
                if key == 'locating':
                    self.element_model.ope_value[key] = await self.__find_element()
                else:
                    # 清洗元素需要的数据
                    self.element_model.ope_value[key] = await self.__input_value(key, value)
        except AttributeError:
            raise UiError(*ERROR_MSG_0027)
        except UiError as error:
            raise error
        try:
            func_doc = getattr(self, self.element_model.ope_key).__doc__
        except AttributeError:
            raise UiError(*ERROR_MSG_0048)
        try:
            await self.action_element()
        except AttributeError:
            raise UiError(*ERROR_MSG_0054)

    async def __ass(self):
        for key, expect in self.element_model.ope_value.items():
            if key == 'actual' and self.element_model.loc:
                self.element_model.ope_value[key] = await self.__find_element()
            else:
                self.element_model.ope_value[key] = await self.__input_value(key, expect)
        await self.assertion_element()

    async def __sql(self):
        if self.is_step:
            sql = self.element_model.sql
            key_list = self.element_model.key_list
        else:
            sql = self.element_data.get('sql')
            key_list = self.element_data.get('key_list')
        if self.mysql_connect:
            result_list: list[dict] = self.mysql_connect.condition_execute(sql)
            if isinstance(result_list, list):
                for result in result_list:
                    try:
                        for value, key in zip(result, key_list):
                            self.test_case.set_cache(key, result.get(value))
                    except SyntaxError:
                        raise ToolsError(*ERROR_MSG_0038)

                if not result_list:
                    raise ToolsError(*ERROR_MSG_0036, value=(self.element_model.sql,))

    async def __custom(self):
        if self.is_step:
            key = self.element_model.key
            value = self.element_model.value
        else:
            key = self.element_data.get('key')
            value = self.element_data.get('value')
        self.test_case.set_cache(key, value)

    async def __find_element(self):
        if self.drive_type == DriveTypeEnum.WEB.value:
            return await self.web_find_ele()
        elif self.drive_type == DriveTypeEnum.ANDROID.value:
            return self.a_find_ele()
        elif self.drive_type == DriveTypeEnum.IOS.value:
            pass
        elif self.drive_type == DriveTypeEnum.DESKTOP.value:
            pass
        else:
            raise Exception('不存在的设备类型')

    async def __input_value(self, key: str, value: dict | str) -> str:
        """
        输入依赖解决
        @return:
        """
        if self.element_data:
            for ele_name, case_data in self.element_data.items():
                if ele_name == key:
                    value = case_data
                    return self.test_case.replace(value)
        return value
