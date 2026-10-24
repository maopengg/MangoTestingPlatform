"""Business error definitions for this Django app."""

from src.common.exceptions.definitions import ErrorDefinition

GRAY_REPOSITORY_GRAY_NOT_FOUND = ErrorDefinition(code=36000, message='灰度仓库不存在')
GRAY_FILE_GRAY_NOT_FOUND = ErrorDefinition(code=36001, message='灰度YAML文件不存在')
GRAY_GRAY_NOT_FOUND = ErrorDefinition(code=36002, message='灰度开关不存在')
GRAY_FILE_BINDING_GRAY_INVALID = ErrorDefinition(code=36003, message='YAML灰度必须绑定YAML文件')
GRAY_FILE_DISABLED = ErrorDefinition(code=36004, message='YAML文件已关闭')
GRAY_FILE_NOT_FOUND = ErrorDefinition(code=36005, message='YAML文件不存在：{}')
GRAY_GRAY_INVALID = ErrorDefinition(code=36006, message='灰度Key不是对象结构：{}')
GRAY_PATH_GRAY_NOT_FOUND = ErrorDefinition(code=36007, message='YAML中不存在灰度路径：{}')
GRAY_PATH_GRAY_REQUIRED = ErrorDefinition(code=36008, message='YAML灰度路径不能为空')
GRAY_PATH_INVALID = ErrorDefinition(code=36009, message='YAML路径不是对象结构：{}')
GRAY_GRAY_REQUIRED = ErrorDefinition(code=36010, message='灰度Key不能为空')
GRAY_GRAY_INVALID_CODE_GRAY_INVALID = ErrorDefinition(code=36011, message='YAML灰度变更范围异常：顶层Key发生变化')
GRAY_YAML_NON_TARGET_KEY_CHANGED = ErrorDefinition(code=36012, message='YAML灰度变更范围异常：非目标Key被修改：{}')
GRAY_GRAY_REQUIRED_CODE_GRAY_REQUIRED = ErrorDefinition(code=36013,
                                                        message='缺少 ruamel.yaml 依赖，请安装后再使用灰度 YAML 功能')
GRAY_SQL_CONFIG_GRAY_REQUIRED = ErrorDefinition(code=36014, message='当前灰度动作未配置SQL')
GRAY_SQL_DATABASE_BINDING_GRAY_INVALID = ErrorDefinition(code=36015, message='SQL灰度必须绑定数据库')
GRAY_EXECUTION_GRAY_UNSUPPORTED = ErrorDefinition(code=36016, message='不支持的灰度执行动作')
GRAY_FEATURE_REQUIRED = ErrorDefinition(code=36017, message='请选择灰度开关')
GRAY_TYPE_CONFIG_GRAY_UNSUPPORTED = ErrorDefinition(code=36018, message='不支持的灰度配置类型')
GRAY_EXECUTION_GRAY_FAILED = ErrorDefinition(code=36019, message='灰度执行失败')
GRAY_RECORD_EXECUTION_GRAY_NOT_FOUND = ErrorDefinition(code=36020, message='灰度执行记录不存在')
GRAY_RECORD_EXECUTION_GRAY_REQUIRED = ErrorDefinition(code=36021, message='灰度执行记录缺少灰度开关，无法恢复')
GRAY_PROJECT_PRODUCT_MODULE_INVALID = ErrorDefinition(code=36022, message='模块不属于当前项目/产品')
GRAY_FILE_GRAY_REQUIRED = ErrorDefinition(code=36023, message='YAML灰度必须选择YAML文件')
GRAY_SQL_DATABASE_GRAY_REQUIRED = ErrorDefinition(code=36024, message='SQL灰度必须选择业务数据库')
GRAY_SQL_CONFIG_GRAY_INVALID = ErrorDefinition(code=36025, message='SQL灰度必须配置开启SQL和关闭SQL')
GRAY_FILE_RELATION_DELETE_BINDING_GRAY_INVALID = ErrorDefinition(code=36026,
                                                                 message='灰度YAML文件-有关联数据，请先删除绑定的数据后再删除！')
