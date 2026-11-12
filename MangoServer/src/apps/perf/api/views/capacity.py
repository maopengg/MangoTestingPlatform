from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.perf.formatters import format_perf_row_datetimes
from src.apps.perf.services.capacity.capacity import PerfCapacityService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001


class PerfCapacityViews(ViewSet):

    @error_response("system")
    def overview(self, request: Request):
        """获取性能测试容量概览"""
        data = PerfCapacityService.capacity_overview()
        data["rows"] = [format_perf_row_datetimes(row) for row in data["rows"]]
        return ResponseData.success(RESPONSE_MSG_0001, data)
