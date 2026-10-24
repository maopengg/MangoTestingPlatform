from django.core.paginator import Paginator
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.data_factory.api.serializers.entity_status_log import DataFactoryEntityStatusLogSerializer
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_ENTITY_NAME_TEMPLATE_DUPLICATED,
    DATA_FACTORY_FIELD_INVALID,
    DataFactoryError,
)
from src.apps.data_factory.models import DataFactoryEntityStatusLog
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001


# -*- coding: utf-8 -*-


class DataFactoryEntityStatusLogViews(ViewSet):
    action_permission_map = {'list': 'data_factory.entity'}

    @error_response('system')
    def list(self, request: Request):
        entity_id = request.query_params.get('entity_id')
        if not entity_id:
            raise DataFactoryError(DATA_FACTORY_ENTITY_NAME_TEMPLATE_DUPLICATED)
        try:
            page = max(1, int(request.query_params.get('page') or 1))
            page_size = min(100, max(1, int(request.query_params.get('pageSize') or 10)))
        except (TypeError, ValueError) as error:
            raise DataFactoryError(DATA_FACTORY_FIELD_INVALID) from error
        queryset = DataFactoryEntityStatusLog.objects.select_related('operator').filter(
            entity_id=entity_id,
        ).order_by('-id')
        paginator = Paginator(queryset, page_size)
        page_data = paginator.get_page(page)
        data = DataFactoryEntityStatusLogSerializer(page_data.object_list, many=True).data
        return ResponseData.success(RESPONSE_MSG_0001, data, paginator.count)
