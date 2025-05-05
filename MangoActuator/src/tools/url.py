# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-05-05 20:45
# @Author : 毛鹏
from urllib.parse import urlparse, urlunparse


def http_to_ws_url(http_url):
    """
    将HTTP/HTTPS URL转换为WebSocket URL
    :param http_url: 原始HTTP/HTTPS URL
    :return: 对应的WebSocket URL，如果输入不合法则返回None
    """
    try:
        parsed = urlparse(http_url)
        if parsed.scheme not in ('http', 'https'):
            return None
        new_scheme = 'wss' if parsed.scheme == 'https' else 'ws'
        path = parsed.path
        if not path.endswith('/'):
            path = path + '/'
        ws_url = urlunparse((
            new_scheme,
            parsed.netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

        return ws_url

    except Exception:
        return None


def is_valid_url(url):
    try:
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return None
        if parsed.scheme not in ('http', 'https', 'ftp'):
            return None
        return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
    except Exception:
        return None
