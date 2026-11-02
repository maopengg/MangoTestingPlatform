import ipaddress
import socket
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from threading import BoundedSemaphore
from urllib.parse import urlsplit

from mangotools.enums import DriveTypeEnum

from src.apps.test_center.enums.environment import AutoTypeEnum
from src.apps.test_center.exceptions import (
    TEST_TARGET_PROBE_ADDRESS_INVALID, TEST_TARGET_PROBE_DENIED, TestCenterError,
)
from src.apps.test_center.models import TestObject
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService


class TestObjectProbeService:
    """只连接已保存地址的 TCP 端口，不发送 HTTP、认证或业务请求。"""

    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='test-object-probe')
    _slots = BoundedSemaphore(4)
    TIMEOUT_SECONDS = 5

    @staticmethod
    def network_options(obj):
        if obj.auto_type == AutoTypeEnum.UI.value and obj.project_product.ui_client_type != DriveTypeEnum.WEB.value:
            return []
        if obj.auto_type not in {item.value for item in AutoTypeEnum}:
            return []
        config = obj.target_config or {}
        candidates = [('默认地址', obj.value)] if obj.value else [
            ('默认地址', config.get('default', '')),
            *((f'条件值：{key}', value) for key, value in (config.get('mapping') or {}).items()),
        ]
        options, seen = [], set()
        for label, value in candidates:
            value = str(value or '').strip()
            if value in seen or TestObjectProbeService.network_target(value) is None:
                continue
            seen.add(value)
            options.append({'label': label, 'value': value})
        return options

    @staticmethod
    def network_target(address):
        try:
            parsed = urlsplit(address)
            if parsed.scheme.lower() not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
                return None
            port = parsed.port if parsed.port is not None else (443 if parsed.scheme.lower() == 'https' else 80)
            if not 1 <= port <= 65535:
                return None
            return parsed.hostname, port
        except ValueError:
            return None

    @classmethod
    def test(cls, object_id, address, user):
        if user is None or (not PermissionMenuService.is_effective_super_admin(user)
                            and 'config.test_object:change' not in PermissionMenuService.permission_keys_for_user(user)):
            raise TestCenterError(TEST_TARGET_PROBE_DENIED)
        obj = TestObject.objects.select_related('project_product').filter(id=object_id).first()
        if obj is None or not ProjectProductScopeService.has_project_product(user, obj.project_product_id):
            raise TestCenterError(TEST_TARGET_PROBE_DENIED)
        options = [item['value'] for item in cls.network_options(obj)]
        address = address or (options[0] if options else '')
        if not address or address not in options:
            raise TestCenterError(TEST_TARGET_PROBE_ADDRESS_INVALID)
        result = {'address': address, 'connected': False, 'host': '', 'port': None,
                  'resolved_ips': [], 'elapsed_ms': 0, 'message': ''}
        host, port = cls.network_target(address)
        result.update(host=host, port=port)
        if not cls._slots.acquire(blocking=False):
            return {**result, 'message': '服务器正在检测其他地址，请稍后重试。'}
        started = time.monotonic()
        try:
            future = cls._executor.submit(cls._probe, host, port)
        except Exception:
            cls._slots.release()
            raise
        # DNS 解析无法由 socket timeout 中断；超时任务仍占用槽位，防止积累无界线程或队列。
        future.add_done_callback(lambda _: cls._slots.release())
        try:
            result.update(future.result(timeout=cls.TIMEOUT_SECONDS))
        except FutureTimeout:
            result['message'] = '检测超时，服务器未能在 5 秒内完成域名解析或端口连接。'
        result['elapsed_ms'] = round((time.monotonic() - started) * 1000)
        return result

    @staticmethod
    def _safe_ip(value):
        address = ipaddress.ip_address(value.split('%')[0])
        address = getattr(address, 'ipv4_mapped', None) or address
        return not (address.is_loopback or address.is_link_local or address.is_multicast
                    or address.is_unspecified or address.is_reserved
                    or str(address) in {'100.100.100.200', 'fd00:ec2::254'})

    @classmethod
    def _probe(cls, host, port):
        try:
            entries = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except (OSError, UnicodeError):
            return {'message': '域名解析失败，请检查服务器 DNS 或域名配置。'}
        ips = list(dict.fromkeys(item[4][0] for item in entries))
        if not ips or any(not cls._safe_ip(ip) for ip in ips):
            return {'message': '不允许检测回环、链路本地、云元数据或其他特殊地址。'}
        deadline = time.monotonic() + 3
        for family, socktype, protocol, _, sockaddr in entries[:3]:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                with socket.socket(family, socktype, protocol) as connection:
                    connection.settimeout(min(remaining, 1))
                    # 使用刚验证的 IP，避免二次 DNS 解析改变实际连接目标。
                    connection.connect(sockaddr)
                return {'connected': True, 'resolved_ips': ips, 'message': '服务器可连接该地址的 TCP 端口。'}
            except OSError:
                continue
        return {'resolved_ips': ips, 'message': '域名解析成功，但端口连接失败，请检查服务、端口、防火墙或网络。'}
