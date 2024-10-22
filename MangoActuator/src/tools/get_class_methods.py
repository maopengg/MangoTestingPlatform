# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-05-11 22:17
# @Author : 毛鹏
import inspect
import json

from src.enums.system_enum import CacheDataKey2Enum
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

    def __init__(self):
        self.android_ope = [
            UiautomatorApplication,
            UiautomatorElement,
            UiautomatorEquipment,
            UiautomatorPage
        ]
        self.web_ope = [
            PlaywrightElement,
            PlaywrightDeviceInput,
            PlaywrightBrowser,
            PlaywrightPage,
            PlaywrightCustomization]
        self.web_ass = [PlaywrightAssertion]
        self.android_ass = [UiautomatorAssertion]
        self.sql_all = [SqlAssertion]
        self.public_ass = [
            WhatIsItAssertion,
            ContainAssertion,
            MatchingAssertion,
            WhatIsEqualToAssertion
        ]

    def main(self):
        return [
            {CacheDataKey2Enum.UIAUTOMATOR_OPERATION_METHOD.value: self.json_(self.get_android())},
            {CacheDataKey2Enum.PLAYWRIGHT_OPERATION_METHOD.value: self.json_(self.get_web())},
            {CacheDataKey2Enum.PLAYWRIGHT_ASSERTION_METHOD.value: self.json_(self.get_web_ass())},
            {CacheDataKey2Enum.PUBLIC_ASSERTION_METHOD.value: self.json_(self.get_public_ass())},
            {CacheDataKey2Enum.UIAUTOMATOR_ASSERTION_METHOD.value: self.json_(self.get_android_ass())},
            {CacheDataKey2Enum.SQL_ASSERTION_METHOD.value: self.json_(self.get_sql_ass())}
        ]

    def option(self):
        return [
            {'value': '1',
             'label': CacheDataKey2Enum.UIAUTOMATOR_OPERATION_METHOD.value,
             'children': self.get_android()
             },
            {'value': '1',
             'label': CacheDataKey2Enum.PLAYWRIGHT_OPERATION_METHOD.value,
             'children': self.get_web()
             },
            {'value': '1',
             'label': CacheDataKey2Enum.PLAYWRIGHT_ASSERTION_METHOD.value,
             'children': self.get_web_ass()
             },
            {'value': '1',
             'label': CacheDataKey2Enum.PUBLIC_ASSERTION_METHOD.value,
             'children': self.get_public_ass()
             },
            {'value': '1',
             'label': CacheDataKey2Enum.UIAUTOMATOR_ASSERTION_METHOD.value,
             'children': self.get_android_ass()
             },
            {'value': '1',
             'label': CacheDataKey2Enum.SQL_ASSERTION_METHOD.value,
             'children': self.get_sql_ass()
             }
        ]

    def json_(self, data):
        return json.dumps(data, ensure_ascii=False).encode('utf-8').decode()

    def get_class_methods(self, cls):
        methods = []
        # 获取类中的所有属性和方法
        for attr in dir(cls):
            obj = getattr(cls, attr)
            # 判断对象是否为方法或函数，并且所属类是传入的类
            if (inspect.ismethod(obj) or inspect.isfunction(obj)) and obj.__qualname__.split('.')[
                0] == cls.__name__:
                if attr != '__init__':
                    # 获取方法的注释
                    doc = inspect.getdoc(obj)
                    # 获取方法的参数信息
                    signature = inspect.signature(obj)
                    parameters = signature.parameters
                    param_dict = {}
                    for param in parameters.values():
                        if param.name != 'self':
                            param_dict[param.name] =''
                    # 将方法名称、注释和参数信息组成一个字典
                    method_dict = {
                        'value': attr,
                        'label': doc,
                        'parameter': param_dict
                    }
                    methods.append(method_dict)
        return methods

    def get_android(self):
        data = []
        for cls in self.android_ope:
            data.append({'value': str(cls.__name__),
                         'label': str(cls.__doc__),
                         'children': self.get_class_methods(cls)})
        return data

    def get_web(self):
        data = []
        for cls in self.web_ope:
            data.append({'value': str(cls.__name__),
                         'label': str(cls.__doc__),
                         'children': self.get_class_methods(cls)})

        return data

    def get_public_ass(self):
        data = []
        for cls in self.public_ass:
            data.append({'value': str(cls.__name__),
                         'label': str(cls.__doc__),
                         'children': self.get_class_methods(cls)})
        return data

    def get_web_ass(self):
        data = []
        for cls in self.web_ass:
            data.append({'value': str(cls.__name__),
                         'label': str(cls.__doc__),
                         'children': self.get_class_methods(cls)})
        return data

    def get_android_ass(self):
        data = []
        for cls in self.android_ass:
            data.append({'value': str(cls.__name__),
                         'label': str(cls.__doc__),
                         'children': self.get_class_methods(cls)})
        return data

    def get_sql_ass(self):
        data = []
        for cls in self.sql_all:
            data.append({'value': str(cls.__name__),
                         'label': str(cls.__doc__),
                         'children': self.get_class_methods(cls)})
        return data

if __name__ == '__main__':
    print(GetClassMethod().get_web())