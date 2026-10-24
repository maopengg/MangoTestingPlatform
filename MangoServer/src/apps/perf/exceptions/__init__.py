"""Business exceptions owned by this Django app."""

from src.common.exceptions.base import MangoServerError
from src.common.exceptions.definitions import ErrorDefinition


class PerfError(MangoServerError):
    pass


PERF_SCENARIO_CONFIG_PERF_INVALID = ErrorDefinition(code=61001, message="性能场景配置无效：{}")
PERF_VERSION_CONFIG_PERF_INVALID = ErrorDefinition(code=61004, message="性能配置版本冲突，请刷新后重试")
PERF_EXECUTOR_EXECUTION_INVALID = ErrorDefinition(code=61005, message="没有满足要求的在线执行器")
PERF_EXECUTOR_EXECUTION_INVALID_CODE_EXECUTOR_EXECUTION_INVALID = ErrorDefinition(code=61006,
                                                                                  message="执行器总安全容量不足，所需 {}，可用 {}")
PERF_STATUS_EXECUTION_NOT_ALLOWED = ErrorDefinition(code=61007, message="当前运行状态不允许执行该操作")
PERF_NODE_FAILED = ErrorDefinition(code=61008, message="指标协议或节点归属校验失败")
PERF_INVALID = ErrorDefinition(code=61009, message="指标序号与已入库内容冲突")
PERF_PERF_NOT_FOUND = ErrorDefinition(code=61010, message="性能运行不存在")
PERF_EXECUTION_PERF_INVALID = ErrorDefinition(code=61011, message="性能执行引擎不受支持：{}")
PERF_SCENARIO_DELETE_PERF_NOT_ALLOWED = ErrorDefinition(code=61013, message="性能测试场景已有历史运行，不能删除")
PERF_PROJECT_PRODUCT_PERF_ACCESS_DENIED = ErrorDefinition(code=61016, message="无权访问该项目产品的性能测试数据")
PERF_PERF_INVALID = ErrorDefinition(code=61018, message="生产环境性能测试必须显式确认风险")
PERF_SCENARIO_REQUEST_CONFIG_PERF_REQUIRED = ErrorDefinition(code=61019, message="性能场景配置请求缺少必填配置：{}")
PERF_SCENARIO_PERF_REQUIRED = ErrorDefinition(code=61020, message="性能场景的{}不能为空")
PERF_EXECUTOR_EXECUTION_PERF_REQUIRED = ErrorDefinition(code=61021,
                                                        message="开始性能测试前必须选择 {} 个执行器，当前选择 {} 个")
PERF_REQUEST_RECORD_NODE_EXECUTION_DOWNLOAD_INVALID = ErrorDefinition(code=61022,
                                                                      message="该执行节点没有可下载的请求记录")
