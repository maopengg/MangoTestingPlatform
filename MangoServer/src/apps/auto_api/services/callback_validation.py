"""回调检查的纯计算部分；签名始终使用进入应用的原始正文。"""
import hashlib
import hmac
import json
import math

from src.apps.auto_api.enums.callback import CallbackCheckType, CallbackSource
from src.apps.auto_api.services.mock_request_decryption import MockRequestDecryptionService
from src.apps.auto_api.services.mock_runtime import MockRuntimeService


def strict_json(text):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('JSON包含重复键')
            result[key] = value
        return result
    def reject_constant(_):
        raise ValueError('JSON包含非有限数值')

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('JSON数值溢出')
        return number

    return json.loads(text, object_pairs_hook=unique_pairs,
                      parse_constant=reject_constant, parse_float=finite_float)


def compact_json_text(text):
    strict_json(text)
    quoted = escaped = False
    parts = []
    for char in text:
        if quoted:
            parts.append(char)
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
            parts.append(char)
        elif char not in ' \r\n\t':
            parts.append(char)
    return ''.join(parts)


def compact_json(text):
    return compact_json_text(text) == text


def extract_callback_value(source, field, context, envelope):
    if source == CallbackSource.ENVELOPE:
        from src.common.responses.json_response import extract_jsonpath_value
        return extract_jsonpath_value(envelope, field, operation='回调关联')
    source_map = {CallbackSource.BUSINESS: 'json_body', CallbackSource.RAW: 'text_body'}
    value, error = MockRuntimeService._extract_value(
        {'source': source_map.get(source, source), 'field': field}, context,
    )
    if error:
        raise ValueError('无法提取回调字段')
    return value


def validate_delivery(rule, raw, headers, context, decryption, *, test_data=None):
    results = []
    try:
        text = raw.decode('utf-8')
    except UnicodeError:
        text = ''
        results.append({'key': 'encoding', 'passed': False, 'message': '正文不是有效UTF-8文本'})
    try:
        envelope = strict_json(text)
    except ValueError:
        envelope = None
        needs_json = any(item['source'] in {CallbackSource.BUSINESS, CallbackSource.ENVELOPE}
                         or item['type'] == CallbackCheckType.COMPACT for item in rule['checks'])
        if needs_json:
            results.append({'key': 'body', 'passed': False, 'message': '正文不是有效且键唯一的JSON'})
    business_text = text
    if decryption.get('type') == MockRequestDecryptionService.TYPE_LARK_EVENT:
        business_text, _ = MockRequestDecryptionService.decrypt_body(text, decryption, preserve_text=True)
        strict_json(business_text)
    lowered = {key.lower(): str(value) for key, value in headers.items()}
    if lowered.get('content-encoding', 'identity').lower() != 'identity':
        results.append({'key': 'content_encoding', 'passed': False, 'message': '暂不支持HTTP内容压缩验签'})
    for item in rule['checks']:
        passed = False
        message = ''
        details = None
        try:
            if item['type'] == CallbackCheckType.COMPACT:
                passed = compact_json(business_text if item['source'] == CallbackSource.BUSINESS else text)
                message = 'JSON字符串之外存在格式空白' if not passed else ''
            elif item['type'] in {CallbackCheckType.SIGNATURE, CallbackCheckType.COMPACT_SIGNATURE_SIMULATION}:
                timestamp = lowered.get('x-lark-request-timestamp', '')
                nonce = lowered.get('x-lark-request-nonce', '')
                signature = lowered.get('x-lark-signature', '')
                key = decryption.get('encrypt_key', '')
                if timestamp and nonce and signature and key:
                    signing_body = compact_json_text(text).encode('utf-8') if item['type'] == CallbackCheckType.COMPACT_SIGNATURE_SIMULATION else raw
                    calculated = hashlib.sha256((timestamp + nonce + key).encode('utf-8') + signing_body).hexdigest()
                    passed = hmac.compare_digest(calculated, signature)
                message = '原始正文签名不匹配或协议字段／密钥缺失' if not passed else ''
            else:
                actual = text if item['source'] == CallbackSource.RAW else extract_callback_value(
                    item['source'], item['field'], context, envelope,
                )
                from src.apps.auto_api.services.mock_runtime import MISSING
                if item.get('assertions'):
                    from src.apps.auto_api.services.callback_general import CallbackGeneralAssertionService
                    passed, details = CallbackGeneralAssertionService.evaluate(item['assertions'], actual, test_data)
                else:
                    operator = item['operator']
                    passed = (actual is not MISSING) if operator == 'exists' else (
                        actual == item['expected'] if operator == 'equals' else item['expected'] in actual
                    )
                message = '回调字段断言不匹配' if not passed else ''
        except Exception:
            message = '回调检查无法完成，请检查字段与类型'
        results.append({'key': item['key'], 'passed': bool(passed), 'message': message,
                        'diagnostic': item['type'] == CallbackCheckType.COMPACT_SIGNATURE_SIMULATION})
        if details is not None:
            results[-1]['assertions'] = details
    return results, business_text
