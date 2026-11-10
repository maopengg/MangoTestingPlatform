from src.apps.task_center.enums.execution import AUTOMATION_EXECUTION_SCENE_OPTIONS, AutomationExecutionSceneEnum
from src.common.enums.base import BaseEnum


class ApiCaseReleaseStatusEnum(BaseEnum):
    PREPUBLISHED = 'prepublished', '预发布'
    PUBLISHED = 'published', '已发布'
    DEPRECATED = 'deprecated', '已取消发布'
    RETIRED = 'retired', '已归档'


class ApiCaseConfigurationFilterEnum(BaseEnum):
    HAS_SQL = 'has_sql', '有 SQL'
    NO_SQL = 'no_sql', '无 SQL'
    HAS_DATA_FACTORY = 'has_data_factory', '有数据工厂'
    NO_DATA_FACTORY = 'no_data_factory', '无数据工厂'


class ApiCaseScenarioTypeEnum(BaseEnum):
    """Case 验证类型"""
    NORMAL = 0
    EXCEPTION = 1
    BOUNDARY = 2
    PERMISSION = 3
    DATA = 4
    FLOW = 5

    @classmethod
    def obj(cls):
        return {
            0: "正常场景",
            1: "异常场景",
            2: "边界场景",
            3: "权限场景",
            4: "数据场景",
            5: "流程场景",
        }


class ApiCaseScenarioLayerEnum(BaseEnum):
    """Case 测试层级"""
    API = 0
    INTEGRATION = 1
    E2E = 2

    @classmethod
    def obj(cls):
        return {
            0: "接口/组件级",
            1: "模块级",
            2: "端到端",
        }


class ApiCaseScenarioTagEnum(BaseEnum):
    """自动化执行场景。效果评测、临时验证和性能测试仅供 Case 标记，不开放给定时任务。"""
    REGRESSION = AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value
    RELEASE_VERIFICATION = AutomationExecutionSceneEnum.RELEASE_VERIFICATION.value
    SMOKE = AutomationExecutionSceneEnum.SMOKE_VERIFICATION.value
    STABILITY_MONITORING = AutomationExecutionSceneEnum.STABILITY_MONITORING.value
    DATA_VERIFICATION = AutomationExecutionSceneEnum.DATA_VERIFICATION.value
    EFFECTIVENESS_TEST = AutomationExecutionSceneEnum.EFFECTIVENESS_TEST.value
    PRODUCTION_INSPECTION = AutomationExecutionSceneEnum.PRODUCTION_INSPECTION.value
    PRODUCTION_REGRESSION = AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value
    TEMPORARY_VALIDATION = 'temporary_validation'
    PERFORMANCE_TEST = 'performance_test'

    @classmethod
    def obj(cls):
        return {
            **AUTOMATION_EXECUTION_SCENE_OPTIONS,
            cls.TEMPORARY_VALIDATION.value: '临时验证',
            cls.PERFORMANCE_TEST.value: '性能测试',
        }
