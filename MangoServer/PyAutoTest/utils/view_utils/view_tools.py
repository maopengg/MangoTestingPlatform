# -*- coding: utf-8 -*-
# @Project: auto_test
# @Descrambles: 视图工具
# @Time   : 2023-02-26 10:15
# @Author : 毛鹏
from django.core.paginator import Paginator


def option_list(data_list) -> list:
    """
    对应web的下拉选项
    :param data_list: model对象
    :return: 返回列表套字典格式的对象
    """
    data = []
    for i in data_list:
        da = {'label': '', 'value': ''}
        for key, value in vars(i).items():
            if key == "id":
                da['value'] = value
            elif key == 'name':
                da['label'] = value
                data.append(da)
    return data


def enum_list(enum) -> list:
    """
    将枚举生成为下拉框列表返回
    :param enum:
    :return:
    """
    ope = []
    for i in enum.__doc__.split('，'):
        for key, value in eval(i).items():
            ope.append({
                'value': int(key),
                'label': value
            })
    return ope


def paging_list(size, current, books, serializer) -> list:
    """
    分页
    :param size:
    :param current:
    :param books:
    :return:
    """
    if int(books.count()) <= int(size):
        current = 1
    pagesize = Paginator(books, size)
    page = pagesize.page(current)
    return serializer(instance=page, many=True).data
