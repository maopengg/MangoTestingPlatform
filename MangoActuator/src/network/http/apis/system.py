# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 系统级接口 —— 登录 / 注册 / 文件上传下载
# @Time   : 2023-08-28 21:23
# @Author : 毛鹏
from src.services.system_error_reporter import ActuatorSystemErrorReporter
import asyncio
import os.path
import traceback
from urllib.parse import urljoin, urlparse

import httpx
from mangotools.data_processor import EncryptionTool

from mangotools.enums import ClientTypeEnum
from src.exceptions import (
    ERROR_MSG_0003, ERROR_MSG_0004, ERROR_MSG_0007, ERROR_MSG_0026,
    ToolsError,
)
from src.models.socket_model import FileUploadResultModel, HttpApiResponse
from src.network.http.apis.base import ApiError as HttpApiError, BaseApi, BaseHttpClient
from src.settings import settings
from src.tools import project_dir
from src.tools.log_collector import log
from src.tools.set_config import SetConfig


def double_md5(value: str) -> str:
    first = EncryptionTool.md5_32_small(value)
    return EncryptionTool.md5_32_small(first)


class SystemApi(BaseApi):
    """系统级接口：登录、注册、文件上传/下载

    继承 BaseApi，所有请求统一走 self.client。
    login / download_file 使用 self.client.raw_request()（完整 URL，不依赖 base_url）。
    所有方法均返回 HttpApiResponse。
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
            return ['api/']
        return [urljoin(server_root, 'api/')]

    @classmethod
    def _absolute_download_url(cls, download_url: str) -> str:
        parsed_url = urlparse(download_url)
        if parsed_url.scheme and parsed_url.netloc:
            return download_url
        return urljoin(cls._server_root_url(), download_url)

    @staticmethod
    def _select_file_data_by_id(file_list: list[dict], file_id: int | str) -> dict | None:
        for file_data in file_list:
            if str(file_data.get('id')) == str(file_id):
                return file_data
        return file_list[0] if file_list else None

    async def get_config_value(self, key: str):
        resp = await self.client.get(
            'system/cache/data/key/value',
            params={'key': key},
            headers=self._headers(),
        )
        return resp.get('data') if isinstance(resp, dict) else None

    async def get_config_values(self, keys: list[str]) -> dict:
        resp = await self.client.get(
            'system/cache/data/key/value',
            params={'keys': ','.join(keys)},
            headers=self._headers(),
        )
        data = resp.get('data') if isinstance(resp, dict) else None
        return data if isinstance(data, dict) else {}

    async def refresh_runtime_config(self):
        from src.services.runtime_config import AiRuntimeConfig, set_ai_config

        config_keys = [
            'AI_TIMEOUT',
            'UI_FIXED_LOCATOR_RETRY_SECONDS',
            'UI_SMART_LOCATOR_TIMEOUT_SECONDS',
            'UI_VISUAL_LOCATOR_ENABLED',
            'AI_PROVIDER_TYPE',
            'AI_API_KEY',
            'AI_BASE_URL',
            'AI_MODEL',
            'AI_VISION_USE_SEPARATE_CONFIG',
            'AI_VISION_PROVIDER_TYPE',
            'AI_VISION_API_KEY',
            'AI_VISION_BASE_URL',
            'AI_VISION_MODEL',
            'AI_VISION_TIMEOUT',
            'AI_VISION_PROXY_URL',
            'EXECUTOR_MAX_CONCURRENT_TASKS',
            'EXECUTOR_MEMORY_THRESHOLD_PERCENT',
            'UI_LIVE_WORKSPACE_MAX_USERS',
            'PERF_EXECUTOR_MAX_CONCURRENT_RUNS',
        ]
        try:
            config_values = await self.get_config_values(config_keys)
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'network/http/apis/system:refresh_runtime_config')
            log.error(f'批量获取系统配置失败，将回退单项获取，错误：{error}')
            config_values = {}

        async def get_value(key: str, default=None):
            if key in config_values:
                return default if config_values.get(key) is None else config_values.get(key)
            try:
                value = await self.get_config_value(key)
            except Exception as error:
                await ActuatorSystemErrorReporter.report(error, 'network/http/apis/system:get_value')
                log.error(f'获取系统配置失败，key={key}，错误：{error}')
                return default
            return default if value is None else value

        timeout = await get_value('AI_TIMEOUT', 60)
        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            timeout = 60
        # Keep the configured provider timeout intact here. Element healing and
        # page-step healing apply their own independent execution-budget caps.
        timeout = max(1, min(timeout, 3600))
        def bounded_int(value, default, minimum, maximum):
            try:
                return max(minimum, min(maximum, int(value)))
            except (TypeError, ValueError):
                return default

        def as_bool(value):
            if isinstance(value, str):
                return value.strip().lower() in {'1', 'true', 'yes', 'on'}
            return bool(value)

        fixed_retry_seconds = bounded_int(
            await get_value('UI_FIXED_LOCATOR_RETRY_SECONDS', 10), 10, 0, 60,
        )
        smart_timeout_seconds = bounded_int(
            await get_value('UI_SMART_LOCATOR_TIMEOUT_SECONDS', 30), 30, 5, 120,
        )
        provider_type = await get_value('AI_PROVIDER_TYPE', 'openai_compatible')
        api_key = await get_value('AI_API_KEY', None)
        base_url = await get_value('AI_BASE_URL', 'https://api.deepseek.com')
        model = await get_value('AI_MODEL', 'deepseek-chat')
        use_separate_vision_config = as_bool(
            await get_value('AI_VISION_USE_SEPARATE_CONFIG', False)
        )
        if use_separate_vision_config:
            vision_provider_type = await get_value(
                'AI_VISION_PROVIDER_TYPE', 'openai_compatible',
            )
            vision_api_key = await get_value('AI_VISION_API_KEY', None)
            vision_base_url = await get_value('AI_VISION_BASE_URL', None)
            vision_model = await get_value('AI_VISION_MODEL', None)
            vision_proxy_url = await get_value('AI_VISION_PROXY_URL', None)
        else:
            vision_provider_type = provider_type
            vision_api_key = api_key
            vision_base_url = base_url
            vision_model = model
            vision_proxy_url = None
        ai_config = AiRuntimeConfig(
            locator_enabled=True,
            locator_mode=2,
            locator_semantic_strength=0,
            fixed_locator_retry_seconds=fixed_retry_seconds,
            smart_locator_timeout_seconds=smart_timeout_seconds,
            visual_locator_enabled=as_bool(
                await get_value('UI_VISUAL_LOCATOR_ENABLED', False)
            ),
            provider_type=provider_type,
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
            vision_provider_type=vision_provider_type,
            vision_api_key=vision_api_key,
            vision_base_url=vision_base_url,
            vision_model=vision_model,
            vision_timeout=bounded_int(
                await get_value('AI_VISION_TIMEOUT', 30), 30, 1, 120,
            ),
            vision_proxy_url=vision_proxy_url,
        )
        set_ai_config(ai_config)
        from src.services.executor_task_worker import ExecutorTaskWorker
        from src.services.ui.live_workspace import UiLiveWorkspaceManager

        ExecutorTaskWorker.MAX_CONCURRENT_TASKS = bounded_int(
            await get_value('EXECUTOR_MAX_CONCURRENT_TASKS', 5), 5, 1, 100,
        )
        settings.MEMORY_THRESHOLD = bounded_int(
            await get_value('EXECUTOR_MEMORY_THRESHOLD_PERCENT', 100), 100, 50, 100,
        )
        UiLiveWorkspaceManager.MAX_USER_SLOTS = bounded_int(
            await get_value('UI_LIVE_WORKSPACE_MAX_USERS', 5), 5, 1, 100,
        )
        os.environ['MANGO_CAPACITY_PERF'] = str(bounded_int(
            await get_value('PERF_EXECUTOR_MAX_CONCURRENT_RUNS', 5), 5, 1, 100,
        ))
        from src.services.capabilities import CapabilityRegistry

        CapabilityRegistry.invalidate()
        log.info(
            '[AI定位配置] '
            f'固定定位等待={ai_config.fixed_locator_retry_seconds}s, '
            f'智能定位超时={ai_config.smart_locator_timeout_seconds}s, '
            f'供应商={ai_config.provider_type or "-"}, '
            f'模型={ai_config.model or "-"}, '
            f'超时={ai_config.timeout}s, '
            f'视觉兜底={"开启" if ai_config.visual_locator_enabled else "关闭"}, '
            f'视觉配置源={"独立" if use_separate_vision_config else "主AI"}, '
            f'视觉模型={ai_config.vision_model or "-"}'
        )

    # ── 文件 ──────────────────────────────────────────────────────────────────

    async def download_file_by_id(self, file_id: int | str) -> str:
        """按测试文件 ID 从服务端下载文件到本地上传目录，并返回本地路径。"""
        try:
            file_resp = await self.client.get(
                'system/file',
                params={'id': file_id},
                headers=self._headers(),
            )
            file_response = HttpApiResponse(**file_resp) if isinstance(file_resp, dict) else file_resp
            file_list = file_response.data if isinstance(file_response.data, list) else []
            file_data = self._select_file_data_by_id(file_list, file_id)
            if not file_data or not file_data.get('id') or not file_data.get('name'):
                raise ToolsError(*ERROR_MSG_0026)

            url_resp = await self.client.get(
                'system/file/download/url',
                params={'id': file_data.get('id')},
                headers=self._headers(),
            )
            url_response = HttpApiResponse(**url_resp) if isinstance(url_resp, dict) else url_resp
            if not isinstance(url_response.data, str) or not url_response.data:
                raise ToolsError(*ERROR_MSG_0026)

            url = self._absolute_download_url(url_response.data)
            content, status_code = await self.client.raw_request(
                'GET', url, return_json=False, return_bytes=True
            )
            if status_code != 200:
                log.error(f'url:{url}, status_code:{status_code}')
                raise ToolsError(*ERROR_MSG_0004, value=(url,))
            file_path = os.path.join(project_dir.upload(), file_data.get('name'))
            with open(file_path, 'wb') as f:
                f.write(content)
            return file_path
        except FileNotFoundError:
            raise ToolsError(*ERROR_MSG_0007)
        except ToolsError:
            raise
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'network/http/apis/system:download_file_by_id')
            raise ToolsError(*ERROR_MSG_0003) from error

    async def download_file_by_id_isolated(self, file_id: int | str) -> str:
        """使用当前事件循环专属客户端下载测试文件。

        测试数据函数运行在独立线程的事件循环中，不能复用执行器主循环持有的
        ``httpx.AsyncClient``，否则 AnyIO 会报客户端资源绑定到其他事件循环。
        """
        isolated_client = BaseHttpClient(
            base_url=self.client.base_url,
            headers=self._headers(),
            proxy=self.client.proxy,
            logger=log,
        )
        try:
            isolated_api = SystemApi(isolated_client, self.auth)
            return await isolated_api.download_file_by_id(file_id)
        finally:
            await isolated_client.close()

    async def upload_file(
            self,
            file_path: str,
            file_name: str,
            retry: int = 0,
            file_field: str = 'failed_screenshot',
            file_dir: str = 'uitest/screenshot',
            timeout: int | None = None,
    ) -> FileUploadResultModel:
        """上传执行产物到服务端对象存储"""
        data = {
            'type': ClientTypeEnum.ACTUATOR.value,
            'name': file_name,
            'screenshot': True,
            'file_field': file_field,
            'file_dir': file_dir,
            'file_path': os.path.join('mango-file', file_dir, file_name),
        }
        try:
            with open(file_path, 'rb') as file_obj:
                files = [
                    (file_field, (file_name, file_obj, 'application/octet-stream'))
                ]
                resp = await self.client.post(
                    '/system/file',
                    headers=self._headers(),
                    data=data,
                    files=files,
                    timeout=timeout or self.client.timeout,
                )
            response = HttpApiResponse(**resp) if isinstance(resp, dict) else resp
        except Exception as e:
            await ActuatorSystemErrorReporter.report(e, 'network/http/apis/system:upload_file')
            if isinstance(e, HttpApiError) and e.status_code in {401, 403}:
                if retry < 2 and await self._refresh_upload_auth():
                    return await self.upload_file(
                        file_path,
                        file_name,
                        retry + 1,
                        file_field,
                        file_dir,
                        timeout,
                    )
                log.error(f'上传文件鉴权失败，HTTP状态码：{e.status_code}')
                return self._upload_exception_result(e)
            if retry < 2:
                delay = retry + 1
                log.warning(
                    f'上传文件异常，将在{delay}秒后重试：'
                    f'{self._upload_exception_log_detail(e)}'
                )
                await asyncio.sleep(delay)
                return await self.upload_file(
                    file_path,
                    file_name,
                    retry + 1,
                    file_field,
                    file_dir,
                    timeout,
                )
            log.error(f'上传文件连续失败，已停止重试：{self._upload_exception_log_detail(e)}')
            return self._upload_exception_result(e)

        if response.code == 200:
            if isinstance(response.data, str) and response.data.strip():
                return FileUploadResultModel(success=True, path=response.data)
            log.error(f'上传文件响应缺少文件路径，响应结果：{response.model_dump()}')
            return FileUploadResultModel(
                success=False,
                error_type='invalid_response',
                error_message='后端已接收上传请求，但响应中缺少文件路径',
            )
        elif response.code == 1004:
            log.error(f'上传文件报错，请管理员检查，响应结果：{response.model_dump()}')
            return FileUploadResultModel(
                success=False,
                error_type='storage',
                error_message=response.msg or '后端文件存储保存失败',
            )
        elif response.code not in {401, 403}:
            return FileUploadResultModel(
                success=False,
                error_type='server_response',
                error_message=f'后端拒绝上传：{response.msg or "未知错误"}（业务码：{response.code}）',
            )
        else:
            if retry >= 2 or not await self._refresh_upload_auth():
                return FileUploadResultModel(
                    success=False,
                    error_type='authentication',
                    error_message='上传鉴权已失效，执行器重新登录失败',
                )
            return await self.upload_file(file_path, file_name, retry + 1, file_field, file_dir, timeout)

    async def _refresh_upload_auth(self) -> bool:
        try:
            login_result = await self.login(SetConfig.get_username(), SetConfig.get_login_password())
            if login_result.code != 200 or not login_result.data:
                return False
            from src.network.http import get_client
            self.client = get_client()
            return True
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'network/http/apis/system:_refresh_upload_auth')
            log.error(f'上传文件重新登录异常：{type(error).__name__}')
            return False

    @staticmethod
    def _upload_exception_log_detail(error: Exception) -> str:
        if isinstance(error, HttpApiError):
            return f'HTTP请求失败，状态码：{error.status_code or "未知"}'
        return f'{type(error).__name__}: {error}'

    @staticmethod
    def _upload_exception_result(error: Exception) -> FileUploadResultModel:
        if isinstance(error, FileNotFoundError):
            return FileUploadResultModel(
                success=False,
                error_type='local_file',
                error_message='执行器本地截图文件不存在或无法读取',
            )
        if isinstance(error, httpx.TimeoutException):
            return FileUploadResultModel(
                success=False,
                error_type='timeout',
                error_message='调用后端截图上传接口超时',
            )
        if isinstance(error, httpx.ConnectError):
            return FileUploadResultModel(
                success=False,
                error_type='connection',
                error_message='无法连接测试平台后端，截图未上传',
            )
        if isinstance(error, HttpApiError):
            status_code = error.status_code
            if status_code in {401, 403}:
                message = '后端拒绝截图上传，请检查执行器登录状态及上传权限'
                error_type = 'authentication'
            elif status_code == 404:
                message = '后端截图上传接口不存在，请检查执行器与平台版本是否一致'
                error_type = 'endpoint'
            elif status_code == 413:
                message = '后端拒绝截图上传，文件大小超过接口限制'
                error_type = 'file_size'
            elif status_code and status_code >= 500:
                message = f'后端截图上传服务异常（HTTP {status_code}）'
                error_type = 'server'
            else:
                message = f'后端拒绝截图上传（HTTP {status_code or "未知"}）'
                error_type = 'http'
            return FileUploadResultModel(
                success=False,
                error_type=error_type,
                error_message=message,
            )
        return FileUploadResultModel(
            success=False,
            error_type='request',
            error_message=f'调用后端截图上传接口异常（{type(error).__name__}）',
        )

    async def upload_video_file(self, file_path: str, file_name: str, retry: int = 0) -> FileUploadResultModel:
        return await self.upload_file(
            file_path,
            file_name,
            retry=retry,
            file_field='execution_video',
            file_dir='uitest/videos',
        )

    # ── 认证 ──────────────────────────────────────────────────────────────────

    async def login(
        self,
        username: str = None,
        password: str = None,
        retry: int = 0,
        is_retry: bool = False,
    ) -> HttpApiResponse:
        """登录：成功后自动写入 token 并重建全局 HTTP 客户端，返回 HttpApiResponse"""
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
                            'password': double_md5(password),
                            'version': settings.SETTINGS.get('version'),
                            'type': ClientTypeEnum.ACTUATOR.value,
                        },
                        headers={'Source-Type': str(ClientTypeEnum.ACTUATOR.value)},
                        return_json=True,
                    )
                    response = HttpApiResponse(**resp)
                    api_base_url = auth_base_url
                    break
                except Exception as error:
                    await ActuatorSystemErrorReporter.report(error, 'network/http/apis/system:login')
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
                log.info(f'执行器登录成功，账号：{username or SetConfig.get_username()}，服务地址：{api_base_url}')
                return response
            if is_retry and retry < 100:
                await asyncio.sleep(3)
                return await self.login(username, password, retry + 1, is_retry)
            return response
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'network/http/apis/system:login')
            if settings.IS_OPEN and retry < 100:
                await asyncio.sleep(3)
                log.info(f'开始登录重试：{retry}，{error}')
                return await self.login(username, password, retry + 1, is_retry)
            log.error(f'登录异常：{traceback.format_exc()}')
            return HttpApiResponse(code=-300, msg=str(error))

    async def user_register(self, json_data: dict) -> HttpApiResponse:
        """用户注册，返回 HttpApiResponse"""
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
                    return HttpApiResponse(**resp) if isinstance(resp, dict) else resp
                except Exception as error:
                    await ActuatorSystemErrorReporter.report(error, 'network/http/apis/system:user_register')
                    last_error = error
            raise last_error
        except Exception as e:
            await ActuatorSystemErrorReporter.report(e, 'network/http/apis/system:user_register')
            return HttpApiResponse(code=-300, msg=str(e))
