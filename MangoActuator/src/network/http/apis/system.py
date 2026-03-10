# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 系统级接口 —— 登录 / 注册 / 文件上传下载
# @Time   : 2023-08-28 21:23
# @Author : 毛鹏
import asyncio
import os.path
import traceback
from urllib.parse import urljoin

from mangotools.data_processor import EncryptionTool

from src.enums.system_enum import ClientTypeEnum
from src.exceptions import (
    ERROR_MSG_0002, ERROR_MSG_0003, ERROR_MSG_0004, ERROR_MSG_0007,
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

    # ── 文件 ──────────────────────────────────────────────────────────────────

    async def download_file(self, file_name: str):
        """从服务端下载文件到本地上传目录"""
        if SetConfig.get_is_minio():
            minio_host = SetConfig.get_minio_url()  # type: ignore
            if minio_host is None:
                raise ToolsError(*ERROR_MSG_0002)
        else:
            minio_host = SetConfig.get_host()
        url = urljoin(minio_host, f'/mango-file/test_file/{file_name}')
        try:
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
            base_url = SetConfig.get_host() or ''
            resp = await self.client.raw_request(
                'POST',
                urljoin(base_url, '/login'),
                data={
                    'username': username,
                    'password': EncryptionTool.md5_32_small(password),
                    'version': settings.SETTINGS.get('version'),
                },
                return_json=True,
            )
            response = ResponseModel(**resp)
            if response.data and response.code == 200:
                token = response.data.get('token') if isinstance(response.data, dict) else None
                if token:
                    self.auth.set_token(token)
                    # 重建全局客户端，登录窗口随后调用 HTTP.refresh() 更新引用
                    from src.network.http import reinit_client
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
            resp = await self.client.post('/register', json=json_data)
            return ResponseModel(**resp) if isinstance(resp, dict) else resp
        except Exception as e:
            return ResponseModel(code=-300, msg=str(e))
