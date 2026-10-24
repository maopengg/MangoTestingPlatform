# -*- coding: utf-8 -*-
import time
from django.core.management.base import BaseCommand

from src.processes.ai_worker.worker import AiWorkerProcess


class Command(BaseCommand):
    help = "运行基于 MySQL 租约的 AI Agent Worker"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="最多执行一个任务后退出")
        parser.add_argument("--poll-seconds", type=float, default=2.0)
        parser.add_argument("--worker-id", default=None)

    def handle(self, *args, **options):
        worker = AiWorkerProcess(options["worker_id"])
        self.stdout.write(self.style.SUCCESS(f"Agent Worker 已启动：{worker.worker_id}"))
        while True:
            handled = worker.run_once()
            if options["once"]:
                return
            if not handled:
                time.sleep(max(options["poll_seconds"], 0.2))
