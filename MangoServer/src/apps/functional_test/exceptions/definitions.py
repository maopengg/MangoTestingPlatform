"""Business error definitions for this Django app."""

from src.common.exceptions.definitions import ErrorDefinition

FUNCTIONAL_TEST_PROJECT_PRODUCT_MODULE_INVALID = ErrorDefinition(code=35000, message='所选模块不属于当前项目产品')
FUNCTIONAL_TEST_PROJECT_PRODUCT_VERSION_REQUIREMENT_INVALID = ErrorDefinition(code=35001,
                                                                              message='需求版本与需求主体必须属于同一项目产品')
FUNCTIONAL_TEST_VERSION_REQUIREMENT_INVALID = ErrorDefinition(code=35002, message='上一版本必须属于同一需求主体')
FUNCTIONAL_TEST_VERSION_REQUIREMENT_NOT_ALLOWED = ErrorDefinition(code=35003, message='需求版本不能将自己设为上一版本')
FUNCTIONAL_TEST_REQUIREMENT_NOT_FOUND = ErrorDefinition(code=35004, message='需求主体不存在')
FUNCTIONAL_TEST_DATABASE_CASE_NOT_ALLOWED = ErrorDefinition(code=35005,
                                                            message='测试平台用例是数据库快照，不能作为上下文资料新增或修改')
FUNCTIONAL_TEST_CASE_INVALID = ErrorDefinition(code=35006, message='功能用例校验未通过：{}')
FUNCTIONAL_TEST_MODULE_REQUIREMENT_REQUIRED = ErrorDefinition(code=35007, message='需求必须选择一级、二级或三级模块')
FUNCTIONAL_TEST_TYPE_SAVE_INVALID = ErrorDefinition(code=35008,
                                                    message='飞书资料类型暂未开放，请先选择普通URL或文本方式保存')
FUNCTIONAL_TEST_PLAN_NOT_FOUND = ErrorDefinition(code=35009, message='测试计划不存在或无权访问')
FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_PLAN_INVALID = ErrorDefinition(code=35010,
                                                                    message='测试计划与所选用例必须属于同一项目产品')
FUNCTIONAL_TEST_CASE_REQUIRED = ErrorDefinition(code=35011, message='请选择至少一条有效的用例')
FUNCTIONAL_TEST_PLAN_STATUS_EXECUTION_NOT_ALLOWED = ErrorDefinition(code=35012,
                                                                    message='当前测试计划状态不允许执行此操作')
FUNCTIONAL_TEST_CASE_PLAN_NOT_FOUND = ErrorDefinition(code=35013, message='计划用例不存在')
FUNCTIONAL_TEST_STEP_RESULT_INVALID = ErrorDefinition(code=35014,
                                                      message='测试步骤必须是数组，每一步必须包含操作或预期结果')
FUNCTIONAL_TEST_RESULT_INVALID = ErrorDefinition(code=35015, message='测试结果值不正确')
FUNCTIONAL_TEST_CONFIG_INVALID = ErrorDefinition(code=35016, message='表格视图配置格式不正确')
FUNCTIONAL_TEST_CASE_PLAN_EXECUTION_DELETE_NOT_ALLOWED = ErrorDefinition(code=35017,
                                                                         message='用例已被测试计划或执行引用，不能删除：{}')
FUNCTIONAL_TEST_ITERATION_NOT_ALLOWED = ErrorDefinition(code=35018, message='迭代结束日期不能早于开始日期')
FUNCTIONAL_TEST_REQUIREMENT_ITERATION_NOT_ALLOWED = ErrorDefinition(code=35019,
                                                                    message='已完成或已取消的迭代不能继续排入需求')
FUNCTIONAL_TEST_PLAN_NOT_ALLOWED = ErrorDefinition(code=35020,
                                                   message='排期日期必须完整，且计划提测日期不能早于计划开始日期')
FUNCTIONAL_TEST_REQUIREMENT_ITERATION_INVALID = ErrorDefinition(code=35021,
                                                                message='需求排期必须位于所选迭代的日期范围内')
FUNCTIONAL_TEST_ITERATION_STATUS_REQUIRED = ErrorDefinition(code=35022,
                                                            message='已排期及后续状态必须选择迭代、开发负责人和完整排期日期')
FUNCTIONAL_TEST_VERSION_PLAN_REQUIREMENT_ITERATION_DELETE_NOT_ALLOWED = ErrorDefinition(code=35023,
                                                                                        message='存在需求版本或测试计划的迭代不能删除')
FUNCTIONAL_TEST_VERSION_PLAN_REQUIREMENT_TYPE_REQUIRED = ErrorDefinition(code=35024,
                                                                         message='需求类型测试计划必须选择具体需求版本')
