# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-11 22:17
# @Author : 毛鹏
import inspect
import json

from auto_ui.android_base import UiautomatorApplication, UiautomatorElementOperation, \
    UiautomatorEquipmentDevice, UiautomatorAssertion, UiautomatorPage
from auto_ui.web_base import PlaywrightPageOperation, PlaywrightInputDevice, PlaywrightElementOperation, \
    PlaywrightOperationBrowser, PlaywrightAssertion
from utils.assertion.public_args import RandomData
from utils.assertion.public_assertion import PublicAssertion


class GetClassMethod:

    def __init__(self):
        self.android_ope = [UiautomatorApplication, UiautomatorElementOperation, UiautomatorEquipmentDevice,
                            UiautomatorPage]
        self.android_ass = [UiautomatorAssertion, ]
        self.web_ope = [PlaywrightElementOperation, PlaywrightInputDevice, PlaywrightOperationBrowser,
                        PlaywrightPageOperation]
        self.web_ass = [PlaywrightAssertion, ]
        self.public_ass = [PublicAssertion, ]
        self.public_data = [RandomData, ]

    def get_all_ope(self):
        android_ope_list = self.get_android()
        web_ope_list = self.get_web()
        data = [{'value': 'web',
                 'label': 'WEB',
                 'children': web_ope_list},
                {'value': 'android',
                 'label': '安卓',
                 'children': android_ope_list}
                ]
        self.json_(data)

    def get_all_ass(self):
        web_ass = self.get_web_ass()
        public_ass = self.get_public_ass()
        android_ass = self.get_android_ass()
        data = [{'value': 'web_ass',
                 'label': 'WEB断言',
                 'children': web_ass},
                {'value': 'android_ass',
                 'label': '安卓断言',
                 'children': android_ass},
                {'value': 'public_ass',
                 'label': '公共断言',
                 'children': public_ass}
                ]
        self.json_(data)

    def json_(self, data):
        res = json.dumps(data, ensure_ascii=False).encode('utf-8').decode()
        print(res)

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
                            param_dict[param.name] = str(param.annotation)
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

    def get_public_method(self):
        data = []
        for cls in self.public_data:
            data.append({'value': str(cls.__name__),
                         'label': str(cls.__doc__),
                         'children': self.get_class_methods(cls)})
        return data


if __name__ == '__main__':
    # 第0个必须是web
    r = GetClassMethod()
    r.get_all_ope()
    r.get_all_ass()
