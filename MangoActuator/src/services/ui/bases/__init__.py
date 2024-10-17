# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-15 11:57
# @Author : 毛鹏
from src.enums.tools_enum import StatusEnum
from src.enums.ui_enum import ElementOperationEnum, DriveTypeEnum
from src.exceptions.error_msg import *
from src.exceptions.tools_exception import SyntaxErrorError, MysqlQueryIsNullError
from src.exceptions.ui_exception import *
from src.models.ui_model import ElementResultModel, ElementModel
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
        if element_model.name:
            self.ope_name = element_model.name
        else:
            self.ope_name = element_model.ope_type if element_model.ope_type else element_model.ass_type
        self.element_test_result = ElementResultModel(
            test_suite_id=self.test_suite_id,
            case_id=self.case_id,
            page_step_id=self.page_step_id,
            ele_name=self.ope_name,
            exp=element_model.exp,
            sub=element_model.sub,
            sleep=element_model.sleep,
            ope_type=element_model.ope_type,
            ass_type=element_model.ass_type,
            status=StatusEnum.FAIL.value,
            ele_quantity=0,
        )
        try:
            for key, value in self.element_model:
                value = self.data_processor.replace(value)
                setattr(self.element_model, key, value)
        except MangoActuatorError as error:
            raise error

    @async_memory
    async def element_main(self) -> None:
        name = self.element_model.name if self.element_model.name else self.element_model.ass_type
        ope_type = self.element_model.ope_type if self.element_model.ope_type else self.element_model.ass_type
        if self.element_model.type == ElementOperationEnum.OPE.value:
            await self.__ope(name, ope_type)
        elif self.element_model.type == ElementOperationEnum.ASS.value:
            await self.__ass(name, ope_type)
        elif self.element_model.type == ElementOperationEnum.SQL.value:
            await self.__sql()
        elif self.element_model.type == ElementOperationEnum.CUSTOM.value:
            await self.__custom()
        else:
            raise ElementTypeError(*ERROR_MSG_0015)
        self.element_test_result.status = StatusEnum.SUCCESS.value

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

    async def __ope(self, name, ope_type):
        try:
            for key, value in self.element_model.ope_value.items():
                if key == 'locating':
                    self.element_model.ope_value[key] = await self.__find_element()
                else:
                    # 清洗元素需要的数据
                    self.element_model.ope_value[key] = await self.__input_value(key, value)
        except AttributeError:
            raise ElementOpeNoneError(*ERROR_MSG_0027)
        except UiError as error:
            raise error
        try:
            func_doc = getattr(self, ope_type).__doc__
        except AttributeError:
            raise ElementOpeNoneError(*ERROR_MSG_0048)
        try:
            await self.action_element()
        except AttributeError:
            raise ElementOpeNoneError(*ERROR_MSG_0054)

    async def __ass(self, name, ope_type):
        for key, expect in self.element_model.ass_value.items():
            if key == 'actual' and self.element_model.loc:
                self.element_model.ass_value[key] = await self.__find_element()
            else:
                self.element_model.ass_value[key] = await self.__input_value(key, expect)
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
                            self.data_processor.set_cache(key, result.get(value))
                    except SyntaxError:
                        raise SyntaxErrorError(*ERROR_MSG_0038)

                if not result_list:
                    raise MysqlQueryIsNullError(*ERROR_MSG_0036, value=(self.element_model.sql,))

    async def __custom(self):
        if self.is_step:
            key = self.element_model.key
            value = self.element_model.value
        else:
            key = self.element_data.get('key')
            value = self.element_data.get('value')
        self.data_processor.set_cache(key, value)

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
                    return self.data_processor.replace(value)
        return value
