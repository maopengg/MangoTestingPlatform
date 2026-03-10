# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 用户相关接口
# @Time   : 2024-09-21 11:19
# @Author : 毛鹏
import json

from src.models.socket_model import ResponseModel
from src.models.user_model import UserModel
from src.network.http.apis.base import BaseApi


class UserApi(BaseApi):
    """用户相关接口，继承 BaseApi 自动携带鉴权头，所有方法返回 ResponseModel"""

    _url = 'user/info'

    async def get_user_info(self, page: int, page_size: int, params: dict = None) -> ResponseModel:
        _params = {'page': page, 'pageSize': page_size}
        if params:
            _params.update(params)
        resp = await self.client.get(self._url, params=_params, headers=self._headers())
        return ResponseModel(**resp) if isinstance(resp, dict) else resp

    async def post_user_info(self, json_data: dict) -> ResponseModel:
        resp = await self.client.post(self._url, json=json_data, headers=self._headers())
        return ResponseModel(**resp) if isinstance(resp, dict) else resp

    async def put_user_info(self, json_data: dict) -> ResponseModel:
        if json_data.get('mailbox') and isinstance(json_data.get('mailbox'), str):
            json_data['mailbox'] = json.loads(json_data['mailbox'])
        for k, v in json_data.items():
            if isinstance(v, dict) and v.get('id'):
                json_data[k] = v['id']
        resp = await self.client.put(self._url, json=json_data, headers=self._headers())
        return ResponseModel(**resp) if isinstance(resp, dict) else resp

    async def delete_user_info(self, _id: int) -> ResponseModel:
        resp = await self.client.delete(self._url, params={'id': _id}, headers=self._headers())
        return ResponseModel(**resp) if isinstance(resp, dict) else resp

    async def get_userinfo(self, _id: int) -> ResponseModel:
        resp = await self.client.get(f'user/info', params={'id': _id}, headers=self._headers())
        response = ResponseModel(**resp) if isinstance(resp, dict) else resp
        if response.code == 200 and response.data:
            data_list = response.data if isinstance(response.data, list) else [response.data]
            if data_list:
                user_model = UserModel(**data_list[0])
                if user_model.config is None:
                    user_model.config = {}
                    await self.put_user_info(data_list[0])
        return response

    async def put_user_project(self, _id: int, selected_project: int) -> ResponseModel:
        resp = await self.client.put(
            f'{self._url}/project',
            json={'id': _id, 'selected_project': selected_project},
            headers=self._headers(),
        )
        return ResponseModel(**resp) if isinstance(resp, dict) else resp

    async def put_environment(self, _id: int, selected_environment: int) -> ResponseModel:
        resp = await self.client.put(
            f'{self._url}/environment',
            json={'id': _id, 'selected_environment': selected_environment},
            headers=self._headers(),
        )
        return ResponseModel(**resp) if isinstance(resp, dict) else resp

    async def put_password(self, _id: int, password: str, new_password: str, confirm_password: str) -> ResponseModel:
        resp = await self.client.put(
            f'{self._url}/password',
            json={
                'id': _id,
                'password': password,
                'new_password': new_password,
                'confirm_password': confirm_password,
            },
            headers=self._headers(),
        )
        return ResponseModel(**resp) if isinstance(resp, dict) else resp

    async def get_name(self) -> ResponseModel:
        resp = await self.client.get(f'{self._url}/name', headers=self._headers())
        return ResponseModel(**resp) if isinstance(resp, dict) else resp
