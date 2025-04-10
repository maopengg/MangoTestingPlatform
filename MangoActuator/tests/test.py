# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-01-06 18:32
# @Author : 毛鹏

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        for i in range(3):
            browser = p.chromium.connect("ws://172.22.20.1:1080")  # IPv6 连接
            context = browser.new_context()
            page = context.new_page()
            page.goto('https://www.baidu.com/')
            print(page.title())
            page.close()
            context.close()
            browser.close()


class Data(type):
    pass


class Meta1(Data):
    def __new__(cls, name, bases, attrs, **kwargs):
        for method_name, method_func in kwargs.get('methods', {}).items():
            attrs[method_name] = method_func
        return super().__new__(cls, name, bases, attrs)


class Meta2(Data):
    def __new__(cls, name, bases, attrs, **kwargs):
        for method_name, method_func in kwargs.get('methods', {}).items():
            attrs[method_name] = lambda self, *args, m=method_func, **kwargs: f"Meta2: {m(self, *args, **kwargs)}"
        return super().__new__(cls, name, bases, attrs)


# 外部方法
def greet(self):
    return f"Hello, {getattr(self, 'name', 'unknown')}"


def calculate(self, x, y):
    return x + y


# 使用元类
class ClassA(metaclass=Meta1, methods={'greet': greet, 'calc': calculate}):
    def __init__(self, name):
        self.name = name


class ClassB(metaclass=Meta2, methods={'greet': greet, 'calc': calculate}):
    def __init__(self, name):
        self.name = name


# 测试
a = ClassA("Alice")
b = ClassB("Bob")

# 反射调用
print(getattr(a, 'greet')())  # 输出: Hello, Alice
print(getattr(b, 'greet')())  # 输出: Meta2: Hello, Bob
print(getattr(a, 'calc')(3, 5))  # 输出: 8
print(getattr(b, 'calc')(3, 5))  # 输出: Meta2: 8
