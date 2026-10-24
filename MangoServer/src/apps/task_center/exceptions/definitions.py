"""Business error definitions for this Django app."""

from src.common.exceptions.definitions import ErrorDefinition

TASK_API_CONCURRENCY_INVALID = ErrorDefinition(code=1107, message='API执行并发必须是大于等于1的整数')
TASK_SCHEDULE_NOT_FOUND = ErrorDefinition(code=1112, message='定时任务不存在，请刷新页面后重试')
TASK_SCHEDULE_CASE_REQUIRED = ErrorDefinition(code=1125,
                                              message='定时任务尚未绑定任何有效用例，请先添加用例后再启用或执行')
EXECUTOR_TASK_EXECUTOR_TASK_EXECUTION_CLEANUP_NOT_FOUND = ErrorDefinition(code=1160,
                                                                          message='执行器任务不存在或已被清理')
EXECUTOR_TASK_EXECUTOR_TASK_EXECUTION_ACCESS_DENIED = ErrorDefinition(code=1161, message='无权访问该执行器任务')
EXECUTOR_TASK_EXECUTOR_TASK_STATUS_EXECUTION_INVALID = ErrorDefinition(code=1162,
                                                                       message='执行器任务状态或领取关系已失效，请停止执行该任务')
EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID = ErrorDefinition(code=1163,
                                                                          message='执行器任务参数或任务内容不正确')
EXECUTOR_TASK_EXECUTOR_TASK_RESULT_EXECUTION_INVALID = ErrorDefinition(code=1164,
                                                                       message='执行器任务结果格式不正确或内容过大')
EXECUTOR_TASK_EXECUTOR_USER_EXECUTION_NOT_FOUND = ErrorDefinition(code=1165, message='目标执行器用户不存在或当前不可用')
SYSTEM_TASK_CATEGORY_SCENARIO_TASK_EXECUTION_REQUIRED = ErrorDefinition(code=39000, message='请选择定时任务的执行场景')
SYSTEM_TASK_CATEGORY_TASK_EXECUTION_REQUIRED = ErrorDefinition(code=39001, message='请选择定时任务的执行范围')
SYSTEM_TASK_CATEGORY_MODULE_EXECUTION_REQUIRED = ErrorDefinition(code=39002,
                                                                 message='执行范围选择“模块全量”时必须选择模块')
SYSTEM_TASK_CATEGORY_MODULE_EXECUTION_BINDING_NOT_ALLOWED = ErrorDefinition(code=39003,
                                                                            message='执行范围选择“产品全量”时不能同时绑定模块')
SYSTEM_TASK_CATEGORY_API_INFO_TYPE_REQUIRED = ErrorDefinition(code=39004,
                                                              message='“其他自动化”类型暂未开放，请选择UI自动化、API自动化、Pytest自动化或全部类型')
SYSTEM_TASK_CATEGORY_CASE_TASK_TYPE_BINDING_INVALID = ErrorDefinition(code=39005,
                                                                      message='当前定时任务已绑定其他类型用例，请先移除后再修改用例类型')
SYSTEM_TASK_CATEGORY_API_INFO_CASE_TYPE_REQUIRED = ErrorDefinition(code=39006,
                                                                   message='用例类型格式错误，请选择UI自动化、API自动化或Pytest自动化')
SYSTEM_TASK_CATEGORY_CASE_EXECUTION_DELETE_NOT_ALLOWED = ErrorDefinition(code=39007,
                                                                         message='当前执行范围由规则自动选择用例，不允许手动添加或删除用例')
SYSTEM_TASK_CATEGORY_PROJECT_PRODUCT_MODULE_INVALID = ErrorDefinition(code=39008,
                                                                      message='所选模块不属于当前项目产品，请重新选择')
SYSTEM_TASK_CATEGORY_SCENARIO_EXECUTION_INVALID = ErrorDefinition(code=39009,
                                                                  message='生产环境仅支持“稳定性监测”“生产巡检”和“生产回归”执行场景')
SYSTEM_TASK_CATEGORY_SCENARIO_EXECUTION_MINIMUM_REQUIRED = ErrorDefinition(code=39010,
                                                                           message='执行场景格式错误，请至少选择一个有效的执行场景')
SYSTEM_TASK_CATEGORY_MINIMUM_REQUIRED = ErrorDefinition(code=39011, message='请至少选择一个定时策略')
SYSTEM_TASK_CATEGORY_TEST_ENVIRONMENT_MINIMUM_REQUIRED = ErrorDefinition(code=39012,
                                                                         message='测试环境格式错误，请至少选择一个有效的测试环境')
SYSTEM_TASK_CATEGORY_TEST_ENVIRONMENT_SCENARIO_EXECUTION_INVALID = ErrorDefinition(code=39013,
                                                                                   message='执行场景与测试环境不匹配，请为每类环境选择对应的执行场景')
SYSTEM_TASK_CATEGORY_TASK_INVALID = ErrorDefinition(code=39014,
                                                    message='“稳定性监测”只能用于仅包含生产环境的手动指定任务')
SYSTEM_TASK_CATEGORY_SCENARIO_TASK_EXECUTION_NOT_ALLOWED = ErrorDefinition(code=39015,
                                                                           message='“效果评测”仅供 Case 分类使用，不能作为定时任务执行场景')
SYSTEM_TASK_CATEGORY_MODULE_TASK_EXECUTION_CREATE_NOT_ALLOWED = ErrorDefinition(code=39016,
                                                                                message='普通入口支持“手动指定”“产品全量”和“模块全量”，已创建任务不能修改执行范围')
SYSTEM_TASK_GROUP_TASK_NOT_FOUND = ErrorDefinition(code=39017, message='任务组不存在或已归档')
SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID = ErrorDefinition(code=39018, message='任务组配置格式错误：{}')
SYSTEM_TASK_GROUP_STABILITY_SCENE_CONFLICT = ErrorDefinition(
    code=39026, message='稳定性监测不能与生产巡检、生产回归同时选择，请分开配置任务组')
SYSTEM_TASK_GROUP_MODULE_TASK_NOT_ALLOWED = ErrorDefinition(code=39019,
                                                            message='同一任务组不能同时包含父模块和其子模块：{}')
SYSTEM_TASK_GROUP_PROJECT_PRODUCT_TASK_NAME_DUPLICATED = ErrorDefinition(code=39020,
                                                                         message='同一项目产品下任务组名称不能重复')
SYSTEM_TASK_GROUP_TASK_CONFIG_GENERATE_NOT_ALLOWED = ErrorDefinition(code=39021,
                                                                     message='任务组生成的定时任务公共配置不能单独修改，请前往任务组')
SYSTEM_TASK_MODULE_CONFIG_PROJECT_PRODUCT_MODULE_TASK_CONFIG_REQUIRED = ErrorDefinition(code=39022,
                                                                                        message='请选择要配置模块全量任务的项目产品')
SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID = ErrorDefinition(code=39023, message='模块全量配置行格式错误')
SYSTEM_TASK_MODULE_CONFIG_MODULE_TASK_DUPLICATED = ErrorDefinition(code=39024, message='模块全量任务已存在：{}')
SYSTEM_TASK_MODULE_CONFIG_TASK_DELETE_GENERATE_NOT_ALLOWED = ErrorDefinition(code=39025,
                                                                             message='任务组生成的定时任务不能在普通定时任务入口删除，请使用“任务组”')
