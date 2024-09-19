# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-01-07 12:11
# @Author : 毛鹏
import socket


def get_host_ip():
    """
    查询本机ip地址
    :return:
    """
    _s = None
    try:
        _s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _s.connect(('8.8.8.8', 80))
        l_host = _s.getsockname()[0]
    finally:
        _s.close()

    return l_host
