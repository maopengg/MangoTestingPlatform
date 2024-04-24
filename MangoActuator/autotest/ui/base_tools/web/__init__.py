# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/5/16 14:50
# @Author : 毛鹏
import re

from playwright._impl._api_types import Error
from playwright._impl._api_types import TimeoutError
from playwright.async_api._generated import Locator

from autotest.ui.base_tools.web.assertion import PlaywrightAssertion
from autotest.ui.base_tools.web.browser import PlaywrightBrowser
from autotest.ui.base_tools.web.customization import PlaywrightCustomization
from autotest.ui.base_tools.web.element import PlaywrightElement
from autotest.ui.base_tools.web.input_device import PlaywrightDeviceInput
from autotest.ui.base_tools.web.page import PlaywrightPage
from enums.tools_enum import StatusEnum
from enums.ui_enum import ElementExpEnum, ElementOperationEnum
from exceptions.ui_exception import *
from models.socket_model.ui_model import ElementModel, ElementResultModel
from tools.assertion.public_assertion import PublicAssertion
from tools.assertion.sql_assertion import SqlAssertion
from tools.decorator.async_retry import async_retry
from tools.message.error_msg import *

re = re


class WebDevice(PlaywrightBrowser,
                PlaywrightPage,
                PlaywrightElement,
                PlaywrightDeviceInput,
                PlaywrightCustomization):
    element_test_result: ElementResultModel = None
    element_model: ElementModel = None

    @async_retry
    async def web_action_element(self) -> None:
        try:
            await getattr(self, self.element_model.ope_type)(**self.element_model.ope_value)
        except TimeoutError as error:
            raise UiTimeoutError(*ERROR_MSG_0011, error=error, value=(self.element_model.name,))
        except Error as error:
            raise ElementLocatorError(*ERROR_MSG_0032, value=(self.element_model.name,), error=error, )
        except ValueError as error:
            raise UiTimeoutError(*ERROR_MSG_0012, error=error)
        else:
            if 'locating' in self.element_model.ope_value:
                del self.element_model.ope_value['locating']
            self.element_test_result.ope_value = self.element_model.ope_value
            if self.element_model.sleep:
                await self.w_wait_for_timeout(self.element_model.sleep)

    @async_retry
    async def web_assertion_element(self) -> None:
        is_method = callable(getattr(PlaywrightAssertion, self.element_model.ass_type, None))
        is_method_public = callable(getattr(PublicAssertion, self.element_model.ass_type, None))
        is_method_sql = callable(getattr(SqlAssertion, self.element_model.ass_type, None))
        self.element_test_result.expect = self.element_model \
            .ass_value \
            .get('expect') if self.element_model \
            .ass_value \
            .get('expect') else None
        if is_method or is_method_public:
            if self.element_model.ass_value['value'] is None:
                raise ElementIsEmptyError(*ERROR_MSG_0031,
                                          value=(self.element_model.name, self.element_model.loc))
        try:
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
    async def web_find_ele(self) -> Locator | list[Locator]:
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
            try:
                count = await locator.count()
            except Error:
                raise LocatorError(*ERROR_MSG_0041, )
            self.element_test_result.ele_quantity = count
            if count < 1 or locator is None and self.element_model.type == ElementOperationEnum.OPE.value:
                if self.element_model.type == ElementOperationEnum.OPE.value:
                    raise ElementIsEmptyError(*ERROR_MSG_0029, value=(self.element_model.name, locator_str))
            return locator.nth(self.element_model.sub - 1) if self.element_model.sub else locator

    async def __find_ele(self, page, loc) -> Locator:
        match self.element_model.exp:
            case ElementExpEnum.LOCATOR.value:
                try:
                    return eval(f"await page.{loc}")
                except SyntaxError:
                    return eval(f"page.{loc}")
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
