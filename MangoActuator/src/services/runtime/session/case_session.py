from dataclasses import dataclass

from mangoautomation.uidrives import BaseData

from src.services.runtime.session.android_session import AndroidDevicePool
from src.services.runtime.session.close_utils import RuntimeCloseUtils


@dataclass
class CaseRuntimeSession:
    session_id: str
    base_data: BaseData
    android_equipment: str | None = None
    ios_equipment: str | None = None

    async def close_all(self, reason: str = "UI用例") -> None:
        await RuntimeCloseUtils.close_page_context(self.base_data, reason)
        await AndroidDevicePool.release(
            self.android_equipment or getattr(self.base_data, '_android_equipment', None),
            owner=self.session_id,
        )
        ios_equipment = self.ios_equipment or getattr(self.base_data, '_ios_equipment', None)
        if ios_equipment or getattr(self.base_data, 'ios', None) is not None:
            from src.services.runtime.session.ios_session import IOSDevicePool

            await IOSDevicePool.release(ios_equipment, owner=self.session_id)
