# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023/5/16 14:50
# @Author : 毛鹏
import re
import traceback

from mangokit import Mango
from playwright._impl._errors import TimeoutError, Error, TargetClosedError
from playwright.async_api._generated import Locator

from src.enums.tools_enum import StatusEnum
from src.enums.ui_enum import ElementExpEnum, ElementOperationEnum
from src.exceptions import *
from src.models.ui_model import ElementModel, ElementResultModel
from src.services.ui.bases.base_data import BaseData
from src.services.ui.bases.web.assertion import PlaywrightAssertion
from src.services.ui.bases.web.browser import PlaywrightBrowser
from src.services.ui.bases.web.customization import PlaywrightCustomization
from src.services.ui.bases.web.element import PlaywrightElement
from src.services.ui.bases.web.input_device import PlaywrightDeviceInput
from src.services.ui.bases.web.page import PlaywrightPage
from src.tools.assertion.sql_assertion import SqlAssertion
from src.tools.decorator.async_retry import async_retry

re = re


class WebDevice(PlaywrightBrowser,
                PlaywrightPage,
                PlaywrightElement,
                PlaywrightDeviceInput,
                PlaywrightCustomization):

    def __init__(self, base_data: BaseData, element_model: ElementModel):
        super().__init__(base_data)
        self.element_model: ElementModel = element_model
        self.element_test_result = ElementResultModel(
            id=self.element_model.id,
            name=self.element_model.name,
            loc=self.element_model.loc,
            exp=element_model.exp,
            sub=element_model.sub,
            sleep=element_model.sleep,

            type=self.element_model.type,
            ope_key=self.element_model.ope_key,
            ope_value=None,
            expect=None,
            actual=None,
            sql=self.element_model.sql,
            key_list=self.element_model.key_list,
            key=self.element_model.key,
            value=self.element_model.value,

            status=StatusEnum.FAIL.value,
            ele_quantity=0,
            error_message=None,
            picture_path=None,
        )

    async def open_url(self):
        if not self.base_data.is_open_url:
            await self.w_goto(self.base_data.url)
            self.base_data.is_open_url = True
        elif self.base_data.switch_step_open_url and self.base_data.page.url != self.base_data.url:
            await self.w_wait_for_timeout(1)
            await self.w_goto(self.base_data.url)

    @async_retry
    async def web_action_element(self) -> dict:
        log.debug(f'元素操作：{self.element_model.model_dump()}')
        try:
            await Mango.a_e(self, self.element_model.ope_key, self.element_model.ope_value)
            if self.element_model.sleep:
                await self.w_wait_for_timeout(self.element_model.sleep)
            return self.element_model.ope_value
        except TimeoutError as error:
            raise UiError(*ERROR_MSG_0011, error=error, value=(self.element_model.name,))
        except TargetClosedError:
            await self.base_data.setup()
            raise UiError(*ERROR_MSG_0010)
        except Error as error:
            raise UiError(*ERROR_MSG_0032, value=(self.element_model.name,), error=error, )
        except ValueError as error:
            raise UiError(*ERROR_MSG_0012, error=error)

    @async_retry
    async def web_assertion_element(self) -> str:
        from src.tools.assertion import PublicAssertion
        is_method = callable(getattr(PlaywrightAssertion, self.element_model.ope_key, None))
        is_method_public = callable(getattr(PublicAssertion, self.element_model.ope_key, None))
        is_method_sql = callable(getattr(SqlAssertion, self.element_model.ope_key, None))

        if is_method or is_method_public:
            if self.element_model.ope_value.get('actual', None) is None:
                traceback.print_exc()
                raise UiError(*ERROR_MSG_0031, value=(self.element_model.name, self.element_model.loc))
        try:
            actual = None
            if is_method:
                actual = '元素是什么'
                log.debug(
                    f'开始断言，方法：{self.element_model.ope_key}，断言值：{self.element_model.ope_value}')
                await getattr(PlaywrightAssertion, self.element_model.ope_key)(**self.element_model.ope_value)
            elif is_method_public:
                text_actual = await self.w_get_text(self.element_model.ope_value['actual'])
                actual = text_actual
                ope_value = {k: text_actual if k == 'actual' else v for k, v in self.element_model.ope_value.items()}
                log.debug(f'开始断言，方法：{self.element_model.ope_key}，断言值：{ope_value}')
                getattr(PublicAssertion, self.element_model.ope_key)(**ope_value)
            elif is_method_sql:
                actual = 'sql匹配'
                if self.base_data.mysql_connect is not None:
                    SqlAssertion.mysql_obj = self.base_data.mysql_connect
                    log.debug(
                        f'开始断言，方法：sql相等端游，实际值：{self.element_model.ope_value}')
                    await SqlAssertion.sql_is_equal(**self.element_model.ope_value)
                else:
                    raise UiError(*ERROR_MSG_0019, value=(self.base_data.case_id, self.base_data.test_suite_id))
            return actual
        except AssertionError as error:
            raise UiError(*ERROR_MSG_0017, error=error)
        except AttributeError as error:
            raise UiError(*ERROR_MSG_0048, error=error)
        except ValueError as error:
            raise UiError(*ERROR_MSG_0018, error=error)
        except TargetClosedError:
            await self.base_data.setup()
            raise UiError(*ERROR_MSG_0010)
        except Error as error:
            raise UiError(*ERROR_MSG_0052, value=(self.element_model.name,), error=error, )

    @async_retry
    async def web_find_ele(self) -> tuple[int, Locator] | tuple[int, list[Locator]]:
        locator_str = self.element_model.loc
        # 是否在iframe中
        if self.element_model.is_iframe == StatusEnum.SUCCESS.value:
            ele_list: list[Locator] = []
            for i in self.base_data.page.frames:
                locator: Locator = await self.__find_ele(i, locator_str)
                try:
                    count = await locator.count()
                except Error as error:
                    raise UiError(*ERROR_MSG_0041, )

                if count > 0:
                    for nth in range(0, count):
                        ele_list.append(locator.nth(nth))
                else:
                    raise UiError(*ERROR_MSG_0023)

            ele_quantity = len(ele_list)
            if not ele_list:
                raise UiError(*ERROR_MSG_0023)
            # 这里需要进行调整
            if not ele_list and self.element_model.type == ElementOperationEnum.OPE.value:
                raise UiError(*ERROR_MSG_0029, value=(self.element_model.name, locator_str))
            try:
                return ele_quantity, ele_list[self.element_model.sub - 1] if self.element_model.sub else ele_list[0]
            except IndexError:
                raise UiError(*ERROR_MSG_0033, value=(ele_quantity,))
        else:
            locator: Locator = await self.__find_ele(self.base_data.page, locator_str)
            try:
                count = await locator.count()
            except Error:
                raise UiError(*ERROR_MSG_0041, )
            ele_quantity = count
            if count < 1 or locator is None and self.element_model.type == ElementOperationEnum.OPE.value:
                if self.element_model.type == ElementOperationEnum.OPE.value:
                    raise UiError(*ERROR_MSG_0029, value=(self.element_model.name, locator_str))
            return ele_quantity, locator.nth(self.element_model.sub - 1) if self.element_model.sub else locator

    async def __find_ele(self, page, loc) -> Locator:
        match self.element_model.exp:
            case ElementExpEnum.LOCATOR.value:
                try:
                    return eval(f"await page.{loc}")
                except SyntaxError:
                    try:
                        return eval(f"page.{loc}")
                    except SyntaxError:
                        raise UiError(*ERROR_MSG_0022)
                    except NameError as error:
                        raise UiError(*ERROR_MSG_0060, error=error)
            case ElementExpEnum.XPATH.value:
                return page.locator(f'xpath={loc}')
            case ElementExpEnum.CSS.value:
                return page.locator(loc)
            case ElementExpEnum.TEXT.value:
                return page.get_by_text(loc, exact=True)
            case ElementExpEnum.PLACEHOLDER.value:
                return page.get_by_placeholder(loc)
            case _:
                raise UiError(*ERROR_MSG_0020)
