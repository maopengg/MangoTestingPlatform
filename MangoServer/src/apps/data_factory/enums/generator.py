from src.common.enums.base import BaseEnum


class DataFactoryGeneratorTypeEnum(BaseEnum):
    """字段生成方式"""
    SKIP = 0
    FIXED = 1
    RANDOM_STRING = 2
    RANDOM_INTEGER = 3
    RANDOM_DECIMAL = 4
    NOW = 5
    RELATIVE_TIME = 6
    UUID = 7
    ENUM = 9
    DEPENDENCY_FIELD = 11
    FUNCTION = 13

    @classmethod
    def obj(cls):
        return {
            0: "跳过",
            1: "固定值",
            2: "随机字符串（长度8）",
            3: "随机整数（1-100）",
            4: "随机小数（1-100，2位）",
            5: "当前时间",
            6: "相对时间",
            7: "UUID",
            9: "枚举值",
            11: "依赖实体字段",
            13: "测试数据方法",
        }
