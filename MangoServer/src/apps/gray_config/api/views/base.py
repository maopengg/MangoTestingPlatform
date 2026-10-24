# -*- coding: utf-8 -*-
from rest_framework.request import Request

from src.common.decorators.error_response import error_response
from src.common.logging import log
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0002, RESPONSE_MSG_0003, RESPONSE_MSG_0004, RESPONSE_MSG_0082


class LastUpdateUserCRUD(ModelCRUD):
    sensitive_keys = {'access_token', 'password', 'token', 'authorization'}

    @classmethod
    def mask_sensitive_data(cls, data):
        if not isinstance(data, dict):
            return data
        return {
            key: '***' if str(key).lower() in cls.sensitive_keys else value
            for key, value in data.items()
        }

    @error_response('system')
    def post(self, request: Request):
        if not self.has_data_scope_permission(request, request.data):
            from src.common.responses.response_msg import RESPONSE_MSG_0210
            return ResponseData.fail(RESPONSE_MSG_0210)
        data = dict(request.data)
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is not None:
            data['last_update_user'] = user.id
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        log.system.error(f'灰度配置保存失败：data={self.mask_sensitive_data(data)}, errors={serializer.errors}')
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response('system')
    def put(self, request: Request):
        data = dict(request.data)
        instance_id = data.get('id')
        try:
            instance = self.model.objects.get(pk=instance_id)
        except self.model.DoesNotExist:
            from src.common.responses.response_msg import RESPONSE_MSG_0158
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_instance_data_scope_permission(request, instance):
            from src.common.responses.response_msg import RESPONSE_MSG_0210
            return ResponseData.fail(RESPONSE_MSG_0210)
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is not None:
            data['last_update_user'] = user.id
        serializer = self.serializer(instance=instance, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0082, serializer.data)
        log.system.error(f'灰度配置修改失败：data={self.mask_sensitive_data(data)}, errors={serializer.errors}')
        return ResponseData.fail(RESPONSE_MSG_0004, serializer.errors)
