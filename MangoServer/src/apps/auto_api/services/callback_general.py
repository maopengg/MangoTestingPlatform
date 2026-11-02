import base64
from copy import deepcopy
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

from src.apps.auto_api.exceptions import AutoApiError, API_CALLBACK_CONFIG_INVALID, API_CALLBACK_EXECUTION_FAILED
from src.apps.auto_api.services.base.case_parameter import CaseParameter
from src.common.testing import ObtainTestData


class CallbackGeneralAssertionService:
    @staticmethod
    def cipher():
        # 仅用于最长 300 秒的执行上下文，不作为跨版本持久密钥；更换实例密钥时明确失败。
        key = hashlib.sha256(('callback-context:' + settings.SECRET_KEY).encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    @classmethod
    def freeze(cls, test_data):
        try:
            payload = {'cache': test_data.get_all(), 'factory': test_data.get_data_factory_snapshot()}
            raw = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
        except (TypeError, ValueError, AttributeError) as error:
            raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('本次断言缓存必须是可序列化的 JSON 数据',)) from error
        if len(raw) > 1024 * 1024:
            raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('回调断言上下文超过 1MB，请精简本次执行缓存',))
        return cls.cipher().encrypt(raw).decode('ascii')

    @classmethod
    def restore(cls, ciphertext):
        try:
            payload = json.loads(cls.cipher().decrypt(ciphertext.encode('ascii'), ttl=600))
        except (InvalidToken, ValueError, TypeError, AttributeError) as error:
            raise AutoApiError(API_CALLBACK_EXECUTION_FAILED, value=('回调断言上下文已失效，请重新执行 Case',)) from error
        data = ObtainTestData()
        data.set_dict_cache(payload['cache'])
        for key, value in payload['factory'].items():
            data.set_data_factory_cache(key, value)
        return data

    @staticmethod
    def evaluate(assertions, actual, test_data):
        if test_data is None:
            raise AutoApiError(API_CALLBACK_EXECUTION_FAILED, value=('缺少本次回调断言上下文',))
        configured = deepcopy(assertions)
        # 保留所有比较参数；只有 actual 固定来自本条回调提取值，绝不覆盖 Case 原缓存。
        test_data.set_cache('__callback_actual__', actual)
        for item in configured:
            for parameter in item['value']['parameter']:
                if parameter['f'] == 'actual':
                    parameter['v'] = '${{__callback_actual__}}'
        passed, results = CaseParameter.evaluate_general_assertions(configured, test_data)
        # 不复制可能包含授权凭证的实际值、预期值、原始配置或异常文案到普通日志／报告。
        details = [{'method': item.method, 'status': item.status, 'group_name': item.group_name,
                    'group_logic': item.group_logic, 'group_result': item.group_result,
                    'source_type': item.source_type, 'assertion_index': item.assertion_index}
                   for item in results]
        return passed, details