GRAY_RELATION_DELETE_BINDING_GRAY_INVALID = ErrorDefinition(code=36027,
                                                            message='灰度开关-有关联数据，请先删除绑定的数据后再删除！')
GRAY_CASE_CONFIG_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=36028,
                                                                   message='用例灰度配置-有关联数据，请先删除绑定的数据后再删除！')
GRAY_EXECUTION_GRAY_FAILED_CODE_EXECUTION_GRAY_FAILED = ErrorDefinition(code=36029, message='灰度执行失败：{}')
GRAY_REPOSITORY_TASK_GRAY_INVALID = ErrorDefinition(code=36030,
                                                    message='当前灰度仓库正在被其他任务占用，等待 5 分钟后仍未释放，请稍后重试')
GRAY_PARAMETER_INVALID = ErrorDefinition(code=36031, message='Git操作参数不完整：{}')
GRAY_FILE_REPOSITORY_CONFIG_INVALID = ErrorDefinition(code=36032, message='配置文件目录只能填写仓库内相对目录')
GRAY_FILE_REPOSITORY_PATH_CONFIG_INVALID = ErrorDefinition(code=36033, message='配置文件路径必须位于仓库配置目录内：{}')
GRAY_CONFIG_MINIMUM_REQUIRED = ErrorDefinition(code=36034, message='请至少填写一个配置目录，例如 office-api/nacos')
GRAY_VARIABLE_GRAY_UNSUPPORTED = ErrorDefinition(code=36035, message='不支持的灰度变量来源：{}')
GRAY_PATH_NO_MATCH = ErrorDefinition(code=36036, message='YAML路径原值未匹配，路径：{}，当前值：{}，原值：{}')
GRAY_FILE_GRAY_NOT_FOUND_CODE_FILE_GRAY_NOT_FOUND = ErrorDefinition(code=36037, message='YAML文件中不存在灰度Key：{}')
GRAY_CODE_CONFIG_GRAY_INVALID = ErrorDefinition(code=36038, message='函数代码灰度必须配置开启代码和关闭代码')
GRAY_CODE_GRAY_INVALID = ErrorDefinition(code=36039, message='函数代码灰度必须定义 gray(context) 函数')
GRAY_CODE_EXECUTION_GRAY_FAILED = ErrorDefinition(code=36040, message='函数代码灰度执行失败：{}')
GRAY_REPOSITORY_CONFIG_GRAY_DUPLICATED = ErrorDefinition(code=36041,
                                                         message='当前环境下已存在同名灰度仓库，请勿重复配置')
GRAY_PROJECT_PRODUCT_FILE_CONFIG_DUPLICATED = ErrorDefinition(code=36042,
                                                              message='当前项目产品下已存在同名配置文件，请勿重复配置')
GRAY_FILE_REPOSITORY_CONFIG_BINDING_GRAY_DUPLICATED = ErrorDefinition(code=36043,
                                                                      message='当前配置文件已绑定该灰度仓库，请勿重复配置')
GRAY_FILE_REPOSITORY_CONFIG_BINDING_GRAY_INVALID = ErrorDefinition(code=36044,
                                                                   message='当前配置文件未绑定{}对应的灰度仓库，请先在配置文件中增加仓库绑定')
GRAY_BRANCH_PERMISSION_GRAY_FAILED = ErrorDefinition(code=36045,
                                                     message='灰度合并到目标分支失败，请确认 Git 令牌具备目标分支合并权限：{}')
GRAY_TEST_ENVIRONMENT_SQL_EXECUTION_GRAY_REQUIRED = ErrorDefinition(code=36046,
                                                                    message='执行灰度 SQL 前必须选择测试环境')
GRAY_TEST_ENVIRONMENT_DATABASE_BINDING_GRAY_INVALID = ErrorDefinition(code=36047,
                                                                      message='当前灰度数据库未绑定到所选测试环境')
GRAY_MERGE_WAIT_TIMEOUT = ErrorDefinition(code=36048, message='MR 自动合并等待超时：state={}，merge_status={}')
