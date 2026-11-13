"""Truly cross-app error definitions."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ErrorDefinition:
    code: int
    message: str


@dataclass(frozen=True, slots=True)
class ExpectedExceptionInfo:
    code: int
    message: str
    error_code: str
    details: dict[str, Any] = field(default_factory=dict)
    log_status_code: int = 400


INTERNAL_SERVICE_ERROR = ErrorDefinition(code=1000, message='内部服务异常，请联系管理员查看')
JSONPATH_EXPRESSION_INVALID = ErrorDefinition(code=1011, message='jsonpath表达式错误，表达式：{}')
STORAGE_FILE_NOT_FOUND = ErrorDefinition(code=1019,
                                         message='下载文件【{}】不存在，请检查文件名称是否正确，或者是否传到测试文件模块中')
REQUEST_TOO_FREQUENT = ErrorDefinition(code=1058, message='请求频繁，请稍后重试')
JSONPATH_VALUE_TYPE_UNSUPPORTED = ErrorDefinition(code=1066,
                                                  message='当前响应JSON类型为{}，不支持JSONPath处理，只有对象或数组可以使用JSONPath')
TEST_DATA_METHOD_ARGUMENT_INVALID = ErrorDefinition(code=1200, message='测试数据方法参数无效：{}')
RESOURCE_NOT_FOUND = ErrorDefinition(code=300, message='指定的数据不存在或已删除，请重新查询后使用有效ID')
SAVE_VALIDATION_FAILED = ErrorDefinition(code=1201, message='内部保存失败，请检查数据：{}')
UPDATE_VALIDATION_FAILED = ErrorDefinition(code=1202, message='内部更新失败，请检查数据：{}')
RESOURCE_ACCESS_DENIED = ErrorDefinition(code=1203, message='暂无权限访问当前资源，请联系管理员开通权限')
RESOURCE_DELETE_PROTECTED = ErrorDefinition(
    code=1205, message='当前记录仍被业务数据引用，不能删除；请先处理相关关联后重试。',
)
JSONPATH_OPERATION_FAILED = ErrorDefinition(code=1204, message='{}失败{}。{}')
