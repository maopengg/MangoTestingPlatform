import io
from django.http import FileResponse
from django.db.models import Q
from mangotools.enums import StatusEnum
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.system.enums import TestSuiteNoticeEnum
from src.apps.task_center.models import ScheduleFire
from src.apps.test_center.api.serializers.test_suite import TestSuiteSerializers, TestSuiteSerializersC, TestSuiteOfflineExportSerializer, TestSuiteOfflineOptionsSerializer
from src.apps.test_center.enums.report_delivery import ReportSourceEnum
from src.apps.test_center.selectors.offline_report import OfflineReportSelector
from src.apps.test_center.services.offline_report import OfflineReportService
from src.apps.test_center.services.offline_report.snapshot import ReportSnapshotService
from src.apps.test_center.exceptions import (
    SYSTEM_REPORT_REPORT_NOT_FOUND,
    TestCenterError,
)
from src.apps.test_center.models import NoticeGroup, TestSuite, TestSuiteDetails
from src.apps.test_center.services.diagnostic_markdown import DiagnosticMarkdownService
from src.apps.test_center.services.test_suite.base_notice import NoticeMain
from src.apps.test_center.services.test_suite.effectiveness import AutomationEffectivenessService
from src.apps.test_center.services.test_suite.send_notice import SendNotice
from src.apps.test_center.services.test_suite.stop import TestSuiteStopService
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0197,
    RESPONSE_MSG_0198,
    RESPONSE_MSG_0199,
    RESPONSE_MSG_0200,
    RESPONSE_MSG_0210,
    RESPONSE_MSG_0252,
    RESPONSE_MSG_0273,
)


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏


class TestSuiteCRUD(ModelCRUD):
    http_method_names = ['get', 'head', 'options']
    model = TestSuite
    queryset = TestSuite.objects.all()
    serializer_class = TestSuiteSerializersC
    serializer = TestSuiteSerializers
    page_permission_key = 'report'
    not_matching_str = ModelCRUD.not_matching_str + [
        'test_env',
        'execution_scenes',
        'execution_scope',
        'create_time__gte',
        'create_time__lte',
    ]

    @error_response('system')
    def get(self, request: Request):
        original_query = request._request.GET
        query = original_query.copy()
        raw_scenes = query.getlist('execution_scene') + query.getlist('execution_scene__in')
        scenes = [
            item
            for value in raw_scenes
            for item in str(value).split(',')
            if item
        ]
        query.pop('execution_scene', None)
        query.pop('execution_scene__in', None)
        case_types = query.pop('case_type__in', [])
        self._case_type_filter = [value.strip() for raw in case_types for value in raw.split(',') if value.strip()]
        group_execution_id = query.pop('group_execution_id', [None])[0]
        id_filters = []
        if scenes:
            scene_query = Q()
            for scene in dict.fromkeys(scenes):
                scene_query |= Q(execution_scenes__contains=[scene])
            id_filters.append(set(
                TestSuite.objects.filter(scene_query).values_list('id', flat=True)
            ))
        if group_execution_id:
            id_filters.append(set(
                ScheduleFire.objects.filter(
                    group_execution_id=group_execution_id,
                    test_suite_id__isnull=False,
                ).values_list('test_suite_id', flat=True)
            ))
        if id_filters:
            matching_ids = set.intersection(*id_filters)
            query.setlist('id__in', [str(item) for item in matching_ids] or ['-1'])
        request._request.GET = query
        try:
            return super().get(request)
        finally:
            request._request.GET = original_query

    def filter_queryset_by_data_scope(self, request, queryset):
        queryset = super().filter_queryset_by_data_scope(request, queryset).filter(report_retained=True)
        case_types = getattr(self, '_case_type_filter', [])
        if case_types:
            if not all(value.isdigit() for value in case_types):
                return queryset.none()
            queryset = queryset.filter(pk__in=TestSuiteDetails.objects.filter(
                type__in=case_types,
            ).values('test_suite_id'))
        return queryset


