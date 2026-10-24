from src.common.enums.base import BaseEnum

AUTOMATION_EXECUTION_SCENE_OPTIONS = {
    'routine_regression': '回归测试',
    'release_verification': '发布验证',
    'smoke_verification': '冒烟验证',
    'stability_monitoring': '稳定性监测',
    'data_verification': '数据校验',
    'effectiveness_test': '效果评测',
    'production_inspection': '生产巡检',
    'production_regression': '生产回归',
}


class AutomationExecutionSceneEnum(BaseEnum):
    """自动化执行场景。未分类仅用于兼容历史定时任务。"""
    UNCLASSIFIED = 'unclassified'
    ROUTINE_REGRESSION = 'routine_regression'
    RELEASE_VERIFICATION = 'release_verification'
    SMOKE_VERIFICATION = 'smoke_verification'
    STABILITY_MONITORING = 'stability_monitoring'
    DATA_VERIFICATION = 'data_verification'
    EFFECTIVENESS_TEST = 'effectiveness_test'
    PRODUCTION_INSPECTION = 'production_inspection'
    PRODUCTION_REGRESSION = 'production_regression'

    @classmethod
    def obj(cls):
        return {cls.UNCLASSIFIED.value: '未分类', **AUTOMATION_EXECUTION_SCENE_OPTIONS}


class ReportRetentionPolicyEnum(BaseEnum):
    ALL = 'all'
    ABNORMAL_ONLY = 'abnormal_only'

    @classmethod
    def obj(cls):
        return {cls.ALL.value: '全部保留', cls.ABNORMAL_ONLY.value: '仅保留异常报告'}


class AutomationExecutionScopeEnum(BaseEnum):
    """定时任务执行范围。未分类仅用于兼容历史数据。"""
    UNCLASSIFIED = 'unclassified'
    MANUAL = 'manual'
    FULL_PRODUCT = 'full_product'
    MODULE = 'module'

    @classmethod
    def obj(cls):
        return {
            cls.UNCLASSIFIED.value: '未分类',
            cls.MANUAL.value: '手动指定',
            cls.FULL_PRODUCT.value: '产品全量',
            cls.MODULE.value: '模块全量',
        }


class ExecutorTaskErrorCodeEnum(BaseEnum):
    CANCELLED = "cancelled"
    SCHEDULE_TIMEOUT = "schedule_timeout"
    EXECUTION_TIMEOUT = "execution_timeout"
    CLAIM_LEASE_RELEASED = "claim_lease_released"
    LEASE_LOST_RETRYING = "lease_lost_retrying"
    EXECUTOR_DISCONNECTED = "executor_disconnected"
    EXECUTOR_DRAINING = "executor_draining"
