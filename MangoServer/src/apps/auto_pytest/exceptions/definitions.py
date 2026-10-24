"""Business error definitions for this Django app."""

from src.common.exceptions.definitions import ErrorDefinition

PYTEST_REPOSITORY_USER_UNAVAILABLE = ErrorDefinition(code=1020, message='pytest仓库无法获取用户信息，请先拉取git仓库')
PYTEST_PROJECT_PRODUCT_REQUIRED = ErrorDefinition(code=1059,
                                                  message='你的测试用例或者pytest项目未绑定项目，请先绑定项目/产品再测试')
PYTEST_TEST_DIRECTORY_REQUIRED = ErrorDefinition(code=1061,
                                                 message='测试文件目录名称为空，请先编辑项目，填写测试文件目录名称')
PYTEST_DIRECTORY_NOT_FOUND = ErrorDefinition(code=1062, message='目录 {} 不存在')
PYTEST_PROJECT_NOT_FOUND = ErrorDefinition(code=1063, message='项目 {} 不存在')
PYTEST_REPOSITORY_LOCKED = ErrorDefinition(code=1102, message='Pytest Git仓库正在被其他操作使用，请稍后重试')
PYTEST_GIT_ARGUMENTS_INCOMPLETE = ErrorDefinition(code=1103, message='Git操作参数不完整：{}')
PYTEST_FILE_TYPE_INVALID = ErrorDefinition(code=32000, message='文件类型只允许 py 或 feature')
PYTEST_FILE_BINDING_INVALID = ErrorDefinition(code=32001, message='当前 Pytest 资产没有绑定对应文件')
PYTEST_EXECUTION_DUPLICATED = ErrorDefinition(code=32002, message='请选择有效且不重复的 Pytest Case 进行批量执行')
PYTEST_CASE_EXECUTION_INVALID = ErrorDefinition(code=32003,
                                                message='所选 Pytest Case 来自多个项目：{}。一次批量执行只能选择同一项目下的用例')
PYTEST_TEST_ENVIRONMENT_EXECUTION_REQUIRED = ErrorDefinition(code=32004, message='批量执行前请选择有效的测试环境')
PYTEST_PROJECT_PRODUCT_BINDING_INVALID = ErrorDefinition(code=32005, message='以下 Pytest Case 尚未绑定项目产品：{}')
PYTEST_EXECUTION_INVALID = ErrorDefinition(code=32006, message='Pytest Git 凭据引用已过期，请重新发起执行')
PYTEST_EXECUTOR_EXECUTION_READ_ACCESS_DENIED = ErrorDefinition(code=32007,
                                                               message='当前执行器无权读取该 Pytest Git 凭据')
PYTEST_CASE_INVALID = ErrorDefinition(code=32008, message='Pytest Case 未设置用例负责人')
PYTEST_REPOSITORY_BRANCH_CODE_INVALID = ErrorDefinition(code=32009,
                                                        message='Pytest 仓库暂存区存在未推送修改，请先推送代码后再拉取或切换分支')
PYTEST_REPOSITORY_UNSUPPORTED = ErrorDefinition(code=32010, message='平台不支持强制推送 Pytest 仓库')
PYTEST_REPOSITORY_FAILED = ErrorDefinition(code=32011, message='Pytest 仓库 API 同步失败：{}')
PYTEST_FILE_REPOSITORY_FAILED = ErrorDefinition(code=32012,
                                                message='Pytest 仓库 API 提交失败：{}；已成功提交的文件不会回滚，请核对后重试')
PYTEST_CASE_FILE_BRANCH_DELETE_INVALID = ErrorDefinition(code=32013,
                                                         message='当前分支中找不到该用例文件，文件可能已被移动或删除。请先同步当前项目；如已切换分支，请切回包含该文件的分支后重试')
PYTEST_REPOSITORY_REQUIRED = ErrorDefinition(code=32014, message='请选择仓库内有效的相对目录')
PYTEST_BRANCH_NOT_FOUND = ErrorDefinition(code=32015, message='当前分支中不存在目录：{}')
PYTEST_FILE_INVALID = ErrorDefinition(code=32016, message='目录 {} 中没有可识别的 Pytest Case 文件')
PYTEST_DUPLICATED = ErrorDefinition(code=32017, message='项目目录 {} 已经导入，请勿重复导入')
PYTEST_NAME_INVALID = ErrorDefinition(code=32018, message='请输入 Pytest 项目名称')
PYTEST_TYPE_REQUIRED = ErrorDefinition(code=32019, message='请选择有效的自动化类型')
PYTEST_PROJECT_PRODUCT_REQUIRED_CODE_PROJECT_PRODUCT_REQUIRED = ErrorDefinition(code=32020,
                                                                                message='请选择有效的项目/产品')
PYTEST_PERMISSION_REQUIRED = ErrorDefinition(code=32021, message='请选择有效且有权限的 Pytest Case')
PYTEST_PROJECT_PRODUCT_MODULE_INVALID = ErrorDefinition(code=32022,
                                                        message='所选 Pytest Case 与目标模块不属于同一项目产品')
