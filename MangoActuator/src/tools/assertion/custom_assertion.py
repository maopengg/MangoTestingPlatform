# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-01-05 18:05
# @Author : 毛鹏
class CustomAssertion:
    """自定义断言"""

    @classmethod
    def ass(cls, func: str):
        """输入断言代码"""
        exec(func)


if __name__ == '__main__':
    CustomAssertion.ass(""" 
a=2
b=4
c=6
assert a+b >= c
""")
