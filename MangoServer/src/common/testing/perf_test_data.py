import secrets
import string
import uuid

import time
from mangotools.decorator import data_method

from src.common.exceptions import CommonError, TEST_DATA_METHOD_ARGUMENT_INVALID
from src.common.utils.snowflake import Snowflake


class PerfTestDataMethods:
    """Case-side counterparts of the lightweight functions supported by k6."""

    @classmethod
    @data_method('performance', '性能测试', '每次调用生成 UUID 字符串', sort=1)
    def perf_uuid(cls) -> str:
        return str(uuid.uuid4())

    @classmethod
    @data_method('performance', '性能测试', '生成雪花式分布式唯一 ID（十进制字符串）', sort=2)
    def perf_snowflake_id(cls) -> str:
        return str(Snowflake.snowflake_id())

    @classmethod
    @data_method('performance', '性能测试', '生成当前毫秒时间戳', sort=3)
    def perf_timestamp_ms(cls) -> str:
        return str(int(time.time() * 1000))

    @classmethod
    @data_method('performance', '性能测试', '生成当前秒级时间戳', sort=4)
    def perf_timestamp_s(cls) -> str:
        return str(int(time.time()))

    @classmethod
    @data_method('performance', '性能测试', '生成字母数字随机字符串，长度 1～256', sort=5)
    def perf_random_string(cls, length=12) -> str:
        size = cls._perf_length(length)
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(size))

    @classmethod
    @data_method('performance', '性能测试', '生成指定范围内的随机整数', sort=6)
    def perf_random_int(cls, left=0, right=1000000) -> int:
        try:
            minimum, maximum = int(left), int(right)
        except (TypeError, ValueError) as exc:
            raise CommonError(TEST_DATA_METHOD_ARGUMENT_INVALID, value=('left 和 right 必须是整数',)) from exc
        if minimum > maximum or minimum < -9007199254740991 or maximum > 9007199254740991 or maximum - minimum >= 9007199254740991:
            raise CommonError(TEST_DATA_METHOD_ARGUMENT_INVALID, value=('随机整数范围无效或超出安全整数范围',))
        return minimum + secrets.randbelow(maximum - minimum + 1)

    @classmethod
    @data_method('performance', '性能测试', '生成纯数字字符串，保留前导零', sort=7)
    def perf_random_digits(cls, length=8) -> str:
        size = cls._perf_length(length)
        return ''.join(secrets.choice(string.digits) for _ in range(size))

    @classmethod
    @data_method('performance', '性能测试', '生成小写十六进制字符串', sort=8)
    def perf_random_hex(cls, length=16) -> str:
        size = cls._perf_length(length)
        return ''.join(secrets.choice(string.hexdigits[:16]) for _ in range(size))

    @classmethod
    @data_method('performance', '性能测试', '生成 32 位十六进制 Trace ID', sort=9)
    def perf_trace_id(cls) -> str:
        return uuid.uuid4().hex

    @classmethod
    @data_method('performance', '性能测试', '生成不带连字符的 UUID', sort=10)
    def perf_uuid_hex(cls) -> str:
        return uuid.uuid4().hex

    @classmethod
    @data_method('performance', '性能测试', '生成 example.com 示例邮箱', sort=11)
    def perf_random_email(cls) -> str:
        return f'perf-{uuid.uuid4().hex}@example.com'

    @classmethod
    @data_method('performance', '性能测试', '生成带前缀的唯一字符串', sort=12)
    def perf_unique_string(cls, prefix='perf') -> str:
        prefix = str(prefix)
        if not prefix or len(prefix) > 32 or not all(character.isalnum() or character in '_-' for character in prefix):
            raise CommonError(TEST_DATA_METHOD_ARGUMENT_INVALID,
                              value=('prefix 只能包含字母、数字、下划线和连字符，长度 1～32',))
        return f'{prefix}-{uuid.uuid4().hex}'

    @classmethod
    @data_method('performance', '性能测试', '生成指定长度的小写字母串', sort=13)
    def perf_random_lowercase(cls, length=12) -> str:
        size = cls._perf_length(length)
        return ''.join(secrets.choice(string.ascii_lowercase) for _ in range(size))

    @classmethod
    def _perf_length(cls, length) -> int:
        try:
            size = int(length)
        except (TypeError, ValueError) as exc:
            raise CommonError(TEST_DATA_METHOD_ARGUMENT_INVALID, value=('length 必须是 1～256 的整数',)) from exc
        if not 1 <= size <= 256:
            raise CommonError(TEST_DATA_METHOD_ARGUMENT_INVALID, value=('length 必须是 1～256 的整数',))
        return size
