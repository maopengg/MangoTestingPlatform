# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-05-11 22:17
# @Author : 毛鹏
import inspect
import json

from mango_ui import CascaderModel

from src.enums.system_enum import CacheDataKey2Enum
from src.enums.ui_enum import ElementOperationEnum, DriveTypeEnum
from src.services.ui.bases.android import UiautomatorApplication, UiautomatorElement, UiautomatorEquipment, \
    UiautomatorPage
from src.services.ui.bases.android.assertion import UiautomatorAssertion
from src.services.ui.bases.web import PlaywrightElement, PlaywrightPage, PlaywrightDeviceInput, \
    PlaywrightBrowser, PlaywrightCustomization
from src.tools.assertion import PlaywrightAssertion, WhatIsItAssertion, ContainAssertion, MatchingAssertion, \
    WhatIsEqualToAssertion
from src.tools.assertion.sql_assertion import SqlAssertion


class GetClassMethod:
    """获取对不同的类的操作方法"""
    android_ope = [
        UiautomatorApplication,
        UiautomatorElement,
        UiautomatorEquipment,
        UiautomatorPage
    ]
    web_ope = [
        PlaywrightElement,
        PlaywrightDeviceInput,
        PlaywrightBrowser,
        PlaywrightPage,
        PlaywrightCustomization]
    web_ass = [PlaywrightAssertion]
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
            {CacheDataKey2Enum.UIAUTOMATOR_OPERATION_METHOD.value: cls.get_android()},
            {CacheDataKey2Enum.PLAYWRIGHT_OPERATION_METHOD.value: cls.get_web()},
            {CacheDataKey2Enum.PLAYWRIGHT_ASSERTION_METHOD.value: cls.get_web_ass()},
            {CacheDataKey2Enum.PUBLIC_ASSERTION_METHOD.value: cls.get_public_ass()},
            {CacheDataKey2Enum.UIAUTOMATOR_ASSERTION_METHOD.value: cls.get_android_ass()},
            {CacheDataKey2Enum.SQL_ASSERTION_METHOD.value: cls.get_sql_ass()},
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
                select_data = [CascaderModel(**q) for q in cls.get_web()]
            elif client_type == DriveTypeEnum.ANDROID.value:
                select_data = [CascaderModel(**q) for q in cls.get_android()]
            else:
                select_data = [CascaderModel(**q) for q in cls.get_web()]
        elif ope_type == ElementOperationEnum.ASS.value:
            if client_type == DriveTypeEnum.WEB.value:
                select_data = [CascaderModel(**q) for q in cls.get_web_ass()]
            elif client_type == DriveTypeEnum.ANDROID.value:
                select_data = [CascaderModel(**q) for q in cls.get_android_ass()]
            else:
                select_data = [CascaderModel(**q) for q in cls.get_public_ass()]
            for e in cls.get_public_ass():
                select_data.append(CascaderModel(**e))
            for e in GetClassMethod().get_sql_ass():
                select_data.append(CascaderModel(**e))
        else:
            return [CascaderModel(value='0', label='请忽略此选项')]
        return select_data

    @classmethod
    def option(cls):
        return [
            {'value': '1',
             'label': CacheDataKey2Enum.UIAUTOMATOR_OPERATION_METHOD.value,
             'children': cls.get_android()
             },
            {'value': '1',
             'label': CacheDataKey2Enum.PLAYWRIGHT_OPERATION_METHOD.value,
             'children': cls.get_web()
             },
            {'value': '1',
             'label': CacheDataKey2Enum.PLAYWRIGHT_ASSERTION_METHOD.value,
             'children': cls.get_web_ass()
             },
            {'value': '1',
             'label': CacheDataKey2Enum.PUBLIC_ASSERTION_METHOD.value,
             'children': cls.get_public_ass()
             },
            {'value': '1',
             'label': CacheDataKey2Enum.UIAUTOMATOR_ASSERTION_METHOD.value,
             'children': cls.get_android_ass()
             },
            {'value': '1',
             'label': CacheDataKey2Enum.SQL_ASSERTION_METHOD.value,
             'children': cls.get_sql_ass()
             }
        ]

    @classmethod
    def get_class_methods(cls, self):
        methods = []
        # 获取类中的所有属性和方法
        for attr in dir(self):
            obj = getattr(self, attr)
            # 判断对象是否为方法或函数，并且所属类是传入的类
            if (inspect.ismethod(obj) or inspect.isfunction(obj)) and obj.__qualname__.split('.')[
                0] == self.__name__:
                if attr != '__init__':
                    # 获取方法的注释
                    doc = inspect.getdoc(obj)
                    # 获取方法的参数信息
                    signature = inspect.signature(obj)
                    parameters = signature.parameters
                    param_dict = {}
                    for param in parameters.values():
                        if param.name != 'self':
                            param_dict[param.name] = ''
                    # 将方法名称、注释和参数信息组成一个字典
                    method_dict = {
                        'value': attr,
                        'label': doc,
                        'parameter': param_dict
                    }
                    methods.append(method_dict)
        return methods

    @classmethod
    def get_android(cls):
        data = []
        for i in cls.android_ope:
            data.append({'value': str(i.__name__),
                         'label': str(i.__doc__),
                         'children': cls.get_class_methods(i)})
        return data

    @classmethod
    def get_web(cls):
        data = []
        for i in cls.web_ope:
            data.append({'value': str(i.__name__),
                         'label': str(i.__doc__),
                         'children': cls.get_class_methods(i)})

        return data

    @classmethod
    def get_public_ass(cls):
        data = []
        for i in cls.public_ass:
            data.append({'value': str(i.__name__),
                         'label': str(i.__doc__),
                         'children': cls.get_class_methods(i)})
        return data

    @classmethod
    def get_web_ass(cls):
        data = []
        for i in cls.web_ass:
            data.append({'value': str(i.__name__),
                         'label': str(i.__doc__),
                         'children': cls.get_class_methods(i)})
        return data

    @classmethod
    def get_android_ass(cls):
        data = []
        for i in cls.android_ass:
            data.append({'value': str(i.__name__),
                         'label': str(i.__doc__),
                         'children': cls.get_class_methods(i)})
        return data

    @classmethod
    def get_sql_ass(cls):
        data = []
        for i in cls.sql_all:
            data.append({'value': str(i.__name__),
                         'label': str(i.__doc__),
                         'children': cls.get_class_methods(i)})
        return data

    @classmethod
    def get_web_select(cls):
        data = []
        for i in cls.web_ope:
            data.append({'操作名称': str(i.__doc__),
                         'children': cls.get_class_methods(i)})

        return data

    @classmethod
    def get_android_select(cls):
        data = []
        for i in cls.android_ope:
            data.append({'label': str(i.__doc__),
                         'children': cls.get_class_methods(i)})
        return data


if __name__ == '__main__':
    print(json.dumps({'安卓 操作方法': GetClassMethod.get_android_select(),
                      'WEB 操作方法': GetClassMethod.get_web_select()}, ensure_ascii=False))
