# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.test_center.api.serializers.test_object import TestObjectSerializers, TestObjectSerializersC
from src.apps.test_center.models import TestObject
from src.common.decorators.error_response import error_response
from src.common.exceptions import MangoServerError
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0098,
)


class TestObjectCRUD(ModelCRUD):
    model = TestObject
    queryset = TestObject.objects.all()
    serializer_class = TestObjectSerializersC
    serializer = TestObjectSerializers
    page_permission_key = 'config.test_object'
    not_matching_str = ModelCRUD.not_matching_str + ['environment', 'auto_type']


class TestObjectViews(ViewSet):
    model = TestObject
    serializer_class = TestObjectSerializers
    action_permission_map = {
        'put_status': 'config.test_object:status',
    }

    @action(methods=['put'], detail=False)
    @error_response('user')
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """

        db_c_status = request.data.get('db_c_status')
        db_rud_status = request.data.get('db_rud_status')
        try:
            obj = self.model.objects.get(id=request.data.get('id'))
            if db_c_status is not None:
                obj.db_c_status = db_c_status
            if db_rud_status is not None:
                obj.db_rud_status = db_rud_status
            obj.update_user_id = request.user.get("id") if isinstance(request.user, dict) else None
            obj.save(update_fields=["db_c_status", "db_rud_status", "update_user", "update_time"])
            return ResponseData.success(RESPONSE_MSG_0098)
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg))
