# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行记录视图

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_data_factory.models import DataFactoryExecution, DataFactoryExecutionItem
from src.apps.auto_data_factory.service.cleanup import DataFactoryCleanup
from src.apps.auto_data_factory.views.template import DataFactoryTemplateSerializerC
from src.apps.auto_system.views.project_product import ProjectProductSerializersC
from src.apps.auto_system.views.product_module import ProductModuleSerializersC
from src.common.enums.data_factory_enum import DataFactoryExecutionSourceEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import RESPONSE_MSG_0001


def _format_execution_source_info(obj: DataFactoryExecution) -> dict:
    if hasattr(obj, "_data_factory_source_info"):
        return obj._data_factory_source_info

    source_label = DataFactoryExecutionSourceEnum.obj().get(obj.source_type, obj.source_type)
    template_name = obj.template.name if obj.template_id and obj.template else None
    info = {
        "source_type": obj.source_type,
        "source_type_name": source_label,
        "source_id": obj.source_id,
        "template_id": obj.template_id,
        "template_name": template_name,
        "display": template_name or (f"{source_label}#{obj.source_id}" if obj.source_id else source_label),
    }
    if not obj.source_id:
        obj._data_factory_source_info = info
        return info

    executor = (obj.context or {}).get("__executor") or {}
    executor_user_id = executor.get("user_id")
    if executor_user_id:
        from src.apps.auto_user.models import User

        executor_user = User.objects.filter(id=executor_user_id).only("id", "name", "username").first()
        info["executor_id"] = executor_user_id
        if executor_user:
            info.update({
                "executor_name": executor_user.name,
                "executor_username": executor_user.username,
            })

    if obj.source_type == DataFactoryExecutionSourceEnum.API_CASE.value:
        from src.apps.auto_api.models import ApiCase

        api_case = ApiCase.objects.select_related("case_people").filter(id=obj.source_id).first()
        if api_case:
            info.update({
                "case_id": api_case.id,
                "case_name": api_case.name,
                "case_owner_id": api_case.case_people_id,
                "case_owner_name": api_case.case_people.name if api_case.case_people_id else None,
                "case_owner_username": api_case.case_people.username if api_case.case_people_id else None,
                "display": f"{source_label}：{api_case.name}",
            })
    elif obj.source_type == DataFactoryExecutionSourceEnum.API_CASE_PARAMETER.value:
        from src.apps.auto_api.models import ApiCaseDetailedParameter
        from src.common.enums.api_enum import MethodEnum

        parameter = ApiCaseDetailedParameter.objects.select_related(
            "case_detailed__case",
            "case_detailed__case__case_people",
            "case_detailed__api_info",
        ).filter(id=obj.source_id).first()
        if parameter:
            api_case = parameter.case_detailed.case
            api_info = parameter.case_detailed.api_info
            info.update({
                "case_id": api_case.id,
                "case_name": api_case.name,
                "case_owner_id": api_case.case_people_id,
                "case_owner_name": api_case.case_people.name if api_case.case_people_id else None,
                "case_owner_username": api_case.case_people.username if api_case.case_people_id else None,
                "api_info_id": api_info.id,
                "api_info_name": api_info.name,
                "api_info_method": api_info.method,
                "api_info_method_name": MethodEnum.obj().get(api_info.method, api_info.method),
                "api_info_url": api_info.url,
                "scenario_id": parameter.id,
                "scenario_name": parameter.name,
                "display": f"{source_label}：{api_case.name} / {api_info.name} / {parameter.name}",
            })
    elif obj.source_type == DataFactoryExecutionSourceEnum.UI_CASE.value:
        from src.apps.auto_ui.models import UiCase

        ui_case = UiCase.objects.select_related("case_people", "module").filter(id=obj.source_id).first()
        if ui_case:
            info.update({
                "case_id": ui_case.id,
                "case_name": ui_case.name,
                "case_owner_id": ui_case.case_people_id,
                "case_owner_name": ui_case.case_people.name if ui_case.case_people_id else None,
                "case_owner_username": ui_case.case_people.username if ui_case.case_people_id else None,
                "ui_module_id": ui_case.module_id,
                "ui_module_name": ui_case.module.name if ui_case.module_id else None,
                "display": f"{source_label}：{ui_case.name}",
            })

    if template_name:
        info["display"] = f"{info['display']} / 模板：{template_name}"
    obj._data_factory_source_info = info
    return info


class DataFactoryExecutionSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    cleanup_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    source_display = serializers.SerializerMethodField(read_only=True)
    source_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DataFactoryExecution
        fields = '__all__'

    @staticmethod
    def get_source_display(obj):
        return _format_execution_source_info(obj).get("display")

    @staticmethod
    def get_source_info(obj):
        return _format_execution_source_info(obj)


class DataFactoryExecutionSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    cleanup_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    source_display = serializers.SerializerMethodField(read_only=True)
    source_info = serializers.SerializerMethodField(read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializersC(read_only=True)
    template = DataFactoryTemplateSerializerC(read_only=True)

    class Meta:
        model = DataFactoryExecution
        fields = '__all__'

    @staticmethod
    def get_source_display(obj):
        return _format_execution_source_info(obj).get("display")

    @staticmethod
    def get_source_info(obj):
        return _format_execution_source_info(obj)

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'project_product',
            'project_product__project',
            'module',
            'template',
            'template__project_product',
            'template__project_product__project',
            'template__module',
            'template__entity',
            'template__entity__project_product',
            'template__entity__project_product__project',
            'template__entity__datasource_alias',
            'template__entity__datasource_alias__project_product',
        )

class DataFactoryExecutionCRUD(ModelCRUD):
    model = DataFactoryExecution
    queryset = DataFactoryExecution.objects.all()
    serializer_class = DataFactoryExecutionSerializerC
    serializer = DataFactoryExecutionSerializer
    not_matching_str = ModelCRUD.not_matching_str + ['template']

class DataFactoryExecutionViews(ViewSet):
    @action(methods=['get'], detail=False)
    @error_response('system')
    def detail_view(self, request: Request):
        from src.apps.auto_data_factory.views.execution_item import DataFactoryExecutionItemSerializerC

        execution = DataFactoryExecution.objects.select_related(
            'project_product',
            'module',
            'template',
        ).get(id=request.query_params.get('execution_id'))
        items = DataFactoryExecutionItemSerializerC.setup_eager_loading(
            DataFactoryExecutionItem.objects.all()
        ).filter(execution=execution).order_by('cleanup_order', 'id')
        return ResponseData.success(RESPONSE_MSG_0001, {
            "execution": DataFactoryExecutionSerializerC(execution).data,
            "items": DataFactoryExecutionItemSerializerC(items, many=True).data,
            "context": execution.context,
        })

    @action(methods=['get'], detail=False)
    @error_response('system')
    def context(self, request: Request):
        execution = DataFactoryExecution.objects.get(id=request.query_params.get('execution_id'))
        return ResponseData.success(RESPONSE_MSG_0001, execution.context)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def cleanup(self, request: Request):
        result = DataFactoryCleanup.cleanup_execution(
            request.data.get('execution_id'),
            force_cleanup=bool(request.data.get('force_cleanup')),
        )
        if result.get("already_cleaned"):
            return ResponseData.success((200, result.get("message") or "当前执行记录没有需要清理的数据"), result)
        return ResponseData.success(RESPONSE_MSG_0001, result)
