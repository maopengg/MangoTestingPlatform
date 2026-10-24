import asyncio

from src.processes.realtime.live_stream.registry import LiveStreamRegistry


class LiveStreamSupervisor:
    def __init__(self, registry: LiveStreamRegistry):
        self.registry = registry
        self.running = False
        self.event_loop_lag_ms = 0.0

    async def run_forever(self) -> None:
        self.running = True
        expected = asyncio.get_running_loop().time()
        while self.running:
            now = asyncio.get_running_loop().time()
            self.event_loop_lag_ms = max(0.0, (now - expected) * 1000)
            await self.registry.set_degraded(self.event_loop_lag_ms >= 500)
            await self.registry.cleanup_expired()
            expected = asyncio.get_running_loop().time() + 1
            await asyncio.sleep(1)

    async def stop(self) -> None:
        self.running = False
        await self.registry.close_all()
