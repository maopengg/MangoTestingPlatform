from datetime import timedelta

from django.db.models import Q
from django.db import transaction
from django.utils import timezone

from src.apps.auto_system.models import TestSuite, TestSuiteDetails
from src.apps.auto_system.service.test_suite.detail_result import TestSuiteDetailResultService
from src.apps.auto_system.service.test_suite.send_notice import SendNotice
from src.common.enums.system_enum import TestSuiteNoticeEnum
from src.common.enums.tools_enum import TaskEnum
from src.settings import RETRY_FREQUENCY
from src.common.tools.decorator.retry import async_task_db_connection
from src.common.tools.log_collector import log


class SchedulerSystemJobService:
    USER_LOG_RETENTION_DAYS = 90
    DATA_FACTORY_EXECUTION_RETENTION_DAYS = 90
    SCHEDULE_FIRE_RETENTION_DAYS = 30
    MONITORING_REPORT_RETENTION_DAYS = 30

    @classmethod
    @async_task_db_connection()
    def repair_test_suite_status(cls):
        try:
            reset_time = 30
            updated_suite_count = 0
            reset_count = 0
            fail_count = 0

            test_suite_list = TestSuite.objects.filter(
                status__in=[TaskEnum.PROCEED.value, TaskEnum.STAY_BEGIN.value]
            )
            for test_suite in test_suite_list:
                status_list = TestSuiteDetails.objects.filter(test_suite=test_suite).values_list('status', flat=True)
                if TaskEnum.STAY_BEGIN.value not in status_list and TaskEnum.PROCEED.value not in status_list:
                    test_suite.status = TaskEnum.FAIL.value if TaskEnum.FAIL.value in status_list else TaskEnum.SUCCESS.value
                    test_suite.save()
                    updated_suite_count += 1

            proceeding_details = TestSuiteDetails.objects.filter(
                status=TaskEnum.PROCEED.value,
                retry__lt=RETRY_FREQUENCY + 1,
            )
            for detail in proceeding_details:
                if detail.push_time and timezone.now() - detail.push_time > timedelta(minutes=reset_time):
                    detail.status = TaskEnum.STAY_BEGIN.value
                    detail.save()
                    reset_count += 1

            retry_exceeded_details = TestSuiteDetails.objects.filter(
                status__in=[TaskEnum.PROCEED.value, TaskEnum.STAY_BEGIN.value],
                retry__gte=RETRY_FREQUENCY + 1,
            )
            for detail in retry_exceeded_details:
                if detail.push_time and timezone.now() - detail.push_time > timedelta(minutes=reset_time):
                    detail.status = TaskEnum.FAIL.value
                    detail.save()
                    fail_count += 1

            return {
                'updated_suite_count': updated_suite_count,
                'reset_count': reset_count,
                'fail_count': fail_count,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 修复测试套卡住状态失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def send_pending_test_suite_notice(cls):
        try:
            notice_count = 0
            notice_suite_list = TestSuite.objects.filter(
                is_notice=TestSuiteNoticeEnum.NOT_SENT.value,
                status__in=[TaskEnum.SUCCESS.value, TaskEnum.FAIL.value],
            )
            for test_suite in notice_suite_list:
                try:
                    SendNotice(test_suite.id).send_test_suite()
                    notice_count += 1
                except Exception as error:
                    log.system.error(f'scheduler-service 发送测试报告通知失败：test_suite={test_suite.id}, error={error}')
            return {'notice_count': notice_count}
        except Exception as error:
            log.system.error(f'scheduler-service 发送未发送测试报告通知失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def repair_api_case_status(cls):
        try:
            from src.apps.auto_api.models import ApiCase, ApiCaseDetailed, ApiInfo
            return cls._repair_stuck_models(
                [ApiInfo, ApiCase, ApiCaseDetailed],
                timeout_minutes=5,
                target_status=TaskEnum.STAY_BEGIN.value,
            )
        except Exception as error:
            log.system.error(f'scheduler-service 修复 API 用例卡住状态失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def repair_ui_case_status(cls):
        try:
            from src.apps.auto_ui.models import PageSteps, UiCase, UiCaseStepsDetailed
            return cls._repair_stuck_models([UiCase, UiCaseStepsDetailed, PageSteps])
        except Exception as error:
            log.system.error(f'scheduler-service 修复 UI 用例卡住状态失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def repair_pytest_case_status(cls):
        try:
            from src.apps.auto_pytest.models import PytestCase
            return cls._repair_stuck_models(
                [PytestCase],
                timeout_minutes=5,
                target_status=TaskEnum.STAY_BEGIN.value,
            )
        except Exception as error:
            log.system.error(f'scheduler-service 修复 Pytest 用例卡住状态失败：{error}')
            raise

    @classmethod
    def _repair_stuck_models(
            cls,
            models: list[type],
            timeout_minutes: int = 10,
            target_status: int = TaskEnum.FAIL.value,
    ):
        timeout_time = timezone.now() - timedelta(minutes=timeout_minutes)
        updated_count = 0
        for model in models:
            updated_count += model.objects.filter(
                status=TaskEnum.PROCEED.value,
                update_time__lt=timeout_time,
            ).update(status=target_status)
        transaction.commit()
        return {
            'updated_count': updated_count,
            'timeout_minutes': timeout_minutes,
            'target_status': target_status,
        }

    @classmethod
    def check_task_status(cls):
        result = cls.repair_test_suite_status()
        result.update(cls.send_pending_test_suite_notice())
        return result

    @classmethod
    def set_case_status(cls):
        api_result = cls.repair_api_case_status()
        ui_result = cls.repair_ui_case_status()
        pytest_result = cls.repair_pytest_case_status()
        return {
            'api_updated_count': api_result.get('updated_count', 0),
            'ui_updated_count': ui_result.get('updated_count', 0),
            'pytest_updated_count': pytest_result.get('updated_count', 0),
        }

    @classmethod
    @async_task_db_connection()
    def clean_test_suite_detail_result(cls):
        try:
            deleted = TestSuiteDetailResultService.clean_expired_results()
            log.system.info(
                f'scheduler-service 清理超过 {TestSuiteDetailResultService.DEFAULT_RETENTION_DAYS} 天的测试详情结果：{deleted} 条'
            )
            return {
                'retention_days': TestSuiteDetailResultService.DEFAULT_RETENTION_DAYS,
                'deleted_count': deleted,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理测试详情大结果失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def clean_user_logs(cls):
        try:
            from src.apps.auto_user.models import UserLogs

            cutoff_time = timezone.now() - timedelta(days=cls.USER_LOG_RETENTION_DAYS)
            deleted = UserLogs.objects.filter(create_time__lt=cutoff_time).delete()[0]
            log.system.info(
                f'scheduler-service 清理超过 {cls.USER_LOG_RETENTION_DAYS} 天的操作日志：{deleted} 条'
            )
            return {
                'retention_days': cls.USER_LOG_RETENTION_DAYS,
                'deleted_count': deleted,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理操作日志失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def clean_data_factory_executions(cls):
        try:
            from src.apps.auto_data_factory.models import DataFactoryExecution
            from src.common.enums.data_factory_enum import DataFactoryCleanupStatusEnum

            cutoff_time = timezone.now() - timedelta(days=cls.DATA_FACTORY_EXECUTION_RETENTION_DAYS)
            deleted = DataFactoryExecution.objects.filter(
                cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value
            ).filter(
                Q(cleanup_time__lt=cutoff_time) |
                Q(cleanup_time__isnull=True, create_time__lt=cutoff_time)
            ).delete()[0]
            log.system.info(
                f'scheduler-service 清理超过 {cls.DATA_FACTORY_EXECUTION_RETENTION_DAYS} 天且已清理的数据工厂执行记录：{deleted} 条'
            )
            return {
                'retention_days': cls.DATA_FACTORY_EXECUTION_RETENTION_DAYS,
                'deleted_count': deleted,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理数据工厂执行记录失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def clean_schedule_fires(cls):
        try:
            from src.apps.task_center.models import ScheduleFire

            cutoff_time = timezone.now() - timedelta(days=cls.SCHEDULE_FIRE_RETENTION_DAYS)
            deleted = ScheduleFire.objects.filter(planned_at__lt=cutoff_time).delete()[0]
            log.system.info(
                f'scheduler-service 清理超过 {cls.SCHEDULE_FIRE_RETENTION_DAYS} 天的定时任务触发记录：{deleted} 条'
            )
            return {
                'retention_days': cls.SCHEDULE_FIRE_RETENTION_DAYS,
                'deleted_count': deleted,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理定时任务触发记录失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def clean_monitoring_reports(cls):
        try:
            from src.apps.monitoring.models import MonitoringReport

            cutoff_time = timezone.now() - timedelta(days=cls.MONITORING_REPORT_RETENTION_DAYS)
            deleted = MonitoringReport.objects.filter(create_time__lt=cutoff_time).delete()[0]
            log.system.info(
                f'scheduler-service 清理超过 {cls.MONITORING_REPORT_RETENTION_DAYS} 天的预警监控报告：{deleted} 条'
            )
            return {
                'retention_days': cls.MONITORING_REPORT_RETENTION_DAYS,
                'deleted_count': deleted,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理预警监控报告失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def scan_data_factory_entity_field_updates(cls):
        log.system.info('scheduler-service 数据工厂字段更新扫描任务已触发，当前逻辑待实现')
        return {
            'implemented': False,
            'message': '数据工厂字段更新扫描逻辑待实现',
        }
