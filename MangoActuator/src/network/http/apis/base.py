# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API 基类 —— 持有客户端与鉴权信息，子类统一通过 self 访问
# @Time   : 2024-09-12
# @Author : 毛鹏
from mangoui.widgets.network import BaseHttpClient


class AuthManager:
    """仅用于类型提示，实际单例在 http/__init__.py 中定义"""
    def get_headers(self) -> dict: ...


class BaseApi:
    """所有业务 API 的基类

    self.client  — 带 base_url + token 的全局客户端，所有请求统一走这里
    self.auth    — 鉴权管理器，通过 self._headers() 注入请求头
    """

    def __init__(self, client: BaseHttpClient, auth):
        self.client = client
        self.auth = auth

    def _headers(self, extra: dict | None = None) -> dict:
        """获取鉴权头，可追加额外自定义头"""
        headers = self.auth.get_headers()
        if extra:
            headers.update(extra)
        return headers
