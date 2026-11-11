"""资产显式引用的 HTTP 适配，查询规则由业务 Selector 提供。"""
from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework.decorators import action

from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0210
from src.common.utils.json_references import reference_case_page


class ConfigurationReferenceViewsMixin:
    def _reference_scope(self, model, request):
        policy = import_string(settings.MODEL_CRUD_DATA_SCOPE_POLICY)
        return policy.filter_queryset(model, request, model.objects.all(), set())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def reference_counts(self, request):
        query = self.reference_counts_query(data={'ids': request.query_params.get('ids', '').split(',')})
        query.is_valid(raise_exception=True)
        ids = list(dict.fromkeys(query.validated_data['ids']))
        assets = self._reference_scope(self.model, request).filter(id__in=ids)
        if assets.count() != len(ids):
            return ResponseData.fail(RESPONSE_MSG_0210)
        references = self.reference_selector(self._reference_scope(self.reference_case_model, request), ids)
        return ResponseData.success(RESPONSE_MSG_0001, {str(key): len(value) for key, value in references.items()})

    @action(methods=['get'], detail=False)
    @error_response('system')
    def reference_cases(self, request):
        query = self.reference_cases_query(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        asset_id = params['id']
        if not self._reference_scope(self.model, request).filter(id=asset_id).exists():
            return ResponseData.fail(RESPONSE_MSG_0210)
        cases = self._reference_scope(self.reference_case_model, request)
        references = self.reference_selector(cases, [asset_id])
        rows, count = reference_case_page(cases, references[asset_id], params['page'], params['pageSize'])
        return ResponseData.success(RESPONSE_MSG_0001, rows, count)