PYTEST_MODULE_BINDING_INVALID = ErrorDefinition(code=32023, message='Pytest Case 只能绑定三级模块')
PYTEST_MODULE_REQUIRED = ErrorDefinition(code=32024, message='请选择有效的模块')
PYTEST_REPOSITORY_DELETE_NOT_FOUND = ErrorDefinition(code=32025, message='Pytest 仓库不存在或已删除')
PYTEST_REPOSITORY_NOT_FOUND = ErrorDefinition(code=32026, message='Pytest 仓库凭证不存在或无法解密')
PYTEST_FILE_REPOSITORY_SAVE_INVALID = ErrorDefinition(code=32027,
                                                      message='Pytest 仓库文件已被其他操作修改，请重新加载后再保存')
PYTEST_FILE_REPOSITORY_PATH_INVALID = ErrorDefinition(code=32028, message='Pytest 仓库文件路径不合法')
PYTEST_REPOSITORY_DELETE_BINDING_INVALID = ErrorDefinition(code=32029, message='Pytest 仓库仍绑定项目，请先删除项目绑定')
PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED = ErrorDefinition(code=32030, message='请选择有效的 Pytest 仓库')
PYTEST_REPOSITORY_FAILED_CODE_REPOSITORY_FAILED = ErrorDefinition(code=32031, message='Pytest 仓库同步失败：{}')
PYTEST_EXECUTION_NOT_ALLOWED = ErrorDefinition(code=32032, message='Pytest 项目已停用，不允许同步、编辑或执行')
PYTEST_FILE_EXECUTION_NOT_ALLOWED = ErrorDefinition(code=32033,
                                                    message='当前 Pytest 测试文件已停用、归档或忽略，不能执行')
PYTEST_FILE_PARSE_FAILED = ErrorDefinition(code=32034,
                                           message='当前 Pytest 测试文件源码缺失、解析失败或存在来源冲突，请先同步并处理源码')
PYTEST_PERMISSION_UPDATE_INVALID = ErrorDefinition(code=32035,
                                                   message='批量编辑必须包含 1-500 条有权限的 Pytest Case 更新')
PYTEST_PARAMETER_INVALID = ErrorDefinition(code=32036, message='第 {} 条 Pytest Case 批量编辑参数不正确：{}')
PYTEST_PROJECT_PRODUCT_MODULE_INVALID_CODE_PROJECT_PRODUCT_MODULE_INVALID = ErrorDefinition(code=32037,
                                                                                            message='Pytest Case {} 选择的模块无效或不属于当前项目产品')
PYTEST_PERMISSION_INVALID = ErrorDefinition(code=32038, message='AI 推断必须包含 1-500 条有权限的 Pytest Case')
PYTEST_FAILED = ErrorDefinition(code=32039, message='Pytest Case AI 推断失败：{}')
PYTEST_FILE_REPOSITORY_REQUIRED = ErrorDefinition(code=32040, message='请选择仓库中的有效文件')
PYTEST_FILE_UNSUPPORTED = ErrorDefinition(code=32041, message='该文件不是 UTF-8 文本文件，暂不支持在线预览')
PYTEST_FILE_REPOSITORY_BRANCH_DELETE_READ_INVALID = ErrorDefinition(code=32042,
                                                                    message='当前分支中的文件无法读取，可能已被移动、删除或仓库尚未同步完成，请同步仓库后重试')
PYTEST_REPOSITORY_INVALID = ErrorDefinition(code=32043, message='Git 平台与仓库地址不匹配，请检查后重试')
PYTEST_REPOSITORY_BRANCH_NAME_NOT_FOUND = ErrorDefinition(code=32044,
                                                          message='仓库中不存在默认分支 {}，请检查分支名称后重试')
PYTEST_BRANCH_INVALID = ErrorDefinition(code=32045, message='远程分支已有新提交，请先拉取并确认差异后再推送')
PYTEST_REPOSITORY_CODE_CONFIG_INVALID = ErrorDefinition(code=32046, message='推送代码需要配置仓库访问凭证')
PYTEST_FILE_REPOSITORY_INVALID = ErrorDefinition(code=32047,
                                                 message='Git API 仅支持推送 UTF-8 文本文件，请通过仓库客户端处理二进制文件')
PYTEST_REPOSITORY_CONFIG_INVALID = ErrorDefinition(code=32048,
                                                   message='Gitee 仓库通过 Git API 同步时需要配置 Access Token')
AUTO_PYTEST_GENERAL_TASK_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=32049,
                                                                           message='定时任务详情-有关联数据，请先删除绑定的数据后再删除！')
PYTEST_PUBLICATION_NOT_FOUND = ErrorDefinition(code=32050, message='Pytest 用例不存在或项目产品未绑定')
PYTEST_PUBLICATION_REQUIRES_PASSED = ErrorDefinition(code=32051, message='用例必须执行通过后才能提交预发布或正式发布')
PYTEST_PUBLICATION_OWNER_REQUIRED = ErrorDefinition(code=32052, message='请配置项目产品负责人；只有产品负责人可以通过发布或退回未发布')
PYTEST_PUBLICATION_INVALID_TRANSITION = ErrorDefinition(code=32053, message='发布状态流转无效，请先提交预发布，由产品负责人通过或退回')
