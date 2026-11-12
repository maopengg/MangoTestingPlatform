from django.db import DatabaseError

from src.apps.auto_api.enums import ApiProtocolTypeEnum
from src.apps.auto_api.enums.retry import ApiTransientRetryCondition
from src.apps.auto_api.exceptions import (
    API_REQUEST_TIMEOUT, API_TARGET_CONNECTION_FAILED, API_TARGET_NO_RESPONSE, AutoApiError,
)
from src.apps.system.services.configuration.system_config import API_TRANSIENT_RETRY_ENABLED_KEY, API_TRANSIENT_RETRY_CONDITIONS_KEY, SystemConfigService
from src.common.logging import log


class ApiTransientRetryService:
    @staticmethod
    def error_condition(error):
        if not isinstance(error, AutoApiError):
            return None
        if error.code == API_REQUEST_TIMEOUT.code:
            return ApiTransientRetryCondition.TIMEOUT
        if error.code in (API_TARGET_CONNECTION_FAILED.code, API_TARGET_NO_RESPONSE.code):
            return ApiTransientRetryCondition.CONNECTION
        return None

    @staticmethod
    def response_condition(response, *, call_success):
        if call_success:
            return ApiTransientRetryCondition.ASSERTION
        return {
            500: ApiTransientRetryCondition.HTTP_500,
            502: ApiTransientRetryCondition.HTTP_502,
            503: ApiTransientRetryCondition.HTTP_503,
            504: ApiTransientRetryCondition.HTTP_504,
        }.get(response.code)

    @staticmethod
    def safe(request, parameter, api_info, *, recovery=False, callbacks=False, factory_ran=False, gray=False):
        # 无显式幂等声明时，不能仅凭一次 HTTP/断言失败就重新执行可能写数据的场景。
        return (
            request.protocol_type == ApiProtocolTypeEnum.HTTP.value
            and request.method.upper() in ('GET', 'HEAD', 'OPTIONS')
            and not (recovery or callbacks or factory_ran or gray)
            and not any(getattr(parameter, field, None) for field in (
                'front_sql', 'front_func', 'posterior_sql', 'posterior_func', 'posterior_file',
                'posterior_response', 'posterior_response_text',
            ))
            and not getattr(api_info, 'posterior_func', None)
        )

    @staticmethod
    def selected(condition):
        if condition is None:
            return False
        try:
            if not SystemConfigService.get(API_TRANSIENT_RETRY_ENABLED_KEY, default=True):
                return False
            conditions = SystemConfigService.get(
                API_TRANSIENT_RETRY_CONDITIONS_KEY, default=ApiTransientRetryCondition.defaults(),
            )
        except (DatabaseError, ValueError, TypeError):
            log.api.warning('自动重试配置读取失败，本轮不额外重试')
            return False
        return isinstance(conditions, list) and condition.value in conditions
