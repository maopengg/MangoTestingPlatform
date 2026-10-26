"""Business exceptions owned by this Django app."""

from src.common.exceptions.base import MangoServerError
from src.common.exceptions.definitions import ErrorDefinition


class TestCenterError(MangoServerError):
    pass


TEST_ARTIFACT_SAVE_FAILED = ErrorDefinition(code=1004, message='执行产物保存失败：{}')
TEST_NOTICE_EMAIL_CACHE_KEY_EMPTY = ErrorDefinition(code=1031,
                                                    message='缓存的key未填写，请先到系统管理->系统设置中填写邮箱配置')
TEST_ENVIRONMENT_DUPLICATED = ErrorDefinition(code=1049,
                                              message='你的测试项目有重复的测试环境，请检查数据，重复的部署环境和产品和自动化类型只允许存在一个')
TEST_DATABASE_TYPE_REQUIRED = ErrorDefinition(code=1065,
                                              message='该用例设置的SQL前置或者后置，但是设置的时候未选择数据库类型')
TEST_ENVIRONMENT_INVALID = ErrorDefinition(code=1113, message='测试环境参数无效，请重新选择')
TEST_REPORT_NOT_FOUND = ErrorDefinition(code=1114, message='测试报告不存在，请刷新页面后重试')
TEST_REPORT_RETRY_RUNNING = ErrorDefinition(code=40100, message='报告仍有待执行或执行中的用例，请完成后再重试失败项')
TEST_REPORT_EVALUATION_OPERATION_UNSUPPORTED = ErrorDefinition(code=40104, message='效果测试报告保留本次执行快照，请前往效果测试用例执行或停止')
TEST_REPORT_DISPOSITION_INVALID = ErrorDefinition(code=40101, message='报告排查参数不正确')
TEST_REPORT_DISPOSITION_ACTIVE = ErrorDefinition(code=40102, message='报告仍在执行，不能修改排除状态或排查结论')
TEST_REPORT_EXCLUSION_NOT_FAILED = ErrorDefinition(code=40103, message='只能排除包含失败结果的执行项')
TEST_CASE_POST_SQL_EMPTY = ErrorDefinition(code=1026, message='用例后置sql的sql不允许为空')
TEST_CASE_PRE_KEY_VALUE_EMPTY = ErrorDefinition(code=1029, message='用例前置的key或value不允许为空')
TEST_SUITE_KEY_EMPTY = ErrorDefinition(code=1032, message='测试套中的key不允许为空')
TEST_CASE_PRE_SQL_REQUIRED = ErrorDefinition(code=1036, message='用例前置的sql中sql是必填')
TEST_CASE_DELETED_PENDING_FAILED = ErrorDefinition(code=1057, message='用例已被删除，历史未执行的全部修改为失败')
TEST_ENVIRONMENT_REQUIRED = ErrorDefinition(code=1077, message='测试环境不能为空')
TEST_FILE_NOT_FOUND = ErrorDefinition(code=40017, message='文件不存在或已删除')
SYSTEM_MODULE_MODULE_BINDING_INVALID = ErrorDefinition(code=40000, message='业务数据只能绑定三级模块')
SYSTEM_MODULE_MODULE_NAME_REQUIRED = ErrorDefinition(code=40001, message='一级、二级、三级模块名称均不能为空')
SYSTEM_MODULE_MODULE_CREATE_DUPLICATED = ErrorDefinition(code=40002, message='当前三级模块已存在，请勿重复创建')
SYSTEM_MODULE_MODULE_PATH_CREATE_INVALID = ErrorDefinition(code=40003,
                                                           message='新增模块必须一次性创建完整的一级、二级、三级路径')
SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_NOT_ALLOWED = ErrorDefinition(code=40004,
                                                                   message='固定三级模块不允许修改所属项目产品或层级')
SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_INVALID = ErrorDefinition(code=40005,
                                                               message='新上级模块必须是同一项目产品下直接上一级的模块')
SYSTEM_REPORT_REPORT_NOT_FOUND = ErrorDefinition(code=40006, message='测试报告不存在')
TEST_DATA_SOURCE_REDIS_PING_INVALID = ErrorDefinition(code=40020, message='Redis PING 返回异常：{}')
TEST_DATA_SOURCE_REDIS_ITEMS_EXCEEDED = ErrorDefinition(code=40021, message='Redis响应项过多，请缩小查询范围')
TEST_DATA_SOURCE_REDIS_EMPTY = ErrorDefinition(code=40022, message='Redis服务端未返回数据')
TEST_DATA_SOURCE_REDIS_ERROR = ErrorDefinition(code=40023, message='Redis返回错误：{}')
TEST_DATA_SOURCE_REDIS_ITEM_TOO_LARGE = ErrorDefinition(code=40024, message='Redis单项响应过大，请缩小查询范围')
TEST_DATA_SOURCE_REDIS_ARRAY_TOO_LARGE = ErrorDefinition(code=40025,
                                                         message='Redis数组响应过大，请使用SCAN类命令分页查询')
TEST_DATA_SOURCE_REDIS_RESPONSE_INVALID = ErrorDefinition(code=40026, message='无法识别 Redis 响应')
SYSTEM_REPORT_REPORT_INVALID = ErrorDefinition(code=40007, message='只有待开始或进行中的测试报告可以立即停止')
SYSTEM_TEST_OBJECT_PROJECT_PRODUCT_API_INFO_TYPE_CONFIG_NOT_FOUND = ErrorDefinition(code=1046,
                                                                                    message='未找到匹配的测试对象配置：项目/产品【{}】，所选环境【{}】，自动化类型【{}】。请前往“测试配置 > 测试对象”新增匹配配置后重试；自动化类型也可选择“UI/API通用”。')

