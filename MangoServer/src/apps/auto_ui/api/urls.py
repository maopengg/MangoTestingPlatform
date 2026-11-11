# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: ui自动化子路由
# @Time   : 2023-01-19 19:21
# @Author : 毛鹏
from django.urls import path

from src.apps.auto_ui.api.views.ui_auth_config import UiAuthConfigCRUD, UiAuthConfigViews
from src.apps.auto_ui.api.views.ui_case import UiCaseCRUD, UiCaseViews
from src.apps.auto_ui.api.views.ui_case_steps_detailed import UiCaseStepsDetailedCRUD, UiCaseStepsDetailedViews
from src.apps.auto_ui.api.views.ui_element import PageElementCRUD, PageElementViews
from src.apps.auto_ui.api.views.ui_live_stream import LiveStreamViews
from src.apps.auto_ui.api.views.ui_page import PageCRUD, PageViews
from src.apps.auto_ui.api.views.ui_page_steps import PageStepsCRUD, PageStepsViews
from src.apps.auto_ui.api.views.ui_page_steps_detailed import PageStepsDetailedCRUD, PageStepsDetailedView
from src.apps.auto_ui.api.views.ui_public import UiPublicCRUD, UiPublicViews

urlpatterns = [
    path("public/reference-counts", UiPublicViews.as_view({'get': 'reference_counts'})),
    path("public/reference-cases", UiPublicViews.as_view({'get': 'reference_cases'})),
    path("live-stream/session", LiveStreamViews.as_view({'post': 'create_session'})),
    path("live-stream/session/<str:stream_id>/start", LiveStreamViews.as_view({'post': 'start_session'})),
    path("live-stream/session/<str:stream_id>", LiveStreamViews.as_view({'delete': 'close_session'})),
    path("live-stream/workspace", LiveStreamViews.as_view({'post': 'create_workspace'})),
    path(
        "live-stream/workspace/<str:workspace_id>",
        LiveStreamViews.as_view({'get': 'workspace_status', 'delete': 'close_workspace'}),
    ),
    #
    path("page", PageCRUD.as_view()),
    path("page/name", PageViews.as_view({'get': 'page_name'})),
    #
    path("element", PageElementCRUD.as_view()),
    path("element/name", PageElementViews.as_view({'get': 'get_element_name'})),
    path("element/identity", PageElementViews.as_view({'get': 'identity'})),
    path("element/category", PageElementViews.as_view({'get': 'category'})),
    path("element/iframe", PageElementViews.as_view({'put': 'put_is_iframe'})),
    path("element/check", PageElementViews.as_view({'post': 'check_element'})),
    path("element/scan", PageElementViews.as_view({'post': 'scan_page'})),
    path("element/check-result/apply", PageElementViews.as_view({'put': 'apply_check_result'})),
    path("element/browser/open", PageElementViews.as_view({'post': 'open_browser'})),
    path("element/upload", PageElementViews.as_view({'post': 'post_upload_element'})),
    path("element/ai/info", PageElementViews.as_view({'get': 'ai_info'})),
    path("element/ai/snapshots", PageElementViews.as_view({'get': 'ai_snapshots'})),
    path("element/ai/snapshot/detail", PageElementViews.as_view({'get': 'ai_snapshot_detail'})),
    path("element/ai/heal-records", PageElementViews.as_view({'get': 'ai_heal_records'})),
    path("element/ai/heal-record/detail", PageElementViews.as_view({'get': 'ai_heal_record_detail'})),
    path("element/ai/locator/recommend", PageElementViews.as_view({'post': 'ai_locator_recommend'})),
    path("element/ai/snapshot", PageElementViews.as_view({'post': 'ai_snapshot'})),
    path("element/ai/heal-record", PageElementViews.as_view({'post': 'ai_heal_record'})),
    path("element/ai/heal-record/apply", PageElementViews.as_view({'put': 'ai_heal_record_apply'})),
    path("element/runtime-result", PageElementViews.as_view({'post': 'runtime_result'})),
    #
    path("page/steps/detailed", PageStepsDetailedCRUD.as_view()),
    path("page/steps/detailed/copy", PageStepsDetailedView.as_view({'post': 'duplicate_node'})),
    path("page/steps/detailed/sort", PageStepsDetailedView.as_view({'put': 'put_step_sort'})),
    #
    path("page/steps", PageStepsCRUD.as_view()),
    path("page/steps/test", PageStepsViews.as_view({'get': 'ui_steps_run'})),
    path("page/steps/browser/open", PageStepsViews.as_view({'post': 'open_browser'})),
    path("page/steps/name", PageStepsViews.as_view({'get': 'get_page_steps_name'})),
    path("page/steps/cases", PageStepsViews.as_view({'get': 'referenced_cases'})),
    path("page/steps/asset/products", PageStepsViews.as_view({'get': 'asset_product_options'})),
    path("page/steps/asset/modules", PageStepsViews.as_view({'get': 'asset_module_options'})),
    path("page/steps/asset/steps", PageStepsViews.as_view({'get': 'asset_step_options'})),
    path("page/steps/copy", PageStepsViews.as_view({'post': 'copy_page_steps'})),
    path("page/steps/recording/commit", PageStepsViews.as_view({'post': 'recording_commit'})),
    path("page/steps/healing/report", PageStepsViews.as_view({'post': 'heal_report'})),
    path("page/steps/healing/records", PageStepsViews.as_view({'get': 'heal_records'})),
    path("page/steps/healing/record", PageStepsViews.as_view({'get': 'heal_record_detail'})),
    path("page/steps/healing/apply", PageStepsViews.as_view({'post': 'heal_apply'})),
    path("page/steps/healing/reject", PageStepsViews.as_view({'post': 'heal_reject'})),
    path("page/steps/healing/versions", PageStepsViews.as_view({'get': 'heal_versions'})),
    path("page/steps/healing/rollback", PageStepsViews.as_view({'post': 'heal_rollback'})),
    #
    path("public", UiPublicCRUD.as_view()),
    path("public/status", UiPublicViews.as_view({'put': 'put_status'})),
    #
    path("auth/config", UiAuthConfigCRUD.as_view()),
    path("auth/config/status", UiAuthConfigViews.as_view({'put': 'put_status'})),
    path("auth/config/refresh", UiAuthConfigViews.as_view({'post': 'refresh'})),
    path("auth/config/clear", UiAuthConfigViews.as_view({'post': 'clear'})),
    path("auth/config/cache", UiAuthConfigViews.as_view({'get': 'cache'})),
    path("auth/config/manual-cache", UiAuthConfigViews.as_view({'put': 'manual_cache', 'post': 'manual_cache'})),
    path("auth/config/auto/start", UiAuthConfigViews.as_view({'post': 'auto_start'})),
    path("auth/config/auto/capture", UiAuthConfigViews.as_view({'post': 'auto_capture'})),
    #
    path("case", UiCaseCRUD.as_view()),
    path("case/copy", UiCaseViews.as_view({'post': 'cody_case'})),
    path("case/test", UiCaseViews.as_view({'get': 'ui_test_case'})),
    path("case/batch", UiCaseViews.as_view({'post': 'ui_test_case_batch'})),
    path("case/publication", UiCaseViews.as_view({'put': 'set_publication'})),
    path("case/publication/review", UiCaseViews.as_view({'get': 'publication_review'})),
    #
    path("case/steps/detailed", UiCaseStepsDetailedCRUD.as_view()),
    path("case/steps/detailed/refresh", UiCaseStepsDetailedViews.as_view({'get': 'post_case_cache_data'})),
    path("case/steps/detailed/sort", UiCaseStepsDetailedViews.as_view({'put': 'put_case_sort'})),
]
