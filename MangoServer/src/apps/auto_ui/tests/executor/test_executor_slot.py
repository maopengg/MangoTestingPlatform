from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.services.execution.executor_slot import ExecutorSlotLeaseService


class ExecutorSlotLeaseServiceTest(SimpleTestCase):
    def setUp(self):
        ExecutorSlotLeaseService.reset_for_tests()
        self.connection = SimpleNamespace(
            connection_id="connection-1",
            user=SimpleNamespace(username="shared-open"),
        )

    def tearDown(self):
        ExecutorSlotLeaseService.reset_for_tests()

    def acquire(self, user_id: int):
        return ExecutorSlotLeaseService.acquire(
            user={"id": user_id, "username": f"user-{user_id}"},
            connection=self.connection,
            runtime_type="page_step_workspace",
            resource_id=user_id,
        )

    def test_same_user_reuses_one_slot(self):
        first = self.acquire(1)
        second = self.acquire(1)

        self.assertEqual(first["slot_id"], second["slot_id"])
        self.assertEqual(second["active_user_count"], 1)

    def test_five_users_are_allowed_and_sixth_is_rejected(self):
        leases = [self.acquire(user_id) for user_id in range(1, 6)]

        self.assertEqual(leases[-1]["active_user_count"], 5)
        with self.assertRaisesRegex(AutoUiError, "已有 5/5 位用户"):
            self.acquire(6)

    def test_idle_slot_expires_after_five_minutes(self):
        with patch(
                "src.apps.auto_ui.services.execution.executor_slot.time.time",
                return_value=1000,
        ):
            first = self.acquire(1)
        with patch(
                "src.apps.auto_ui.services.execution.executor_slot.time.time",
                return_value=1301,
        ):
            second = self.acquire(2)

        self.assertNotEqual(first["slot_id"], second["slot_id"])
        self.assertEqual(second["active_user_count"], 1)

    def test_running_or_live_slot_is_not_removed_as_idle(self):
        with patch(
                "src.apps.auto_ui.services.execution.executor_slot.time.time",
                return_value=1000,
        ):
            running = self.acquire(1)
            live = self.acquire(2)
            ExecutorSlotLeaseService.set_running(
                self.connection.connection_id,
                running["slot_id"],
                True,
            )
            ExecutorSlotLeaseService.set_live(
                self.connection.connection_id,
                live["slot_id"],
                True,
            )
        with patch(
                "src.apps.auto_ui.services.execution.executor_slot.time.time",
                return_value=1600,
        ):
            occupancy = ExecutorSlotLeaseService.occupancy(self.connection)

        self.assertEqual(occupancy["active_user_count"], 2)

    def test_activity_refreshes_idle_deadline(self):
        with patch(
                "src.apps.auto_ui.services.execution.executor_slot.time.time",
                return_value=1000,
        ):
            lease = self.acquire(1)
        with patch(
                "src.apps.auto_ui.services.execution.executor_slot.time.time",
                return_value=1200,
        ):
            touched = ExecutorSlotLeaseService.touch(
                self.connection.connection_id,
                slot_id=lease["slot_id"],
            )

        self.assertEqual(touched["idle_deadline"], 1500)

    def test_repeated_live_start_for_same_stream_is_idempotent(self):
        lease = self.acquire(1)

        ExecutorSlotLeaseService.set_live(
            self.connection.connection_id,
            lease["slot_id"],
            True,
            stream_id="stream-1",
        )
        active = ExecutorSlotLeaseService.set_live(
            self.connection.connection_id,
            lease["slot_id"],
            True,
            stream_id="stream-1",
        )
        stopped = ExecutorSlotLeaseService.set_live(
            self.connection.connection_id,
            lease["slot_id"],
            False,
            stream_id="stream-1",
        )

        self.assertEqual(active["live_stream_count"], 1)
        self.assertEqual(stopped["live_stream_count"], 0)
