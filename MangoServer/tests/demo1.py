# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-03-25 22:22
# @Author : 毛鹏
from typing import Optional, Union, Dict, List, Any
from pydantic import BaseModel, HttpUrl
import json
from pathlib import Path




class RequestModel(BaseModel):
    method: str  # 不应为可选，必须有方法
    url: HttpUrl  # 使用HttpUrl自动验证URL格式
    headers: Optional[dict[str, str]] = None
    params: Optional[Union[Dict[str, Any], str]] = None  # 通常为字典，但也支持字符串
    data: Optional[Union[Dict[str, Any], str, bytes]] = None  # 支持多种格式
    json: Optional[Any] = None  # 可以是任何可JSON序列化的Python对象
    files: dict | list[dict[str, Any]] = None
    auth: Optional[Union[tuple, Dict[str, str]]] = None  # 认证信息
    timeout: Optional[Union[float, tuple]] = None  # 超时设置
    allow_redirects: Optional[bool] = None  # 是否允许重定向
    verify: Optional[Union[bool, str]] = None  # SSL验证

    def prepare_request(self):
        """准备请求参数，将模型转换为requests库接受的格式"""
        request_args = {
            'method': self.method,
            'url': str(self.url),
        }

        if self.headers:
            request_args['headers'] = self.headers

        if isinstance(self.params, dict):
            request_args['params'] = self.params
        elif self.params:
            request_args['params'] = json.loads(self.params)

        if isinstance(self.data, dict):
            request_args['data'] = self.data
        elif self.data:
            request_args['data'] = self.data

        if self.json is not None:
            request_args['json'] = self.json

        if self.files:
            if isinstance(self.files, list):
                request_args['files'] = [f.dict() for f in self.files]
            else:
                request_args['files'] = self.files.dict()

        # 添加其他可选参数
        for field in ['auth', 'timeout', 'allow_redirects', 'verify']:
            if getattr(self, field) is not None:
                request_args[field] = getattr(self, field)

        return request_args