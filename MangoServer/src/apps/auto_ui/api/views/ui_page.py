# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_ui.api.serializers.ui_page_mutation import PageSerializers
from src.apps.auto_ui.api.serializers.ui_page_presentation import PageSerializersC
from src.apps.auto_ui.exceptions import AutoUiError, UI_PAGE_DUPLICATED
from src.apps.auto_ui.models import Page
from src.apps.auto_ui.selectors.page import normalize_page_url
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0052,
    RESPONSE_MSG_0053,
    RESPONSE_MSG_0158,
    RESPONSE_MSG_0203,
)


# fields = ['project']  # 选中部分进行序列化
# exclude = ['name']  # 除了这个字段，其他全序列化


class PageCRUD(ModelCRUD):
    model = Page
    queryset = Page.objects.all()
    serializer_class = PageSerializersC
    page_permission_key = 'ui.page'
    not_matching_str = ModelCRUD.not_matching_str + ['project_product__ui_client_type']
    # post专用序列化器
    serializer = PageSerializers

    @staticmethod
    def _normalize_url(url: str | None):
        return normalize_page_url(url)

    @classmethod
    def _duplicate_url_page(cls, data: dict, instance: Page | None = None):
        url = cls._normalize_url(data.get('url') if data.get('url') is not None else getattr(instance, 'url', ''))
        if not url or url == '/':
            return None
        project_product = data.get('project_product') or getattr(instance, 'project_product_id', None)
        if not project_product:
            return None
        queryset = Page.objects.filter(project_product_id=project_product)
        if instance:
            queryset = queryset.exclude(id=instance.id)
        for page in queryset.only('id', 'url'):
            if cls._normalize_url(page.url) == url:
                return page
        return None

    @classmethod
    def inside_post(cls, data: dict) -> dict:
        duplicate_page = cls._duplicate_url_page(data)
        if duplicate_page:
            raise AutoUiError(UI_PAGE_DUPLICATED, value=(duplicate_page.id,))
        return super().inside_post(data)

    @classmethod
    def inside_put(cls, _id: int, data: dict) -> dict:
        instance = cls.model.objects.get(pk=_id)
        duplicate_page = cls._duplicate_url_page(data, instance)
        if duplicate_page:
            raise AutoUiError(UI_PAGE_DUPLICATED, value=(duplicate_page.id,))
        return super().inside_put(_id, data)

    @error_response('ui')
    def post(self, request: Request):
        duplicate_page = self._duplicate_url_page(request.data)
        if duplicate_page:
            return ResponseData.fail(RESPONSE_MSG_0203, value=(duplicate_page.id,))
        return super().post(request)

    @error_response('ui')
    def put(self, request: Request):
        instance_id = request.data.get('id') if not isinstance(request, dict) else request.get('id')
        try:
            instance = self.model.objects.get(pk=instance_id)
        except self.model.DoesNotExist:
            return ResponseData.fail(RESPONSE_MSG_0158)
        duplicate_page = self._duplicate_url_page(request.data if not isinstance(request, dict) else request, instance)
        if duplicate_page:
            return ResponseData.fail(RESPONSE_MSG_0203, value=(duplicate_page.id,))
        return super().put(request)


class PageViews(ViewSet):
    model = Page
    serializer_class = PageSerializers

    @action(methods=['GET'], detail=False)
    @error_response('ui')
    def page_name(self, request: Request):
        """
        根据项目获取页面id和名称
        """
        module_id = request.query_params.get('module_id')
        project_product_id = request.query_params.get('project_product_id')
        if module_id:
            queryset = Page.objects.filter(module=module_id)
        else:
            queryset = Page.objects.all()
        if project_product_id:
            queryset = queryset.filter(project_product_id=project_product_id)
        queryset = PageCRUD().filter_queryset_by_data_scope(request, queryset)
        res = queryset.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        if data:
            return ResponseData.success(RESPONSE_MSG_0052, data)

        else:
            return ResponseData.fail(RESPONSE_MSG_0053)
