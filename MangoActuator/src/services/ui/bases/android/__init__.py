# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏

from uiautomator2 import UiObject, UiObjectNotFoundError
from uiautomator2.exceptions import XPathElementNotFoundError
from uiautomator2.xpath import XPathSelector

from src.enums.tools_enum import StatusEnum
from src.enums.ui_enum import ElementExpEnum
from src.exceptions import *
from src.models.ui_model import ElementModel, ElementResultModel
from src.services.ui.bases.android.application import UiautomatorApplication
from src.services.ui.bases.android.assertion import UiautomatorAssertion
from src.services.ui.bases.android.customization import UiautomatorCustomization
from src.services.ui.bases.android.element import UiautomatorElement
from src.services.ui.bases.android.equipment import UiautomatorEquipment
from src.services.ui.bases.android.page import UiautomatorPage
from src.tools.assertion.sql_assertion import SqlAssertion
from src.tools.decorator.async_retry import sync_retry


class AndroidDriver(UiautomatorEquipment,
                    UiautomatorApplication,
                    UiautomatorPage,
                    UiautomatorElement,
                    UiautomatorCustomization):
    def __init__(self, base_data, element_model: ElementModel):
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

    def open_app(self):
        if not self.base_data.is_open_app:
            self.base_data.is_open_app = True
            self.a_press_home()
            self.a_app_stop_all()
            if self.base_data.android and self.base_data.package_name:
                self.a_start_app(self.base_data.package_name)

    @sync_retry
    def a_action_element(self) -> dict:
        try:
            getattr(self, self.element_model.ope_key)(**self.element_model.ope_value)
            if self.element_model.sleep:
                self.a_sleep(self.element_model.sleep)
            return self.element_model.ope_value
        except ValueError as error:
            raise UiError(*ERROR_MSG_0012, error=error)
        # except NullPointerExceptionError as error:
        #     raise ElementLocatorError(*ERROR_MSG_0032, value=(self.element_model.name,), error=error, )
        except UiObjectNotFoundError as error:
            raise UiError(*ERROR_MSG_0032, value=(self.element_model.name,), error=error, )
        except XPathElementNotFoundError as error:
            raise UiError(*ERROR_MSG_0050, value=(self.element_model.name,), error=error, )

    @sync_retry
    def a_assertion_element(self) -> str:
        is_method = callable(getattr(UiautomatorAssertion, self.element_model.ope_key, None))
        from src.tools.assertion import PublicAssertion
        is_method_public = callable(getattr(PublicAssertion, self.element_model.ope_key, None))
        is_method_sql = callable(getattr(SqlAssertion, self.element_model.ope_key, None))
        self.element_test_result.element_data.expect = self.element_model \
            .ope_value \
            .get('expect') if self.element_model \
            .ope_value \
            .get('expect') else None

        if is_method or is_method_public:
            if self.element_model.ope_value['value'] is None:
                raise UiError(*ERROR_MSG_0031, value=(self.element_model.name, self.element_model.loc))

        try:
            actual = None
            if is_method:
                actual = '判断元素是什么'
                getattr(UiautomatorAssertion, self.element_model.ope_key)(**self.element_model.ope_value)
            elif is_method_public:
                actual = self.a_get_text(self.element_model.ope_value['value'])
                getattr(PublicAssertion, self.element_model.ope_key)(
                    **{k: actual if k == 'value' else v for k, v in self.element_model.ope_value.items()})
            elif is_method_sql:
                actual = 'sql匹配'
                if self.base_data.mysql_connect is not None:
                    SqlAssertion.mysql_obj = self.base_data.mysql_connect
                    SqlAssertion.sql_is_equal(**self.element_model.ope_value)
                else:
                    raise UiError(*ERROR_MSG_0019, value=(self.base_data.case_id, self.base_data.test_suite_id))
            return actual
        except AssertionError as error:
            raise UiError(*ERROR_MSG_0017, error=error)
        except AttributeError as error:
            raise UiError(*ERROR_MSG_0030, error=error)
        except ValueError as error:
            raise UiError(*ERROR_MSG_0018, error=error)

    @sync_retry
    def a_find_ele(self) -> tuple[int, UiObject] | tuple[int, XPathSelector]:
        match self.element_model.exp:
            case ElementExpEnum.LOCATOR.value:
                try:
                    if self.element_model.loc[:5] == 'xpath':
                        loc = eval(f"self.android.{self.element_model.loc}")
                    else:
                        loc = eval(f"self.android{self.element_model.loc}")
                except SyntaxError:
                    raise UiError(*ERROR_MSG_0022)
            case ElementExpEnum.XPATH.value:
                loc = self.base_data.android.xpath(self.element_model.loc)
            case ElementExpEnum.BOUNDS.value:
                loc = self.base_data.android(text=self.element_model.loc)
            case ElementExpEnum.DESCRIPTION.value:
                loc = self.base_data.android(description=self.element_model.loc)
            # case ElementExpEnum.PERCENTAGE.value:
            #     return self.android(resourceId=self.element_model.loc)
            case ElementExpEnum.RESOURCE_ID.value:
                loc = self.base_data.android(resourceId=self.element_model.loc)
            case _:
                raise UiError(*ERROR_MSG_0020)
        return 0, loc
