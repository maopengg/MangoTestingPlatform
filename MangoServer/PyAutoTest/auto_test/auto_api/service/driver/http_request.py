# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 封装请求
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import logging

import requests
import time
from requests import RequestException

from PyAutoTest.exceptions.api_exception import AgentError, UnknownError
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel

log = logging.getLogger('api')


class HTTPRequest:

    @classmethod
    def http(cls, request_data: RequestDataModel) -> ResponseDataModel:
        s = time.time()
        # if "/dev-api/business/workFlowInfo/remove" in request_data.url:
        #     print(request_data.dict())
        try:
            response = requests.request(
                method=request_data.method,
                url=request_data.url,
                headers=request_data.headers,
                params=request_data.params,
                data=request_data.data,
                json=request_data.json_data,
                files=request_data.file
            )
            end = time.time() - s
        except requests.exceptions.ProxyError:
            raise AgentError('系统代理出错，请检查系统代理')
        except RequestException as e:
            log.error(f'请求发生未知错误，请联系管理员检查！错误数据：{request_data.dict()}，报错内容：{e}')
            raise UnknownError('请求发生未知错误，请联系管理员检查！')
        try:
            response_json = response.json()
        except Exception:
            response_json = None
        return ResponseDataModel(
            url=response.url,
            method=request_data.method,
            headers=request_data.headers,
            params=request_data.params,
            data=request_data.data,
            json_data=request_data.json_data,
            file=str(request_data.file),
            status_code=response.status_code,
            response_time=end,
            response_headers=response.headers,
            response_json=response_json,
            response_text=response.text
        )


if __name__ == '__main__':
    data = {"method": "POST", "url": "https://app-test.growknows.cn/dev-api/business/template/add", "headers": {
        "Authorization": "eyJhbGciOiJIUzUxMiJ9.eyJhY2Nlc3NfdG9rZW4iOiJCZWFyZXIgdG9rZW46bG9naW5fdG9rZW5zOjE6MTphY2Nlc3NfdG9rZW46OWExNDdlMTMtYjYzMS00OGM1LWE4N2MtMTIyYWIyNDA5ZDI3IiwicmVmcmVzaF90b2tlbiI6IkJlYXJlciB0b2tlbjpsb2dpbl90b2tlbnM6MToxOnJlZnJlc2hfdG9rZW46eXg5OWNHbXBpVm5ucTdWQ1h1SFFiVmI5WmZaVVh5RVRxdjhLZ0htVnpSTk95WlpJV1lNVmltaFVwRHdSdnN0Y2hScTMyMGJoTHdueXNVMUhRVHFNUGZaSFdHNzc0OVNSeTBfS29haHptdzlXaWI2MlBOcFBFeHBXNTZHdHNBM1QiLCJhY2NvdW50X3R5cGUiOiJhZG1pbiIsInVzZXJfdHlwZSI6IjAwIiwidXNlcl9pZCI6MSwidXNlcl9uYW1lIjoiYWRtaW5AYWlnYy5jb20iLCJpc19sZXNzb3IiOiJZIiwiZW50ZXJwcmlzZV9pZCI6MSwiZW50ZXJwcmlzZV9uYW1lIjoiYWRtaW5pc3RyYXRvciIsInNvdXJjZV9uYW1lIjoic2xhdmUifQ.OcIo2ydTAlt8735-B5Eaw4fOb5meuS93O9ggqdyl96HLlsw1yWa-ZORNfu5lHjB3d_N8rvxGIUd5Uk6JfBTVyg",
        "Accept": "application/json, text/plain, */*", "Content-Type": "application/json"}, "params": None,
            "data": None, "json_data": {"template": {
            "logo": "https://minio-test.growknows.cn/aigc-dev/2024/01/23/主图-06_bcc2aaf54a754f6699aa72cecae3f553.jpg",
            "name": "api自动化测试模版", "type": "1", "detail": None, "summary": "api自动化测试模版", "categoryId": "1",
            "screenshot": None}, "templateFlowInfo": {"workFlowIds": None, "fromInputArr": [], "connectOutputArr": []}},
            "file": None}

    print(HTTPRequest.http(RequestDataModel(**data)).response_text)
"""
data 和 json 是 requests 库中用于发送 HTTP 请求体数据的两个参数。它们的最大区别在于数据格式和发送方式。

data 参数用于发送表单数据或者文件数据，它的值可以是一个字典对象或者一个文件对象。当请求体数据是表单数据时，
data 参数应该是一个字典对象，其中键值对表示表单字段和字段值。当请求体数据是文件数据时，data 参数应该是一个
文件对象，例如使用 open() 函数打开的文件对象。

json 参数用于发送 JSON 数据，它的值应该是一个 Python 对象。requests 库会自动将 Python 对象序列化为 
JSON 格式的字符串，并设置请求头的 Content-Type 为 application/json。服务器收到请求后会自动将 JSO
N 字符串反序列化为对应的数据类型。

因此，最大的区别在于数据格式和发送方式。如果需要发送表单数据或者文件数据，则应该使用 data 参数；如果需要发送 JSON 数据，则应该使用 json 参数。
"""
