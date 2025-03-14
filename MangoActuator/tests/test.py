# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-01-06 18:32
# @Author : 毛鹏
class BaseDATA:
    def __init__(self):
        self.data = "Base Data"


class A(BaseDATA):
    def method_a(self):
        return f"A operates on {self.data}"


class B(BaseDATA):
    def method_b(self):
        return f"B operates on {self.data}"


class C(BaseDATA):
    def method_c(self):
        return f"C operates on {self.data}"


def inject_methods(*classes):
    def decorator(cls):
        for clazz in classes:
            for name, method in clazz.__dict__.items():
                if callable(method) and not name.startswith("__"):
                    setattr(cls, name, method)
        return cls
    return decorator


@inject_methods(A, B, C)
class Method(BaseDATA):
    pass


# 使用
tool = Method()
print(tool.method_a())  # 输出: A operates on Base Data
print(tool.method_b())  # 输出: B operates on Base Data
print(tool.method_c())  # 输出: C operates on Base Data

# 反射调用
method_name = "method_a"
if hasattr(tool, method_name):
    method = getattr(tool, method_name)
    print(method())  # 输出: A operates on Base Data