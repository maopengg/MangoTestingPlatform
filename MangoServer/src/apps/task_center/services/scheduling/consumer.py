import threading

import time
from django.db import close_old_connections

from src.apps.system.enums import RuntimeServiceName
from src.apps.task_center.services.scheduling.dispatch import ScheduleDispatchService
from src.common.decorators.system_error import system_error_guard
from src.common.enums.system_error import SystemErrorEventSource
from src.common.logging import log


class ScheduleFireConsumer:
    """在 scheduler-service 内异步消费普通测试任务触发记录。"""

    def __init__(
            self,
            node_name: str,
            stop_event: threading.Event,
            wakeup_event: threading.Event,
            poll_interval: float = 2,
            recovery_interval: float = 60,
    ):
        self.node_name = node_name
        self.stop_event = stop_event
        self.wakeup_event = wakeup_event
        self.poll_interval = poll_interval
        self.recovery_interval = recovery_interval
        self.last_recovery_at = 0.0

    def run_forever(self):
        log.system.info(f'scheduler-service 触发记录消费者启动：node={self.node_name}')
        try:
            while not self.stop_event.is_set():
                close_old_connections()
                try:
                    self.recover_stale_fires_if_due()
                except Exception as error:
                    # 恢复检查失败不能阻止正常待分发记录继续消费。
                    log.system.error(
                        f'scheduler-service 恢复超时触发记录异常：'
                        f'node={self.node_name}, error={error}'
                    )
                try:
                    if self.consume_next_fire():
                        continue
                except Exception as error:
                    # 单条记录或短暂数据库异常不能终止整个消费线程。
                    log.system.error(
                        f'scheduler-service 消费触发记录异常：node={self.node_name}, error={error}'
                    )
                self.wakeup_event.wait(self.poll_interval)
                self.wakeup_event.clear()
        finally:
            close_old_connections()
            log.system.info(f'scheduler-service 触发记录消费者停止：node={self.node_name}')

    @system_error_guard(
        source=SystemErrorEventSource.SCHEDULER,
        request_path='recover_stale_schedule_fires',
        service_name=RuntimeServiceName.SCHEDULER,
    )
    def recover_stale_fires_if_due(self):
        now = time.monotonic()
        if now - self.last_recovery_at < self.recovery_interval:
            return
        ScheduleDispatchService.recover_stale_dispatching_fires(self.node_name)
        self.last_recovery_at = now

    @system_error_guard(
        source=SystemErrorEventSource.SCHEDULER,
        request_path='consume_schedule_fire',
        service_name=RuntimeServiceName.SCHEDULER,
    )
    def consume_next_fire(self) -> bool:
        fire = ScheduleDispatchService.claim_pending_fire(self.node_name)
        if not fire:
            return False
        ScheduleDispatchService.dispatch_fire(fire, self.node_name)
        return True
