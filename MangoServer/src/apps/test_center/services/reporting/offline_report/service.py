import json
import re
import uuid
from datetime import timedelta

from django.utils import timezone
from pydantic import ValidationError
from mangotools.enums import TaskEnum

from src.apps.system.services.configuration.system_config import SystemConfigService
from src.apps.test_center.constants import OFFLINE_REPORT_MAX_BYTES
from src.apps.test_center.enums.report_delivery import ReportSourceEnum
from src.apps.test_center.exceptions import (
    REPORT_ARTIFACT_FAILED, REPORT_ARTIFACT_TOO_LARGE, REPORT_ARTIFACT_RETENTION_SKIPPED, REPORT_LOCAL_LINK_UNAVAILABLE, TestCenterError,
)
from src.apps.test_center.models import TestSuite
from src.apps.test_center.schemas.report_delivery import ReportDeliveryConfig
from src.apps.test_center.services.reporting.offline_report.renderer import ReportHtmlService
from src.apps.test_center.services.reporting.offline_report.snapshot import ReportSnapshotService
from src.apps.test_center.services.reporting.offline_report.storage import ReportStorageService
from src.common.logging import log


class OfflineReportService:
    @classmethod
    def publish(cls, kind, source_id):
        if ReportStorageService().local is not None:
            raise TestCenterError(REPORT_LOCAL_LINK_UNAVAILABLE)
        config = cls.config()
        filename, content = cls.render(kind, source_id, config)
        # 有效期按签名前的时间计算，不把上传耗时额外计入可用时间。
        expires_at = timezone.now() + timedelta(seconds=config.link_ttl_seconds)
        links = cls.upload_links(config, filename, content)
        return {
            'filename': filename, 'preview_url': links['查看离线报告'],
            'download_url': links['下载 HTML'], 'expires_at': expires_at.isoformat(),
        }

    @staticmethod
    def config():
        raw = SystemConfigService.get('REPORT_DELIVERY_CONFIG', default={})
        try:
            return ReportDeliveryConfig.model_validate(json.loads(raw) if isinstance(raw, str) else raw)
        except (ValidationError, TypeError, json.JSONDecodeError) as error:
            raise TestCenterError(REPORT_ARTIFACT_FAILED) from error

    @classmethod
    def render(cls, kind, source_id, config=None):
        try:
            config = config or cls.config()
            if kind == ReportSourceEnum.SUITE:
                suite = TestSuite.objects.filter(id=source_id).first()
                if suite and ReportSnapshotService.suppresses_success_report(suite):
                    raise TestCenterError(REPORT_ARTIFACT_RETENTION_SKIPPED)
            snapshot = ReportSnapshotService.build(kind, source_id, config)
            content = ReportHtmlService.render(snapshot, SystemConfigService.get_platform_name())
            if len(content) > OFFLINE_REPORT_MAX_BYTES:
                raise TestCenterError(REPORT_ARTIFACT_TOO_LARGE)
            return f'report-{kind.value}-{source_id}.html', content
        except TestCenterError:
            raise
        except Exception as error:
            # 原始结果读取可能触发存储 SDK 异常，其正文可能带签名地址。
            log.system.warning(f'离线 HTML 生成失败：source={kind.value}:{source_id}, type={type(error).__name__}')
            raise TestCenterError(REPORT_ARTIFACT_FAILED) from error

    @staticmethod
    def upload_links(config, filename, content):
        storage = ReportStorageService()
        if storage.local is not None:
            raise TestCenterError(REPORT_LOCAL_LINK_UNAVAILABLE)
        key = storage.key(uuid.uuid4().hex)
        stage = 'upload'
        try:
            storage.save(key, content)
            stage = 'sign_links'
            return {
                '查看离线报告': storage.url(key, filename, config.link_ttl_seconds),
                '下载 HTML': storage.url(key, filename, config.link_ttl_seconds, True),
            }
        except Exception as error:
            OfflineReportService.log_storage_failure(stage, error)
            try:
                storage.delete(key)
            except Exception as cleanup_error:
                OfflineReportService.log_storage_failure('cleanup', cleanup_error)
            raise TestCenterError(REPORT_ARTIFACT_FAILED) from error

    @staticmethod
    def log_storage_failure(stage, error):
        # SDK 原始异常可能带 Authorization 或签名 URL，只记录白名单格式的错误码。
        code = str(getattr(error, 'code', '') or '')
        code = code if re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', code) else 'unknown'
        status = getattr(error, 'status_code', None)
        status = status if isinstance(status, int) else 'unknown'
        log.system.warning(f'离线报告存储失败：stage={stage}, type={type(error).__name__}, status={status}, code={code}')

    @classmethod
    def sample(cls):
        config = cls.config()
        snapshot = {'name': '示例离线报告（模拟数据）', 'product': '示例项目 / 示例产品', 'environment': '测试环境',
                    'started_at': '-', 'generated_at': '-', 'result': '失败', 'rate': '50.00%',
                    'summary': {'case_sum': 3, 'success': 1, 'fail': 1, 'warning': 0, 'excluded_count': 1},
                    'suites': [{'name': '示例子任务', 'cases': [
                        {'id': 1, 'name': '示例查询用例', 'type': 'API', 'status': '通过', 'excluded': False, 'duration': 0.28},
                        {'id': 2, 'name': '示例数据校验用例', 'type': 'API', 'status': '失败', 'excluded': False, 'duration': 0.64,
                         'error': '预期状态为已完成，实际为处理中（模拟信息）', 'reason': '产品缺陷待修复',
                         'description': '模拟排查记录，等待修复后重试。', 'payload': {'response': {'status': 'processing'}}},
                        {'id': 3, 'name': '示例页面校验用例', 'type': 'UI', 'status': '失败', 'excluded': True, 'duration': 1.2,
                         'reason': '测试平台问题', 'description': '模拟平台问题，已排除，不计入有效失败。'},
                    ]}]}
        snapshot['failed_cases_only'] = config.failed_cases_only
        snapshot['online_url'] = ReportSnapshotService.online_url(ReportSourceEnum.SUITE)
        for suite in snapshot['suites']:
            suite['cases'] = ([case for case in suite['cases'] if not config.failed_cases_only or case['status'] == TaskEnum.get_value(TaskEnum.FAIL.value)]
                              if config.include_details else [])
        return ReportHtmlService.render(snapshot, SystemConfigService.get_platform_name())
