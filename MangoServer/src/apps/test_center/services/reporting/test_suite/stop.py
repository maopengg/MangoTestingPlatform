from django.db import transaction
from django.utils import timezone
from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract
from mangotools.enums import TaskEnum

from src.apps.system.enums import ClientTypeEnum
from src.apps.system.enums import ServerToolsCommandEnum
from src.apps.system.services.socket_link.connection_service import SocketConnectionService
from src.apps.system.services.socket_link.message_service import SocketMessageService
from src.apps.test_center.exceptions import (
    SYSTEM_REPORT_REPORT_NOT_FOUND,
    SYSTEM_REPORT_REPORT_INVALID,
    TestCenterError,
)
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.common.logging import log


class TestSuiteStopService:
    STOP_REASON = '用户手动停止'
    ACTIVE_STATUSES = (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value)

    @classmethod
    def stop(cls, test_suite_id: int) -> dict:
        with transaction.atomic():
            test_suite = (
                TestSuite.objects.select_for_update()
                .select_related('user')
                .filter(id=test_suite_id)
                .first()
            )
            if test_suite is None:
                raise TestCenterError(SYSTEM_REPORT_REPORT_NOT_FOUND)
            from src.apps.test_center.services.reporting.test_suite.retry import TestSuiteRetryService
            TestSuiteRetryService.ensure_retry_supported(TestSuiteDetails.objects.filter(test_suite=test_suite))
            if test_suite.status == TaskEnum.STOPPED.value:
                return {
                    'test_suite_id': test_suite.id,
                    'stopped_details': 0,
                    'notified_actuators': 0,
                    'status': test_suite.status,
                }
            if test_suite.status not in cls.ACTIVE_STATUSES:
                raise TestCenterError(SYSTEM_REPORT_REPORT_INVALID)

            now = timezone.now()
            stopped_details = TestSuiteDetails.objects.filter(
                test_suite_id=test_suite.id,
                status__in=cls.ACTIVE_STATUSES,
            ).update(
                status=TaskEnum.STOPPED.value,
                error_message=cls.STOP_REASON,
                push_time=None,
                success=0,
                fail=0,
                warning=0,
                update_time=now,
            )
            TestSuite.objects.filter(id=test_suite.id).update(
                status=TaskEnum.STOPPED.value,
                update_time=now,
            )

        notified_actuators = cls._notify_actuators(test_suite.id)
        return {
            'test_suite_id': test_suite.id,
            'stopped_details': stopped_details,
            'notified_actuators': notified_actuators,
            'status': TaskEnum.STOPPED.value,
        }

    @classmethod
    def _notify_actuators(cls, test_suite_id: int) -> int:
        usernames = {
            connection.user.username
            for connection in SocketConnectionService.list_online_actuators()
        }
        notified = 0
        for username in usernames:
            try:
                SocketMessageService.send_socket_data(
                    SocketEnvelopeContract(
                        code=200,
                        msg=f'立即停止测试报告：{test_suite_id}',
                        user=username,
                        is_notice=ClientTypeEnum.ACTUATOR,
                        data=SocketCommandContract(
                            func_name=ServerToolsCommandEnum.STOP_TEST_SUITE.value,
                            func_args={'test_suite_id': test_suite_id},
                        ),
                    ),
                    message_key=f'test-suite-stop:{test_suite_id}:{username}',
                )
                notified += 1
            except Exception as error:
                log.system.error(
                    f'通知执行器停止测试报告失败：test_suite={test_suite_id}, '
                    f'username={username}, error={error}'
                )
        return notified