TEST_CENTER_DATABASE_CONNECTION_DATABASE_TYPE_UNSUPPORTED = ErrorDefinition(code=40008,
                                                                            message='暂不支持该数据库类型：{}')

TEST_CENTER_PRODUCT_MODULE_MODULE_NAME_DUPLICATED = ErrorDefinition(code=40009,
                                                                    message='同一父模块下的模块名称不能重复')

TEST_CENTER_PRODUCT_MODULE_MODULE_NOT_ALLOWED = ErrorDefinition(code=40010, message='模块不能将自己设为父模块')

TEST_CENTER_PRODUCT_MODULE_PROJECT_PRODUCT_MODULE_INVALID = ErrorDefinition(code=40011,
                                                                            message='父模块必须属于同一项目产品')

TEST_CENTER_PRODUCT_MODULE_MODULE_INVALID = ErrorDefinition(code=40012, message='模块层级最多为三级')

TEST_CENTER_PRODUCT_MODULE_MODULE_INVALID_CODE_MODULE_INVALID = ErrorDefinition(code=40013,
                                                                                message='一级模块的父模块必须为空')

TEST_CENTER_PRODUCT_MODULE_PROJECT_PRODUCT_MODULE_NOT_ALLOWED = ErrorDefinition(code=40014,
                                                                                message='存在子模块时不能切换项目产品')

TEST_CENTER_PRODUCT_MODULE_MODULE_SAVE_NOT_ALLOWED = ErrorDefinition(code=40015,
                                                                     message='移动后子模块将超过三级，不能保存')

TEST_CENTER_PRODUCT_MODULE_MODULE_NOT_ALLOWED_CODE_MODULE_NOT_ALLOWED = ErrorDefinition(code=40016,
                                                                                        message='模块不能移动到自身后代下')
EXECUTION_ARTIFACT_PATH_REQUIRED = ErrorDefinition(code=40018, message='执行产物路径不能为空')
EXECUTION_ARTIFACT_PATH_INVALID = ErrorDefinition(code=40019, message='执行产物路径不合法')

DATA_SOURCE_DISCOVERY_NOT_FOUND = ErrorDefinition(code=40027, message='数据源配置不存在或已删除')
REPORT_ARTIFACT_INVALID = ErrorDefinition(code=40040, message='报告不存在或无权导出离线 HTML')
REPORT_ARTIFACT_FAILED = ErrorDefinition(code=40042, message='离线报告生成或交付失败，请检查报告交付配置及服务日志')
REPORT_ARTIFACT_RUNNING = ErrorDefinition(code=40043, message='报告中仍有执行中的用例，暂不能生成最终离线报告')
REPORT_ARTIFACT_TOO_LARGE = ErrorDefinition(code=40044, message='离线报告超过文件大小上限，请减少请求响应或截图内容')
REPORT_ARTIFACT_RETENTION_SKIPPED = ErrorDefinition(code=40046, message='该原始全成功报告按仅异常保留策略不生成离线文件')
REPORT_LOCAL_LINK_UNAVAILABLE = ErrorDefinition(code=40047, message='当前为本地文件存储，无法提供离线报告链接；请在执行报告中手动下载 HTML，或配置 MinIO/TOS。')
DATA_SOURCE_DISCOVERY_UNSUPPORTED = ErrorDefinition(code=40028, message='当前类型暂不支持此发现操作')
DATA_SOURCE_DISCOVERY_FAILED = ErrorDefinition(code=40029, message='读取数据库元数据失败，请测试连接并查看服务日志')
DATA_SOURCE_QUERY_READ_ONLY = ErrorDefinition(code=40034,
                                              message='仅支持单条只读 SELECT、SHOW 或 DESCRIBE 查询，不允许写入、锁定或导出操作')
DATA_SOURCE_QUERY_LIMIT_REQUIRED = ErrorDefinition(code=40035,
                                                   message='查询必须在最外层明确指定 LIMIT 1至200，例如 SELECT * FROM table_name LIMIT 20')
TEST_TARGET_INVALID = ErrorDefinition(code=40036,
                                      message='测试地址配置无效：请填写默认地址，或设置缓存键名和非空地址映射；键名不使用模板语法')
TEST_TARGET_UNRESOLVED = ErrorDefinition(code=40037, message='{}')
TEST_TARGET_AUTH_CHANGED = ErrorDefinition(code=40038,
                                           message='认证过程中地址条件变量发生变化，已停止保存认证缓存；请保持登录与用例使用相同的条件值')
DATA_SOURCE_IMPORT_SELECTION_INVALID = ErrorDefinition(code=40030,
                                                       message='所选数据库不在当前账号可发现的列表中，请刷新后重试')
DATA_SOURCE_IMPORT_ALIAS_INVALID = ErrorDefinition(code=40031,
                                                   message='导入别名必须为 1 至 64 个字符，且只能设置所选数据库的别名')
DATA_SOURCE_ALIAS_SUGGESTION_FAILED = ErrorDefinition(code=40032,
                                                      message='AI别名推断失败，请检查AI配置或手动填写别名后重试')
DATA_SOURCE_CONNECTION_DUPLICATED = ErrorDefinition(
    code=40033,
    message='相同连接已存在：{}（ID {}），请复用已有数据库配置；密码变更请编辑原配置',
)
