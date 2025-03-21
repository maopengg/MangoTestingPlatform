# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-07-15 11:57
# @Author : 毛鹏
import asyncio
import os
import traceback

from mangokit import MangoKitError
from playwright._impl._errors import TargetClosedError, Error, TimeoutError

from src.enums.tools_enum import StatusEnum
from src.enums.ui_enum import ElementOperationEnum, DriveTypeEnum
from src.exceptions import *
from src.models.ui_model import ElementResultModel, ElementModel
from src.network import HTTP
from src.services.ui.bases.android import AndroidDriver
from src.services.ui.bases.web import WebDevice
from src.tools import project_dir
from src.tools.decorator.memory import async_memory
from src.tools.log_collector import log


class ElementOperation(WebDevice, AndroidDriver):

    def __init__(self, base_data, element_model: ElementModel, element_data: dict, drive_type: int):
        super().__init__(base_data, element_model)
        self.element_data = element_data
        self.drive_type = drive_type
        self.ope_name = element_model.name if element_model.name else element_model.ope_key

    async def open_device(self):
        if self.drive_type == DriveTypeEnum.WEB.value:
            await self.open_url()
        elif self.drive_type == DriveTypeEnum.ANDROID.value:
            self.open_app()
        elif self.drive_type == DriveTypeEnum.DESKTOP.value:
            pass
        else:
            log.error('不存在的设备类型')
            raise Exception('不存在的设备类型')

    @async_memory
    async def element_main(self) -> ElementResultModel:
        try:
            for key, value in self.element_model:
                value = self.base_data.test_data.replace(value)
                setattr(self.element_model, key, value)
        except MangoKitError as error:
            raise UiError(error.code, error.msg)

        try:
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
            self.element_test_result.status = StatusEnum.SUCCESS.value
            return self.element_test_result
        except TargetClosedError as error:
            await self.base_data.setup()
            log.warning(f'浏览器对象关闭异常：{error}')
            self.element_test_result.status = StatusEnum.FAIL.value
            self.element_test_result.error_message = '浏览器对象被关闭，请检查是人为关闭还是异常关闭，异常关闭请发送error日志联系管理员！'
            raise UiError(*ERROR_MSG_0010)
        except UiError as error:
            await self.__error(error)
            raise error
        except Error as error:
            log.warning(f'浏览器对象关闭异常：{error}')
            self.element_test_result.status = StatusEnum.FAIL.value
            self.element_test_result.error_message = f'未捕获的异常，可以联系管理来添加异常提示。或者你可以根据异常提示进行修改测试内容。异常内容：{error}'
            raise error

        except Exception as error:
            self.element_test_result.status = StatusEnum.FAIL.value
            self.element_test_result.error_message = f'未知异常，可以联系管理来添加异常提示。或者你可以根据异常提示进行修改测试内容。异常内容：{error}'
            raise error

    async def action_element(self):
        ope_value = self.element_model.ope_value
        try:
            if self.drive_type == DriveTypeEnum.WEB.value:
                ope_value = await self.web_action_element()
            elif self.drive_type == DriveTypeEnum.ANDROID.value:
                ope_value = self.a_action_element()
            elif self.drive_type == DriveTypeEnum.DESKTOP.value:
                ope_value = None
            else:
                log.error('不存在的设备类型')
                raise Exception('不存在的设备类型')
        except UiError as error:
            if ope_value:
                self.element_test_result.ope_value = str(ope_value)
            raise error
        else:
            self.element_test_result.ope_value = str(ope_value)

    async def assertion_element(self):
        async def set_result(actual):
            if 'actual' in self.element_model.ope_value:
                del self.element_model.ope_value['actual']
            ass_dict = {'actual': actual}
            ass_dict.update(self.element_model.ope_value)
            self.element_test_result.ope_value = ass_dict
            self.element_test_result.expect = self.element_model.ope_value.get('expect')
            self.element_test_result.actual = str(actual)

        actual = self.element_model.ope_value
        try:
            if self.drive_type == DriveTypeEnum.WEB.value:
                actual = await self.web_assertion_element()
            elif self.drive_type == DriveTypeEnum.ANDROID.value:
                actual = self.a_assertion_element()
            elif self.drive_type == DriveTypeEnum.DESKTOP.value:
                actual = None
            else:
                log.error('不存在的设备类型')
                raise Exception('不存在的设备类型')
        except UiError as error:
            if actual:
                await set_result(actual)
            raise error
        else:
            await set_result(actual)

    async def __ope(self):
        try:
            func_doc = getattr(self, self.element_model.ope_key).__doc__
        except AttributeError:
            raise UiError(*ERROR_MSG_0048)
        except TypeError:
            raise UiError(*ERROR_MSG_0051)
        if self.element_model.ope_value is None:
            raise UiError(*ERROR_MSG_0054)
        try:
            for key, value in self.element_model.ope_value.items():
                if key == 'locating':
                    self.element_model.ope_value[key] = await self.__find_element()
                else:
                    self.element_model.ope_value[key] = await self.__input_value(key, value)
        except AttributeError:
            traceback.print_exc()
            raise UiError(*ERROR_MSG_0027)
        except UiError as error:
            raise error
        await self.action_element()

    async def __ass(self):
        if self.element_model.ope_value is None:
            raise UiError(*ERROR_MSG_0053)
        for key, expect in self.element_model.ope_value.items():
            if key == 'actual' and self.element_model.loc:
                self.element_model.ope_value[key] = await self.__find_element()
            else:
                self.element_model.ope_value[key] = await self.__input_value(key, expect)
        await self.assertion_element()

    async def __sql(self):
        if self.base_data.is_step:
            sql = self.element_model.sql
            key_list = self.element_model.key_list
        else:
            sql = self.element_data.get('sql')
            key_list = self.element_data.get('key_list')
        if self.base_data.mysql_connect:
            result_list: list[dict] = self.base_data.mysql_connect.condition_execute(sql)
            if isinstance(result_list, list):
                for result in result_list:
                    try:
                        for value, key in zip(result, key_list):
                            self.base_data.test_data.set_cache(key, result.get(value))
                    except SyntaxError:
                        raise ToolsError(*ERROR_MSG_0038)

                if not result_list:
                    raise ToolsError(*ERROR_MSG_0036, value=(self.element_model.sql,))

    async def __custom(self):
        if self.base_data.is_step:
            key = self.element_model.key
            value = self.element_model.value
        else:
            key = self.element_data.get('key')
            value = self.element_data.get('value')
        self.base_data.test_data.set_cache(key, value)

    async def __find_element(self):
        try:
            if self.drive_type == DriveTypeEnum.WEB.value:
                count, loc = await self.web_find_ele()
            elif self.drive_type == DriveTypeEnum.ANDROID.value:
                count, loc = self.a_find_ele()
            # elif self.drive_type == DriveTypeEnum.DESKTOP.value:
            #     pass
            else:
                raise Exception('不存在的设备类型')
            self.element_test_result.ele_quantity = count
            return loc
        except UiError as error:
            raise error

    async def __input_value(self, key: str, value: dict | str) -> str:
        """
        输入依赖解决
        @return:
        """
        if self.element_data:
            for ele_name, case_data in self.element_data.items():
                if ele_name == key:
                    value = case_data
                    return self.base_data.test_data.replace(value)
        return value

    async def __error(self, error: UiError):
        self.element_test_result.status = StatusEnum.FAIL.value
        self.element_test_result.error_message = error.msg
        log.warning(
            f"""
            元素操作失败----->
            元 素 对 象：{self.element_model.model_dump() if self.element_model else self.element_model}
            元素测试结果：{
            self.element_test_result.model_dump() if self.element_test_result else self.element_test_result}
            报 错 信 息：{error.msg}
            """
        )
        if self.element_test_result:
            file_name = f'失败截图-{self.element_model.name}{self.base_data.test_data.get_time_for_min()}.jpg'
            file_path = os.path.join(project_dir.screenshot(), file_name)
            self.element_test_result.picture_path = file_name
            await self.__error_screenshot(file_path, file_name)

    async def __error_screenshot(self, file_path, file_name):
        # try:
        match self.drive_type:
            case DriveTypeEnum.WEB.value:
                try:
                    await self.w_screenshot(file_path)
                except (TargetClosedError, TimeoutError):
                    await self.base_data.setup()
                    raise UiError(*ERROR_MSG_0010)
                except AttributeError:
                    await self.base_data.setup()
                    raise UiError(*ERROR_MSG_0010)
            case DriveTypeEnum.ANDROID.value:
                self.a_screenshot(file_path)
            case DriveTypeEnum.DESKTOP.value:
                pass
            case _:
                log.error('自动化类型不存在，请联系管理员检查！')
        HTTP.not_auth.upload_file(file_path, file_name)
