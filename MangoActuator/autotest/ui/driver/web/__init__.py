# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/5/16 14:50
# @Author : 毛鹏
import copy
import traceback

from playwright._impl._api_types import Error
from playwright._impl._api_types import TimeoutError
from playwright.async_api import Locator

from autotest.ui.driver.web.device_Input import PlaywrightDeviceInput
from autotest.ui.driver.web.element_assertion import PlaywrightAssertion
from autotest.ui.driver.web.element_operation import PlaywrightElementOperation
from autotest.ui.driver.web.operation_browser import PlaywrightOperationBrowser
from autotest.ui.driver.web.operation_page import PlaywrightPageOperation
from enums.tools_enum import StatusEnum
from enums.ui_enum import ElementExpEnum, ElementOperationEnum
from exceptions.tools_exception import SyntaxErrorError, MysqlQueryIsNullError
from exceptions.ui_exception import *
from models.socket_model.ui_model import ElementModel, ElementResultModel
from tools.assertion.public_assertion import PublicAssertion
from tools.assertion.sql_assertion import SqlAssertion
from tools.decorator.async_retry import async_retry
from tools.logs.log_control import ERROR
from tools.message.error_msg import *

class WebDevice(PlaywrightPageOperation, PlaywrightOperationBrowser, PlaywrightElementOperation, PlaywrightDeviceInput):
    element_test_result: ElementResultModel = None
    element_model: ElementModel = None
    element_data: list[dict] = None
    ope_name: str = None

    async def element_setup(self, element_model, element_data):
        self.element_model = copy.deepcopy(element_model)
        self.element_data = element_data
        if element_model.ele_name_a:
            self.ope_name = element_model.ele_name_a
        elif element_model.ope_type:
            self.ope_name = element_model.ope_type
        else:
            self.ope_name = element_model.ass_type
        self.element_test_result = ElementResultModel(
            test_suite_id=self.test_suite_id,
            case_id=self.case_id,
            page_step_id=self.page_step_id,
            ele_name_a=self.ope_name,
            exp=element_model.ele_exp,
            sub=element_model.ele_sub,
            sleep=element_model.ele_sleep,
            ope_type=element_model.ope_type,
            ass_type=element_model.ass_type,
            status=StatusEnum.FAIL.value,
            ele_quantity=0,
        )

    async def web_element_main(self) -> None:
        if self.element_model.ope_value or self.element_model.ass_value or self.element_model.sql:
            # 判断元素是操作类型
            name = self.element_model.ele_name_a if self.element_model.ele_name_a else self.element_model.ass_type
            ope_type = self.element_model.ope_type if self.element_model.ope_type else self.element_model.ass_type
            if self.element_model.type == ElementOperationEnum.OPE.value:
                for key, value in self.element_model.ope_value.items():
                    await self.__ope(key, value)
                self.notice_signal.send(3,
                                        data=f'操作->元素：{name}正在进行{ope_type}，元素个数：{self.element_test_result.ele_quantity}')
                await self.web_action_element()
            # 判断元素是断言类型
            elif self.element_model.type == ElementOperationEnum.ASS.value:
                for key, expect in self.element_model.ass_value.items():
                    await self.__ass(key, expect)
                await self.web_assertion_element()
                self.notice_signal.send(3,
                                        data=f'断言->元素：{name}正在进行{ope_type}，元素个数：{self.element_test_result.ele_quantity}')
            elif self.element_model.type == ElementOperationEnum.SQL.value:
                if self.mysql_connect:
                    sql = self.data_processor.replace(self.element_model.sql)
                    result_list: list[dict] = self.mysql_connect.condition_execute(sql)
                    if isinstance(result_list, list):
                        for result in result_list:
                            try:
                                for value, key in zip(result, self.element_model.key_list):
                                    self.data_processor.set_cache(key, result.get(value))
                            except SyntaxError:
                                raise SyntaxErrorError(*ERROR_MSG_0038)

                        if not result_list:
                            raise MysqlQueryIsNullError(*ERROR_MSG_0036, value=(sql,))
            else:
                raise ElementTypeError(*ERROR_MSG_0015)
        else:
            raise UiAttributeError(*ERROR_MSG_0023)

    @async_retry
    async def web_action_element(self) -> None:
        """
        处理元素的一些事件，包括点击，输入，移动
        @return:
        """
        if self.element_model.ope_value.get('element_locator'):
            del self.element_model.ope_value['element_locator']
        try:
            await getattr(self, self.element_model.ope_type)(**self.element_model.ope_value)
        except TimeoutError as error:
            raise UiTimeoutError(*ERROR_MSG_0011, error=error, value=(self.element_model.ele_name_a,))
        except Error as error:
            raise ElementLocatorError(*ERROR_MSG_0032, value=(self.element_model.ele_name_a,), error=error, )
        except ValueError as error:
            raise UiTimeoutError(*ERROR_MSG_0012, error=error)
        except Exception as error:
            traceback.print_exc()  # 打印异常追踪信息
            ERROR.logger.error(f"元素操作任务出现异常：{error}")
        else:
            if 'locating' in self.element_model.ope_value:
                del self.element_model.ope_value['locating']
            self.element_test_result.ope_value = self.element_model.ope_value
            if self.element_model.ele_sleep:
                await self.w_wait_for_timeout(self.element_model.ele_sleep)

    @async_retry
    async def web_assertion_element(self):
        is_method = callable(getattr(PlaywrightAssertion, self.element_model.ass_type, None))
        is_method_public = callable(getattr(PublicAssertion, self.element_model.ass_type, None))
        is_method_sql = callable(getattr(SqlAssertion, self.element_model.ass_type, None))
        self.element_test_result.expect = str(
            self.element_model.ass_value.get('value')) if self.element_model.ass_value.get('value') else None
        self.element_test_result.actual = self.element_model.ass_value.get(
            'expect') if self.element_model.ass_value.get('expect') else None
        try:
            if is_method or is_method_public:
                if self.element_model.ass_value['value'] is None:
                    raise ElementIsEmptyError(*ERROR_MSG_0031,
                                              value=(self.element_model.ele_name_a, self.element_model.ele_loc_a))
            if is_method:
                await getattr(PlaywrightAssertion, self.element_model.ass_type)(**self.element_model.ass_value)
            elif is_method_public:
                if self.element_model.ass_value.get('value'):
                    value = self.data_processor.replace(self.element_model.ass_value.get('value'))
                else:
                    value = await self.w_get_text(self.element_model.ass_value['value'])
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
            self.element_model.ope_value[key] = await self.__web_find_ele(self.element_model.ele_loc_a)
        else:
            # 清洗元素需要的数据
            self.element_model.ope_value[key] = await self.__web_input_value(key, value)

    @async_retry
    async def __ass(self, key, expect):
        if key == 'value' and self.element_model.ele_loc_a:
            self.element_model.ass_value[key] = await self.__web_find_ele(self.element_model.ele_loc_a)
        else:
            self.element_model.ass_value[key] = await self.__web_input_value(key, expect)

    async def __web_find_ele(self, ele_loc: str) -> Locator | list[Locator]:
        """
        基于playwright的元素查找
        @return:
        """
        if self.element_model.locator:
            try:
                locator: Locator = eval(f"await self.{self.element_model.locator}")
            except SyntaxError:
                locator: Locator = eval(f"self.{self.element_model.locator}")

            return locator.nth(self.element_model.ele_sub) if self.element_model.ele_sub else locator

        if self.data_processor.is_extract(ele_loc):
            element_locator = self.element_model.ope_value.get('element_locator')
            if element_locator:
                ele_loc = self.data_processor.specify_replace(ele_loc, element_locator)
            else:
                raise ReplaceElementLocatorError(*ERROR_MSG_0027)
        self.element_test_result.loc = ele_loc

        async def find_ele(page) -> Locator:
            match self.element_model.ele_exp:
                case ElementExpEnum.XPATH.value:
                    ele = page.locator(f'xpath={ele_loc}')
                case ElementExpEnum.TEST_ID.value:
                    ele = page.get_by_test_id(ele_loc)
                case ElementExpEnum.TEXT.value:
                    ele = page.get_by_text(ele_loc, exact=True)
                case ElementExpEnum.PLACEHOLDER.value:
                    ele = page.get_by_placeholder(ele_loc)
                case ElementExpEnum.LABEL.value:
                    ele = page.get_by_label(ele_loc)
                case ElementExpEnum.TITLE.value:
                    ele = page.get_by_title(ele_loc)
                case ElementExpEnum.ROLE.value:
                    ele = page.get_by_role(ele_loc)
                case ElementExpEnum.AIT_TEXT.value:
                    ele = page.get_by_alt_text(ele_loc)
                case _:
                    raise LocatorError(*ERROR_MSG_0020)
            if self.element_model.locator:
                ele = ele.locator(self.element_model.locator)
            return ele

        if self.element_model.is_iframe == StatusEnum.SUCCESS.value:
            ele_list: list[Locator] = []
            for i in self.page.frames:
                locator: Locator = await find_ele(i)
                count = await locator.count()
                if count > 0:
                    for nth in range(0, count):
                        ele_list.append(locator.nth(nth))
            self.element_test_result.ele_quantity = len(ele_list)
            if not ele_list:
                if self.element_model.type == ElementOperationEnum.OPE.value:
                    raise ElementIsEmptyError(*ERROR_MSG_0029, value=(self.element_model.ele_name_a, ele_loc))
                else:
                    return ele_list
            else:
                if self.element_model.ele_sub == 10000:
                    return ele_list
            return ele_list[self.element_model.ele_sub - 1] if self.element_model.ele_sub else ele_list[0]
        else:
            locator: Locator = await find_ele(self.page)
            count = await locator.count()
            self.element_test_result.ele_quantity = count
            if count < 1 or locator is None:
                if self.element_model.type == ElementOperationEnum.OPE.value:
                    raise ElementIsEmptyError(*ERROR_MSG_0029, value=(self.element_model.ele_name_a, ele_loc))
            else:
                if self.element_model.ele_sub == 10000:
                    return [locator.nth(i) for i in range(0, count)]

            if self.element_model.ele_sub is None:
                return locator
            else:
                return locator.nth(self.element_model.ele_sub - 1)

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
        return self.data_processor.replace(value)
