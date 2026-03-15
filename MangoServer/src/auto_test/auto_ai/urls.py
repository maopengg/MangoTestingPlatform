# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: AI写用例模块路由
# @Author : 毛鹏
from django.urls import path

from src.auto_test.auto_ai.views.ai_requirement import AiRequirementCRUD, AiRequirementViews
from src.auto_test.auto_ai.views.ai_requirement_split import AiRequirementSplitCRUD, AiRequirementSplitViews
from src.auto_test.auto_ai.views.ai_test_case import AiTestCaseCRUD, AiTestCaseViews
from src.auto_test.auto_ai.views.ai_test_point import AiTestPointCRUD, AiTestPointViews

urlpatterns = [
    # 需求管理
    path('requirement', AiRequirementCRUD.as_view()),
    path('requirement/name', AiRequirementViews.as_view({'get': 'get_name'})),
    path('requirement/analyze', AiRequirementViews.as_view({'post': 'analyze'})),
    path('requirement/generate/points', AiRequirementViews.as_view({'post': 'generate_points'})),
    path('requirement/generate/cases', AiRequirementViews.as_view({'post': 'generate_cases'})),

    # 需求拆分
    path('requirement/split', AiRequirementSplitCRUD.as_view()),
    path('requirement/split/by/requirement', AiRequirementSplitViews.as_view({'get': 'by_requirement'})),
    path('requirement/split/batch/confirm', AiRequirementSplitViews.as_view({'post': 'batch_confirm'})),

    # 测试点
    path('test/point', AiTestPointCRUD.as_view()),
    path('test/point/by/requirement', AiTestPointViews.as_view({'get': 'by_requirement'})),
    path('test/point/by/split', AiTestPointViews.as_view({'get': 'by_split'})),
    path('test/point/batch/confirm', AiTestPointViews.as_view({'post': 'batch_confirm'})),

    # 测试用例
    path('test/case', AiTestCaseCRUD.as_view()),
    path('test/case/by/requirement', AiTestCaseViews.as_view({'get': 'by_requirement'})),
    path('test/case/by/test/point', AiTestCaseViews.as_view({'get': 'by_test_point'})),
    path('test/case/export/excel', AiTestCaseViews.as_view({'get': 'export_excel'})),
]
