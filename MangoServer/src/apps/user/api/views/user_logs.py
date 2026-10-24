# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏

from src.apps.user.api.serializers.user_logs import UserLogsSerializersC
from src.apps.user.api.serializers.user_logs_mutation import UserLogsSerializers
from src.apps.user.models import UserLogs
from src.common.responses.model_crud import ModelCRUD


class UserLogsCRUD(ModelCRUD):
    model = UserLogs
    queryset = UserLogs.objects.all()
    serializer_class = UserLogsSerializersC
    serializer = UserLogsSerializers
    page_permission_key = 'system.user_logs'
    not_matching_str = [*ModelCRUD.not_matching_str, 'method']
