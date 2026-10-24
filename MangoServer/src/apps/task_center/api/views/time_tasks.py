# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet

from src.apps.task_center.api.serializers.time_tasks import TimeTasksSerializers
from src.apps.task_center.models import TimeTasks
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0103


class TimeTasksCRUD(ModelCRUD):
    model = TimeTasks
    queryset = TimeTasks.objects.all()
    serializer_class = TimeTasksSerializers
    serializer = TimeTasksSerializers
    page_permission_key = 'timing.strategy'


class TimeTasksViews(ViewSet):

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_time_obj_name(self, request):
        """
         获取平台枚举
         :param request:
         :return:
         """
        res = TimeTasks.objects.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0103, data)