FUNCTIONAL_TEST_PLAN_ITERATION_TYPE_REQUIRED = ErrorDefinition(code=35025, message='Sprint 类型测试计划必须选择迭代')
FUNCTIONAL_TEST_STEP_DEFECT_INVALID = ErrorDefinition(code=35026, message='缺陷复现步骤格式不正确')
FUNCTIONAL_TEST_DEFECT_DUPLICATED = ErrorDefinition(code=35027, message='缺陷附件必须是不重复的正整数数组')
FUNCTIONAL_TEST_DEFECT_INVALID = ErrorDefinition(code=35028, message='处理中缺陷必须指定经办人')
FUNCTIONAL_TEST_DEFECT_DISABLED = ErrorDefinition(code=35029, message='已解决或已关闭缺陷必须填写解决方式')
FUNCTIONAL_TEST_CASE_PLAN_DEFECT_RELATION_MINIMUM_REQUIRED = ErrorDefinition(code=35030,
                                                                             message='测试计划来源的缺陷必须关联至少一条计划用例')
FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_DEFECT_RELATION_INVALID = ErrorDefinition(code=35031,
                                                                               message='缺陷关联的用例必须属于同一项目产品')
FUNCTIONAL_TEST_DEFECT_STATUS_EXECUTION_NOT_ALLOWED = ErrorDefinition(code=35032, message='缺陷状态不允许执行此流转')
FUNCTIONAL_TEST_VERSION_PLAN_REQUIREMENT_DELETE_NOT_ALLOWED = ErrorDefinition(code=35033,
                                                                              message='存在测试计划的需求版本不能删除')
FUNCTIONAL_TEST_PLAN_DELETE_NOT_ALLOWED = ErrorDefinition(code=35034, message='已完成或已关闭的测试计划不能删除')
FUNCTIONAL_TEST_PLAN_DEFECT_DELETE_NOT_ALLOWED = ErrorDefinition(code=35035, message='测试计划已有缺陷引用，不能删除')
FUNCTIONAL_TEST_VERSION_REQUIREMENT_ITERATION_BINDING_INVALID = ErrorDefinition(code=35036,
                                                                                message='需求版本必须绑定迭代')
FUNCTIONAL_TEST_REQUIREMENT_STATUS_INVALID = ErrorDefinition(code=35037, message='需求状态已被其他人修改，请刷新后重试')
FUNCTIONAL_TEST_PLAN_RELATION_MINIMUM_REQUIRED = ErrorDefinition(code=35038,
                                                                 message='进入测试中前必须至少启动一个关联测试计划')
FUNCTIONAL_TEST_PLAN_REQUIREMENT_EXECUTION_NOT_ALLOWED = ErrorDefinition(code=35039,
                                                                         message='存在执行中的测试计划，不能将需求标记为测试完成')
FUNCTIONAL_TEST_REQUIREMENT_STATUS_INVALID_CODE_REQUIREMENT_STATUS_INVALID = ErrorDefinition(code=35040,
                                                                                             message='需求状态值不正确')
FUNCTIONAL_TEST_CASE_REQUIREMENT_REQUIRED = ErrorDefinition(code=35041, message='请选择当前需求下的有效用例')
FUNCTIONAL_TEST_TASK_PLAN_NOT_ALLOWED = ErrorDefinition(code=35042, message='子任务计划结束日期不能早于开始日期')
FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_REQUIREMENT_REQUIRED = ErrorDefinition(code=35043,
                                                                            message='请选择有效且与需求项目产品一致的用例')
FUNCTIONAL_TEST_TASK_NOT_FOUND = ErrorDefinition(code=35044, message='子任务不存在或无权访问')
FUNCTIONAL_TEST_PROJECT_PRODUCT_REQUIREMENT_DEFECT_RELATION_INVALID = ErrorDefinition(code=35045,
                                                                                      message='缺陷关联需求与项目产品不一致')
FUNCTIONAL_TEST_REQUIREMENT_INVALID = ErrorDefinition(code=35046,
                                                      message='进入需求就绪前必须填写需求描述，并设置 PM 和需求分类')
FUNCTIONAL_TEST_PLAN_INVALID = ErrorDefinition(code=35047,
                                               message='进入待开发前必须设置开发负责人、计划开始日期和计划提测日期')
FUNCTIONAL_TEST_TASK_CREATE_MINIMUM_REQUIRED = ErrorDefinition(code=35048,
                                                               message='进入开发中前必须至少创建一个未取消的开发子任务')
FUNCTIONAL_TEST_TASK_INVALID = ErrorDefinition(code=35049,
                                               message='进入待提测前必须完成全部开发子任务，并通过或豁免开发自测')
FUNCTIONAL_TEST_PLAN_INVALID_CODE_PLAN_INVALID = ErrorDefinition(code=35050, message='进入待发布前必须填写计划上线日期')
FUNCTIONAL_TEST_DYNAMIC_ERROR = ErrorDefinition(code=35051, message='{}')
FUNCTIONAL_TEST_SUITE_REQUIRED = ErrorDefinition(code=35052, message='测试负责人不能为空')
