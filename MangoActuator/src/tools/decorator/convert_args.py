# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-01-03 21:35
# @Author : 毛鹏


def convert_args(set_type, set_=None):
    """
    转换类型装饰器
    @param set_:
    @param set_type:
    @return:
    """

    def decorator(func):
        async def wrapper(self, data):
            if set_ == 'list':
                data = [set_type(**i) for i in data]
            elif set_ == 'str':
                data = data
            elif set_type == type(data):
                return await func(self, data)
            else:
                data = set_type(**data)
            return await func(self, data)

        return wrapper

    return decorator
