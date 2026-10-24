from src.common.enums.base import BaseEnum


class ReportFailureReasonEnum(BaseEnum):
    PRODUCT_PENDING = 'product_pending'
    PRODUCT_ACCEPTED = 'product_accepted'
    TEST_CASE = 'test_case'
    PLATFORM = 'platform'
    ENVIRONMENT = 'environment'
    OTHER = 'other'

    @classmethod
    def obj(cls):
        return {
            cls.PRODUCT_PENDING.value: '产品缺陷待修复',
            cls.PRODUCT_ACCEPTED.value: '已接受产品缺陷',
            cls.TEST_CASE.value: '测试用例问题',
            cls.PLATFORM.value: '测试平台问题',
            cls.ENVIRONMENT.value: '环境／依赖问题',
            cls.OTHER.value: '其他原因',
        }


class CaseLevelEnum(BaseEnum):
    """测试用例级别"""
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3

    @classmethod
    def obj(cls):
        return {0: "高", 1: "中", 2: "低", 3: "极低"}
