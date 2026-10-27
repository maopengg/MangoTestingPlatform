# -*- coding: utf-8 -*-
import json
from dataclasses import dataclass
from typing import Any

import time
from mangotools.enums import CacheValueTypeEnum

from src.apps.system.enums.cache import SystemConfigManagementLevelEnum
from src.apps.system.exceptions import (
    SYSTEM_CONFIG_NOT_FOUND,
    SystemError,
)
from src.apps.system.models import CacheData
from src.apps.test_center.enums.environment import EnvironmentEnum

ENVIRONMENT_DISPLAY_NAMES_KEY = 'ENVIRONMENT_DISPLAY_NAMES'

CONFIG_GROUP_TITLES = {
    "report_delivery": "报告生成与交付",
    "system": "后端服务设置",
    "runtime": "系统运行配置",
    "email": "邮箱配置",
    "execution": "执行任务配置",
    "api": "API自动化配置",
    "ui": "UI自动化配置",
    "pytest": "Pytest自动化配置",
    "data_factory": "数据工厂配置",
    "ai": "AI配置",
    "ai_vision": "视觉模型配置",
    "evaluation_ai": "效果测评 AI",
    "retention": "数据保留配置",
    "cache_performance": "缓存与性能配置",
    "access": "用户与访问配置",
    "data_source": "数据源配置",
    "mock": "Mock运行配置",
    "internal": "系统内部配置",
}

API_WORKER_THREAD_POOL_SIZE_KEY = "API_WORKER_THREAD_POOL_SIZE"
API_WORKER_THREAD_POOL_SIZE_DEFAULT = 5
API_WORKER_THREAD_POOL_SIZE_MIN = 1
API_WORKER_THREAD_POOL_SIZE_MAX = 20
API_WORKER_DESIRED_COUNT_KEY = "API_WORKER_DESIRED_COUNT"
API_WORKER_DESIRED_COUNT_DEFAULT = 5
API_TIMEOUT_DEFAULT = 120
GUEST_CAN_VIEW_ALL_PROJECT_DATA_KEY = "GUEST_CAN_VIEW_ALL_PROJECT_DATA"
GUEST_PROJECT_DATA_SCOPE_CACHE_SECONDS = 60
DATA_FACTORY_VALIDATION_ENVIRONMENTS_KEY = "DATA_FACTORY_VALIDATION_ENVIRONMENTS"
SQL_SLOW_QUERY_THRESHOLD_SECONDS_KEY = "SQL_SLOW_QUERY_THRESHOLD_SECONDS"
SQL_SLOW_QUERY_THRESHOLD_SECONDS_DEFAULT = 20
UI_FIXED_LOCATOR_RETRY_SECONDS_KEY = "UI_FIXED_LOCATOR_RETRY_SECONDS"
UI_SMART_LOCATOR_TIMEOUT_SECONDS_KEY = "UI_SMART_LOCATOR_TIMEOUT_SECONDS"
UI_VISUAL_LOCATOR_ENABLED_KEY = "UI_VISUAL_LOCATOR_ENABLED"
AI_VISION_USE_SEPARATE_CONFIG_KEY = "AI_VISION_USE_SEPARATE_CONFIG"
UI_FIXED_LOCATOR_RETRY_SECONDS_DEFAULT = 10
UI_FIXED_LOCATOR_RETRY_SECONDS_MIN = 0
UI_FIXED_LOCATOR_RETRY_SECONDS_MAX = 60
UI_SMART_LOCATOR_TIMEOUT_SECONDS_DEFAULT = 30
UI_SMART_LOCATOR_TIMEOUT_SECONDS_MIN = 5
UI_SMART_LOCATOR_TIMEOUT_SECONDS_MAX = 120
EXECUTOR_API_MAX_RUNTIME_MINUTES_KEY = "EXECUTOR_API_MAX_RUNTIME_MINUTES"
EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES_KEY = "EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES"
EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES_KEY = "EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES"
EXECUTOR_UI_PAGE_STEP_MAX_RUNTIME_MINUTES_KEY = "EXECUTOR_UI_PAGE_STEP_MAX_RUNTIME_MINUTES"
TEST_SUITE_STUCK_RESET_MINUTES_KEY = "TEST_SUITE_STUCK_RESET_MINUTES"
TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY = "TEST_SUITE_TIMEOUT_RETRY_COUNT"
EXECUTION_TIMEOUT_MINUTES_MIN = 1
EXECUTION_TIMEOUT_MINUTES_MAX = 1440
TEST_SUITE_TIMEOUT_RETRY_COUNT_MIN = 0
TEST_SUITE_TIMEOUT_RETRY_COUNT_MAX = 10
EXECUTOR_TIMEOUT_DEFAULT_MINUTES = {
    EXECUTOR_API_MAX_RUNTIME_MINUTES_KEY: 60,
    EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES_KEY: 60,
    EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES_KEY: 60,
    EXECUTOR_UI_PAGE_STEP_MAX_RUNTIME_MINUTES_KEY: 30,
}
TEST_SUITE_STUCK_RESET_MINUTES_DEFAULT = 65
TEST_SUITE_TIMEOUT_RETRY_COUNT_DEFAULT = 3

# 这批配置会由 sync_registered_configs 在初始化或服务启动时写入数据库。
# 取值范围统一在服务层校验，避免不同入口产生不同边界。
RANGED_INT_CONFIGS = {
    # 数据保留（天）
    "RESULT_DATA_RETENTION_DAYS": (60, 1, 3650),
    "UI_ARTIFACT_RETENTION_DAYS": (30, 1, 3650),
    "USER_LOG_RETENTION_DAYS": (90, 1, 3650),
    "DATA_FACTORY_EXECUTION_RETENTION_DAYS": (60, 1, 3650),
    "SQL_EXECUTION_RETENTION_DAYS": (60, 1, 3650),
    "SCHEDULE_FIRE_RETENTION_DAYS": (30, 1, 3650),
    "MONITORING_REPORT_RETENTION_DAYS": (30, 1, 3650),
    "API_CASE_TRACE_RETENTION_DAYS": (30, 1, 3650),
    "GRAY_EXECUTION_LOG_RETENTION_DAYS": (30, 1, 3650),
    "MOCK_REQUEST_LOG_RETENTION_DAYS": (30, 1, 3650),
    "SERVICE_HEARTBEAT_RETENTION_DAYS": (7, 1, 3650),
    "EXECUTOR_TASK_RETENTION_DAYS": (7, 1, 3650),
    "SYSTEM_ERROR_EVENT_RETENTION_DAYS": (30, 1, 3650),
    "UI_PENDING_HEAL_RETENTION_DAYS": (30, 1, 3650),
    "UI_RESOLVED_HEAL_RETENTION_DAYS": (90, 1, 3650),
    "UI_INACTIVE_SNAPSHOT_RETENTION_DAYS": (7, 1, 3650),
    # 页面缓存（秒）
    "HOME_INDEX_CACHE_SECONDS": (300, 0, 86400),
    "HOME_OVERVIEW_CACHE_SECONDS": (600, 0, 86400),
    "REPORT_OVERVIEW_CACHE_SECONDS": (600, 0, 86400),
    "EFFECTIVENESS_CACHE_SECONDS": (600, 0, 86400),
    "EFFECTIVENESS_AI_CACHE_SECONDS": (3600, 0, 86400),
    # 数据源和运行资源
    "DATA_SOURCE_TIMEOUT_SECONDS": (5, 1, 300),
    "DATA_QUERY_MAX_ROWS": (100, 1, 10000),
    "REDIS_MAX_RESPONSE_ITEMS": (2000, 1, 100000),
    API_WORKER_DESIRED_COUNT_KEY: (API_WORKER_DESIRED_COUNT_DEFAULT, 1, 100),
    "EXECUTOR_MAX_CONCURRENT_TASKS": (5, 1, 100),
    "PERF_EXECUTOR_MAX_CONCURRENT_RUNS": (5, 1, 100),
    "EXECUTOR_MEMORY_THRESHOLD_PERCENT": (100, 50, 100),
    "UI_LIVE_WORKSPACE_MAX_USERS": (5, 1, 100),
    "AI_AGENT_HISTORY_LIMIT": (16, 1, 100),
    "AI_AGENT_TOOL_LIMIT": (64, 1, 256),
    "AI_VISION_TIMEOUT": (30, 1, 120),
    "MOCK_REQUEST_MAX_KB": (1024, 1, 10240),
    "MOCK_RESPONSE_MAX_KB": (1024, 1, 10240),
    "MOCK_LOG_BODY_MAX_KB": (32, 1, 1024),
}


