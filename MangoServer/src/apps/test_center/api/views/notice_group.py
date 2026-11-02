from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.test_center.api.serializers.notice_group import NoticeGroupSerializers, NoticeGroupSerializersC
from src.apps.test_center.models import NoticeGroup
from src.apps.test_center.services.test_suite.base_notice import NoticeMain
from src.common.decorators.error_response import error_response
from src.common.exceptions import MangoServerError
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0046,
)


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏


class NoticeGroupCRUD(ModelCRUD):
    model = NoticeGroup
    queryset = NoticeGroup.objects.all()
    serializer_class = NoticeGroupSerializersC
    serializer = NoticeGroupSerializers
    page_permission_key = 'config.project'


class NoticeGroupViews(ViewSet):
    model = NoticeGroup
    queryset = NoticeGroup.objects.all()
    serializer_class = NoticeGroupSerializersC
    serializer = NoticeGroupSerializers

    @action(methods=['get'], detail=False)
    @error_response('system')
    def test(self, request: Request):
        _id = request.query_params.get('id')
        try:
            # NoticeMain.notice_main(2, 2, 197899881973)
            NoticeMain(int(_id)).test_notice_send()
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg))
        else:
            return ResponseData.success(RESPONSE_MSG_0046)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_name(self, request: Request):
        from src.apps.test_center.models import ProjectProduct
        project_id = ProjectProduct.objects.get(id=request.query_params.get('project_product_id')).project_id
        model = self.model.objects.filter(project_id=project_id)
        return ResponseData.success(RESPONSE_MSG_0046, data=[{'value': i.id, 'label': i.name} for i in model])
