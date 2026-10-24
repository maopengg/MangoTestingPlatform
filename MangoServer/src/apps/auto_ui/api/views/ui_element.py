# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-01-15 22:06
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_ui.api.serializers.ui_element import UiOpenElementPageBrowserSerializer, \
    UiElementPageScanSerializer, UiElementIdentityQuerySerializer
from src.apps.auto_ui.api.serializers.ui_element_mutation import PageElementSerializers
from src.apps.auto_ui.api.serializers.ui_element_presentation import PageElementSerializersC
from src.apps.auto_ui.enums import ElementExpEnum
from src.apps.auto_ui.exceptions import AutoUiError, UI_ELEMENT_CATEGORY_REQUIRED
from src.apps.auto_ui.models import PageElement
from src.apps.auto_ui.services.element_ai import (
    ElementAiLocatorRecommendationService,
    ElementAiService,
)
from src.apps.auto_ui.services.element_ai.data_sanitizer import ElementAiDataSanitizer
from src.apps.auto_ui.services.test_case.test_case import TestCase
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0005,
    RESPONSE_MSG_0079,
    RESPONSE_MSG_0080,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0083,
    RESPONSE_MSG_0158,
    RESPONSE_MSG_0204,
    RESPONSE_MSG_0244,
    RESPONSE_MSG_0248,
    RESPONSE_MSG_0259,
    RESPONSE_MSG_0260,
    RESPONSE_MSG_0270,
)
from src.common.utils.spreadsheet import read_excel_records


class PageElementCRUD(ModelCRUD):
    model = PageElement
    queryset = PageElement.objects.all()
    serializer_class = PageElementSerializersC
    serializer = PageElementSerializers
    page_permission_key = 'ui.page'
    not_matching_str = ModelCRUD.not_matching_str + ['category']

    @staticmethod
    def _category_is_empty(data: dict, instance: PageElement | None = None):
        category = data.get('category') if data.get('category') is not None else getattr(instance, 'category', None)
        return not str(category or '').strip()

    @classmethod
    def inside_post(cls, data: dict) -> dict:
        if cls._category_is_empty(data):
            raise AutoUiError(UI_ELEMENT_CATEGORY_REQUIRED)
        return super().inside_post(data)

    @classmethod
    def inside_put(cls, _id: int, data: dict) -> dict:
        instance = cls.model.objects.get(pk=_id)
        if cls._category_is_empty(data, instance):
            raise AutoUiError(UI_ELEMENT_CATEGORY_REQUIRED)
        return super().inside_put(_id, data)

    @error_response('ui')
    def post(self, request: Request):
        if self._category_is_empty(request.data):
            return ResponseData.fail(RESPONSE_MSG_0204)
        serializer = self.serializer(data=request.data)
        if not serializer.is_valid():
            return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)
        from src.apps.auto_ui.services.element_service import PageElementService

        instance, created = PageElementService.upsert_element(
            serializer.validated_data,
            user_id=self.get_request_user_id(request),
        )
        response_message = RESPONSE_MSG_0002 if created else RESPONSE_MSG_0005
        return ResponseData.success(response_message, self.serializer_class(instance=instance).data)

    @error_response('ui')
    def put(self, request: Request):
        instance_id = request.data.get('id') if not isinstance(request, dict) else request.get('id')
        try:
            instance = self.model.objects.get(pk=instance_id)
        except self.model.DoesNotExist:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if self._category_is_empty(request.data if not isinstance(request, dict) else request, instance):
            return ResponseData.fail(RESPONSE_MSG_0204)
        return super().put(request)


