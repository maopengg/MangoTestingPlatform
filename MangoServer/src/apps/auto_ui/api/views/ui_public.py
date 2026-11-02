# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_ui.api.serializers.ui_public import UiPublicSerializers, UiPublicSerializersC
from src.apps.auto_ui.enums import UiPublicTypeEnum
from src.apps.auto_ui.models import UiPublic
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0021,
)


class UiPublicCRUD(ModelCRUD):
    model = UiPublic
    queryset = UiPublic.objects.filter(type__in=UiPublicTypeEnum.get_key_list())
    serializer_class = UiPublicSerializersC
    serializer = UiPublicSerializers
    page_permission_key = 'ui.public'
    not_matching_str = ModelCRUD.not_matching_str + [
        'test_env',
        'datasource_alias',
    ]


class UiPublicViews(ViewSet):
    model = UiPublic
    serializer_class = UiPublicSerializers

    @action(methods=['put'], detail=False)
    @error_response('ui')
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        obj.update_user_id = request.user.get("id") if isinstance(request.user, dict) else None
        obj.save(update_fields=["status", "update_user", "update_time"])
        return ResponseData.success(RESPONSE_MSG_0021, )
