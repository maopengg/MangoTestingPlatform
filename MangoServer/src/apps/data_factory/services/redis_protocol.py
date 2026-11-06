from redis._parsers.resp2 import _RESP2Parser

from src.apps.data_factory.services.datasource_cost import DatasourceCostService
from src.apps.system.services.system_config import SystemConfigService


class BoundedRedisBuffer:
    def __init__(self, buffer):
        self.buffer = buffer
        self.items = 0
        self.bytes = 0
        self.maximum = SystemConfigService.get_ranged_int('REDIS_MAX_RESPONSE_ITEMS')

    def __getattr__(self, key):
        return getattr(self.buffer, key)

    def readline(self):
        line = self.buffer.readline()
        if line[:1] != b'*':
            self.items += 1
        self.bytes += len(line)
        maximum = self.maximum
        if self.items > maximum:
            DatasourceCostService.reject(f'Redis返回结果超过元素数上限：当前配置为 {maximum} 个，已读取至少 {self.items} 个。请缩小用例查询范围；本次不返回截断结果')
        if self.bytes > 1_048_576:
            DatasourceCostService.reject(f'Redis返回结果超过大小上限：最多允许 1048576 字节，已读取至少 {self.bytes} 字节。请缩小用例查询范围；本次不返回截断结果')
        if line[:1] in (b'*', b'$'):
            size = int(line[1:])
            if line[:1] == b'*' and size > maximum:
                DatasourceCostService.reject(f'Redis返回数组声明包含 {size} 个元素，超过当前配置上限 {maximum} 个。请缩小用例查询范围；本次不返回截断结果')
            if line[:1] == b'$' and size > 1_048_576:
                DatasourceCostService.reject(f'Redis返回字符串声明长度为 {size} 字节，超过大小上限 1048576 字节。请缩小用例查询范围；本次不返回截断结果')
        return line

    def read(self, length):
        if length < 0:
            DatasourceCostService.reject('Redis响应包含非法的负数读取长度，无法完整解析结果。请管理员检查协议解析日志')
        if self.bytes + length > 1_048_576:
            DatasourceCostService.reject(f'Redis返回结果超过大小上限：最多允许 1048576 字节，继续读取将达到 {self.bytes + length} 字节。请缩小用例查询范围；本次不返回截断结果')
        self.bytes += length
        return self.buffer.read(length)


class BoundedRedisParser(_RESP2Parser):
    def read_response(self, disable_decoding=False):
        if self._buffer and not isinstance(self._buffer, BoundedRedisBuffer):
            self._buffer = BoundedRedisBuffer(self._buffer)
        elif self._buffer:
            self._buffer.maximum = SystemConfigService.get_ranged_int('REDIS_MAX_RESPONSE_ITEMS')
        if self._buffer:
            self._buffer.items = self._buffer.bytes = 0
        return super().read_response(disable_decoding=disable_decoding)
