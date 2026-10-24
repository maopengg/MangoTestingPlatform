# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行明细视图

from src.apps.data_factory.api.serializers.execution_item import DataFactoryExecutionItemSerializer, \
    DataFactoryExecutionItemSerializerC
from src.apps.data_factory.models import DataFactoryExecutionItem
from src.common.responses.model_crud import ModelCRUD


class DataFactoryExecutionItemCRUD(ModelCRUD):
    model = DataFactoryExecutionItem
    queryset = DataFactoryExecutionItem.objects.all()
    serializer_class = DataFactoryExecutionItemSerializerC
    serializer = DataFactoryExecutionItemSerializer
    page_permission_key = 'data_factory.execution'
    not_matching_str = ModelCRUD.not_matching_str + ['execution', 'template', 'database', 'datasource_binding']
