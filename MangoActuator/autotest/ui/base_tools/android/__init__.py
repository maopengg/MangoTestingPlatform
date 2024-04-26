# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
from retrying import retry
from uiautomator2 import UiObject, NullPointerExceptionError, UiObjectNotFoundError
from uiautomator2.xpath import XPathSelector

from autotest.ui.base_tools.android.application import UiautomatorApplication
from autotest.ui.base_tools.android.assertion import UiautomatorAssertion
from autotest.ui.base_tools.android.customization import UiautomatorCustomization
from autotest.ui.base_tools.android.element import UiautomatorElement
from autotest.ui.base_tools.android.equipment import UiautomatorEquipment
from autotest.ui.base_tools.android.page import UiautomatorPage
from enums.ui_enum import ElementExpEnum
from exceptions.ui_exception import *
from models.socket_model.ui_model import ElementModel, ElementResultModel
from tools.assertion.sql_assertion import SqlAssertion
from tools.message.error_msg import *


class AndroidDriver(UiautomatorEquipment,
                    UiautomatorApplication,
                    UiautomatorPage,
                    UiautomatorElement,
                    UiautomatorCustomization):
    element_test_result: ElementResultModel = None
    element_model: ElementModel = None

    @retry(stop_max_attempt_number=10, wait_fixed=500)
    def a_find_ele(self) -> UiObject | XPathSelector:
        match self.element_model.exp:
            case ElementExpEnum.LOCATOR.value:
                return eval(f"self.android{self.element_model.loc}")
            case ElementExpEnum.XPATH.value:
                return self.android.xpath(self.element_model.loc)
            case ElementExpEnum.BOUNDS.value:
                return self.android(text=self.element_model.loc)
            case ElementExpEnum.DESCRIPTION.value:
                return self.android(description=self.element_model.loc)
            case ElementExpEnum.PERCENTAGE.value:
                return self.android(description=self.element_model.loc)
            case _:
                raise LocatorError(*ERROR_MSG_0020)

    @retry(stop_max_attempt_number=10, wait_fixed=500)
    def a_action_element(self) -> None:
        try:
            getattr(self, self.element_model.ope_type)(**self.element_model.ope_value)
        except ValueError as error:
            raise UiTimeoutError(*ERROR_MSG_0012, error=error)
        except NullPointerExceptionError as error:
            raise ElementLocatorError(*ERROR_MSG_0032, value=(self.element_model.name,), error=error, )
        except UiObjectNotFoundError as error:
            raise ElementLocatorError(*ERROR_MSG_0032, value=(self.element_model.name,), error=error, )
        except Exception as error:
            print(error)
        else:
            if 'locating' in self.element_model.ope_value:
                del self.element_model.ope_value['locating']
            self.element_test_result.ope_value = self.element_model.ope_value
            if self.element_model.sleep:
                self.a_sleep(self.element_model.sleep)

    @retry(stop_max_attempt_number=10, wait_fixed=500)
    def a_assertion_element(self) -> None:
        is_method = callable(getattr(UiautomatorAssertion, self.element_model.ass_type, None))
        from tools.assertion import PublicAssertion
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
                getattr(UiautomatorAssertion, self.element_model.ass_type)(**self.element_model.ass_value)
            elif is_method_public:
                if self.element_model.ass_value.get('value'):
                    value = self.element_model.ass_value.get('value')
                    self.element_test_result.actual = f'断言元素本身，元素：{str(value)}'
                else:
                    value = self.a_get_text(self.element_model.ass_value['value'])
                    self.element_test_result.actual = value
                getattr(PublicAssertion, self.element_model.ass_type)(
                    **{k: value if k == 'value' else v for k, v in self.element_model.ass_value.items()})
            elif is_method_sql:
                if self.mysql_connect is not None:
                    SqlAssertion.mysql_obj = self.mysql_connect
                    SqlAssertion.sql_is_equal(**self.element_model.ass_value)
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
