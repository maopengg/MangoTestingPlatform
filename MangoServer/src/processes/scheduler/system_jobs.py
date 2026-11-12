from calendar import monthrange
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.monitoring.selectors.querysets import MonitoringQuerySelector
from src.apps.system.enums import TestSuiteNoticeEnum
from src.apps.system.services.configuration.system_config import SystemConfigService
from src.apps.task_center.selectors.querysets import ScheduleFireQuerySelector
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.test_center.services.results.execution_result import ExecutionResultService
from src.apps.test_center.services.reporting.test_suite.send_notice import SendNotice
from src.apps.test_center.services.reporting.test_suite.timeout_recovery import TestSuiteTimeoutRecoveryService
from src.apps.user.selectors.querysets import UserQuerySelector
from src.common.decorators.retry import async_task_db_connection
from src.common.logging import log


def subtract_calendar_months(value: datetime, months: int) -> datetime:
    """保留给历史数据边界测试使用；运行配置已经统一按天管理。"""
    if months < 0:
        raise ValueError("months must be greater than or equal to zero")
    target_year, target_month_index = divmod(value.year * 12 + value.month - 1 - months, 12)
    target_month = target_month_index + 1
    target_day = min(value.day, monthrange(target_year, target_month)[1])
    return value.replace(year=target_year, month=target_month, day=target_day)