@dataclass(frozen=True)
class SystemConfigDefinition:
    key: str
    describe: str
    group: str
    value_type: int = CacheValueTypeEnum.STR.value
    default_value: Any = None
    required: bool = False
    is_secret: bool = False
    is_enabled: bool = True
    management_level: int = SystemConfigManagementLevelEnum.STANDARD.value
    sort: int = 100
    placeholder: str | None = None

    def default_value_text(self):
        if self.default_value is None:
            return None
        if self.value_type in (CacheValueTypeEnum.DICT.value, CacheValueTypeEnum.JSON.value,
                               CacheValueTypeEnum.LIST.value):
            return json.dumps(self.default_value, ensure_ascii=False)
        return str(self.default_value)


SYSTEM_CONFIG_REGISTRY = [
    SystemConfigDefinition(
        key="REPORT_DELIVERY_CONFIG", describe="离线报告交付配置", group="report_delivery",
        value_type=CacheValueTypeEnum.DICT.value, default_value={}, sort=10,
    ),
    SystemConfigDefinition(
        key="PLATFORM_NAME", describe="测试平台中文名称", group="system",
        default_value="芒果测试平台", required=True, sort=11,
        placeholder="登录页、导航、浏览器标题及通知中使用的名称",
    ),
    SystemConfigDefinition(
        key="PLATFORM_NAME_EN", describe="测试平台英文名称", group="system",
        default_value="mango-test-platform", required=True, sort=12,
        placeholder="登录页英文品牌名称，不改变 MCP 等技术标识",
    ),
    SystemConfigDefinition(
        key="EVALUATION_AI_PROFILES", describe="效果测评 AI 列表", group="evaluation_ai",
        value_type=CacheValueTypeEnum.LIST.value, default_value=[], sort=10, is_secret=True,
        placeholder="独立配置效果测评的评分、回答与总结模型；不使用默认 AI",
    ),
    SystemConfigDefinition(
        key=ENVIRONMENT_DISPLAY_NAMES_KEY,
        describe='部署环境显示名称',
        group='system',
        value_type=CacheValueTypeEnum.DICT.value,
        default_value={},
        sort=10,
        placeholder='仅修改显示名称，不改变环境编号和生产环境安全限制',
    ),
    SystemConfigDefinition(
        key=EXECUTOR_API_MAX_RUNTIME_MINUTES_KEY,
        describe="API最大执行时间（分钟）",
        group="execution",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=EXECUTOR_TIMEOUT_DEFAULT_MINUTES[EXECUTOR_API_MAX_RUNTIME_MINUTES_KEY],
        required=True,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
        sort=10,
        placeholder="从任务真正开始执行起计算，默认 60 分钟",
    ),
    SystemConfigDefinition(
        key=EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES_KEY,
        describe="Pytest最大执行时间（分钟）",
        group="execution",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=EXECUTOR_TIMEOUT_DEFAULT_MINUTES[EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES_KEY],
        required=True,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
        sort=20,
        placeholder="从任务真正开始执行起计算，默认 60 分钟",
    ),
    SystemConfigDefinition(
        key=EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES_KEY,
        describe="UI用例最大执行时间（分钟）",
        group="execution",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=EXECUTOR_TIMEOUT_DEFAULT_MINUTES[EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES_KEY],
        required=True,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
        sort=30,
        placeholder="从任务真正开始执行起计算，默认 60 分钟",
    ),
    SystemConfigDefinition(
        key=EXECUTOR_UI_PAGE_STEP_MAX_RUNTIME_MINUTES_KEY,
        describe="UI页面步骤最大执行时间（分钟）",
        group="execution",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=EXECUTOR_TIMEOUT_DEFAULT_MINUTES[
            EXECUTOR_UI_PAGE_STEP_MAX_RUNTIME_MINUTES_KEY
        ],
        required=True,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
        sort=40,
        placeholder="从任务真正开始执行起计算，默认 30 分钟",
    ),
    SystemConfigDefinition(
        key=TEST_SUITE_STUCK_RESET_MINUTES_KEY,
        describe="测试报告卡住重置时间（分钟）",
        group="execution",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=TEST_SUITE_STUCK_RESET_MINUTES_DEFAULT,
        required=True,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
        sort=50,
        placeholder="从本次报告明细分发时间起计算，默认 65 分钟",
    ),
    SystemConfigDefinition(
        key=TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY,
        describe="测试报告超时重试次数",
        group="execution",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=TEST_SUITE_TIMEOUT_RETRY_COUNT_DEFAULT,
        required=True,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
        sort=60,
        placeholder="不含首次执行；默认重试 3 次，0 表示不重试",
    ),
    SystemConfigDefinition(
        key="SYSTEM_DOMAIN_NAME",
        describe="本系统域名",
        group="report_delivery",
        value_type=CacheValueTypeEnum.STR.value,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=1,
        placeholder="请输入通知中使用的平台访问地址",
    ),
    SystemConfigDefinition(
        key="SYSTEM_SEND_USER",
        describe="邮箱发送人",
        group="email",
        value_type=CacheValueTypeEnum.STR.value,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=10,
        placeholder="请输入邮箱发送人",
    ),
    SystemConfigDefinition(
        key="SYSTEM_EMAIL_HOST",
        describe="邮箱域名",
        group="email",
        value_type=CacheValueTypeEnum.STR.value,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=20,
        placeholder="请输入邮箱域名",
    ),
    SystemConfigDefinition(
        key="SYSTEM_STAMP_KET",
        describe="邮箱的stamp_key",
        group="email",
        value_type=CacheValueTypeEnum.STR.value,
        is_secret=True,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=30,
        placeholder="请输入邮箱授权密钥",
    ),
    SystemConfigDefinition(
        key="API_TIMEOUT",
        describe="API请求超时时间",
        group="api",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=API_TIMEOUT_DEFAULT,
        required=True,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=10,
        placeholder="请输入 API 请求超时时间",
    ),
    SystemConfigDefinition(
        key=DATA_FACTORY_VALIDATION_ENVIRONMENTS_KEY,
        describe="数据模型校验环境",
        group="data_factory",
        value_type=CacheValueTypeEnum.LIST.value,
        default_value=None,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=10,
        placeholder="请选择数据模型启用和定时巡检时需要校验的环境",
    ),
    SystemConfigDefinition(
        key=SQL_SLOW_QUERY_THRESHOLD_SECONDS_KEY,
        describe="慢SQL阈值（秒）",
        group="data_factory",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=SQL_SLOW_QUERY_THRESHOLD_SECONDS_DEFAULT,
        required=True,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=20,
        placeholder="超过该耗时将生成工作台待办",
    ),
    SystemConfigDefinition(
        key=GUEST_CAN_VIEW_ALL_PROJECT_DATA_KEY,
        describe="允许游客查看所有项目数据",
        group="system",
        value_type=CacheValueTypeEnum.BOOL.value,
        default_value=False,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=20,
        placeholder="关闭时游客仅能查看所属部门授权的项目产品数据",
    ),
    SystemConfigDefinition(
        key=API_WORKER_THREAD_POOL_SIZE_KEY,
        describe="API Worker线程池大小",
        group="runtime",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=API_WORKER_THREAD_POOL_SIZE_DEFAULT,
        required=True,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
        sort=20,
        placeholder=f"请输入 {API_WORKER_THREAD_POOL_SIZE_MIN}-{API_WORKER_THREAD_POOL_SIZE_MAX} 之间的整数",
    ),
    SystemConfigDefinition(
        key=UI_FIXED_LOCATOR_RETRY_SECONDS_KEY,
        describe="固定定位重试窗口（秒）",
        group="ui",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=UI_FIXED_LOCATOR_RETRY_SECONDS_DEFAULT,
        required=True,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=10,
        placeholder="所有有效定位组共享；每组至少尝试一次，0 表示完成一轮后立即进入智能定位",
    ),
    SystemConfigDefinition(
        key=UI_SMART_LOCATOR_TIMEOUT_SECONDS_KEY,
        describe="智能定位总超时（秒）",
        group="ui",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=UI_SMART_LOCATOR_TIMEOUT_SECONDS_DEFAULT,
        required=True,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=20,
        placeholder="历史、DOM 与 Accessibility AI 共用的总时间",
    ),
    SystemConfigDefinition(
        key=UI_VISUAL_LOCATOR_ENABLED_KEY,
        describe="启用截图视觉兜底",
        group="ui",
        value_type=CacheValueTypeEnum.BOOL.value,
        default_value=False,
        sort=30,
        placeholder="仅在其他定位方式全部失败后调用视觉模型",
    ),
    SystemConfigDefinition(
        key="AI_PROVIDER_TYPE",
        describe="AI供应商类型",
        group="ai",
        value_type=CacheValueTypeEnum.STR.value,
        default_value="openai_compatible",
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=5,
        placeholder="openai_compatible/openai/azure_openai/anthropic/gemini",
    ),
    SystemConfigDefinition(
        key="AI_API_KEY",
        describe="AI的APIKey",
        group="ai",
        value_type=CacheValueTypeEnum.STR.value,
        is_secret=True,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=10,
        placeholder="请输入 AI APIKey",
    ),
    SystemConfigDefinition(
        key="AI_BASE_URL",
        describe="AI接口地址(兼容OpenAI格式)",
        group="ai",
        value_type=CacheValueTypeEnum.STR.value,
        default_value="https://api.deepseek.com",
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=20,
        placeholder="请输入 AI 接口地址",
    ),
    SystemConfigDefinition(
        key="AI_MODEL",
        describe="AI模型名称",
        group="ai",
        value_type=CacheValueTypeEnum.STR.value,
        default_value="deepseek-chat",
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=30,
        placeholder="请输入 AI 模型名称",
    ),
    SystemConfigDefinition(
        key="AI_TIMEOUT",
        describe="AI请求超时时间(秒)",
        group="ai",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=600,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=40,
        placeholder="请输入 AI 请求超时时间",
    ),
    SystemConfigDefinition(
        key=AI_VISION_USE_SEPARATE_CONFIG_KEY,
        describe="使用独立视觉模型配置",
        group="ai_vision",
        value_type=CacheValueTypeEnum.BOOL.value,
        default_value=False,
        sort=10,
        placeholder="关闭时复用主 AI 的供应商、APIKey、接口地址和模型",
    ),
    SystemConfigDefinition(
        key="AI_VISION_PROVIDER_TYPE",
        describe="视觉AI供应商类型",
        group="ai_vision",
        value_type=CacheValueTypeEnum.STR.value,
        default_value="openai_compatible",
        sort=20,
        placeholder="openai_compatible",
    ),
    SystemConfigDefinition(
        key="AI_VISION_API_KEY",
        describe="视觉AI的APIKey",
        group="ai_vision",
        value_type=CacheValueTypeEnum.STR.value,
        is_secret=True,
        sort=30,
        placeholder="留空时不启用独立视觉模型",
    ),
    SystemConfigDefinition(
        key="AI_VISION_BASE_URL",
        describe="视觉AI接口地址",
        group="ai_vision",
        value_type=CacheValueTypeEnum.STR.value,
        sort=40,
        placeholder="请输入兼容 OpenAI 格式的接口地址",
    ),
    SystemConfigDefinition(
        key="AI_VISION_MODEL",
        describe="视觉AI模型名称",
        group="ai_vision",
        value_type=CacheValueTypeEnum.STR.value,
        sort=50,
        placeholder="请输入支持图片输入的模型名称",
    ),
    SystemConfigDefinition(
        key="AI_VISION_TIMEOUT",
        describe="视觉AI请求超时（秒）",
        group="ai_vision",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=30,
        sort=60,
        placeholder="请输入视觉AI请求超时时间",
    ),
    SystemConfigDefinition(
        key="AI_VISION_PROXY_URL",
        describe="视觉AI请求代理",
        group="ai_vision",
        value_type=CacheValueTypeEnum.STR.value,
        default_value=None,
        is_secret=True,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        sort=70,
        placeholder="默认不走代理，使用代理时填写完整地址",
    ),
]


