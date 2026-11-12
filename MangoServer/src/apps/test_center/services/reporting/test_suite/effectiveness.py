from __future__ import annotations

import logging

from django.core.cache import cache
from mangotools.enums import TaskEnum

from src.apps.system.services.configuration.system_config import SystemConfigService
from src.common.prompts.quality_effectiveness import (
    QUALITY_EFFECTIVENESS_INSIGHT_CONFIGS,
    QUALITY_EFFECTIVENESS_INSIGHT_PROMPT_VERSION,
    QUALITY_EFFECTIVENESS_SUMMARY_PROMPT_VERSION,
)

logger = logging.getLogger(__name__)

from src.apps.test_center.services.reporting.test_suite.effectiveness_parts.ai import AutomationEffectivenessAiMixin
from src.apps.test_center.services.reporting.test_suite.effectiveness_parts.overview import AutomationEffectivenessOverviewMixin
from src.apps.test_center.services.reporting.test_suite.effectiveness_parts.query import AutomationEffectivenessQueryMixin
from src.apps.test_center.services.reporting.test_suite.effectiveness_parts.quality import AutomationEffectivenessQualityMixin
from src.apps.test_center.services.reporting.test_suite.effectiveness_parts.module import AutomationEffectivenessModuleMixin
from src.apps.test_center.services.reporting.test_suite.effectiveness_parts.task import AutomationEffectivenessTaskMixin


class AutomationEffectivenessService(AutomationEffectivenessAiMixin, AutomationEffectivenessOverviewMixin,
                                     AutomationEffectivenessQueryMixin, AutomationEffectivenessQualityMixin,
                                     AutomationEffectivenessModuleMixin, AutomationEffectivenessTaskMixin):
    DEFAULT_DAYS = 7
    MAX_DAYS = 366
    HEALTHY_FLAKY_RATE = 1.0
    CACHE_PREFIX = 'system:test-suite:effectiveness:v20'
    AI_SUMMARY_PROMPT_VERSION = QUALITY_EFFECTIVENESS_SUMMARY_PROMPT_VERSION
    AI_INSIGHT_PROMPT_VERSION = QUALITY_EFFECTIVENESS_INSIGHT_PROMPT_VERSION
    AI_METRIC_LABELS = {
        'detected_issue_count': ('异常结果', '次'),
        'unique_case_count': ('覆盖', '个用例'),
        'suite_count': ('执行报告', '份'),
        'detail_count': ('用例执行', '次'),
        'failed_count': ('失败结果', '次'),
        'warning_count': ('警告结果', '次'),
        'issue_count': ('问题结果', '次'),
        'recovered_case_count': ('重试恢复用例', '个'),
        'final_pass_rate': ('最终通过率', '%'),
        'completion_rate': ('完成率', '%'),
    }
    AI_INSIGHT_CONFIGS = QUALITY_EFFECTIVENESS_INSIGHT_CONFIGS
    CACHE_FILTER_KEYS = (
        'start_date',
        'end_date',
        'test_env',
        'execution_scene',
        'execution_scope',
        'project_id',
        'project_product_id',
        'task_id',
        'module_id',
    )
    MULTI_FILTER_KEYS = ('test_env', 'execution_scene', 'execution_scope')
    COMPLETED_STATUSES = (
        TaskEnum.FAIL.value,
        TaskEnum.SUCCESS.value,
        TaskEnum.WARNING.value,
        TaskEnum.STOPPED.value,
    )

    @classmethod
    def overview(cls, request) -> dict:
        cache_key = cls._cache_key(request)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cls._refresh_task_diagnostic_paths(cached_data)

        data = cls._build_overview(request)
        cache.set(cache_key, data, SystemConfigService.get_ranged_int('EFFECTIVENESS_CACHE_SECONDS'))
        return data
