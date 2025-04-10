# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-05-11 22:17
# @Author : 毛鹏
from mangokit.enums.ui_enum import ElementOperationEnum
from mangokit.tools.assertion import WhatIsItAssertion, ContainAssertion, MatchingAssertion, WhatIsEqualToAssertion
from mangokit.tools.assertion.sql_assertion import SqlAssertion
from mangokit.uidrive.android import UiautomatorAssertion, UiautomatorPage, UiautomatorEquipment, UiautomatorElement, \
    UiautomatorApplication
from mangokit.uidrive.web.async_web import AsyncWebBrowser, AsyncWebCustomization, AsyncWebPage, AsyncWebElement, \
    AsyncWebDeviceInput, AsyncWebAssertion
from mangoui import CascaderModel
from mangokit import ClassMethodModel
from mangokit.tools.method import class_own_methods

from src.enums.system_enum import CacheDataKey2Enum
from src.enums.ui_enum import DriveTypeEnum


class GetClassMethod:
    """获取对不同的类的操作方法"""
    android_ope = [
        UiautomatorApplication,
        UiautomatorElement,
        UiautomatorEquipment,
        UiautomatorPage
    ]
    web_ope = [
        AsyncWebElement,
        AsyncWebDeviceInput,
        AsyncWebBrowser,
        AsyncWebPage,
        AsyncWebCustomization]
    web_ass = [AsyncWebAssertion]
    android_ass = [UiautomatorAssertion]
    sql_all = [SqlAssertion]
    public_ass = [
        WhatIsItAssertion,
        ContainAssertion,
        MatchingAssertion,
        WhatIsEqualToAssertion
    ]

    @classmethod
    def main(cls):
        return [
            {CacheDataKey2Enum.UIAUTOMATOR_OPERATION_METHOD.value: [i.model_dump() for i in cls.get_android()]},
            {CacheDataKey2Enum.PLAYWRIGHT_OPERATION_METHOD.value: [i.model_dump() for i in cls.get_web()]},
            {CacheDataKey2Enum.PLAYWRIGHT_ASSERTION_METHOD.value: [i.model_dump() for i in cls.get_web_ass()]},
            {CacheDataKey2Enum.PUBLIC_ASSERTION_METHOD.value: [i.model_dump() for i in cls.get_public_ass()]},
            {CacheDataKey2Enum.UIAUTOMATOR_ASSERTION_METHOD.value: [i.model_dump() for i in cls.get_android_ass()]},
            {CacheDataKey2Enum.SQL_ASSERTION_METHOD.value: [i.model_dump() for i in cls.get_sql_ass()]},
        ]

    @classmethod
    def find_parameter_by_value(cls, select_data, target_value):
        for item in select_data:
            if item.value == target_value:
                return item.parameter
            if item.children:
                result = cls.find_parameter_by_value(item.children, target_value)
                if result is not None:
                    return result
        return None

    @classmethod
    def ope_select_data(cls, ope_type: int, client_type) -> list[CascaderModel]:
        if ope_type == ElementOperationEnum.OPE.value:
            if client_type == DriveTypeEnum.WEB.value:
                select_data = [CascaderModel(**q.model_dump()) for q in cls.get_web()]
            elif client_type == DriveTypeEnum.ANDROID.value:
                select_data = [CascaderModel(**q.model_dump()) for q in cls.get_android()]
            else:
                select_data = [CascaderModel(**q.model_dump()) for q in cls.get_web()]
        elif ope_type == ElementOperationEnum.ASS.value:
            if client_type == DriveTypeEnum.WEB.value:
                select_data = [CascaderModel(**q.model_dump()) for q in cls.get_web_ass()]
            elif client_type == DriveTypeEnum.ANDROID.value:
                select_data = [CascaderModel(**q.model_dump()) for q in cls.get_android_ass()]
            else:
                select_data = [CascaderModel(**q.model_dump()) for q in cls.get_public_ass()]
            for e in cls.get_public_ass():
                select_data.append(CascaderModel(**e.model_dump()))
            for e in GetClassMethod().get_sql_ass():
                select_data.append(CascaderModel(**e.model_dump()))
        else:
            return [CascaderModel(value='0', label='请忽略此选项')]
        return select_data

    @classmethod
    def option(cls):
        return [
            {'value': '1',
             'label': CacheDataKey2Enum.UIAUTOMATOR_OPERATION_METHOD.value,
             'children': [i.model_dump() for i in cls.get_android()]
             },
            {'value': '1',
             'label': CacheDataKey2Enum.PLAYWRIGHT_OPERATION_METHOD.value,
             'children': [i.model_dump() for i in cls.get_web()]
             },
            {'value': '1',
             'label': CacheDataKey2Enum.PLAYWRIGHT_ASSERTION_METHOD.value,
             'children': [i.model_dump() for i in cls.get_web_ass()]
             },
            {'value': '1',
             'label': CacheDataKey2Enum.PUBLIC_ASSERTION_METHOD.value,
             'children': [i.model_dump() for i in cls.get_public_ass()]
             },
            {'value': '1',
             'label': CacheDataKey2Enum.UIAUTOMATOR_ASSERTION_METHOD.value,
             'children': [i.model_dump() for i in cls.get_android_ass()]
             },
            {'value': '1',
             'label': CacheDataKey2Enum.SQL_ASSERTION_METHOD.value,
             'children': [i.model_dump() for i in cls.get_sql_ass()]
             }
        ]

    @classmethod
    def get_android(cls):
        return [ClassMethodModel(value=str(i.__name__),
                                 label=str(i.__doc__),
                                 children=class_own_methods(i)) for i in cls.android_ope]

    @classmethod
    def get_web(cls):
        return [ClassMethodModel(value=str(i.__name__),
                                 label=str(i.__doc__),
                                 children=class_own_methods(i)) for i in cls.web_ope]

    @classmethod
    def get_public_ass(cls):
        return [ClassMethodModel(value=str(i.__name__),
                                 label=str(i.__doc__),
                                 children=class_own_methods(i)) for i in cls.public_ass]

    @classmethod
    def get_web_ass(cls):
        return [ClassMethodModel(value=str(i.__name__),
                                 label=str(i.__doc__),
                                 children=class_own_methods(i)) for i in cls.web_ass]

    @classmethod
    def get_android_ass(cls):
        return [ClassMethodModel(value=str(i.__name__),
                                 label=str(i.__doc__),
                                 children=class_own_methods(i)) for i in cls.android_ass]

    @classmethod
    def get_sql_ass(cls):
        return [ClassMethodModel(value=str(i.__name__),
                                 label=str(i.__doc__),
                                 children=class_own_methods(i)) for i in cls.sql_all]

    @classmethod
    def get_web_select(cls):
        return [ClassMethodModel(value=str(i.__name__),
                                 label=str(i.__doc__),
                                 children=class_own_methods(i)) for i in cls.web_ope]

    @classmethod
    def get_android_select(cls):
        return [ClassMethodModel(value=str(i.__name__),
                                 label=str(i.__doc__),
                                 children=class_own_methods(i)) for i in cls.android_ope]


if __name__ == '__main__':
    # print(json.dumps({'安卓 操作方法': GetClassMethod.get_android_select(),
    #                   'WEB 操作方法': GetClassMethod.get_web_select()}, ensure_ascii=False))
    print(GetClassMethod.option())
