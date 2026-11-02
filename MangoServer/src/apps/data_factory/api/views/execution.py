# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行记录视图

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.data_factory.api.serializers.execution import (
    DataFactoryExecutionBatchCleanupSerializer,
    DataFactoryExecutionSerializer,
    DataFactoryExecutionSerializerC,
)
from src.apps.data_factory.models import DataFactoryExecution, DataFactoryExecutionItem
from src.apps.data_factory.services.cleanup import DataFactoryCleanup
from src.apps.test_center.services.product_module import ProductModuleService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001


class DataFactoryExecutionCRUD(ModelCRUD):
    http_method_names = ['get', 'delete', 'head', 'options']
    model = DataFactoryExecution
    queryset = DataFactoryExecution.objects.all()
    serializer_class = DataFactoryExecutionSerializerC
    serializer = DataFactoryExecutionSerializer
    page_permission_key = 'data_factory.execution'
    not_matching_str = ModelCRUD.not_matching_str + ['template']


class DataFactoryExecutionViews(ViewSet):

    @action(methods=['get'], detail=False)
    @error_response('system')
    def detail_view(self, request: Request):
        from src.apps.data_factory.models import SqlExecutionRecord
        from src.apps.data_factory.api.serializers.execution_item import DataFactoryExecutionItemSerializer, \
            DataFactoryExecutionItemSerializerC

        execution = ProductModuleService.with_full_paths(
            DataFactoryExecution.objects.all(),
            'module',
            'template__module',
        ).select_related(
            'project_product',
            'template',
        ).get(id=request.query_params.get('execution_id'))
        items = DataFactoryExecutionItemSerializerC.setup_eager_loading(
            DataFactoryExecutionItem.objects.all()
        ).filter(execution=execution).order_by('cleanup_order', 'id')
        sql_records = SqlExecutionRecord.objects.filter(
            source_type='data_factory',
            source_detail__execution_id=execution.id,
        ).order_by('create_time', 'id')
        return ResponseData.success(RESPONSE_MSG_0001, {
            "execution": DataFactoryExecutionSerializerC(execution).data,
            "items": DataFactoryExecutionItemSerializerC(items, many=True).data,
            "context": execution.context,
            "sql_executions": [
                DataFactoryExecutionItemSerializer.serialize_sql_execution(record)
                for record in sql_records
            ],
        })

    @action(methods=['get'], detail=False)
    @error_response('system')
    def context(self, request: Request):
        execution = DataFactoryExecution.objects.get(id=request.query_params.get('execution_id'))
        return ResponseData.success(RESPONSE_MSG_0001, execution.context)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def cleanup(self, request: Request):
        result = DataFactoryCleanup.cleanup_execution_on_demand(
            request.data.get('execution_id')
        )
        if result.get("already_cleaned"):
            return ResponseData.success(
                (200, result.get("message") or "当前执行记录没有需要清理的数据"),
                result,
            )
        return ResponseData.success(RESPONSE_MSG_0001, result)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def batch_cleanup(self, request: Request):
        serializer = DataFactoryExecutionBatchCleanupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = DataFactoryCleanup.batch_cleanup_executions(
            serializer.validated_data['execution_ids']
        )
        message = (
            f"批量清理完成：成功 {result['success']} 条，"
            f"失败 {result['fail']} 条，跳过 {result['skipped']} 条"
        )
        return ResponseData.success((200, message), result)
