# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-25 20:10
# @Author : 毛鹏

import os
from urllib.parse import urlparse

import requests
import time
from requests import Response
from requests.exceptions import *

from src.auto_test.auto_system.service.cache_data_value import CacheDataValue
from src.enums.system_enum import CacheDataKeyEnum
from src.exceptions import *
from src.models.api_model import RequestModel, ResponseModel
from src.tools import project_dir


class BaseRequest:

    def __init__(self, test_data):
        self.timeout = CacheDataValue.get_cache_value(CacheDataKeyEnum.API_TIMEOUT.name)
        self.test_data = test_data

    def http(self, request_data: RequestModel) -> ResponseModel:
        request_data.serialize()
        try:
            if request_data.file:
                log.api.debug(f'开始执行接口：{request_data.model_dump()}')
            else:
                log.api.debug(f'开始执行接口：{request_data.model_dump_json()}')
            s = time.time()
            response = requests.request(
                method=request_data.method,
                url=request_data.url,
                headers=request_data.headers,
                params=request_data.params,
                data=request_data.data,
                json=request_data.json,
                files=request_data.file,
                timeout=int(self.timeout),
                proxies={'http': None, 'https': None}
            )
            end = time.time() - s
        except ProxyError:
            raise ApiError(*ERROR_MSG_0001)
        except SSLError:
            raise ApiError(*ERROR_MSG_0001)
        except Timeout:
            raise ApiError(*ERROR_MSG_0037)
        except RequestException as error:
            log.api.error(f'接口请求时发生未知错误，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise ApiError(*ERROR_MSG_0002)
        if request_data.posterior_file:
            parsed_url = urlparse(request_data.url)
            file_name = os.path.basename(parsed_url.path)
            file_path = os.path.join(project_dir.download(), file_name)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            self.test_data.set_cache(request_data.posterior_file, file_path)
        else:
            file_path = ''
        try:
            response_json = response.json()
        except Exception:
            response_json = None
        response = ResponseModel(
            code=response.status_code,
            time=end,
            request_headers=request_data.headers,
            request_params=request_data.params,
            request_data=request_data.data,
            request_json=request_data.json,
            request_file=str(request_data.file) if request_data.file else None,
            headers=response.headers,
            json=response_json,
            text=file_path if request_data.posterior_file else response.text
        )

        log.api.debug(f'API响应数据：{response.model_dump_json()}')
        return response

    @classmethod
    def test_http(cls, request_data: RequestModel) -> Response:
        s = time.time()
        response = requests.request(
            method=request_data.method,
            url=request_data.url,
            headers=request_data.headers,
            params=request_data.params,
            data=request_data.data,
            json=request_data.json,
            files=request_data.file,
            timeout=int(30)
        )
        end = time.time() - s
        return response
