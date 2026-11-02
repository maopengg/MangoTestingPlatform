# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-17 21:39
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.api_pulic import ApiPublicSerializers, ApiPublicSerializersC
from src.apps.auto_api.enums import ApiPublicTypeEnum
from src.apps.auto_api.models import ApiPublic
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0104,
)
from src.common.responses.update_audit import ApiUpdateUserCRUDMixin, save_update_user


class ApiPublicCRUD(ApiUpdateUserCRUDMixin, ModelCRUD):
    model = ApiPublic
    queryset = ApiPublic.objects.filter(type__in=ApiPublicTypeEnum.get_key_list())
    serializer_class = ApiPublicSerializersC
    serializer = ApiPublicSerializers
    page_permission_key = 'api.public'
    not_matching_str = ModelCRUD.not_matching_str + [
        'test_env',
        'datasource_alias',
        'update_user',
    ]


class ApiPublicViews(ViewSet):
    model = ApiPublic
    serializer_class = ApiPublicSerializers

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """

        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        save_update_user(obj, request, ['status'])
        return ResponseData.success(RESPONSE_MSG_0104, )