def _ranged_int_definition(
        key,
        describe,
        group,
        sort,
        placeholder=None,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
):
    default, minimum, maximum = RANGED_INT_CONFIGS[key]
    return SystemConfigDefinition(
        key=key,
        describe=describe,
        group=group,
        value_type=CacheValueTypeEnum.INT.value,
        default_value=default,
        required=True,
        management_level=management_level,
        sort=sort,
        placeholder=placeholder or f"允许范围 {minimum}～{maximum}",
    )


SYSTEM_CONFIG_REGISTRY.extend([
    *[
        _ranged_int_definition(
            key,
            describe,
            "retention",
            sort,
            "单位：天；修改后下次清理任务生效",
            (
                SystemConfigManagementLevelEnum.STANDARD.value
                if key == "SQL_EXECUTION_RETENTION_DAYS"
                else SystemConfigManagementLevelEnum.CAUTION.value
            ),
        )
        for sort, (key, describe) in enumerate([
            ("RESULT_DATA_RETENTION_DAYS", "执行结果完整数据保留天数"),
            ("UI_ARTIFACT_RETENTION_DAYS", "UI截图、录屏等文件保留天数"),
            ("USER_LOG_RETENTION_DAYS", "操作日志保留天数"),
            ("DATA_FACTORY_EXECUTION_RETENTION_DAYS", "数据工厂执行记录保留天数"),
            ("SQL_EXECUTION_RETENTION_DAYS", "SQL执行记录保留天数"),
            ("SCHEDULE_FIRE_RETENTION_DAYS", "定时任务触发记录保留天数"),
            ("MONITORING_REPORT_RETENTION_DAYS", "监控报告保留天数"),
            ("API_CASE_TRACE_RETENTION_DAYS", "API执行链路保留天数"),
            ("GRAY_EXECUTION_LOG_RETENTION_DAYS", "灰度执行记录保留天数"),
            ("MOCK_REQUEST_LOG_RETENTION_DAYS", "Mock调用日志保留天数"),
            ("SERVICE_HEARTBEAT_RETENTION_DAYS", "服务心跳保留天数"),
            ("EXECUTOR_TASK_RETENTION_DAYS", "执行器历史任务保留天数"),
            ("SYSTEM_ERROR_EVENT_RETENTION_DAYS", "系统异常记录保留天数"),
            ("UI_PENDING_HEAL_RETENTION_DAYS", "UI待处理自愈记录保留天数"),
            ("UI_RESOLVED_HEAL_RETENTION_DAYS", "UI已解决自愈记录保留天数"),
            ("UI_INACTIVE_SNAPSHOT_RETENTION_DAYS", "UI非活跃基线快照保留天数"),
        ], start=10)
    ],
    *[
        _ranged_int_definition(
            key,
            describe,
            "cache_performance",
            sort,
            "单位：秒；0 表示不缓存",
            SystemConfigManagementLevelEnum.CAUTION.value,
        )
        for sort, (key, describe) in enumerate([
            ("HOME_INDEX_CACHE_SECONDS", "首页基础缓存时间"),
            ("HOME_OVERVIEW_CACHE_SECONDS", "首页统计缓存时间"),
            ("REPORT_OVERVIEW_CACHE_SECONDS", "测试报告统计缓存时间"),
            ("EFFECTIVENESS_CACHE_SECONDS", "自动化效能统计缓存时间"),
            ("EFFECTIVENESS_AI_CACHE_SECONDS", "AI效能总结缓存时间"),
        ], start=10)
    ],
    SystemConfigDefinition(
        key="ALLOW_HOME_REGISTRATION", describe="允许首页自助注册", group="access",
        value_type=CacheValueTypeEnum.BOOL.value, default_value=True, sort=10,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        placeholder="关闭后仅管理员可以创建账号",
    ),
    SystemConfigDefinition(
        key="REGISTRATION_DISABLED_MESSAGE", describe="禁止注册提示文案", group="access",
        default_value="当前平台未开放自助注册，请联系管理员开通账号。", required=True, sort=20,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
    ),
    SystemConfigDefinition(
        key="SHOW_LOGIN_AUTHOR_INFO", describe="登录页显示开源作者信息", group="access",
        value_type=CacheValueTypeEnum.BOOL.value, default_value=True, sort=30,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        placeholder="关闭后隐藏登录页的开源项目与作者介绍",
    ),
    SystemConfigDefinition(
        key="SHOW_HOME_AUTHOR_POPUP", describe="登录后自动显示联系作者弹窗", group="access",
        value_type=CacheValueTypeEnum.BOOL.value, default_value=True, sort=40,
        management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        placeholder="仅控制自动弹窗，不影响手动查看作者信息",
    ),
    _ranged_int_definition(
        "DATA_SOURCE_TIMEOUT_SECONDS", "数据源连接超时时间（秒）", "data_source", 10,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
    ),
    _ranged_int_definition(
        "DATA_QUERY_MAX_ROWS", "数据查询最大返回行数", "data_source", 20,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
    ),
    _ranged_int_definition(
        "REDIS_MAX_RESPONSE_ITEMS", "Redis最大返回条数", "data_source", 30,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
    ),
    _ranged_int_definition(
        API_WORKER_DESIRED_COUNT_KEY,
        "API Worker期望实例数",
        "api",
        20,
        "用于容量规划与健康诊断；实际实例由部署控制器扩缩容",
        SystemConfigManagementLevelEnum.STANDARD.value,
    ),
    _ranged_int_definition(
        "EXECUTOR_MAX_CONCURRENT_TASKS", "执行器最大并发任务数", "runtime", 30,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
    ),
    _ranged_int_definition(
        "PERF_EXECUTOR_MAX_CONCURRENT_RUNS", "性能任务单执行器并发数", "runtime", 40,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
    ),
    _ranged_int_definition(
        "EXECUTOR_MEMORY_THRESHOLD_PERCENT", "执行器内存保护阈值（%）", "runtime", 50,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
    ),
    _ranged_int_definition(
        "UI_LIVE_WORKSPACE_MAX_USERS", "UI实时工作区最大用户数", "runtime", 60,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
    ),
    _ranged_int_definition("AI_AGENT_HISTORY_LIMIT", "AI Agent历史轮数", "ai", 110),
    _ranged_int_definition("AI_AGENT_TOOL_LIMIT", "AI Agent工具调用上限", "ai", 120),
    _ranged_int_definition(
        "MOCK_REQUEST_MAX_KB", "Mock请求体上限（KB）", "mock", 10,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
    ),
    _ranged_int_definition(
        "MOCK_RESPONSE_MAX_KB", "Mock响应体上限（KB）", "mock", 20,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
    ),
    _ranged_int_definition(
        "MOCK_LOG_BODY_MAX_KB", "Mock日志正文保存上限（KB）", "mock", 30,
        management_level=SystemConfigManagementLevelEnum.CAUTION.value,
    ),
])