class PageElementViews(ViewSet):
    model = PageElement
    serializer_class = PageElementSerializers
    action_permission_map = {
        'check_element': 'ui.page:debug',
        'check_result': 'ui.page:debug',
        'scan_page': 'ui.page:debug',
        'apply_check_result': 'ui.page:edit',
        'open_browser': 'ui.page:debug',
        'post_upload_element': 'ui.page:create',
        'get_element_name': 'ui.page',
        'identity': 'ui.page',
        'put_is_iframe': 'ui.page:edit',
        'ai_locator_recommend': 'ui.page:debug',
        'runtime_result': 'ui.page:debug',
    }

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def identity(self, request: Request):
        from src.apps.auto_ui.services.element_service import PageElementService

        serializer = UiElementIdentityQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = PageElementService.resolve_element_identity(**serializer.validated_data)
        return ResponseData.success(RESPONSE_MSG_0260, data)

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def open_browser(self, request: Request):
        serializer = UiOpenElementPageBrowserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        page_model = TestCase(
            request.user.get('id'),
            request.user.get('username'),
            data['test_env'],
            is_send=True,
        ).open_page_browser(data['page_id'])
        return ResponseData.success(RESPONSE_MSG_0248, page_model.model_dump())

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def check_element(self, request: Request):
        from src.apps.auto_ui.services.element_service import PageElementService

        data = PageElementService.check_element(
            element_id=request.data.get('element_id'),
            user_id=request.user.get('id'),
            username=request.user.get('username'),
            test_env_id=request.data.get('test_env'),
            workspace_id=request.data.get('workspace_id'),
            check_mode=request.data.get('check_mode'),
            runtime_variables=request.data.get('runtime_variables'),
        )
        return ResponseData.success(RESPONSE_MSG_0244, data=data)

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def scan_page(self, request: Request):
        from src.apps.auto_ui.services.element_service import PageElementService

        serializer = UiElementPageScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_data = serializer.validated_data
        data = PageElementService.scan_page_elements(
            page_id=request_data['page_id'],
            user_id=request.user.get('id'),
            username=request.user.get('username'),
            workspace_id=request_data['workspace_id'],
            scan_mode=request_data['mode'],
        )
        return ResponseData.success(RESPONSE_MSG_0270, data=data)

    @action(methods=['PUT'], detail=False)
    @error_response('ui')
    def apply_check_result(self, request: Request):
        data = ElementAiService.apply_deep_check_task_result(
            request.data.get('element_id'),
            request.data.get('task_id'),
            request.user.get('id'),
        )
        return ResponseData.success(RESPONSE_MSG_0082, data=data)

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def post_upload_element(self, request):
        uploaded_file = request.FILES['file']
        records = read_excel_records(uploaded_file)
        expression_mapping = ElementExpEnum.reversal_obj()
        column_mapping = {
            '*元素名称': 'name',
            '*类型-1': 'exp',
            '*定位-1': 'loc',
            '类型-2': 'exp2',
            '定位-2': 'loc2',
            '类型-3': 'exp3',
            '定位-3': 'loc3',
            '等待时间': 'sleep',
            '元素下标-1': 'sub',
            '元素下标-2': 'sub2',
            '元素下标-3': 'sub3',
        }
        for source_record in records:
            source_record['*类型-1'] = expression_mapping.get(source_record['*类型-1'])
            for column in ('类型-2', '类型-3'):
                value = source_record[column]
                source_record[column] = expression_mapping.get(value) if value is not None else None
            record = {
                column_mapping.get(key, key): value
                for key, value in source_record.items()
            }
            record['page'] = request.data.get("page_id")
            record['update_user'] = request.user.get('id') if isinstance(request.user, dict) else None
            record['category'] = request.data.get('category') or ElementAiService.DEFAULT_CATEGORY
            record['is_iframe'] = 0
            record['sleep'] = None if record['sleep'] == '' else record['sleep']
            record['sub'] = None if record['sub'] == '' else record['sub']
            record['sub2'] = None if record['sub2'] == '' else record['sub2']
            record['sub3'] = None if record['sub3'] == '' else record['sub3']
            PageElementCRUD.inside_post(record)
        return ResponseData.success(RESPONSE_MSG_0083)

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def get_element_name(self, request: Request):
        """
        获取
        :param request:
        :return:
        """
        res = PageElement.objects.filter(page=request.query_params.get('id')).values(
            'id',
            'name',
            'category',
            'prompt',
            'location_description',
            'surrounding_text',
            'expected_event',
            'exp',
            'loc',
            'sub',
            'exp2',
            'loc2',
            'sub2',
            'exp3',
            'loc3',
            'sub3',
            'latest_match_count',
            'latest_element_text',
            'latest_runtime_time',
            'latest_runtime_snapshot',
        )
        data = [
            {
                'id': item['id'],
                'name': item['name'],
                'category': item['category'],
                'prompt': item.get('prompt'),
                'location_description': item.get('location_description'),
                'surrounding_text': item.get('surrounding_text'),
                'expected_event': item.get('expected_event') or {},
                'exp': item.get('exp'),
                'loc': item.get('loc'),
                'sub': item.get('sub'),
                'exp2': item.get('exp2'),
                'loc2': item.get('loc2'),
                'sub2': item.get('sub2'),
                'exp3': item.get('exp3'),
                'loc3': item.get('loc3'),
                'sub3': item.get('sub3'),
                'latest_match_count': item.get('latest_match_count'),
                'latest_element_text': item.get('latest_element_text'),
                'latest_runtime_time': ElementAiDataSanitizer.datetime_text(item.get('latest_runtime_time')),
                'latest_runtime_snapshot': ElementAiDataSanitizer.runtime_snapshot(
                    item.get('latest_runtime_snapshot') or {}
                ),
            }
            for item in res
        ]
        return ResponseData.success(RESPONSE_MSG_0080, data)

    @action(methods=['put'], detail=False)
    @error_response('ui')
    def put_is_iframe(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        from src.apps.auto_ui.services.element_service import PageElementService

        PageElementService.set_iframe(
            request.data.get('id'),
            request.data.get('is_iframe'),
            request.user.get('id') if isinstance(request.user, dict) else None,
        )
        return ResponseData.success(RESPONSE_MSG_0079, )

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def category(self, request: Request):
        data = ElementAiService.category_list(request.query_params.get('page_id') or request.query_params.get('id'))
        return ResponseData.success(RESPONSE_MSG_0080, data)

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def ai_info(self, request: Request):
        data = ElementAiService.ai_info(
            request.query_params.get('element_id') or request.query_params.get('id'),
            request.query_params.get('test_env')
        )
        return ResponseData.success(RESPONSE_MSG_0080, data)

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def ai_snapshots(self, request: Request):
        data = ElementAiService.snapshot_history(
            request.query_params.get('element_id') or request.query_params.get('id'),
            request.query_params.get('test_env'),
            request.query_params.get('page', 1),
            request.query_params.get('pageSize', 10),
        )
        return ResponseData.success(RESPONSE_MSG_0080, data)

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def ai_snapshot_detail(self, request: Request):
        data = ElementAiService.snapshot_detail(
            request.query_params.get('snapshot_id') or request.query_params.get('id'),
            request.query_params.get('element_id'),
        )
        return ResponseData.success(RESPONSE_MSG_0080, data)

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def ai_heal_records(self, request: Request):
        data = ElementAiService.heal_history(
            request.query_params.get('element_id') or request.query_params.get('id'),
            request.query_params.get('test_env'),
            request.query_params.get('page', 1),
            request.query_params.get('pageSize', 20),
        )
        return ResponseData.success(RESPONSE_MSG_0080, data)

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def ai_heal_record_detail(self, request: Request):
        data = ElementAiService.heal_record_detail(
            request.query_params.get('record_id') or request.query_params.get('id'),
            request.query_params.get('element_id'),
        )
        return ResponseData.success(RESPONSE_MSG_0080, data)

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def ai_snapshot(self, request: Request):
        data = ElementAiService.save_snapshot(request.data)
        return ResponseData.success(RESPONSE_MSG_0002, data)

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def ai_locator_recommend(self, request: Request):
        data = ElementAiLocatorRecommendationService.recommend(
            request.data,
            self._request_user_id(request.user),
        )
        return ResponseData.success(RESPONSE_MSG_0259, data)

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def ai_heal_record(self, request: Request):
        data = ElementAiService.save_heal_record(request.data)
        return ResponseData.success(RESPONSE_MSG_0002, data)

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def runtime_result(self, request: Request):
        data = ElementAiService.save_runtime_result(request.data)
        return ResponseData.success(RESPONSE_MSG_0002, data)

    @action(methods=['put'], detail=False)
    @error_response('ui')
    def ai_heal_record_apply(self, request: Request):
        data = ElementAiService.apply_heal_record(
            request.data.get('record_id'),
            request.data.get('candidate_index', 0),
            request.data.get('target_slot', 1),
            self._request_user_id(request.user),
        )
        return ResponseData.success(RESPONSE_MSG_0082, data)

    @staticmethod
    def _request_user_id(user):
        if isinstance(user, dict):
            return user.get('id')
        return getattr(user, 'id', None)
