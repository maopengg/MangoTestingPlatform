from django.db import transaction

from src.apps.perf.exceptions import PERF_PERF_NOT_FOUND, PerfError
from src.apps.perf.models import PerfBaseline, PerfScenario


class PerfBaselineService:
    @staticmethod
    @transaction.atomic
    def set_baseline(run, *, name=None, created_by=None):
        if not run.scenario_id:
            raise PerfError(PERF_PERF_NOT_FOUND)
        # 锁定稳定存在的父记录，首次创建及不同 Run 的并发切换也能串行化。
        scenario = PerfScenario.objects.select_for_update().filter(id=run.scenario_id).first()
        if scenario is None:
            raise PerfError(PERF_PERF_NOT_FOUND)
        PerfBaseline.objects.filter(
            scenario_id=scenario.pk, environment_key=str(run.test_env), engine=run.engine, active=True,
        ).update(active=False)
        return PerfBaseline.objects.create(
            scenario=scenario, run=run, name=name or run.name,
            environment_key=str(run.test_env), engine=run.engine, snapshot_hash=run.snapshot_hash,
            created_by=created_by,
        )
