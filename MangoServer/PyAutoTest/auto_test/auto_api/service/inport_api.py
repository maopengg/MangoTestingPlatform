# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-04-18 16:29
# @Author : 毛鹏
from urllib.parse import urlparse, parse_qs

import uncurl
from uncurl.api import ParsedContext


class ImportApi:
    def curl_import(self, curl_command: str):
        try:
            print(uncurl.parse(curl_command))
        except Exception as error:
            print(error)
        r: ParsedContext = uncurl.parse_context(curl_command)
        host, path, query_params = self.url(r.url)
        from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoCRUD
        return ApiInfoCRUD.inside_post({
            'url': path,
            'method': r.method,
            'header': dict(r.headers),
            'params': query_params,
            'data': None,
            'json': r.data
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
    print(ImportApi.curl_import(d))
