# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: HTTP 模块统一入口 —— 客户端管理 + API 聚合
# @Time   : 2024-09-12 18:08
# @Author : 毛鹏
from src.network.http.apis.base import BaseHttpClient

from mangotools.enums import ClientTypeEnum
from src.tools.set_config import SetConfig
from src.tools.log_collector import log


def get_api_base_url() -> str:
    host = (SetConfig.get_host() or '').rstrip('/')
    if not host:
        return ''
    if host.endswith('/api'):
        return f'{host}/'
    return f'{host}/api/'


class AuthManager:
    """Token 管理器，全局维护鉴权状态"""

    def __init__(self):
        self.token: str | None = None

    def set_token(self, token: str):
        if isinstance(token, bytes):
            token = token.decode()
        if isinstance(token, str) and token.startswith("b'") and token.endswith("'"):
            token = token[2:-1]
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

_client: BaseHttpClient = BaseHttpClient(logger=log)
_api_base_url: str | None = None


def get_client() -> BaseHttpClient:
    """获取全局共享的 HTTP 客户端"""
    return _client


def set_api_base_url(base_url: str | None):
    global _api_base_url
    _api_base_url = base_url


def reinit_client():
    """base_url / token 变更后重新初始化客户端（登录成功后调用）"""
    global _client
    _client = BaseHttpClient(
        base_url=_api_base_url or get_api_base_url(),
        headers=auth_manager.get_headers(),
        proxy=SetConfig.get_proxy_url(),
        logger=log
    )


# ── API 聚合器 ────────────────────────────────────────────────────────────────

from src.network.http.apis.system import SystemApi  # noqa: E402
from src.network.http.apis.user import UserApi      # noqa: E402
from src.network.http.apis.actuator_tasks import ActuatorTaskApi  # noqa: E402
from src.network.http.apis.ui_element import UiElementApi  # noqa: E402
from src.network.http.apis.ui_page_step import UiPageStepApi  # noqa: E402
from src.network.http.apis.data_source import DataSourceApi  # noqa: E402
from src.network.http.apis.perf import PerfApi  # noqa: E402


class _HTTP:
    """API 聚合器（全局单例，通过 ``HTTP`` 访问）

    用法::

        from src.network import HTTP

        await HTTP.system.login(username, password)
        await HTTP.system.download_file_by_id(1)
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
        self.actuator_tasks = ActuatorTaskApi(client, auth_manager)
        self.ui_element = UiElementApi(client, auth_manager)
        self.ui_page_step = UiPageStepApi(client, auth_manager)
        self.data_source = DataSourceApi(client, auth_manager)
        self.perf = PerfApi(client, auth_manager)

    def refresh(self):
        """token / base_url 变更后调用，重建所有 API 实例"""
        reinit_client()
        self._rebuild_apis()


# 全局单例
HTTP = _HTTP()