DEPRECATED_SYSTEM_CONFIG_KEYS = {
    "AI_TEMPERATURE",
    "AI_TOP_P",
    "AI_MAX_TOKENS",
    "AI_STREAM",
    "AI_API_VERSION",
    "AI_ORGANIZATION",
    "AI_PROJECT",
    "AI_EXTRA_HEADERS",
    "AI_EXTRA_BODY",
    "AI_PROXY_URL",
    "PYTEST_GIT_URL",
    "PYTEST_GIT_USERNAME",
    "PYTEST_GIT_PASSWORD",
    "PYTEST_GIT_DEFAULT_PROJECT",
    "PYTEST_GIT_DEFAULT_BRANCH",
    "PYTEST_GIT_WORK_BRANCH_PREFIX",
    "PYTEST_AUTO_TEST_DIR",
    "PYTEST_GIT_PROVIDER",
    "PYTEST_GIT_API_BASE_URL",
    "PYTEST_GIT_ACCESS_TOKEN",
    "PYTEST_GIT_OPERATION_MODE",
    "PYTEST_ACT",
    "PYTEST_TESTCASE",
    "PYTEST_TOOLS",
    "PYTEST_UPLOAD",
    "SQL_EXECUTION_AUDIT_ENABLED",
    "SQL_EXECUTION_AUDIT_RETENTION_DAYS",
    "playwright_operation_method",
    "playwright_assertion_method",
    "public_assertion_method",
    "sql_assertion_method",
    "uiautomator_operation_method",
    "desktop_operation_method",
    "ios_operation_method",
    "uiautomator_assertion_method",
    "assertion_method",
    "AI_UI_LOCATOR_ENABLED",
    "AI_UI_LOCATOR_MODE",
    "AI_UI_LOCATOR_SEMANTIC_STRENGTH",
}

DEPRECATED_SYSTEM_CONFIG_GROUPS = {
    "gray",
}

