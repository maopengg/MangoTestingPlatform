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

    def main(self):
        def json_(data):
            res = json.dumps(data, ensure_ascii=False).encode('utf-8').decode()
            print(res)

        android = self.get_android()
        web = self.get_web()
        public_ass = self.get_public_ass()
        json_(android)
        json_(web)
        json_(public_ass)

    def get_class_methods(self, cls):
        methods = []
        # 获取类中的所有属性和方法
        for attr in dir(cls):
            obj = getattr(cls, attr)
            # 判断对象是否为方法或函数
            if inspect.ismethod(obj) or inspect.isfunction(obj):
                # 获取方法的所有属性和方法
                members = inspect.getmembers(obj)
                # 遍历方法的所有属性和方法，获取方法的注释
                for name, value in members:
                    if name == '__doc__':
                        doc = value
                        break
                if attr != '__init__':
                    # 获取方法的参数信息
                    signature = inspect.signature(obj)
                    parameters = signature.parameters
                    param_dict = {}
                    for param in parameters.values():
                        if param.name != 'self':
                            param_dict[param.name] = str(param.annotation)
                    # 将方法名称、注释和参数信息组成一个字典
                    method_dict = {
                        '方法名': attr,
                        '函数介绍': doc,
                        '函数参数': param_dict
                    }
                    methods.append(method_dict)
        # 遍历父类，重复上述步骤
        for base in cls.__bases__:
            base_methods = self.get_class_methods(base)
            methods.extend(base_methods)
        return methods

    def get_android(self):
        data = []
        for cls in self.android_ope:
            data.append({'android_ope': self.get_class_methods(cls)})
        for cls in self.android_ass:
            data.append({'android_ass': self.get_class_methods(cls)})
        return data

    def get_web(self):
        data = []
        for cls in self.web_ope:
            data.append({'web_ope': self.get_class_methods(cls)})
        for cls in self.web_ass:
            data.append({'web_ass': self.get_class_methods(cls)})
        return data

    def get_public_ass(self):
        data = []
        for cls in self.public_ass:
            data.append({'public_ass': self.get_class_methods(cls)})
        return data


if __name__ == '__main__':
    r = GetClassMethod()
    r.main()
