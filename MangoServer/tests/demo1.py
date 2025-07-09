# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-03-25 22:22
# @Author : 毛鹏
from typing import Optional, Union, Dict, Any

from pydantic import BaseModel, HttpUrl


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


data = {'method': 'assert_cell_value',
        'actual': '{"文件路径":"D:\\GitCode\\MangoTestingPlatform\\MangoServer\\download\\20250319151528-yq-test03.xlsx","工作表":"sheet1"}',
        'expect': '{"单元格":"B2","预期值":"6414c5e50000000011023c12"}'}

import json

print(json.loads(data.get('actual')))
print(json.loads(data.get('expect')))
