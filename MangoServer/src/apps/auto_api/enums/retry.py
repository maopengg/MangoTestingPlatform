from enum import Enum


class ApiTransientRetryCondition(str, Enum):
    CONNECTION = 'connection'
    TIMEOUT = 'timeout'
    HTTP_500 = 'http_500'
    HTTP_502 = 'http_502'
    HTTP_503 = 'http_503'
    HTTP_504 = 'http_504'
    ASSERTION = 'assertion_failed'

    @classmethod
    def get_option(cls):
        return [
            {'key': cls.CONNECTION.value, 'title': '连接失败／连接中断'},
            {'key': cls.TIMEOUT.value, 'title': '请求超时'},
            {'key': cls.HTTP_500.value, 'title': 'HTTP 500 · 服务内部异常'},
            {'key': cls.HTTP_502.value, 'title': 'HTTP 502 · 网关上游异常'},
            {'key': cls.HTTP_503.value, 'title': 'HTTP 503 · 服务暂不可用'},
            {'key': cls.HTTP_504.value, 'title': 'HTTP 504 · 网关超时'},
            {'key': cls.ASSERTION.value, 'title': '业务断言失败（谨慎选择）'},
        ]

    @classmethod
    def defaults(cls):
        return [item.value for item in (cls.CONNECTION, cls.TIMEOUT, cls.HTTP_502, cls.HTTP_503, cls.HTTP_504)]
