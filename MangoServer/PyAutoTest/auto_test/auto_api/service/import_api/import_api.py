# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-04-18 16:29
# @Author : 毛鹏
import io
import json
import re
import urllib
from urllib.parse import urlparse, parse_qs

from PyAutoTest.enums.api_enum import MethodEnum


class ImportApi:

    @classmethod
    def curl_import(cls, data: dict):
        from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoCRUD
        host, path, query_params = cls.url(data['curl'].get('url'))
        _data = None
        _json = None
        if 'from-data' in data['curl'].get('data'):
            _data = data['curl'].get('data')
            _data = _data[2:]
            _data = _data[:-1]
        else:
            _data = data['curl'].get('data')
            _data = _data[2:]
            _data = _data[:-1]
        return ApiInfoCRUD.inside_post({
            'project_product': data['project_product'],
            'module': data['module'],
            'type': data['type'],
            'name': data['name'],
            'client': data['client'],
            'url': path,
            'method': MethodEnum.get_key(data['curl'].get('method')),
            'header': data['curl'].get('header'),
            'params': query_params,
            'data': _data,
            'json': _json
        })

    @classmethod
    def curl_import_(cls, data: dict):
        fetch_string = data.get('data')
        url = re.search(r'fetch\("(.*?)"', fetch_string).group(1)
        # headers = json.loads(re.search(r'"headers":\s*({.*?})', fetch_string, re.DOTALL).group(1))
        body_match = re.search(r'"body":\s*(.*?)(,|\n|\r)', fetch_string, re.DOTALL)
        print(body_match.group(1))
        print(type(body_match))
        body = json.loads(body_match.group(1)) if body_match else None
        method = re.search(r'"method":\s*"(.*?)"', fetch_string).group(1)

        # 提取请求头字符串
        headers_match = re.search(r'"headers":\s*({.*?})', fetch_string, re.DOTALL)
        headers_str = headers_match.group(1) if headers_match else None

        # 将请求头字符串转换为字典
        headers = {}
        if headers_str:
            header_pairs = re.findall(r'"(.*?)":\s*"(.*?)"', headers_str)
            headers = {key: value for key, value in header_pairs}

        host, path, query_params = cls.url(url)
        from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoCRUD
        return ApiInfoCRUD.inside_post({
            'project': data.get('project'),
            'type': data.get('type'),
            'module': data.get('module'),
            'name': data.get('name'),
            'client': data.get('client'),
            'url': path,
            'method': MethodEnum.get_key(method),
            'header': headers,
            'params': query_params,
            'data': None,
            'json': body
        })

    @classmethod
    def url(cls, url: str) -> tuple[str, str, None | dict]:
        parsed_url = urlparse(url)
        host = parsed_url.netloc
        path = parsed_url.path
        if parsed_url.query:
            query_params = parse_qs(parsed_url.query)
            query_params = {key: value[0] for key, value in query_params.items()}
        else:
            query_params = None
        return host, path, query_params

    @classmethod
    def from_data(cls, data:str=None):
        data = '''
        ------WebKitFormBoundaryL30SdvU0YozVLK4A
        Content-Disposition: form-data; name="username"

        maopeng@zalldigital.com
        ------WebKitFormBoundaryL30SdvU0YozVLK4A
        Content-Disposition: form-data; name="password"

        dc483e80a7a0bd9ef71d8cf973673924
        ------WebKitFormBoundaryL30SdvU0YozVLK4A--
        '''

        # 使用io.StringIO将字符串转换为类文件对象
        file_obj = io.StringIO(data)

        fields = {}
        while True:
            # 读取分隔符
            line = file_obj.readline().strip()
            if not line:
                break

            # 读取字段名称
            name = urllib.parse.parse_qs(line)['name'][0]

            # 读取字段值
            file_obj.readline()  # 读取空行
            value = file_obj.readline().strip()
            fields[name] = value

        print(fields)

