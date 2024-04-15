# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/5/16 14:50
# @Author : 毛鹏
import copy
import re
import traceback

from playwright._impl._api_types import Error
from playwright._impl._api_types import TimeoutError
from playwright.async_api import Locator

from autotest.ui.driver.web.assertion import PlaywrightAssertion
from autotest.ui.driver.web.browser import PlaywrightOperationBrowser
from autotest.ui.driver.web.mouse_keyboard import PlaywrightDeviceInput
from autotest.ui.driver.web.operation import PlaywrightElementOperation
from autotest.ui.driver.web.page import PlaywrightPageOperation
from enums.tools_enum import StatusEnum
from enums.ui_enum import ElementExpEnum, ElementOperationEnum
from exceptions.tools_exception import SyntaxErrorError, MysqlQueryIsNullError
from exceptions.ui_exception import *
from models.socket_model.ui_model import ElementModel, ElementResultModel
from tools.assertion.public_assertion import PublicAssertion
from tools.assertion.sql_assertion import SqlAssertion
from tools.decorator.async_retry import async_retry
from tools.log_collector import log
from tools.message.error_msg import *

re = re


class WebDevice(PlaywrightPageOperation, PlaywrightOperationBrowser, PlaywrightElementOperation, PlaywrightDeviceInput):
    element_test_result: ElementResultModel = None
    element_model: ElementModel = None
    element_data: dict = None
    ope_name: str = None

    async def element_setup(self, element_model, element_data):
        self.element_model = copy.deepcopy(element_model)
        self.element_data = element_data
        if element_model.name:
            self.ope_name = element_model.name
        elif element_model.ope_type:
            self.ope_name = element_model.ope_type
        else:
            self.ope_name = element_model.ass_type
        for key, value in self.element_model:
            value = self.data_processor.replace(value)
            setattr(self.element_model, key, value)
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

    async def web_element_main(self) -> None:
        name = self.element_model.name if self.element_model.name else self.element_model.ass_type
        ope_type = self.element_model.ope_type if self.element_model.ope_type else self.element_model.ass_type
        if self.element_model.type == ElementOperationEnum.OPE.value:
            try:
                for key, value in self.element_model.ope_value.items():
                    await self.__ope(key, value)
                self.notice_signal.send(3,
                                        data=f'操作->元素：{name}正在进行{ope_type}，元素个数：{self.element_test_result.ele_quantity}')
            except AttributeError:
                raise ElementOpeNoneError(*ERROR_MSG_0027)
            await self.web_action_element()
        # 判断元素是断言类型
        elif self.element_model.type == ElementOperationEnum.ASS.value:
            for key, expect in self.element_model.ass_value.items():
                await self.__ass(key, expect)
            await self.web_assertion_element()
            self.notice_signal.send(3,
                                    data=f'断言->元素：{name}正在进行{ope_type}，元素个数：{self.element_test_result.ele_quantity}')
        elif self.element_model.type == ElementOperationEnum.SQL.value:
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
        elif self.element_model.type == ElementOperationEnum.CUSTOM.value:
            if self.is_step:
                self.data_processor.set_cache(self.element_model.key, self.element_model.value)
            else:
                self.data_processor.set_cache(self.element_data.get('key'), self.element_data.get('value'))

        else:
            raise ElementTypeError(*ERROR_MSG_0015)

    @async_retry
    async def web_action_element(self) -> None:
        """
        处理元素的一些事件，包括点击，输入，移动
        @return:
        """
        try:
            await getattr(self, self.element_model.ope_type)(**self.element_model.ope_value)
        except TimeoutError as error:
            raise UiTimeoutError(*ERROR_MSG_0011, error=error, value=(self.element_model.name,))
        except Error as error:
            raise ElementLocatorError(*ERROR_MSG_0032, value=(self.element_model.name,), error=error, )
        except ValueError as error:
            raise UiTimeoutError(*ERROR_MSG_0012, error=error)
        except Exception as error:
            traceback.print_exc()  # 打印异常追踪信息
            log.error(f"元素操作任务出现异常：{error}")
        else:
            if 'locating' in self.element_model.ope_value:
                del self.element_model.ope_value['locating']
            self.element_test_result.ope_value = self.element_model.ope_value
            if self.element_model.sleep:
                await self.w_wait_for_timeout(self.element_model.sleep)

    @async_retry
    async def web_assertion_element(self):
        is_method = callable(getattr(PlaywrightAssertion, self.element_model.ass_type, None))
        is_method_public = callable(getattr(PublicAssertion, self.element_model.ass_type, None))
        is_method_sql = callable(getattr(SqlAssertion, self.element_model.ass_type, None))
        self.element_test_result.expect = self.element_model.ass_value.get(
            'expect') if self.element_model.ass_value.get('expect') else None
        try:
            if is_method or is_method_public:
                if self.element_model.ass_value['value'] is None:
                    raise ElementIsEmptyError(*ERROR_MSG_0031,
                                              value=(self.element_model.name, self.element_model.loc))
            if is_method:
                self.element_test_result.actual = '判断元素是什么'
                await getattr(PlaywrightAssertion, self.element_model.ass_type)(**self.element_model.ass_value)
            elif is_method_public:
                if self.element_model.ass_value.get('value'):
                    value = self.element_model.ass_value.get('value')
                    self.element_test_result.actual = f'断言元素本身，元素：{str(value)}'
                else:
                    value = await self.w_get_text(self.element_model.ass_value['value'])
                    self.element_test_result.actual = value
                getattr(PublicAssertion, self.element_model.ass_type)(
                    **{k: value if k == 'value' else v for k, v in self.element_model.ass_value.items()})
            elif is_method_sql:
                if self.mysql_connect is not None:
                    SqlAssertion.mysql_obj = self.mysql_connect
                    await SqlAssertion.sql_is_equal(**self.element_model.ass_value)
                else:
                    raise UiSqlAssertionError(*ERROR_MSG_0019, value=(self.case_id, self.test_suite_id))
        except AssertionError as error:
            raise UiAssertionError(*ERROR_MSG_0017, error=error)
        except AttributeError as error:
            raise UiAssertionError(*ERROR_MSG_0030, error=error)
        except ValueError as error:
            raise UiAssertionError(*ERROR_MSG_0018, error=error)
        if 'value' in self.element_model.ass_value:
            del self.element_model.ass_value['value']

        self.element_test_result.ass_value = self.element_model.ass_value

    @async_retry
    async def __ope(self, key, value):
        if key == 'locating':
            self.element_model.ope_value[key] = await self.__web_find_ele()
        else:
            # 清洗元素需要的数据
            self.element_model.ope_value[key] = await self.__web_input_value(key, value)

    @async_retry
    async def __ass(self, key, expect):
        if key == 'value' and self.element_model.loc:
            self.element_model.ass_value[key] = await self.__web_find_ele()
        else:
            self.element_model.ass_value[key] = await self.__web_input_value(key, expect)

    async def __web_find_ele(self) -> Locator | list[Locator]:
        """
        基于playwright的元素查找
        @return:
        """
        locator_str = self.element_model.loc
        self.element_test_result.loc = locator_str
        # 是否在iframe中
        if self.element_model.is_iframe == StatusEnum.SUCCESS.value:
            ele_list: list[Locator] = []
            for i in self.page.frames:
                locator: Locator = await self.__find_ele(i, locator_str)
                count = await locator.count()
                if count > 0:
                    for nth in range(0, count):
                        ele_list.append(locator.nth(nth))
            self.element_test_result.ele_quantity = len(ele_list)
            if not ele_list and self.element_model.type == ElementOperationEnum.OPE.value:
                raise ElementIsEmptyError(*ERROR_MSG_0029, value=(self.element_model.name, locator_str))
            return ele_list[self.element_model.sub - 1] if self.element_model.sub else ele_list[0]
        else:
            locator: Locator = await self.__find_ele(self.page, locator_str)
            count = await locator.count()
            self.element_test_result.ele_quantity = count
            if count < 1 or locator is None and self.element_model.type == ElementOperationEnum.OPE.value:
                if self.element_model.type == ElementOperationEnum.OPE.value:
                    raise ElementIsEmptyError(*ERROR_MSG_0029, value=(self.element_model.name, locator_str))
            return locator.nth(self.element_model.sub - 1) if self.element_model.sub else locator

    async def __find_ele(self, page, loc) -> Locator:
        match self.element_model.exp:
            case ElementExpEnum.LOCATOR.value:
                try:
                    return eval(f"await self.{loc}")
                except SyntaxError:
                    return eval(f"self.{loc}")
            case ElementExpEnum.XPATH.value:
                return page.locator(f'xpath={loc}')
            case ElementExpEnum.CSS.value:
                return page.locator(loc)
            case ElementExpEnum.TEST_ID.value:
                return page.get_by_test_id(loc)
            case ElementExpEnum.TEXT.value:
                return page.get_by_text(loc, exact=True)
            case ElementExpEnum.PLACEHOLDER.value:
                return page.get_by_placeholder(loc)
            case ElementExpEnum.LABEL.value:
                return page.get_by_label(loc)
            case ElementExpEnum.TITLE.value:
                return page.get_by_title(loc)
            case ElementExpEnum.ROLE.value:
                return page.get_by_role(loc)
            case ElementExpEnum.AIT_TEXT.value:
                return page.get_by_alt_text(loc)
            case _:
                raise LocatorError(*ERROR_MSG_0020)

    async def __web_input_value(self, key: str, value: dict | str) -> str:
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
