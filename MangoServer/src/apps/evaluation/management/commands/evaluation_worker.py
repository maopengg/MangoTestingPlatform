import os
import socket
import time
import uuid
from django.core.management.base import BaseCommand
from src.apps.evaluation.services.execution import EvaluationCaseExecutionService


class Command(BaseCommand):
    help = "消费待执行评测，并恢复租约过期的评测运行"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="只扫描一次后退出")
        parser.add_argument("--poll-seconds", type=float, default=2.0)
        parser.add_argument("--batch-size", type=int, default=10)

    def handle(self, *args, **options):
        worker_id = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        while True:
            execution_ids = EvaluationCaseExecutionService.recoverable_execution_ids(limit=max(1, options["batch_size"]))
            for execution_id in execution_ids:
                EvaluationCaseExecutionService._execute_safe(execution_id, worker_id)
            if options["once"]:
                return
            time.sleep(max(0.2, options["poll_seconds"]))
