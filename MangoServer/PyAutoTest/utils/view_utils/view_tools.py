# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Descrambles: 视图工具
# @Time   : 2023-02-26 10:15
# @Author : 毛鹏
from django.core.paginator import Paginator


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
                'title': value,
                'key': int(key)
            })
    return ope


def paging_list(size, current, books, serializer) -> list:
    """
    分页
    @param size:在、
    @param current:现在页数
    @param books:
    @param serializer:
    @return:
    """
    if int(books.count()) <= int(size):
        current = 1
    pagesize = Paginator(books, size)
    page = pagesize.page(current)
    return serializer(instance=page, many=True).data