if __name__ == '__main__':
    d = """curl 'https://sara-test.growknows.cn/dev-api/business/template-tenant/activate' \
  -H 'authority: sara-test.growknows.cn' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'accept-language: zh-CN,zh;q=0.9,en;q=0.8' \
  -H 'authorization: eyJhbGciOiJIUzUxMiJ9.eyJhY2Nlc3NfdG9rZW4iOiJCZWFyZXIgdG9rZW46bG9naW5fdG9rZW5zOjE6MjphY2Nlc3NfdG9rZW46YTAwNzY5ZjAtMGVlYS00NDE4LTg0MTItYzJlNDAzYTY2MjIwIiwicmVmcmVzaF90b2tlbiI6IkJlYXJlciB0b2tlbjpsb2dpbl90b2tlbnM6MToyOnJlZnJlc2hfdG9rZW46eGJSWHFMdzNIUUk3OTVjVC0tbGlhbzRwMHZwdEFIXzUwd3NEX1h3cDNMaUdlY0lybkdTNThPdzB4YUIxc2FLbENPcWllZUZEOU96SmVHR3ltNHBIZDlndThvWGt6MGgxRWFka2ZHeXFGenFwN3VYT0h6OFVFaTR0VUJ4Q0ktcjAiLCJhY2NvdW50X3R5cGUiOiJ2aXAiLCJ1c2VyX3R5cGUiOiIwMCIsInVzZXJfaWQiOjIsInVzZXJfbmFtZSI6ImFkbWluQGFpZ2MuY29tIiwiaXNfbGVzc29yIjoiWSIsImVudGVycHJpc2VfaWQiOjEsImVudGVycHJpc2VfbmFtZSI6ImFkbWluaXN0cmF0b3IiLCJzb3VyY2VfbmFtZSI6InNsYXZlIn0.xjGha5TbkWqMQKVM2GFG0k8xCbJ30NzoG8pFjaMDbgtZwm6gduVnetXehs1IkZC1AL66hqooAcgsVcnTUIVGQg' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -H 'cookie: _c_WBKFRo=dlTUE5hIZjLTFyzPnKkAQtOgveGWPYOa1ybUKh3L; _ga=GA1.1.155622883.1708941518; sessionid=jb7qvl9jtbrccw9fgy1s5u5mcyet3ef6; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%222%22%2C%22first_id%22%3A%2218df3b55cd5173e-0d09555913fe9-26001b51-2073600-18df3b55cd61ab2%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E5%BC%95%E8%8D%90%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%20Did%20not%20take%20to%20the%20value%20%22%2C%22%24latest_referrer%22%3A%22https%3A%2F%2Fcmnm66.feishu.cn%2F%22%7D%2C%22%24device_id%22%3A%2218df3b55cd5173e-0d09555913fe9-26001b51-2073600-18df3b55cd61ab2%22%7D; _ga_RCPQ42QGB3=GS1.1.1713429078.107.1.1713430218.0.0.0; SERVERID=5f2c27a2826e61a65f5771b981490dee|1713430219|1713429077; SERVERCORSID=5f2c27a2826e61a65f5771b981490dee|1713430219|1713429077' \
  -H 'origin: https://sara-test.growknows.cn' \
  -H 'pragma: no-cache' \
  -H 'referer: https://sara-test.growknows.cn/' \
  -H 'sec-ch-ua: "Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-origin' \
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36' \
  --data-raw '{"name":"文生图01","summary":"文生图01文生图01","money":0,"sort":0,"logo":"https://minio-test.growknows.cn/aigc-dev/2024/03/25/cinematic_1317125d39884237b3ad30f6eb153461.jpg","categoryId":"1","templateId":"1772081536215752705","config":"[]","exampleText":"","docSourceAuth":"{\"id\":\"\",\"name\":\"\",\"permissions\":[]}"}'
    """
    print(ImportApi.from_data())