class SchedulerSystemJobService:
    @staticmethod
    @async_task_db_connection()
    def clean_runtime_kv():
        from src.apps.system.services.runtime_kv.cleanup import RuntimeKVCleanupService

        return RuntimeKVCleanupService.cleanup_expired()

    @staticmethod
    def retention_days(key: str) -> int:
        return SystemConfigService.get_ranged_int(key)

    @classmethod
    @async_task_db_connection()
    def recover_perf_runs(cls):
        from src.apps.perf.services.execution.recovery import PerfRecoveryService
        PerfRecoveryService.recover()
        return {"recovered": True}

    @classmethod
    @async_task_db_connection()
    def clean_ui_element_ai_history(cls):
        try:
            from src.apps.auto_ui.services.elements.ai.cleanup_service import ElementAiCleanupService

            result = ElementAiCleanupService.cleanup()
            log.system.info(
                'scheduler-service 清理 UI 元素 AI 历史：'
                f"自愈记录 {result['heal_deleted_count']} 条，"
                f"基线快照 {result['snapshot_deleted_count']} 条"
            )
            return result
        except Exception as error:
            log.system.error(f'scheduler-service 清理 UI 元素 AI 历史失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def clean_execution_result_data(cls):
        try:
            from src.apps.test_center.services.diagnostics.diagnostic_markdown import DiagnosticMarkdownService
            from src.apps.test_center.services.storage.execution_artifact import ExecutionArtifactService
            from src.apps.test_center.services.reporting.test_suite.api_report_export import ApiReportExportService

            result = ExecutionResultService.cleanup_expired()
            result.update(DiagnosticMarkdownService.cleanup_expired(result['retention_days']))
            result.update(ExecutionArtifactService.cleanup_expired())
            result.update(ExecutionArtifactService.cleanup_perf_captures(result['retention_days']))
            result.update(ApiReportExportService.cleanup_expired_files(result['retention_days']))
            log.system.info(
                f'scheduler-service 清理过期执行结果完整数据：{result}'
            )
            return result
        except Exception as error:
            log.system.error(f'scheduler-service 清理执行结果完整数据失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def recover_executor_tasks(cls):
        from src.apps.task_center.services.execution.executor_task import ExecutorTaskService

        return ExecutorTaskService.recover_expired()

    @classmethod
    @async_task_db_connection()
    def cleanup_realtime_data(cls):
        from src.apps.system.services.socket_link.connection_service import SocketConnectionService

        return {
            'expired_connection_count': SocketConnectionService.expire_stale(),
        }

    @classmethod
    @async_task_db_connection()
    def clean_executor_task_history(cls):
        from src.apps.system.services.socket_link.connection_service import SocketConnectionService
        from src.apps.task_center.services.execution.executor_task import ExecutorTaskService

        retention_days = cls.retention_days('EXECUTOR_TASK_RETENTION_DAYS')
        deleted_connections = SocketConnectionService.cleanup_history(retention_days=retention_days)
        deleted_tasks = ExecutorTaskService.cleanup_history(retention_days=retention_days)
        return {
            'deleted_connection_count': deleted_connections,
            'deleted_task_count': deleted_tasks,
        }

    @classmethod
    @async_task_db_connection()
    def repair_test_suite_status(cls):
        try:
            from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
            interrupted_count = TestSuiteInfrastructureService.repair_legacy_blocks()
            reset_time = SystemConfigService.get_test_suite_stuck_reset_minutes()
            max_attempts = SystemConfigService.get_test_suite_timeout_max_attempts()
            updated_suite_count = 0
            reset_count = 0
            fail_count = 0

            proceeding_details = TestCenterQuerySelector.test_suite_details().filter(
                status=TaskEnum.PROCEED.value,
                retry__lt=max_attempts,
            )
            for detail in proceeding_details:
                if detail.push_time and timezone.now() - detail.push_time > timedelta(minutes=reset_time):
                    reset = TestSuiteTimeoutRecoveryService.reset_for_retry(
                        detail,
                        timeout_minutes=reset_time,
                        max_attempts=max_attempts,
                    )
                    reset_count += int(reset)

            retry_exceeded_details = TestCenterQuerySelector.test_suite_details().filter(
                status__in=[TaskEnum.PROCEED.value, TaskEnum.STAY_BEGIN.value],
                retry__gte=max_attempts,
            )
            for detail in retry_exceeded_details:
                if detail.push_time and timezone.now() - detail.push_time > timedelta(minutes=reset_time):
                    failed = TestSuiteTimeoutRecoveryService.fail_after_retries(
                        detail,
                        timeout_minutes=reset_time,
                        max_attempts=max_attempts,
                    )
                    fail_count += int(failed)

            test_suite_list = TestCenterQuerySelector.test_suite().filter(
                status__in=[TaskEnum.PROCEED.value, TaskEnum.STAY_BEGIN.value]
            )
            for test_suite in test_suite_list:
                status_list = list(
                    TestCenterQuerySelector.test_suite_details().filter(test_suite=test_suite).values_list('status',
                                                                                                           flat=True)
                )
                if not status_list:
                    final_status = TaskEnum.FAIL.value
                elif TaskEnum.STAY_BEGIN.value in status_list or TaskEnum.PROCEED.value in status_list:
                    continue
                elif TaskEnum.FAIL.value in status_list:
                    final_status = TaskEnum.FAIL.value
                elif TaskEnum.WARNING.value in status_list:
                    final_status = TaskEnum.WARNING.value
                else:
                    final_status = TaskEnum.SUCCESS.value
                test_suite.status = final_status
                test_suite.save(update_fields=['status', 'update_time'])
                updated_suite_count += 1

            return {
                'interrupted_count': interrupted_count,
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
            notice_suite_list = TestCenterQuerySelector.test_suite().filter(
                is_notice=TestSuiteNoticeEnum.NOT_SENT.value,
                status__in=[TaskEnum.SUCCESS.value, TaskEnum.FAIL.value],
            )
            for test_suite in notice_suite_list:
                try:
                    SendNotice(test_suite.id).send_test_suite()
                    notice_count += 1
                except Exception as error:
                    log.system.error(
                        f'scheduler-service 发送测试报告通知失败：test_suite={test_suite.id}, error={error}')
            from src.apps.task_center.services.scheduling.task_group_execution import (
                ScheduledTaskGroupExecutionService,
            )
            group_notice_count = ScheduledTaskGroupExecutionService.retry_pending_notices()
            return {
                'notice_count': notice_count,
                'group_notice_count': group_notice_count,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 发送未发送测试报告通知失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def reconcile_auth_risk_todos(cls):
        try:
            from src.apps.task_center.services.workbench.todo import WorkbenchTodoService

            return WorkbenchTodoService.reconcile_auth_risk_todos()
        except Exception as error:
            log.system.error(f'scheduler-service 同步授权风险代办失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def reconcile_workbench_todos(cls):
        try:
            from src.apps.data_factory.services.recovery.execution_recovery import DataFactoryExecutionRecovery
            from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService
            from src.apps.data_factory.services.recovery.permit_reconciliation import DatasourcePermitReconciliationService
            from src.apps.task_center.services.workbench.todo import WorkbenchTodoService
            result = {
                **SqlExecutionAuditService.recover_stale(),
                **DataFactoryExecutionRecovery.recover(),
                **WorkbenchTodoService.reconcile_non_auth_todos(),
            }
            try:
                result.update(DatasourcePermitReconciliationService.scheduled_monitor())
                from src.apps.data_factory.services.reporting.report_progress import DatasourceReportProgressService
                result.update(DatasourceReportProgressService.scheduled_monitor())
            except Exception as error:
                # 监控控制面故障必须可见，但不能挡住既有清理责任对账。
                log.system.error('event=datasource_monitor_failed exception_type=%s action=inspect_control_database',
                                 type(error).__name__)
                result['datasource_monitor_failed'] = True
            return result
        except Exception as error:
            log.system.error(f'scheduler-service 同步首页风险待办失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def reconcile_execution_statuses(cls):
        try:
            from src.apps.task_center.services.execution.status_reconciliation import (
                ExecutionStatusProjectionService,
            )

            from src.apps.auto_api.services.execution_trace.reconciliation import ApiTraceReconciliationService
            return {**ExecutionStatusProjectionService.reconcile(), **ApiTraceReconciliationService.reconcile()}
        except Exception as error:
            log.system.error(f'scheduler-service 修复执行状态一致性失败：{error}')
            raise


    @classmethod
    def check_task_status(cls):
        result = cls.repair_test_suite_status()
        result.update(cls.send_pending_test_suite_notice())
        result.update(cls.reconcile_auth_risk_todos())
        return result

    @classmethod
    @async_task_db_connection()
    def clean_user_logs(cls):
        try:
            retention_days = cls.retention_days('USER_LOG_RETENTION_DAYS')
            cutoff_time = timezone.now() - timedelta(days=retention_days)
            deleted = UserQuerySelector.user_logs().filter(create_time__lt=cutoff_time).delete()[0]
            log.system.info(
                f'scheduler-service 清理超过 {retention_days} 天的操作日志：{deleted} 条'
            )
            return {
                'retention_days': retention_days,
                'deleted_count': deleted,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理操作日志失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def clean_data_factory_executions(cls):
        try:
            from src.apps.data_factory.enums import DataFactoryCleanupStatusEnum

            retention_days = cls.retention_days('DATA_FACTORY_EXECUTION_RETENTION_DAYS')
            cutoff_time = timezone.now() - timedelta(days=retention_days)
            deleted = DataFactoryQuerySelector.data_factory_execution().filter(
                cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value
            ).filter(
                Q(cleanup_time__lt=cutoff_time) |
                Q(cleanup_time__isnull=True, create_time__lt=cutoff_time)
            ).delete()[0]
            log.system.info(
                f'scheduler-service 清理超过 {retention_days} 天且已清理的数据工厂执行记录：{deleted} 条'
            )
            return {
                'retention_days': retention_days,
                'deleted_count': deleted,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理数据工厂执行记录失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def clean_sql_execution_records(cls):
        try:
            retention_days = cls.retention_days('SQL_EXECUTION_RETENTION_DAYS')
            cutoff_time = timezone.now() - timedelta(days=retention_days)
            from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService
            deleted = SqlExecutionAuditService.cleanup_expired(cutoff_time)
            log.system.info(
                f'scheduler-service 清理超过 {retention_days} 天的 SQL 执行记录：{deleted} 条'
            )
            return {
                'retention_days': retention_days,
                'deleted_count': deleted,
                'cutoff_time': cutoff_time.isoformat(),
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理 SQL 执行记录失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def clean_schedule_fires(cls):
        try:
            retention_days = cls.retention_days('SCHEDULE_FIRE_RETENTION_DAYS')
            cutoff_time = timezone.now() - timedelta(days=retention_days)
            fire_deleted = ScheduleFireQuerySelector.schedule_fire().filter(
                planned_at__lt=cutoff_time,
            ).delete()[0]
            group_execution_deleted = ScheduleFireQuerySelector.scheduled_task_group_execution().filter(
                planned_at__lt=cutoff_time,
            ).delete()[0]
            log.system.info(
                f'scheduler-service 清理超过 {retention_days} 天的定时任务触发记录：'
                f'{fire_deleted} 条，任务组批次：{group_execution_deleted} 条'
            )
            return {
                'retention_days': retention_days,
                'deleted_count': fire_deleted,
                'group_execution_deleted_count': group_execution_deleted,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理定时任务触发记录失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def clean_monitoring_reports(cls):
        try:
            retention_days = cls.retention_days('MONITORING_REPORT_RETENTION_DAYS')
            cutoff_time = timezone.now() - timedelta(days=retention_days)
            deleted = MonitoringQuerySelector.monitoring_report().filter(
                create_time__lt=cutoff_time,
            ).delete()[0]
            log.system.info(
                f'scheduler-service 清理超过 {retention_days} 天的预警监控报告：{deleted} 条'
            )
            return {
                'retention_days': retention_days,
                'deleted_count': deleted,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理预警监控报告失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def clean_api_case_execution_traces(cls):
        try:
            retention_days = cls.retention_days('API_CASE_TRACE_RETENTION_DAYS')
            cutoff_time = timezone.now() - timedelta(days=retention_days)
            deleted = ApiQuerySelector.api_case_execution_trace().filter(
                create_time__lt=cutoff_time,
            ).delete()[0]
            log.system.info(
                f'scheduler-service 清理超过 {retention_days} 天的 API 用例执行链路：{deleted} 条'
            )
            return {
                'retention_days': retention_days,
                'deleted_count': deleted,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理 API 用例执行链路失败：{error}')
            raise


    @classmethod
    @async_task_db_connection()
    def clean_mock_request_logs(cls):
        try:
            from src.apps.auto_api.services.mock.mock_log_cleanup import MockRequestLogCleanupService

            retention_days = cls.retention_days('MOCK_REQUEST_LOG_RETENTION_DAYS')
            cutoff_time = timezone.now() - timedelta(days=retention_days)
            deleted = MockRequestLogCleanupService.cleanup_before(cutoff_time)
            log.system.info(
                f'scheduler-service 清理超过 {retention_days} 天的 Mock 调用记录：'
                f'{deleted} 条'
            )
            return {
                'retention_days': retention_days,
                'deleted_count': deleted,
                'cutoff_time': cutoff_time.isoformat(),
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理 Mock 调用记录失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def cleanup_service_heartbeat(cls):
        try:
            from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService

            retention_days = cls.retention_days('SERVICE_HEARTBEAT_RETENTION_DAYS')
            deleted = ServiceHeartbeatService.cleanup_expired(retention_days)
            log.system.info(
                f'scheduler-service 清理超过 {retention_days} 天的服务心跳记录：{deleted} 条'
            )
            return {
                'retention_days': retention_days,
                'deleted_count': deleted,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理服务心跳记录失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def clean_system_error_events(cls):
        try:
            from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventService

            retention_days = cls.retention_days('SYSTEM_ERROR_EVENT_RETENTION_DAYS')
            deleted = SystemErrorEventService.cleanup_expired(retention_days)
            log.system.info(
                f'scheduler-service 清理超过 {retention_days} 天的系统异常记录：{deleted} 条'
            )
            return {
                'retention_days': retention_days,
                'deleted_count': deleted,
            }
        except Exception as error:
            log.system.error(f'scheduler-service 清理系统异常记录失败：{error}')
            raise

    @classmethod
    @async_task_db_connection()
    def scan_data_factory_entity_field_updates(cls, schedule_fire_id: int | None = None):
        from src.apps.data_factory.services.schema.schema_monitor import DataFactorySchemaMonitorService

        result = DataFactorySchemaMonitorService.scan(source_record_id=schedule_fire_id)
        log.system.info(
            'scheduler-service 数据工厂字段更新扫描完成：'
            f"实体 {result['scanned_entity_count']} 个，"
            f"观察到结构差异 {result['observed_changed_entity_count']} 个，"
            f"检测差异 {result['detected_changed_entity_count']} 个，"
            f"变更 {result['changed_entity_count']} 个，"
            f"失效模板 {result['invalidated_template_count']} 个，"
            f"失败绑定 {result['failed_binding_count']} 个，"
            f"批量保护 {'已触发' if result['auto_disable_blocked'] else '未触发'}"
        )
        if result["auto_disable_blocked"]:
            log.system.warning(
                f"scheduler-service 数据工厂字段更新扫描触发批量保护：{result['safety_message']}"
            )
        return result
