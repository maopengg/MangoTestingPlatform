# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-11 22:17
# @Author : 毛鹏
import inspect


def get_class_methods(cls):
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
        base_methods = get_class_methods(base)
        methods.extend(base_methods)
    return methods


if __name__ == '__main__':
    from auto_ui.android_base import DriverMerge
    import json

    data = get_class_methods(DriverMerge)
    print(json.dumps(data, ensure_ascii=False).encode('utf-8').decode())
    print(len(data))
