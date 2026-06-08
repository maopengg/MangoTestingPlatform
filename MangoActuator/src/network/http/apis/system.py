# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 系统级接口 —— 登录 / 注册 / 文件上传下载
# @Time   : 2023-08-28 21:23
# @Author : 毛鹏
import asyncio
import os.path
import traceback
from urllib.parse import urljoin, urlparse

from mangotools.data_processor import EncryptionTool

from src.enums.system_enum import ClientTypeEnum
from src.exceptions import (
    ERROR_MSG_0003, ERROR_MSG_0004, ERROR_MSG_0007, ERROR_MSG_0026,
    ToolsError,
)
from src.models.socket_model import ResponseModel
from src.network.http.apis.base import BaseApi
from src.settings import settings
from src.tools import project_dir
from src.tools.log_collector import log
from src.tools.set_config import SetConfig


class SystemApi(BaseApi):
    """系统级接口：登录、注册、文件上传/下载

    继承 BaseApi，所有请求统一走 self.client。
    login / download_file 使用 self.client.raw_request()（完整 URL，不依赖 base_url）。
    所有方法均返回 ResponseModel。
    """

    @staticmethod
    def _server_root_url() -> str:
        base_url = (SetConfig.get_host() or '').rstrip('/')
        if base_url.endswith('/api'):
            base_url = base_url[:-4]
        return f'{base_url}/' if base_url else ''

    @classmethod
    def _auth_base_urls(cls) -> list[str]:
        server_root = cls._server_root_url()
        if not server_root:
            return ['']
        return [server_root, urljoin(server_root, 'api/')]

    @classmethod
    def _absolute_download_url(cls, download_url: str) -> str:
        parsed_url = urlparse(download_url)
        if parsed_url.scheme and parsed_url.netloc:
            return download_url
        return urljoin(cls._server_root_url(), download_url)

    @staticmethod
    def _select_file_data(file_list: list[dict], file_name: str) -> dict | None:
        for file_data in file_list:
            if file_data.get('name') == file_name:
                return file_data
        return file_list[0] if file_list else None

    async def get_config_value(self, key: str):
        resp = await self.client.get(
            'system/cache/data/key/value',
            params={'key': key},
            headers=self._headers(),
        )
        return resp.get('data') if isinstance(resp, dict) else None

    async def refresh_runtime_config(self):
        from src.services.runtime_config import AiRuntimeConfig, set_ai_config

        def is_enabled(value) -> bool:
            return value in (True, 'true', 'True', '1', 1)

        async def get_value(key: str, default=None):
            try:
                value = await self.get_config_value(key)
            except Exception as error:
                log.error(f'获取系统配置失败，key={key}，错误：{error}')
                return default
            return default if value is None else value

        timeout = await get_value('AI_TIMEOUT', 60)
        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            timeout = 60
        set_ai_config(AiRuntimeConfig(
            locator_enabled=is_enabled(await get_value('AI_UI_LOCATOR_ENABLED', 0)),
            provider_type=await get_value('AI_PROVIDER_TYPE', 'openai_compatible'),
            api_key=await get_value('AI_API_KEY', None),
            base_url=await get_value('AI_BASE_URL', 'https://api.deepseek.com'),
            model=await get_value('AI_MODEL', 'deepseek-chat'),
            timeout=timeout,
        ))

    # ── 文件 ──────────────────────────────────────────────────────────────────

    async def download_file(self, file_name: str):
        """从服务端下载文件到本地上传目录"""
        try:
            file_resp = await self.client.get(
                'system/file',
                params={'name': file_name},
                headers=self._headers(),
            )
            file_response = ResponseModel(**file_resp) if isinstance(file_resp, dict) else file_resp
            file_list = file_response.data if isinstance(file_response.data, list) else []
            file_data = self._select_file_data(file_list, file_name)
            if not file_data or not file_data.get('id'):
                raise ToolsError(*ERROR_MSG_0026)

            url_resp = await self.client.get(
                'system/file/download/url',
                params={'id': file_data.get('id')},
                headers=self._headers(),
            )
            url_response = ResponseModel(**url_resp) if isinstance(url_resp, dict) else url_resp
            if not isinstance(url_response.data, str) or not url_response.data:
                raise ToolsError(*ERROR_MSG_0026)

            url = self._absolute_download_url(url_response.data)
            content, status_code = await self.client.raw_request(
                'GET', url, return_json=False, return_bytes=True
            )
            if status_code != 200:
                log.error(f'url:{url}, status_code:{status_code}')
                raise ToolsError(*ERROR_MSG_0004, value=(url,))
            with open(os.path.join(project_dir.upload(), file_name), 'wb') as f:
                f.write(content)
        except FileNotFoundError:
            raise ToolsError(*ERROR_MSG_0007)
        except ToolsError:
            raise
        except Exception:
            raise ToolsError(*ERROR_MSG_0003)

    async def upload_file(self, file_path: str, file_name: str, retry: int = 0):
        """上传截图文件到服务端"""
        data = {
            'type': ClientTypeEnum.ACTUATOR.value,
            'name': file_name,
            'screenshot': True,
            'file_path': os.path.join('mango-file', 'failed_screenshot', file_name),
        }
        files = [
            ('failed_screenshot', (file_name, open(file_path, 'rb'), 'application/octet-stream'))
        ]
        try:
            resp = await self.client.post(
                '/system/file',
                headers=self._headers(),
                data=data,
                files=files,
            )
            response = ResponseModel(**resp) if isinstance(resp, dict) else resp
        except Exception as e:
            log.error(f'上传文件异常：{e}')
            return None

        if response.code == 200:
            return response.data
        elif response.code == 1004:
            log.error(f'上传文件报错，请管理员检查，响应结果：{response.model_dump()}')
            return None
        else:
            if retry >= 1:
                return None
            await self.login(SetConfig.get_username(), SetConfig.get_password())
            return await self.upload_file(file_path, file_name, retry + 1)

    # ── 认证 ──────────────────────────────────────────────────────────────────

    async def login(
        self,
        username: str = None,
        password: str = None,
        retry: int = 0,
        is_retry: bool = False,
    ) -> ResponseModel:
        """登录：成功后自动写入 token 并重建全局 HTTP 客户端，返回 ResponseModel"""
        try:
            response = None
            last_error = None
            api_base_url = None
            for auth_base_url in self._auth_base_urls():
                try:
                    resp = await self.client.raw_request(
                        'POST',
                        urljoin(auth_base_url, 'login'),
                        data={
                            'username': username,
                            'password': EncryptionTool.md5_32_small(password),
                            'version': settings.SETTINGS.get('version'),
                        },
                        return_json=True,
                    )
                    response = ResponseModel(**resp)
                    api_base_url = auth_base_url
                    break
                except Exception as error:
                    last_error = error
            if response is None:
                raise last_error

            if response.data and response.code == 200:
                token = response.data.get('token') if isinstance(response.data, dict) else None
                if token:
                    self.auth.set_token(token)
                    # 重建全局客户端，登录窗口随后调用 HTTP.refresh() 更新引用
                    from src.network.http import reinit_client, set_api_base_url
                    set_api_base_url(api_base_url)
                    reinit_client()
                log.info(response.model_dump())
                return response
            if is_retry and retry < 100:
                await asyncio.sleep(3)
                return await self.login(username, password, retry + 1, is_retry)
            return response
        except Exception as error:
            if settings.IS_OPEN and retry < 100:
                await asyncio.sleep(3)
                log.info(f'开始登录重试：{retry}，{error}')
                return await self.login(username, password, retry + 1, is_retry)
            log.error(f'登录异常：{traceback.format_exc()}')
            return ResponseModel(code=-300, msg=str(error))

    async def user_register(self, json_data: dict) -> ResponseModel:
        """用户注册，返回 ResponseModel"""
        try:
            last_error = None
            for auth_base_url in self._auth_base_urls():
                try:
                    resp = await self.client.raw_request(
                        'POST',
                        urljoin(auth_base_url, 'register'),
                        json=json_data,
                        return_json=True,
                    )
                    return ResponseModel(**resp) if isinstance(resp, dict) else resp
                except Exception as error:
                    last_error = error
            raise last_error
        except Exception as e:
            return ResponseModel(code=-300, msg=str(e))
