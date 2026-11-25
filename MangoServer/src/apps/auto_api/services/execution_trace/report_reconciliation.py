from src.apps.auto_api.selectors.report_trace_state import ApiReportTraceStateSelector
from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
from src.common.logging import log
from src.common.logging.diagnostics import safe_exception_diagnostics


class ApiReportTraceReconciliationService:
    @staticmethod
    def reconcile(limit=100):
        repaired = 0
        for detail_id in ApiReportTraceStateSelector.candidates(limit):
            try:
                repaired += bool(TestSuiteInfrastructureService.reconcile_trace(detail_id))
            except Exception as error:
                code, frames = safe_exception_diagnostics(error)
                log.system.error('报告执行链路补偿待重试：detail=%s type=%s database_code=%s traceback=%s',
                                 detail_id, type(error).__name__, code, frames)
        return repaired
