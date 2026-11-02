from enum import Enum


class _CallbackEnum(str, Enum):
    def __new__(cls, value, label):
        member = str.__new__(cls, value)
        member._value_ = value
        member.label = label
        return member

    @classmethod
    def get_option(cls):
        return [{'key': item.value, 'title': item.label} for item in cls]


class CallbackRunStatus(_CallbackEnum):
    NOT_RUN = 'not_run', '未执行'
    WAITING = 'waiting', '等待中'
    PASSED = 'passed', '通过'
    FAILED = 'failed', '失败'
    TIMEOUT = 'timeout', '超时'
    CANCELLED = 'cancelled', '已取消'


class CallbackSource(_CallbackEnum):
    HEADER = 'header', '请求头'
    QUERY = 'query', 'Query'
    PATH = 'path', '路径参数'
    ENVELOPE = 'envelope_json', '外层 JSON'
    BUSINESS = 'business_json', '业务 JSON（解密后）'
    RAW = 'raw_body', '原始正文'


class CallbackCheckType(_CallbackEnum):
    FIELD = 'field', '字段断言'
    COMPACT = 'json_compact', '紧凑 JSON'
    SIGNATURE = 'lark_signature', '飞书协议原始正文验签'
    COMPACT_SIGNATURE_SIMULATION = 'lark_compact_signature_simulation', '客户压紧后验签模拟（仅诊断）'


class CallbackResponseMode(_CallbackEnum):
    OBSERVE = 'observe', '观察模式，保持原响应'
    STRICT = 'strict', '严格模式，返回错误'


class CallbackEventMode(_CallbackEnum):
    AT_LEAST = 'at_least', '至少'
    EXACT = 'exact', '精确'


class CallbackDeliveryPolicy(_CallbackEnum):
    ALL = 'all_observed_pass', '所有已观测投递通过'
    EVENTUAL = 'eventual_success', '各事件最终成功'


class CallbackErrorCode(str, Enum):
    AMBIGUOUS = 'CALLBACK_AMBIGUOUS'
    DEPENDENCY_CHANGED = 'CALLBACK_DEPENDENCY_CHANGED'
    STORAGE_UNAVAILABLE = 'CALLBACK_STORAGE_UNAVAILABLE'
