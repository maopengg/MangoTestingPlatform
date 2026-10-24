# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-17 21:39
# @Author : 毛鹏
from django.db import transaction
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.api_headers import ApiHeadersSerializers, ApiHeadersSerializersC
from src.apps.auto_api.models import ApiHeaders
from src.apps.auto_api.services.api_header import ApiHeaderDeleteService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0005, RESPONSE_MSG_0029, RESPONSE_MSG_0210
from src.common.responses.update_audit import ApiUpdateUserCRUDMixin


class ApiHeadersCRUD(ApiUpdateUserCRUDMixin, ModelCRUD):
    model = ApiHeaders
    queryset = ApiHeaders.objects.all()
    serializer_class = ApiHeadersSerializersC
    serializer = ApiHeadersSerializers
    page_permission_key = 'api.headers'
    not_matching_str = ModelCRUD.not_matching_str + ['project_product__api_client_type', 'update_user']

    @error_response('system')
    def delete(self, request: Request):
        header_ids = list(dict.fromkeys(
            int(header_id) for header_id in request.query_params.getlist('id[]')
        ))
        if not header_ids:
            return super().delete(request)

        headers = list(self.model.objects.filter(id__in=header_ids))
        if len(headers) != len(header_ids):
            return ResponseData.fail(RESPONSE_MSG_0029)
        for header in headers:
            if not self.has_instance_data_scope_permission(request, header):
                return ResponseData.fail(RESPONSE_MSG_0210)

        ApiHeaderDeleteService.validate_batch(headers)
        snapshots = [
            (header, self.capture_config_snapshot(header).snapshot)
            for header in headers
        ]
        with transaction.atomic():
            self.model.objects.filter(id__in=header_ids).delete()
            for header, before_snapshot in snapshots:
                self.record_config_delete(header, before_snapshot, request=request)
        return ResponseData.success(RESPONSE_MSG_0005)


class ApiHeadersViews(ViewSet):
    model = ApiHeaders
    serializer_class = ApiHeadersSerializers
