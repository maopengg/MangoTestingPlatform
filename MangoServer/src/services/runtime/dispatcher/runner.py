import socket
import time

from src.apps.task_center.services.dispatch_service import ScheduleDispatchService
from src.common.tools.decorator.retry import async_task_db_connection
from src.common.tools.log_collector import log


class DispatchRunner:
    def __init__(self, node_name: str | None = None, poll_interval: int = 5):
        self.node_name = node_name or socket.gethostname()
        self.poll_interval = poll_interval
        self.running = True

    def run_forever(self):
        log.system.info(f'task-dispatcher 启动：node={self.node_name}')
        while self.running:
            handled = self.tick()
            if not handled:
                time.sleep(self.poll_interval)

    @async_task_db_connection(max_retries=1, retry_delay=1)
    def tick(self) -> bool:
        fire = ScheduleDispatchService.claim_pending_fire(self.node_name)
        if not fire:
            return False
        ScheduleDispatchService.dispatch_fire(fire, self.node_name)
        return True

