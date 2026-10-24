from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from threading import Event, RLock
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.task_center.enums import ScheduleFireSourceTypeEnum, ScheduleFireStatusEnum
from src.apps.task_center.services.scheduling.dispatch import ScheduleDispatchService


class ScheduleDispatchIdempotencyTests(SimpleTestCase):
    def setUp(self):
        self.persisted = SimpleNamespace(
            id=101, task_id=202, group_execution_id=68,
            source_type=ScheduleFireSourceTypeEnum.TEST_SUITE.value,
            status=ScheduleFireStatusEnum.PENDING.value,
            test_suite_id=None, extra_data={'test_env': 0},
        )
        # 两个调用方都持有分发前的旧对象，复现手动接口与消费者的竞争。
        self.stale_fire = SimpleNamespace(**vars(self.persisted))
        manager = patch('src.apps.task_center.services.scheduling.dispatch.ScheduleFire.objects')
        self.fires = manager.start()
        self.addCleanup(manager.stop)
        self.fires.select_for_update.return_value.filter.return_value.first.side_effect = (
            lambda: SimpleNamespace(**vars(self.persisted))
        )
        self.fires.filter.return_value.update.side_effect = self.update_fire
        tasks = patch('src.apps.task_center.services.scheduling.dispatch.Tasks.objects')
        self.tasks = tasks.start()
        self.addCleanup(tasks.stop)
        self.tasks.select_related.return_value.get.return_value = SimpleNamespace(id=202, test_envs=[0])

    def update_fire(self, **values):
        for key, value in values.items():
            setattr(self.persisted, key, value)
        return 1

    def test_stale_repeated_dispatch_reuses_suite_and_preserves_group(self):
        with (
            patch('src.apps.task_center.services.scheduling.dispatch.transaction.atomic', side_effect=nullcontext),
            patch.object(ScheduleDispatchService, 'create_test_suite', return_value=9001) as create,
        ):
            self.assertEqual(ScheduleDispatchService.dispatch_fire(self.stale_fire), 9001)
            self.assertEqual(ScheduleDispatchService.dispatch_fire(self.stale_fire, 'scheduler'), 9001)
        create.assert_called_once()
        self.assertEqual(self.persisted.group_execution_id, 68)
        self.assertEqual(self.persisted.test_suite_id, 9001)
        self.fires.select_for_update.assert_called()
        self.assertEqual(self.fires.filter.return_value.update.call_count, 1)

    def test_existing_completed_suite_is_not_dispatched_again(self):
        self.persisted.test_suite_id = 9001
        self.persisted.status = ScheduleFireStatusEnum.SUCCESS.value
        with (
            patch('src.apps.task_center.services.scheduling.dispatch.transaction.atomic', side_effect=nullcontext),
            patch.object(ScheduleDispatchService, 'create_test_suite') as create,
        ):
            self.assertEqual(ScheduleDispatchService.dispatch_fire(self.stale_fire), 9001)
        create.assert_not_called()
        self.fires.filter.return_value.update.assert_not_called()

    def test_terminal_records_without_suite_are_not_retried(self):
        for status in (ScheduleFireStatusEnum.FAIL, ScheduleFireStatusEnum.SKIPPED,
                       ScheduleFireStatusEnum.CANCELLED, ScheduleFireStatusEnum.DISPATCHED):
            with self.subTest(status=status):
                self.persisted.status = status.value
                with (
                    patch('src.apps.task_center.services.scheduling.dispatch.transaction.atomic',
                          side_effect=nullcontext),
                    patch.object(ScheduleDispatchService, 'create_test_suite') as create,
                ):
                    self.assertIsNone(ScheduleDispatchService.dispatch_fire(self.stale_fire))
                create.assert_not_called()

    def test_missing_record_is_not_dispatched(self):
        self.fires.select_for_update.return_value.filter.return_value.first.side_effect = None
        self.fires.select_for_update.return_value.filter.return_value.first.return_value = None
        with (
            patch('src.apps.task_center.services.scheduling.dispatch.transaction.atomic', side_effect=nullcontext),
            patch.object(ScheduleDispatchService, 'create_test_suite') as create,
        ):
            self.assertIsNone(ScheduleDispatchService.dispatch_fire(self.stale_fire))
        create.assert_not_called()

    def test_concurrent_manual_and_consumer_dispatch_generate_one_linked_suite(self):
        # 用互斥事务桩模拟行锁；不连接业务数据库，也不发送真实通知。
        lock = RLock()
        creating = Event()
        competing = Event()

        @contextmanager
        def atomic():
            with lock:
                yield

        def create_suite(*args, **kwargs):
            creating.set()
            self.assertTrue(competing.wait(timeout=5))
            return 9001

        def consume():
            self.assertTrue(creating.wait(timeout=5))
            competing.set()
            return ScheduleDispatchService.dispatch_fire(self.stale_fire, 'scheduler')

        with (
            patch('src.apps.task_center.services.scheduling.dispatch.transaction.atomic', side_effect=atomic),
            patch.object(ScheduleDispatchService, 'create_test_suite', side_effect=create_suite) as create,
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            manual = pool.submit(ScheduleDispatchService.dispatch_fire, self.stale_fire)
            consumer = pool.submit(consume)
            self.assertEqual(manual.result(timeout=10), 9001)
            self.assertEqual(consumer.result(timeout=10), 9001)
        create.assert_called_once()
        self.assertEqual(self.persisted.test_suite_id, 9001)
        self.assertEqual(self.persisted.group_execution_id, 68)
        self.assertEqual(self.fires.filter.return_value.update.call_count, 1)
