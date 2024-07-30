# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-07-25 下午1:59
# @Author : 毛鹏
import re
from urllib.parse import urlparse


def is_url(string):
    # 正则表达式判断是否为 URL
    url_pattern = re.compile(
        r'^(https?://)?'  # 协议
        r'([a-zA-Z0-9.-]+|(\d{1,3}\.){3}\d{1,3})'  # 域名或 IP 地址
        r'(:\d+)?'  # 可选的端口
        r'(/.*)?$'  # 可选的路径
    )
    return re.match(url_pattern, string) is not None


def process_urls(strings):
    result = []

    for string in strings:
        if is_url(string):
            parsed_url = urlparse(string)
            # 检查是否是 IP 地址加端口的形式
            if parsed_url.hostname and re.match(r'^\d{1,3}(\.\d{1,3}){3}$', parsed_url.hostname):
                # 是 IP 地址，去掉端口
                cleaned_url = f"{parsed_url.scheme}://{parsed_url.hostname}"
                result.append(cleaned_url)
            else:
                # 不是 IP 地址加端口，加入到列表中
                result.append(string)

    return result