SYSTEM_INTERNAL_CONFIG_REGISTRY = [
    SystemConfigDefinition(
        key="test_data_select_value",
        describe="随机测试数据方法选项",
        group="internal",
        value_type=CacheValueTypeEnum.DICT.value,
        management_level=SystemConfigManagementLevelEnum.INTERNAL.value,
        sort=5,
    ),
    SystemConfigDefinition(
        key="select_value",
        describe="执行器操作方法选项",
        group="internal",
        value_type=CacheValueTypeEnum.DICT.value,
        management_level=SystemConfigManagementLevelEnum.INTERNAL.value,
        sort=10,
    ),
    SystemConfigDefinition(
        key="ass_select_value",
        describe="断言方法选项",
        group="internal",
        value_type=CacheValueTypeEnum.DICT.value,
        management_level=SystemConfigManagementLevelEnum.INTERNAL.value,
        sort=20,
    ),
]


def get_config_definition_map():
    return {item.key: item for item in [*SYSTEM_CONFIG_REGISTRY, *SYSTEM_INTERNAL_CONFIG_REGISTRY]}


class SystemConfigService:
    _environment_display_names_cache: tuple[float, dict[str, str]] | None = None
    _guest_project_data_scope_cache_value = None
    _guest_project_data_scope_cache_expires_at = 0.0
    _runtime_int_cache: dict[str, tuple[float, int]] = {}
    _runtime_int_cache_seconds = 5.0

    @classmethod
    def editable_config_keys(cls) -> set[str]:
        return {
            item.key for item in SYSTEM_CONFIG_REGISTRY
            if item.management_level >= SystemConfigManagementLevelEnum.CAUTION.value
            and item.group not in DEPRECATED_SYSTEM_CONFIG_GROUPS
            and item.key not in DEPRECATED_SYSTEM_CONFIG_KEYS
        }

    @classmethod
    def sync_registered_configs(cls):
        CacheData.objects.filter(management_level=4).update(
            management_level=SystemConfigManagementLevelEnum.STANDARD.value,
        )
        CacheData.objects.filter(key__in=DEPRECATED_SYSTEM_CONFIG_KEYS, is_enabled=True).update(is_enabled=False)
        CacheData.objects.filter(group__in=DEPRECATED_SYSTEM_CONFIG_GROUPS, is_enabled=True).update(is_enabled=False)
        for item in [*SYSTEM_CONFIG_REGISTRY, *SYSTEM_INTERNAL_CONFIG_REGISTRY]:
            defaults = cls._definition_defaults(item)
            obj, created = CacheData.objects.get_or_create(key=item.key, defaults=defaults)
            if created:
                cls.invalidate(item.key)
                continue
            if (
                    item.key == "ALLOW_HOME_REGISTRATION"
                    and obj.value in (False, "false", "False", "0", 0)
                    and obj.update_user_id is None
            ):
                # 该配置最初以关闭状态自动初始化过；只修正未被用户编辑的系统默认记录。
                updated = CacheData.objects.filter(
                    pk=obj.pk,
                    update_user__isnull=True,
                    value=obj.value,
                ).update(value="true")
                if updated:
                    obj.value = "true"
                    cls.invalidate(item.key)
            if (
                    item.key == API_WORKER_DESIRED_COUNT_KEY
                    and str(obj.value) == "1"
                    and obj.update_user_id is None
            ):
                # 将旧版本自动初始化的默认值升级为 5；管理员主动保存过的值保持不变。
                updated = CacheData.objects.filter(
                    pk=obj.pk,
                    update_user__isnull=True,
                    value=obj.value,
                ).update(value=str(API_WORKER_DESIRED_COUNT_DEFAULT))
                if updated:
                    obj.value = str(API_WORKER_DESIRED_COUNT_DEFAULT)
                    cls.invalidate(item.key)
            if obj.value in (None, "") and defaults["value"] is not None:
                # 条件更新避免初始化读到空值后覆盖另一个请求刚保存的用户配置。
                updated = CacheData.objects.filter(pk=obj.pk, value=obj.value).update(
                    value=defaults["value"],
                )
                if updated:
                    cls.invalidate(item.key)
            changed_fields = []
            for field, value in defaults.items():
                if field == "value":
                    continue
                if getattr(obj, field, None) != value:
                    setattr(obj, field, value)
                    changed_fields.append(field)
            if changed_fields:
                changed_fields.append("update_time")
                obj.save(update_fields=changed_fields)
        cls.normalize_ai_timeout()
        cls.normalize_api_worker_thread_pool_size()
        cls.normalize_data_factory_validation_environments()
        cls.normalize_ui_locator_timeouts()
        cls.normalize_execution_settings()
        cls.normalize_ranged_int_configs()

    @classmethod
    def set_internal_value(cls, key: str, value):
        definition = next(
            (item for item in SYSTEM_INTERNAL_CONFIG_REGISTRY if item.key == key),
            None,
        )
        if definition is None:
            raise SystemError(SYSTEM_CONFIG_NOT_FOUND, value=(key,))
        defaults = cls._definition_defaults(definition)
        defaults["value"] = None if value is None else str(value)
        config, _created = CacheData.objects.update_or_create(key=key, defaults=defaults)
        cls.invalidate(key)
        return cls.cast_value(config.value, config.value_type)

    @classmethod
    def normalize_ai_locator_enabled(cls):
        try:
            obj = CacheData.objects.get(key="AI_UI_LOCATOR_ENABLED")
        except CacheData.DoesNotExist:
            return
        if obj.value in (True, "true", "True", "1", 1):
            normalized_value = "1"
        else:
            normalized_value = "0"
        if obj.value != normalized_value:
            obj.value = normalized_value
            obj.save(update_fields=["value", "update_time"])

    @classmethod
    def normalize_ai_locator_mode(cls):
        try:
            obj = CacheData.objects.get(key="AI_UI_LOCATOR_MODE")
        except CacheData.DoesNotExist:
            return
        try:
            mode = int(obj.value)
        except (TypeError, ValueError):
            mode = 1
        if mode not in (1, 2, 3):
            mode = 1
        normalized_value = str(mode)
        if obj.value != normalized_value:
            obj.value = normalized_value
            obj.save(update_fields=["value", "update_time"])
            cls.invalidate("AI_UI_LOCATOR_MODE")

    @classmethod
    def normalize_ai_locator_semantic_strength(cls):
        try:
            obj = CacheData.objects.get(key="AI_UI_LOCATOR_SEMANTIC_STRENGTH")
        except CacheData.DoesNotExist:
            return
        strength = cls.normalize_ai_locator_semantic_strength_value(obj.value)
        normalized_value = str(strength)
        if obj.value != normalized_value:
            obj.value = normalized_value
            obj.save(update_fields=["value", "update_time"])
            cls.invalidate("AI_UI_LOCATOR_SEMANTIC_STRENGTH")

    @staticmethod
    def normalize_ai_locator_semantic_strength_value(value) -> int:
        try:
            strength = int(value)
        except (TypeError, ValueError):
            strength = 0
        return strength if strength in (0, 20, 50, 80, 100) else 0

    @classmethod
    def normalize_ai_timeout(cls):
        try:
            obj = CacheData.objects.get(key="AI_TIMEOUT")
        except CacheData.DoesNotExist:
            return
        try:
            timeout = int(obj.value)
        except (TypeError, ValueError):
            timeout = 0
        if timeout < 600:
            obj.value = "600"
            obj.save(update_fields=["value", "update_time"])
            cls.invalidate("AI_TIMEOUT")

    @classmethod
    def normalize_api_worker_thread_pool_size(cls):
        try:
            obj = CacheData.objects.get(key=API_WORKER_THREAD_POOL_SIZE_KEY)
        except CacheData.DoesNotExist:
            return
        size = cls.normalize_int_range(
            obj.value,
            default=API_WORKER_THREAD_POOL_SIZE_DEFAULT,
            min_value=API_WORKER_THREAD_POOL_SIZE_MIN,
            max_value=API_WORKER_THREAD_POOL_SIZE_MAX,
        )
        normalized_value = str(size)
        if obj.value != normalized_value:
            obj.value = normalized_value
            obj.save(update_fields=["value", "update_time"])
            cls.invalidate(API_WORKER_THREAD_POOL_SIZE_KEY)

    @classmethod
    def normalize_data_factory_validation_environments(cls):
        try:
            obj = CacheData.objects.get(key=DATA_FACTORY_VALIDATION_ENVIRONMENTS_KEY)
        except CacheData.DoesNotExist:
            return
        environments = cls.normalize_environment_list(obj.value)
        normalized_value = json.dumps(environments, ensure_ascii=False) if environments else None
        if obj.value != normalized_value:
            obj.value = normalized_value
            obj.save(update_fields=["value", "update_time"])
            cls.invalidate(DATA_FACTORY_VALIDATION_ENVIRONMENTS_KEY)

    @classmethod
    def normalize_ui_locator_timeouts(cls):
        ranges = {
            UI_FIXED_LOCATOR_RETRY_SECONDS_KEY: (
                UI_FIXED_LOCATOR_RETRY_SECONDS_DEFAULT,
                UI_FIXED_LOCATOR_RETRY_SECONDS_MIN,
                UI_FIXED_LOCATOR_RETRY_SECONDS_MAX,
            ),
            UI_SMART_LOCATOR_TIMEOUT_SECONDS_KEY: (
                UI_SMART_LOCATOR_TIMEOUT_SECONDS_DEFAULT,
                UI_SMART_LOCATOR_TIMEOUT_SECONDS_MIN,
                UI_SMART_LOCATOR_TIMEOUT_SECONDS_MAX,
            ),
        }
        for key, (default, minimum, maximum) in ranges.items():
            try:
                obj = CacheData.objects.get(key=key)
            except CacheData.DoesNotExist:
                continue
            normalized = cls.normalize_int_range(
                obj.value, default=default, min_value=minimum, max_value=maximum,
            )
            if obj.value != str(normalized):
                obj.value = str(normalized)
                obj.save(update_fields=["value", "update_time"])
                cls.invalidate(key)

    @classmethod
    def normalize_execution_settings(cls):
        ranges = {
            **{
                key: (
                    default,
                    EXECUTION_TIMEOUT_MINUTES_MIN,
                    EXECUTION_TIMEOUT_MINUTES_MAX,
                )
                for key, default in EXECUTOR_TIMEOUT_DEFAULT_MINUTES.items()
            },
            TEST_SUITE_STUCK_RESET_MINUTES_KEY: (
                TEST_SUITE_STUCK_RESET_MINUTES_DEFAULT,
                EXECUTION_TIMEOUT_MINUTES_MIN,
                EXECUTION_TIMEOUT_MINUTES_MAX,
            ),
            TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY: (
                TEST_SUITE_TIMEOUT_RETRY_COUNT_DEFAULT,
                TEST_SUITE_TIMEOUT_RETRY_COUNT_MIN,
                TEST_SUITE_TIMEOUT_RETRY_COUNT_MAX,
            ),
        }
        for key, (default, minimum, maximum) in ranges.items():
            try:
                obj = CacheData.objects.get(key=key)
            except CacheData.DoesNotExist:
                continue
            normalized = cls.normalize_int_range(
                obj.value,
                default=default,
                min_value=minimum,
                max_value=maximum,
            )
            if obj.value != str(normalized):
                obj.value = str(normalized)
                obj.save(update_fields=["value", "update_time"])
            cls.invalidate(key)

    @classmethod
    def validate_ui_locator_config(cls, key: str, value) -> str | None:
        ranges = {
            UI_FIXED_LOCATOR_RETRY_SECONDS_KEY: (
                UI_FIXED_LOCATOR_RETRY_SECONDS_MIN,
                UI_FIXED_LOCATOR_RETRY_SECONDS_MAX,
                '固定定位重试窗口必须是 0～60 秒的整数',
            ),
            UI_SMART_LOCATOR_TIMEOUT_SECONDS_KEY: (
                UI_SMART_LOCATOR_TIMEOUT_SECONDS_MIN,
                UI_SMART_LOCATOR_TIMEOUT_SECONDS_MAX,
                '智能定位总超时必须是 5～120 秒的整数',
            ),
        }
        if key not in ranges:
            return None
        minimum, maximum, message = ranges[key]
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return message
        return None if minimum <= normalized <= maximum else message

    @classmethod
    def normalize_ranged_int_configs(cls):
        for key, (default, minimum, maximum) in RANGED_INT_CONFIGS.items():
            try:
                obj = CacheData.objects.get(key=key)
            except CacheData.DoesNotExist:
                continue
            normalized = cls.normalize_int_range(
                obj.value, default=default, min_value=minimum, max_value=maximum,
            )
            if obj.value != str(normalized):
                obj.value = str(normalized)
                obj.save(update_fields=["value", "update_time"])
            cls.invalidate(key)

    @classmethod
    def validate_sql_execution_config(cls, key: str, value) -> str | None:
        if key != SQL_SLOW_QUERY_THRESHOLD_SECONDS_KEY:
            return None
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return '慢SQL阈值必须是 1～3600 秒的整数'
        return None if 1 <= normalized <= 3600 else '慢SQL阈值必须是 1～3600 秒的整数'

    @classmethod
    def validate_editable_config(cls, key: str, value) -> str | None:
        """统一校验配置管理页可编辑的单个配置项。"""
        if key not in cls.editable_config_keys():
            return '该配置已停用或不属于可编辑的系统配置'
        if key == 'REPORT_DELIVERY_CONFIG':
            from pydantic import ValidationError
            from src.apps.test_center.schemas.report_delivery import ReportDeliveryConfig
            try:
                ReportDeliveryConfig.model_validate(json.loads(value) if isinstance(value, str) else value)
            except (ValidationError, json.JSONDecodeError, TypeError):
                return '报告交付配置无效：请检查渠道能力、存储地址、有效期及文件保留时间'
            return None
        if key in ('PLATFORM_NAME', 'PLATFORM_NAME_EN'):
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > 64:
                return '平台名称不能为空，且不能超过 64 个字符'
            if any(ord(char) < 32 or ord(char) == 127 for char in value):
                return '平台名称不能包含换行或控制字符'
            return None
        if key == "EVALUATION_AI_PROFILES":
            from src.apps.system.services.ai.evaluation_profiles import EvaluationAiProfileService
            EvaluationAiProfileService.parse(value)
            return None
        return (
                (cls.validate_environment_display_names(value) if key == ENVIRONMENT_DISPLAY_NAMES_KEY else None)
                or
                cls.validate_ui_locator_config(key, value)
                or cls.validate_sql_execution_config(key, value)
                or cls.validate_execution_config(key, value)
                or cls.validate_ranged_int_config(key, value)
        )

    @classmethod
    def validate_ranged_int_config(cls, key: str, value) -> str | None:
        bounds = RANGED_INT_CONFIGS.get(key)
        if bounds is None:
            return None
        _default, minimum, maximum = bounds
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return f"{key} 必须是 {minimum}～{maximum} 的整数"
        return None if minimum <= normalized <= maximum else f"{key} 必须是 {minimum}～{maximum} 的整数"

    @classmethod
    def validate_execution_config(cls, key: str, value) -> str | None:
        if key in {
            *EXECUTOR_TIMEOUT_DEFAULT_MINUTES,
            TEST_SUITE_STUCK_RESET_MINUTES_KEY,
        }:
            try:
                normalized = int(value)
            except (TypeError, ValueError):
                normalized = 0
            if not EXECUTION_TIMEOUT_MINUTES_MIN <= normalized <= EXECUTION_TIMEOUT_MINUTES_MAX:
                return "执行与重置时间必须是 1～1440 分钟的整数"
        if key == TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY:
            try:
                normalized = int(value)
            except (TypeError, ValueError):
                normalized = -1
            if not TEST_SUITE_TIMEOUT_RETRY_COUNT_MIN <= normalized <= TEST_SUITE_TIMEOUT_RETRY_COUNT_MAX:
                return "测试报告超时重试次数必须是 0～10 次的整数"
        return None

    @classmethod
    def validate_execution_config_values(cls, values: dict[str, Any]) -> str | None:
        execution_keys = {
            *EXECUTOR_TIMEOUT_DEFAULT_MINUTES,
            TEST_SUITE_STUCK_RESET_MINUTES_KEY,
            TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY,
        }
        for key, value in values.items():
            if key in execution_keys:
                error = cls.validate_execution_config(key, value)
                if error:
                    return error
        if not execution_keys.intersection(values):
            return None
        timeout_values = {
            key: int(values[key]) if key in values else cls.get_runtime_int(
                key,
                default=default,
                min_value=EXECUTION_TIMEOUT_MINUTES_MIN,
                max_value=EXECUTION_TIMEOUT_MINUTES_MAX,
            )
            for key, default in EXECUTOR_TIMEOUT_DEFAULT_MINUTES.items()
        }
        reset_minutes = (
            int(values[TEST_SUITE_STUCK_RESET_MINUTES_KEY])
            if TEST_SUITE_STUCK_RESET_MINUTES_KEY in values
            else cls.get_test_suite_stuck_reset_minutes()
        )
        report_execution_maximum = max(
            timeout_values[EXECUTOR_API_MAX_RUNTIME_MINUTES_KEY],
            timeout_values[EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES_KEY],
            timeout_values[EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES_KEY],
        )
        if reset_minutes <= report_execution_maximum:
            return "测试报告卡住重置时间必须大于 API、Pytest 和 UI 用例最大执行时间"
        return None

    @staticmethod
    def normalize_environment_list(value) -> list[int]:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (TypeError, ValueError, json.JSONDecodeError):
                value = []
        if not isinstance(value, (list, tuple, set)):
            return []
        valid_environments = EnvironmentEnum.default_obj()
        normalized = []
        for item in value:
            try:
                environment = int(item)
            except (TypeError, ValueError):
                continue
            if environment in valid_environments and environment not in normalized:
                normalized.append(environment)
        return sorted(normalized)

    @classmethod
    def _definition_defaults(cls, item: SystemConfigDefinition):
        return {
            "describe": item.describe,
            "value": item.default_value_text(),
            "value_type": item.value_type,
            "group": item.group,
            "sort": item.sort,
            "required": item.required,
            "is_enabled": item.is_enabled,
            "is_secret": item.is_secret,
            "management_level": item.management_level,
            "placeholder": item.placeholder,
        }

    @classmethod
    def invalidate(cls, key: str):
        if key == ENVIRONMENT_DISPLAY_NAMES_KEY:
            cls._environment_display_names_cache = None
        cls._runtime_int_cache.pop(key, None)
        if key == GUEST_CAN_VIEW_ALL_PROJECT_DATA_KEY:
            cls._guest_project_data_scope_cache_value = None
            cls._guest_project_data_scope_cache_expires_at = 0.0
        return None

    @classmethod
    def get_runtime_int(
            cls,
            key: str,
            *,
            default: int,
            min_value: int,
            max_value: int,
    ) -> int:
        now = time.monotonic()
        cached = cls._runtime_int_cache.get(key)
        if cached and cached[0] > now:
            return cached[1]
        try:
            value = cls.get(key, default=default)
        except Exception:
            value = default
        normalized = cls.normalize_int_range(
            value,
            default=default,
            min_value=min_value,
            max_value=max_value,
        )
        cls._runtime_int_cache[key] = (
            now + cls._runtime_int_cache_seconds,
            normalized,
        )
        return normalized

    @classmethod
    def get_ranged_int(cls, key: str) -> int:
        default, minimum, maximum = RANGED_INT_CONFIGS[key]
        return cls.get_runtime_int(
            key, default=default, min_value=minimum, max_value=maximum,
        )

    @classmethod
    def get_executor_execution_timeout_seconds(
            cls,
            task_type: str,
            *,
            default_seconds: int,
    ) -> int:
        from src.apps.system.enums import ExecutorTaskTypeEnum

        key_map = {
            ExecutorTaskTypeEnum.API_EXECUTION.value: EXECUTOR_API_MAX_RUNTIME_MINUTES_KEY,
            ExecutorTaskTypeEnum.PYTEST_EXECUTION.value: EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES_KEY,
            ExecutorTaskTypeEnum.UI_CASE.value: EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES_KEY,
            ExecutorTaskTypeEnum.UI_CASE_STEP.value: EXECUTOR_UI_PAGE_STEP_MAX_RUNTIME_MINUTES_KEY,
            ExecutorTaskTypeEnum.PAGE_STEP_DEBUG.value: EXECUTOR_UI_PAGE_STEP_MAX_RUNTIME_MINUTES_KEY,
        }
        key = key_map.get(str(task_type))
        if key is None:
            return default_seconds
        default_minutes = EXECUTOR_TIMEOUT_DEFAULT_MINUTES[key]
        return cls.get_runtime_int(
            key,
            default=default_minutes,
            min_value=EXECUTION_TIMEOUT_MINUTES_MIN,
            max_value=EXECUTION_TIMEOUT_MINUTES_MAX,
        ) * 60

    @classmethod
    def get_test_suite_stuck_reset_minutes(cls) -> int:
        return cls.get_runtime_int(
            TEST_SUITE_STUCK_RESET_MINUTES_KEY,
            default=TEST_SUITE_STUCK_RESET_MINUTES_DEFAULT,
            min_value=EXECUTION_TIMEOUT_MINUTES_MIN,
            max_value=EXECUTION_TIMEOUT_MINUTES_MAX,
        )

    @classmethod
    def get_test_suite_timeout_retry_count(cls) -> int:
        return cls.get_runtime_int(
            TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY,
            default=TEST_SUITE_TIMEOUT_RETRY_COUNT_DEFAULT,
            min_value=TEST_SUITE_TIMEOUT_RETRY_COUNT_MIN,
            max_value=TEST_SUITE_TIMEOUT_RETRY_COUNT_MAX,
        )

    @classmethod
    def get_test_suite_timeout_max_attempts(cls) -> int:
        return cls.get_test_suite_timeout_retry_count() + 1

    @classmethod
    def validate_environment_display_names(cls, value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return '部署环境名称必须是 JSON 对象'
        if not isinstance(value, dict):
            return '部署环境名称必须是 JSON 对象'
        defaults = EnvironmentEnum.default_obj()
        valid_keys = {str(key) for key in defaults}
        if any(key not in valid_keys for key in value):
            return '只能修改已有部署环境的名称，不能新增环境编号'
        if any(not isinstance(name, str) or not name.strip() or len(name.strip()) > 32 for name in value.values()):
            return '部署环境名称不能为空，且不能超过 32 个字符'
        effective = {key: value.get(str(key), name).strip() for key, name in defaults.items()}
        if len(set(effective.values())) != len(effective):
            return '部署环境名称不能重复（包括未修改的默认名称）'
        return None

    @classmethod
    def get_environment_display_names(cls) -> dict[str, str]:
        now = time.monotonic()
        cached = cls._environment_display_names_cache
        if cached and cached[0] > now:
            return dict(cached[1])
        aliases = cls.get(ENVIRONMENT_DISPLAY_NAMES_KEY, default={})
        if cls.validate_environment_display_names(aliases):
            aliases = {}
        elif isinstance(aliases, str):
            aliases = json.loads(aliases)
        aliases = {key: name.strip() for key, name in aliases.items()}
        cls._environment_display_names_cache = (now + cls._runtime_int_cache_seconds, aliases)
        return dict(aliases)

    @classmethod
    def get_registration_config(cls) -> dict:
        definitions = get_config_definition_map()
        return {
            'allow_registration': cls.get(
                'ALLOW_HOME_REGISTRATION', default=definitions['ALLOW_HOME_REGISTRATION'].default_value,
            ),
            'disabled_message': cls.get(
                'REGISTRATION_DISABLED_MESSAGE', default=definitions['REGISTRATION_DISABLED_MESSAGE'].default_value,
            ),
            'show_author_info': cls.get(
                'SHOW_LOGIN_AUTHOR_INFO', default=definitions['SHOW_LOGIN_AUTHOR_INFO'].default_value,
            ),
            'show_home_author_popup': cls.get(
                'SHOW_HOME_AUTHOR_POPUP', default=definitions['SHOW_HOME_AUTHOR_POPUP'].default_value,
            ),
            **cls.get_platform_branding(),
        }

    @classmethod
    def get_platform_branding(cls) -> dict[str, str]:
        definitions = get_config_definition_map()
        result = {}
        for field, key in (('platform_name', 'PLATFORM_NAME'), ('platform_name_en', 'PLATFORM_NAME_EN')):
            default = definitions[key].default_value
            value = cls.get(key, default=default)
            result[field] = value.strip() if isinstance(value, str) and value.strip() else default
        return result

    @classmethod
    def get_platform_name(cls) -> str:
        default = get_config_definition_map()['PLATFORM_NAME'].default_value
        value = cls.get('PLATFORM_NAME', default=default)
        return value.strip() if isinstance(value, str) and value.strip() else default

    @classmethod
    def get(cls, key: str, default=None):
        try:
            cache_data_obj = CacheData.objects.get(key=key)
        except CacheData.DoesNotExist:
            if default is not None:
                return default
            raise SystemError(SYSTEM_CONFIG_NOT_FOUND, value=(key,))
        return cls.cast_value(cache_data_obj.value, cache_data_obj.value_type, default)

    @classmethod
    async def aget(cls, key: str, default=None):
        try:
            cache_data_obj = await CacheData.objects.aget(key=key)
        except CacheData.DoesNotExist:
            if default is not None:
                return default
            raise SystemError(SYSTEM_CONFIG_NOT_FOUND, value=(key,))
        return cls.cast_value(cache_data_obj.value, cache_data_obj.value_type, default)

    @classmethod
    def cast_value(cls, value, value_type, default=None):
        if value is None:
            return default
        if value_type == CacheValueTypeEnum.INT.value:
            return int(value)
        if value_type == CacheValueTypeEnum.FLOAT.value:
            return float(value)
        if value_type == CacheValueTypeEnum.BOOL.value:
            return value in (True, "true", "True", "1", 1)
        if value_type in (CacheValueTypeEnum.DICT.value, CacheValueTypeEnum.JSON.value, CacheValueTypeEnum.LIST.value):
            return json.loads(value)
        return value

    @classmethod
    def get_api_worker_thread_pool_size(cls, default: int | None = None):
        fallback = default or API_WORKER_THREAD_POOL_SIZE_DEFAULT
        try:
            value = cls.get(API_WORKER_THREAD_POOL_SIZE_KEY, default=fallback)
        except Exception:
            value = fallback
        return cls.normalize_int_range(
            value,
            default=fallback,
            min_value=API_WORKER_THREAD_POOL_SIZE_MIN,
            max_value=API_WORKER_THREAD_POOL_SIZE_MAX,
        )

    @classmethod
    def get_data_factory_validation_environments(cls) -> list[int] | None:
        """空配置表示保持兼容并校验全部已绑定环境。"""
        try:
            value = cls.get(DATA_FACTORY_VALIDATION_ENVIRONMENTS_KEY, default=[])
        except Exception:
            value = []
        environments = cls.normalize_environment_list(value)
        return environments or None

    @classmethod
    def get_sql_slow_query_threshold_seconds(cls) -> int:
        try:
            value = cls.get(
                SQL_SLOW_QUERY_THRESHOLD_SECONDS_KEY,
                default=SQL_SLOW_QUERY_THRESHOLD_SECONDS_DEFAULT,
            )
        except Exception:
            value = SQL_SLOW_QUERY_THRESHOLD_SECONDS_DEFAULT
        return cls.normalize_int_range(
            value,
            default=SQL_SLOW_QUERY_THRESHOLD_SECONDS_DEFAULT,
            min_value=1,
            max_value=3600,
        )

    @classmethod
    async def aget_api_worker_thread_pool_size(cls, default: int | None = None):
        fallback = default or API_WORKER_THREAD_POOL_SIZE_DEFAULT
        try:
            value = await cls.aget(API_WORKER_THREAD_POOL_SIZE_KEY, default=fallback)
        except Exception:
            value = fallback
        return cls.normalize_int_range(
            value,
            default=fallback,
            min_value=API_WORKER_THREAD_POOL_SIZE_MIN,
            max_value=API_WORKER_THREAD_POOL_SIZE_MAX,
        )

    @classmethod
    def guest_can_view_all_project_data(cls):
        now = time.monotonic()
        if (
                cls._guest_project_data_scope_cache_value is not None and
                cls._guest_project_data_scope_cache_expires_at > now
        ):
            return cls._guest_project_data_scope_cache_value
        try:
            value = bool(cls.get(GUEST_CAN_VIEW_ALL_PROJECT_DATA_KEY, default=False))
        except Exception:
            value = False
        cls._guest_project_data_scope_cache_value = value
        cls._guest_project_data_scope_cache_expires_at = now + GUEST_PROJECT_DATA_SCOPE_CACHE_SECONDS
        return value

    @staticmethod
    def normalize_int_range(value, default: int, min_value: int, max_value: int):
        try:
            normalized_value = int(value)
        except (TypeError, ValueError):
            normalized_value = default
        return max(min_value, min(max_value, normalized_value))
