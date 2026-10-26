"""Business exceptions owned by this Django app."""

from src.common.exceptions.base import MangoServerError
from src.common.exceptions.definitions import ErrorDefinition

SYSTEM_EVALUATION_AI_CONFIG_INVALID = ErrorDefinition(code=38041, message='效果测评 AI 配置无效：请检查所选 AI、唯一标识、模型、服务地址及密钥，已停用或删除的 AI 不能执行')


class SystemError(MangoServerError):
    pass


SYSTEM_NOTICE_WEBHOOK_FAILED = ErrorDefinition(code=38042, message='机器人通知发送失败，请检查 Webhook 配置或网络')
SYSTEM_NOTICE_EMAIL_FAILED = ErrorDefinition(code=38043, message='邮件发送失败，请检查邮箱配置或网络')
SYSTEM_NOTICE_FILE_FAILED = ErrorDefinition(code=38044, message='通知文件上传或发送失败，请检查机器人配置')


SYSTEM_ID_SEQUENCE_EXHAUSTED = ErrorDefinition(code=38039, message='系统ID号段分配失败，请稍后重试')
SYSTEM_ID_SEQUENCE_PROTECTED = ErrorDefinition(code=38040, message='系统ID序列不允许手动修改或删除')

SYSTEM_SAVE_VALIDATION_FAILED = ErrorDefinition(code=38037, message='内部保存失败，请检查数据：{}')
SYSTEM_UPDATE_VALIDATION_FAILED = ErrorDefinition(code=38038, message='内部更新失败，请检查数据：{}')
SYSTEM_TASK_SEND_FAILED = ErrorDefinition(code=1028, message='发送任务失败，请确保{}已连接{}')
SYSTEM_CONFIG_NOT_FOUND = ErrorDefinition(code=1038, message='系统配置【{}】不存在，请先到系统管理->系统设置中配置')
SYSTEM_DIAGNOSTIC_BINDING_REPORT_UNSUPPORTED = ErrorDefinition(code=38000, message='不支持的排查报告绑定对象')
SYSTEM_DIAGNOSTIC_BINDING_REPORT_NOT_FOUND = ErrorDefinition(code=38001, message='排查报告绑定对象不存在或无权访问')
SYSTEM_DIAGNOSTIC_FILE_REPORT_INVALID = ErrorDefinition(code=38002, message='排查报告文件名必须以 .md 结尾')
SYSTEM_DIAGNOSTIC_REPORT_REQUIRED = ErrorDefinition(code=38003, message='排查报告内容不能为空')
SYSTEM_DIAGNOSTIC_REPORT_TOO_LONG = ErrorDefinition(code=38004, message='排查报告不能超过 5 MB')
SYSTEM_DIAGNOSTIC_BINDING_REPORT_INVALID = ErrorDefinition(code=38005, message='当前对象尚未绑定排查报告')
SYSTEM_DIAGNOSTIC_FILE_READ_REPORT_NOT_FOUND = ErrorDefinition(code=38006, message='排查报告文件不存在或读取失败')
SYSTEM_FRONTEND_PARAMETER_INVALID = ErrorDefinition(code=38007, message='前端异常上报参数不正确')

SYSTEM_CATALOG_PROJECT_PRODUCT_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38008,
                                                                                 message='项目产品-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_NOTICE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38009,
                                                                        message='通知组-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_MODULE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38010,
                                                                        message='产品模块-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38011,
                                                                 message='测试对象-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_API_INFO_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38012,
                                                                          message='接口信息-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_CASE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38013,
                                                                      message='API用例-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_PARAMETER_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38014,
                                                                           message='API全局参数-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_REQUEST_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38015,
                                                                         message='API请求头-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_PAGE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38016,
                                                                      message='UI页面-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_STEP_PAGE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38017,
                                                                           message='页面步骤-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_CASE_RELATION_DELETE_BINDING_INVALID_CODE_CASE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(
    code=38018, message='UI用例-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_PARAMETER_RELATION_DELETE_BINDING_INVALID_CODE_PARAMETER_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(
    code=38019, message='UI全局参数-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_TASK_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38020,
                                                                      message='定时任务-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_RELATION_DELETE_BINDING_INVALID_CODE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38021,
                                                                                                      message='项目绑定-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_MODULE_RELATION_DELETE_BINDING_INVALID_CODE_MODULE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(
    code=38022, message='子模块-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_API_INFO_RELATION_DELETE_BINDING_INVALID_CODE_API_INFO_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(
    code=38023, message='接口信息-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_API_CASE_DELETE_PROTECTED = ErrorDefinition(code=38024, message='API用例-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_UI_CASE_DELETE_PROTECTED = ErrorDefinition(code=38025, message='UI用例-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_PAGE_RELATION_DELETE_BINDING_INVALID_CODE_PAGE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(
    code=38026, message='UI页面-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_STEP_PAGE_RELATION_DELETE_BINDING_INVALID_CODE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(
    code=38027, message='页面步骤-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_PYTEST_CASE_DELETE_PROTECTED = ErrorDefinition(code=38028,
                                                      message='Pytest用例-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_ENTITY_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38029,
                                                                        message='数据实体有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_STATUS_TEMPLATE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38030,
                                                                                 message='数据工厂状态模板-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_RECORD_RELATION_EXECUTION_DELETE_BINDING_INVALID = ErrorDefinition(code=38031,
                                                                                  message='数据工厂执行记录-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_TASK_RELATION_DELETE_BINDING_INVALID_CODE_TASK_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(
    code=38032, message='定时任务-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_CATALOG_REQUIREMENT_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38033,
                                                                             message='功能测试需求-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_FUNCTIONAL_CASE_DELETE_PROTECTED = ErrorDefinition(code=38034,
                                                          message='功能测试用例-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_SCHEDULING_TASK_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=38035,
                                                                         message='定时任务-有关联数据，请先删除绑定的数据后再删除！')

SYSTEM_SCHEDULING_TASK_RELATION_DELETE_BINDING_INVALID_CODE_TASK_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(
    code=38036, message='任务明细-有关联数据，请先删除绑定的数据后再删除！')
