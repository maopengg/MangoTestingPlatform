"""AI Worker 进程适配层。"""

from src.apps.ai.services.agent.worker import AgentWorkerService


class AiWorkerProcess:
    def __init__(self, worker_id: str | None = None):
        self._service = AgentWorkerService(worker_id)

    @property
    def worker_id(self) -> str:
        return self._service.worker_id

    def run_once(self) -> bool:
        return self._service.run_once()