class TestSuiteViews(ViewSet):
    model = TestSuite
    serializer_class = TestSuiteSerializers

    @error_response('system')
    def offline_options(self, request: Request):
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        OfflineReportSelector.require_permission(user)
        serializer = TestSuiteOfflineOptionsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data['source_kind'] = ReportSourceEnum(data['source_kind'])
        response = ResponseData.success(RESPONSE_MSG_0001, OfflineReportSelector.options(user, **data))
        response['Cache-Control'] = 'no-store'
        return response

    @error_response('system')
    def offline_publish(self, request: Request):
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        OfflineReportSelector.require_permission(user)
        serializer = TestSuiteOfflineExportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind = ReportSourceEnum(serializer.validated_data['source_kind'])
        source_id = serializer.validated_data['source_id']
        OfflineReportSelector.require_product(user, ReportSnapshotService.source_product_id(kind, source_id))
        response = ResponseData.success(RESPONSE_MSG_0001, OfflineReportService.publish(kind, source_id))
        response['Cache-Control'] = 'no-store'
        return response

    @error_response('system')
    def offline_export(self, request: Request):
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        OfflineReportSelector.require_permission(user)
        serializer = TestSuiteOfflineExportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind = ReportSourceEnum(serializer.validated_data['source_kind'])
        source_id = serializer.validated_data['source_id']
        OfflineReportSelector.require_product(user, ReportSnapshotService.source_product_id(kind, source_id))
        filename, content = OfflineReportService.render(kind, source_id)
        response = FileResponse(io.BytesIO(content), as_attachment=True, filename=filename, content_type='text/html; charset=utf-8')
        response['Cache-Control'] = 'no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

    @action(methods=['post'], detail=False)
    @error_response('system')
    def stop(self, request: Request):
        test_suite_id = request.data.get('id')
        test_suite = self.model.objects.filter(id=test_suite_id).first()
        if test_suite and not self._has_project_product_scope(request, test_suite.project_product_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        return ResponseData.success(RESPONSE_MSG_0252, TestSuiteStopService.stop(test_suite_id))

    @action(methods=['get'], detail=False)
    @error_response('system')
    def effectiveness_overview(self, request: Request):
        return ResponseData.success(
            RESPONSE_MSG_0001,
            AutomationEffectivenessService.overview(request),
        )

    @action(methods=['post'], detail=False)
    @error_response('system')
    def effectiveness_ai_summary(self, request: Request):
        return ResponseData.success(
            RESPONSE_MSG_0001,
            AutomationEffectivenessService.ai_summary(request),
        )

    @action(methods=['post'], detail=False)
    @error_response('system')
    def effectiveness_clear_cache(self, request: Request):
        AutomationEffectivenessService.clear_cache(request)
        return ResponseData.success(RESPONSE_MSG_0273)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def diagnostic_markdown(self, request: Request):
        test_suite = self.model.objects.filter(id=request.query_params.get('id')).first()
        if not test_suite:
            raise TestCenterError(SYSTEM_REPORT_REPORT_NOT_FOUND)
        if not self._has_project_product_scope(request, test_suite.project_product_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            DiagnosticMarkdownService.read(
                DiagnosticMarkdownService.TARGET_TEST_REPORT,
                test_suite,
            ),
        )

    @staticmethod
    def _has_project_product_scope(request: Request, project_product_id) -> bool:
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        return ProjectProductScopeService.has_project_product(user, project_product_id)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def send_notice(self, request: Request):
        test_suite = self.model.objects.select_related(
            'tasks',
            'tasks__notice_group',
            'tasks__task_group',
            'tasks__task_group__notice_group',
            'project_product',
            'project_product__project',
        ).get(id=request.data.get('id'))
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is not None and not PermissionMenuService.is_effective_super_admin(user):
            if not ProjectProductScopeService.has_project_product(user, test_suite.project_product_id):
                return ResponseData.fail(RESPONSE_MSG_0210)
        if test_suite.status not in [StatusEnum.SUCCESS.value, StatusEnum.FAIL.value]:
            return ResponseData.fail(RESPONSE_MSG_0198)

        notice_group_id = request.data.get('notice_group')
        if not notice_group_id and test_suite.tasks:
            notice_group_id = SendNotice.task_notice_config(test_suite.tasks)[2]
        if not notice_group_id:
            return ResponseData.fail(RESPONSE_MSG_0199)

        notice_group = NoticeGroup.objects.get(id=notice_group_id)
        if notice_group.project_id != test_suite.project_product.project_id:
            return ResponseData.fail(RESPONSE_MSG_0200)

        test_suite.is_notice = TestSuiteNoticeEnum.SENDING.value
        test_suite.save(update_fields=['is_notice', 'update_time'])
        try:
            NoticeMain(int(notice_group_id)).notice_main(test_suite.id)
        except Exception:
            test_suite.is_notice = TestSuiteNoticeEnum.NOT_SENT.value
            test_suite.save(update_fields=['is_notice', 'update_time'])
            raise
        test_suite.is_notice = TestSuiteNoticeEnum.SENT.value
        test_suite.save(update_fields=['is_notice', 'update_time'])
        return ResponseData.success(RESPONSE_MSG_0197)
