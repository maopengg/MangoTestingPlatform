import asyncio
from dataclasses import dataclass, field

from mangoautomation.uidrives import AndroidDriverFactory, AndroidRuntime, BaseData

from src.tools.log_collector import log


@dataclass
class AndroidLease:
    equipment: str
    owner: str
    runtime: AndroidRuntime
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class AndroidDevicePool:
    _leases: dict[str, AndroidLease] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def acquire(
        cls,
        base_data: BaseData,
        equipment: str,
        package_name: str | None,
        owner: str,
    ):
        equipment_key = str(equipment or "default")
        async with cls._lock:
            lease = cls._leases.get(equipment_key)
            if lease is None:
                lease = AndroidLease(
                    equipment=equipment_key,
                    owner=owner,
                    runtime=AndroidDriverFactory.create_runtime(equipment),
                )
                cls._leases[equipment_key] = lease
        if lease.lock.locked() and lease.owner == owner:
            base_data.package_name = package_name
            setattr(base_data, "_runtime_session_id", owner)
            setattr(base_data, "_android_equipment", equipment_key)
            if base_data.android is None:
                base_data.bind_android(lease.runtime, lease.runtime.connect(), package_name)
            log.debug(f"[安卓设备租约] 复用设备：{equipment_key}，owner={owner}")
            return base_data.android
        await lease.lock.acquire()
        lease.owner = owner
        base_data.package_name = package_name
        if base_data.android is None:
            base_data.bind_android(lease.runtime, lease.runtime.connect(), package_name)
        setattr(base_data, "_runtime_session_id", owner)
        setattr(base_data, "_android_equipment", equipment_key)
        log.debug(f"[安卓设备租约] 已获取设备：{equipment_key}，owner={owner}")
        return base_data.android

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
                lease.lock.release()
                log.debug(f"[安卓设备租约] 已释放设备：{lease.equipment}，owner={lease.owner}")
