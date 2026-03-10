# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: HTTP 模块统一入口 —— 客户端管理 + API 聚合
# @Time   : 2024-09-12 18:08
# @Author : 毛鹏
from mangoui.widgets.network import BaseHttpClient

from src.enums.system_enum import ClientTypeEnum
from src.tools.set_config import SetConfig


class AuthManager:
    """Token 管理器，全局维护鉴权状态"""

    def __init__(self):
        self.token: str | None = None

    def set_token(self, token: str):
        self.token = token

    def clear_token(self):
        self.token = None

    def get_headers(self) -> dict:
        headers = {'Source-Type': str(ClientTypeEnum.ACTUATOR.value)}
        if self.token:
            headers['Authorization'] = self.token
        return headers


# ── 全局单例 ──────────────────────────────────────────────────────────────────

auth_manager = AuthManager()

_client: BaseHttpClient = BaseHttpClient()


def get_client() -> BaseHttpClient:
    """获取全局共享的 HTTP 客户端"""
    return _client


def reinit_client():
    """base_url / token 变更后重新初始化客户端（登录成功后调用）"""
    global _client
    _client = BaseHttpClient(
        base_url=SetConfig.get_host() or '',
        headers=auth_manager.get_headers(),
    )


# ── API 聚合器 ────────────────────────────────────────────────────────────────

from src.network.http.apis.system import SystemApi  # noqa: E402
from src.network.http.apis.user import UserApi      # noqa: E402


class _HTTP:
    """API 聚合器（全局单例，通过 ``HTTP`` 访问）

    用法::

        from src.network import HTTP

        await HTTP.system.login(username, password)
        await HTTP.system.download_file('xxx.zip')
        await HTTP.system.upload_file(path, name)
        await HTTP.system.user_register(data)

        await HTTP.user.get_userinfo(user_id)
        await HTTP.user.get_user_info(1, 20)
    """

    def __init__(self):
        self._rebuild_apis()

    def _rebuild_apis(self):
        client = get_client()
        self.system = SystemApi(client, auth_manager)
        self.user = UserApi(client, auth_manager)

    def refresh(self):
        """token / base_url 变更后调用，重建所有 API 实例"""
        reinit_client()
        self._rebuild_apis()


# 全局单例
HTTP = _HTTP()
