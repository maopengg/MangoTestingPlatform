# -*- coding: utf-8 -*-
import json

from django.core.management.base import BaseCommand, CommandError

from src.apps.ai.services.harness.definition import DEFINITIONS
from src.apps.ai.services.harness.regression import HarnessRegressionGate


class Command(BaseCommand):
    help = "运行固定 Agent Harness 回归门禁，不调用模型、不写数据库"

    def add_arguments(self, parser):
        parser.add_argument(
            "--agent",
            choices=sorted(DEFINITIONS),
            help="只评估指定 Agent；不传时评估全部",
        )

    def handle(self, *args, **options):
        agent_keys = [options["agent"]] if options.get("agent") else sorted(DEFINITIONS)
        failed = []
        for agent_key in agent_keys:
            definition = dict(DEFINITIONS[agent_key])
            definition.pop("version", None)
            report = HarnessRegressionGate.evaluate(agent_key, definition)
            self.stdout.write(json.dumps({"agent": agent_key, **report}, ensure_ascii=False))
            if not report["passed"]:
                failed.append(agent_key)
        if failed:
            raise CommandError("Harness 回归门禁失败：" + "、".join(failed))
        self.stdout.write(self.style.SUCCESS("Harness 固定回归门禁通过"))
