import asyncio
from dataclasses import dataclass, field

from mangoautomation.uidrives import BaseData, IOSDriverFactory, IOSRuntime

from src.tools.log_collector import log


@dataclass
class IOSLease:
    equipment: str
    owner: str
    runtime: IOSRuntime
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    connect_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class IOSDevicePool:
    _leases: dict[str, IOSLease] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def acquire(cls, base_data: BaseData, server_url: str, capabilities: dict, owner: str):
        equipment = str(capabilities.get('appium:udid') or capabilities.get('appium:deviceName') or 'ios-default')
        created = False
        async with cls._lock:
            lease = cls._leases.get(equipment)
            if lease is None:
                lease = IOSLease(
                    equipment=equipment,
                    owner='',
                    runtime=IOSDriverFactory.create_runtime(server_url, capabilities),
                )
                cls._leases[equipment] = lease
                created = True
        acquired_here = False
        if not (lease.lock.locked() and lease.owner == owner):
            await lease.lock.acquire()
            acquired_here = True
            lease.owner = owner
        try:
            # Appium Python Client 是同步客户端，建连可能包含 WDA 启动和应用安装，
            # 放在线程中避免阻塞执行器的任务领取、心跳和直播消息循环。
            async with lease.connect_lock:
                driver = await asyncio.to_thread(lease.runtime.connect)
            base_data.bind_ios(lease.runtime, driver, capabilities.get('appium:bundleId'))
        except Exception:
            if acquired_here and lease.lock.locked() and lease.owner == owner:
                lease.owner = ''
                lease.lock.release()
            if created:
                async with cls._lock:
                    if cls._leases.get(equipment) is lease and not lease.lock.locked():
                        cls._leases.pop(equipment, None)
            raise
        setattr(base_data, '_runtime_session_id', owner)
        setattr(base_data, '_ios_equipment', equipment)
        log.debug(f'[iOS设备租约] 已获取设备：{equipment}，owner={owner}')
        return base_data.ios

    @classmethod
    async def release(cls, equipment: str | None = None, owner: str | None = None) -> None:
        async with cls._lock:
            leases = list(cls._leases.values())
        for lease in leases:
            if equipment and lease.equipment != str(equipment):
                continue
            if owner and lease.owner != owner:
                continue
            if lease.lock.locked():
                released_owner = lease.owner
                lease.owner = ''
                lease.lock.release()
                log.debug(f'[iOS设备租约] 已释放设备：{lease.equipment}，owner={released_owner}')
