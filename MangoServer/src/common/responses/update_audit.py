# -*- coding: utf-8 -*-
import json

from rest_framework.request import Request

from src.common.decorators.error_response import error_response
from src.common.logging import log
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0004,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0158,
    RESPONSE_MSG_0210,
)


def get_request_user_id(request: Request) -> int | None:
    user = getattr(request, 'user', None)
    if isinstance(user, dict):
        return user.get('id')
    return getattr(user, 'id', None)


def with_update_user(data, request: Request) -> dict:
    payload = dict(data)
    user_id = get_request_user_id(request)
    if user_id:
        payload['update_user'] = user_id
    return payload


def set_update_user(instance, request: Request):
    user_id = get_request_user_id(request)
    if user_id and hasattr(instance, 'update_user_id'):
        instance.update_user_id = user_id


def save_update_user(instance, request: Request, update_fields: list[str] | None = None):
    set_update_user(instance, request)
    if update_fields is not None:
        update_fields = [*update_fields]
        if hasattr(instance, 'update_user_id') and 'update_user' not in update_fields:
            update_fields.append('update_user')
        if hasattr(instance, 'update_time') and 'update_time' not in update_fields:
            update_fields.append('update_time')
    instance.save(update_fields=update_fields)


class UpdateUserCRUDMixin:
    @error_response('system')
    def post(self, request: Request):
        data = with_update_user(request.data, request)
        if not self.has_data_scope_permission(request, data):
            return ResponseData.fail(RESPONSE_MSG_0210)
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            self.asynchronous_callback(data.get('parent_id'))
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        log.system.error(
            f'执行保存时报错，请检查！数据：{data}, 报错信息：{json.dumps(serializer.errors)}')
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response('system')
    def put(self, request: Request):
        data = with_update_user(request.data, request)
        instance_id = data.get('id')
        try:
            instance = self.model.objects.get(pk=instance_id)
        except self.model.DoesNotExist:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_instance_data_scope_permission(request, instance):
            return ResponseData.fail(RESPONSE_MSG_0210)
        if not self.has_data_scope_permission(request, data):
            return ResponseData.fail(RESPONSE_MSG_0210)
        serializer = self.serializer(
            instance=instance,
            data=data,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            self.asynchronous_callback(data.get('parent_id'))
            return ResponseData.success(RESPONSE_MSG_0082, serializer.data)
        log.system.error(f'执行修改时报错，请检查！数据：{data}, 报错信息：{str(serializer.errors)}')
        return ResponseData.fail(RESPONSE_MSG_0004, serializer.errors)


ApiUpdateUserCRUDMixin = UpdateUserCRUDMixin
