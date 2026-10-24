"""Business error definitions for this Django app."""

from src.common.exceptions.definitions import ErrorDefinition

UI_PAGE_DUPLICATED = ErrorDefinition(code=33081, message='同一项目产品下已存在相同的具体页面地址，重复页面ID：{}')
UI_ELEMENT_CATEGORY_REQUIRED = ErrorDefinition(code=33082, message='元素分类不能为空')
UI_PAGE_NOT_FOUND = ErrorDefinition(code=33102, message='UI页面不存在或已删除')

UI_PAGE_STEPS_EMPTY = ErrorDefinition(code=1041, message='页面步骤为空，请先配置页面步骤')
UI_CASE_STEPS_EMPTY = ErrorDefinition(code=1042, message='用例步骤为空，请先配置用例步骤')
UI_CANDIDATE_LOCATOR_NOT_FOUND = ErrorDefinition(code=1096, message='候选定位器不存在')
UI_CANDIDATE_LOCATOR_INVALID = ErrorDefinition(code=1097, message='候选定位器缺少表达式类型或定位表达式')
UI_TARGET_SLOT_INVALID = ErrorDefinition(code=1098, message='target_slot 只支持 1、2、3')
UI_AUTH_CACHE_STRUCTURE_INVALID = ErrorDefinition(code=1100, message='手动复制授权缓存结构错误：{}')
UI_AUTH_CACHE_EXPIRED = ErrorDefinition(code=1101, message='UI授权【{}】缓存已过期或为空，请先更新授权缓存后再执行')
UI_AI_LOCATOR_CONTEXT_INVALID = ErrorDefinition(code=1122, message='AI定位器推荐上下文无效，请重新采集元素')
UI_AI_LOCATOR_RECOMMEND_FAILED = ErrorDefinition(code=1123, message='AI定位器推荐失败：{}')
UI_AI_LOCATOR_SESSION_EXPIRED = ErrorDefinition(code=1124, message='AI定位器推荐会话已过期，请重新采集元素')
UI_AUTH_AUTH_CACHE_CONFIG_UPDATE_INVALID = ErrorDefinition(code=1099, message='只有手动复制授权配置可以手动更新缓存')
UI_CASE_EXECUTION_DUPLICATED = ErrorDefinition(code=33000, message='请选择有效且不重复的 UI Case 进行批量执行。')
UI_CASE_CASE_EXECUTION_INVALID = ErrorDefinition(code=33001,
                                                 message='所选 UI Case 来自多个项目：{}。一次批量执行只能选择同一项目下的用例')
UI_CASE_TEST_ENVIRONMENT_EXECUTION_REQUIRED = ErrorDefinition(code=33002, message='批量执行前请选择有效的测试环境。')
UI_DATA_SOURCE_DATA_SOURCE_REQUIRED = ErrorDefinition(code=33003, message='{}第{}项必须选择逻辑数据源')
UI_DATA_SOURCE_DATA_SOURCE_EXECUTION_INVALID = ErrorDefinition(code=33004, message='{}第{}项必须填写数据源执行内容')
UI_DATA_SOURCE_DATA_SOURCE_NOT_FOUND = ErrorDefinition(code=33005, message='{}第{}项选择的逻辑数据源不存在')
UI_DATA_SOURCE_PROJECT_PRODUCT_DATA_SOURCE_INVALID = ErrorDefinition(code=33006,
                                                                     message='{}第{}项选择的逻辑数据源不属于当前项目产品')
UI_DATA_SOURCE_DATA_SOURCE_INVALID = ErrorDefinition(code=33007, message='{}第{}项选择的逻辑数据源已停用')
UI_DATA_SOURCE_EXECUTION_INVALID = ErrorDefinition(code=33008, message='{}第{}项的{}执行内容必须是{}')
UI_DATA_SOURCE_PROJECT_PRODUCT_PARAMETER_INVALID = ErrorDefinition(code=33009, message='{}的项目产品参数不合法')
UI_ELEMENT_RESULT_NOT_FOUND = ErrorDefinition(code=33010,
                                              message='本次深度检测结果不存在或已被新的检测结果覆盖，请重新检测。')
UI_ELEMENT_LOCATOR_WRITE_INVALID = ErrorDefinition(code=33011, message='本次深度检测没有可写入的定位组。')
UI_ELEMENT_PAGE_DELETE_NOT_FOUND = ErrorDefinition(code=33012, message='待扫描的页面不存在或已被删除。')
UI_ELEMENT_PAGE_ELEMENT_INVALID = ErrorDefinition(code=33013, message='页面元素扫描模式无效。')
UI_ELEMENT_PAGE_ELEMENT_ACCESS_DENIED = ErrorDefinition(code=33014, message='无权使用该实时工作区扫描页面元素。')
UI_ELEMENT_ELEMENT_LOCATOR_CONFIG_WRITE_INVALID = ErrorDefinition(code=33015,
                                                                  message='元素定位配置已被其他操作修改，请重新检测后再写入。')
UI_ELEMENT_LOCATOR_INVALID = ErrorDefinition(code=33101, message='候选定位器不满足写回条件：{}')
UI_EXECUTOR_EXECUTOR_EXECUTION_INVALID = ErrorDefinition(code=33016,
                                                         message='当前没有可用的执行器，请启动自己的执行器，或等待公共执行器上线。')
UI_EXECUTOR_EXECUTOR_EXECUTION_INVALID_CODE_EXECUTOR_EXECUTION_INVALID = ErrorDefinition(code=33017,
                                                                                         message='所选执行器【{}】当前不可用，请确认执行器已启动并保持在线。')
UI_EXECUTOR_EXECUTOR_TASK_EXECUTION_INVALID = ErrorDefinition(code=1028, message='执行器在任务发送过程中断开连接。')
UI_LIVE_NOT_FOUND = ErrorDefinition(code=33018, message='实时工作区不存在或已过期，请重新打开。')
UI_LIVE_STEP_PAGE_ACCESS_DENIED = ErrorDefinition(code=33019, message='无权使用该实时工作区调试页面步骤。')
UI_LIVE_STEP_PAGE_INVALID = ErrorDefinition(code=33020, message='实时工作区与当前页面步骤不匹配，请重新打开。')
UI_LIVE_EXECUTOR_USER_EXECUTION_REQUIRED = ErrorDefinition(code=33021,
                                                           message='执行器【{}】当前已有 {}/{} 位用户使用，请选择其他执行器或稍后再试。')
UI_LIVE_EXECUTOR_STATUS_EXECUTION_UPDATE_INVALID = ErrorDefinition(code=33022,
                                                                   message='执行器容量状态正在更新，请稍后重试。')
UI_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_REQUIRED = ErrorDefinition(code=33023, message='SQL断言必须选择逻辑数据源')
UI_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_DELETE_NOT_FOUND = ErrorDefinition(code=33024,
                                                                              message='SQL断言选择的逻辑数据源不存在或已删除')
UI_SQL_ASSERTION_PROJECT_PRODUCT_SQL_DATA_SOURCE_ASSERTION_INVALID = ErrorDefinition(code=33025,
                                                                                     message='SQL断言选择的逻辑数据源不属于当前项目产品')
UI_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_INVALID = ErrorDefinition(code=33026,
                                                                     message='SQL断言选择的逻辑数据源已停用')
UI_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_TYPE_UNSUPPORTED = ErrorDefinition(code=33027,
                                                                              message='SQL断言暂不支持数据源类型：{}')
UI_STEP_STEP_PAGE_NODE_INVALID = ErrorDefinition(code=33028, message='所选节点不属于当前页面步骤，请刷新页面后重新选择。')
UI_STEP_CASE_STEP_PAGE_ORDER_INVALID = ErrorDefinition(code=33029,
                                                       message='排序数据不属于同一个页面步骤或用例，请刷新后重试。')
UI_STEP_STEP_PAGE_INVALID = ErrorDefinition(code=33030, message='页面步骤流程图结构错误：{}')
UI_STEP_STEP_PAGE_CONFIG_INVALID = ErrorDefinition(code=33031, message='页面步骤详情配置错误：{}')
UI_STEP_STEP_PAGE_NOT_FOUND = ErrorDefinition(code=33032, message='页面步骤详情不存在或不属于当前页面步骤。')
UI_STEP_STEP_PAGE_CONFIG_INVALID_CODE_STEP_PAGE_CONFIG_INVALID = ErrorDefinition(code=33033,
                                                                                 message='流程图引用了其他页面步骤的详情配置。')
UI_STEP_CACHE_STEP_NOT_FOUND = ErrorDefinition(code=33034, message='未找到需要刷新缓存的 UI Case 步骤。')
UI_STEP_STEP_PAGE_TYPE_UNSUPPORTED = ErrorDefinition(code=33035, message='不支持的 UI 页面步骤类型：{}')
UI_STEP_HEAL_PAGE_REPORT_INVALID = ErrorDefinition(code=33036, message='页面流程自愈报告结构错误：{}')
UI_STEP_HEAL_RECORD_NOT_ALLOWED = ErrorDefinition(code=33037, message='该修复记录已经应用，不能再拒绝')
UI_STEP_HEAL_STEP_VERSION_PAGE_INVALID = ErrorDefinition(code=33038,
                                                         message='页面步骤已被修改，请基于最新版本重新确认修复建议')
UI_STEP_HEAL_INVALID = ErrorDefinition(code=33039, message='修复建议结构错误：{}')
UI_STEP_HEAL_INVALID_CODE_INVALID = ErrorDefinition(code=33040,
                                                    message='该修复包含新增或跳转动作，请先在画布确认正式流程后再应用')
UI_STEP_HEAL_NODE_NOT_FOUND = ErrorDefinition(code=33041, message='修复建议引用的流程节点不存在')
UI_STEP_HEAL_BRANCH_NODE_NOT_ALLOWED = ErrorDefinition(code=33042,
                                                       message='分支节点不能直接应用跳过建议，请在画布中人工确认')
AUTO_UI_CASE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=33043,
                                                                         message='页面步骤详情-有关联数据，请先删除绑定的数据后再删除！')
AUTO_UI_CASE_TASK_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=33044,
                                                                    message='定时任务详情-有关联数据，请先删除绑定的数据后再删除！')
AUTO_UI_ELEMENT_SERVICE_ELEMENT_NAME_REQUIRED = ErrorDefinition(code=33045, message='元素名称和元素分类不能为空。')
AUTO_UI_ELEMENT_SERVICE_ELEMENT_LOCATOR_EXPRESSION_MINIMUM_REQUIRED = ErrorDefinition(code=33046,
                                                                                      message='元素描述和定位表达式至少填写一项。')
AUTO_UI_ELEMENT_SERVICE_INVALID = ErrorDefinition(code=33047, message='is_iframe 只能是 0 或 1。')
AUTO_UI_ELEMENT_SERVICE_ELEMENT_REQUIRED = ErrorDefinition(code=33048, message='缺少待检测的元素ID。')
AUTO_UI_ELEMENT_SERVICE_ELEMENT_DELETE_NOT_FOUND = ErrorDefinition(code=33049, message='待检测的元素不存在或已被删除。')
AUTO_UI_ELEMENT_SERVICE_NOT_FOUND = ErrorDefinition(code=33050, message='实时工作区不存在或已过期，请重新打开。')
AUTO_UI_ELEMENT_SERVICE_ELEMENT_EXECUTION_ACCESS_DENIED = ErrorDefinition(code=33051,
                                                                          message='无权使用该实时工作区执行元素检测。')
AUTO_UI_ELEMENT_SERVICE_TEST_ENVIRONMENT_USER_INVALID = ErrorDefinition(code=33052,
                                                                        message='当前用户未选择测试环境，请先调用 switch_user_test_environment。')
AUTO_UI_ELEMENT_SERVICE_INVALID_CODE_INVALID = ErrorDefinition(code=33053, message='{} 必须属于 ElementExpEnum。')
AUTO_UI_ELEMENT_SERVICE_ELEMENT_REQUIRED_CODE_ELEMENT_REQUIRED = ErrorDefinition(code=33054,
                                                                                 message='元素分类不能为空。请提供 category，例如：搜索区域、表格、弹窗、表单区域。')
AUTO_UI_ELEMENT_SERVICE_FIELD_REQUIRED = ErrorDefinition(code=33055, message='{}缺少必填字段：{}。')
AUTO_UI_LIVE_STREAM_PERMISSION_SERVICE_EXECUTION_NOT_FOUND = ErrorDefinition(code=33056,
                                                                             message='直播对应的UI执行对象不存在')
AUTO_UI_LIVE_STREAM_PERMISSION_SERVICE_TYPE_EXECUTION_UNSUPPORTED = ErrorDefinition(code=33057,
                                                                                    message='不支持的直播执行类型')
AUTO_UI_LIVE_STREAM_SESSION_SERVICE_EXECUTOR_USER_EXECUTION_INVALID = ErrorDefinition(code=33058,
                                                                                      message='该执行器未开放给其他用户使用')
AUTO_UI_LIVE_STREAM_SESSION_SERVICE_EXECUTOR_EXECUTION_INVALID = ErrorDefinition(code=33059,
                                                                                 message='执行器连接已变化，请重新打开实时画面')
AUTO_UI_LIVE_STREAM_SESSION_SERVICE_ACCESS_DENIED = ErrorDefinition(code=33060, message='无权访问该直播会话')
AUTO_UI_LIVE_STREAM_SESSION_SERVICE_NOT_FOUND = ErrorDefinition(code=33061,
                                                                message='实时工作区不存在或已过期，请重新打开')
AUTO_UI_LIVE_STREAM_SESSION_SERVICE_NOT_FOUND_CODE_NOT_FOUND = ErrorDefinition(code=33062,
                                                                               message='实时工作区不存在或已过期，请重新打开')
AUTO_UI_LIVE_STREAM_SESSION_WORKSPACE_EXPIRED = ErrorDefinition(code=33063,
                                                                message='实时工作区不存在或已过期，请重新打开')
AUTO_UI_LIVE_STREAM_SESSION_STORE_NOT_FOUND = ErrorDefinition(code=33064,
                                                              message='实时画面会话不存在或已关闭，请重新连接')
AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_TYPE_UNSUPPORTED = ErrorDefinition(code=33065, message='不支持的UI实时工作区类型')
AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_TYPE_UNSUPPORTED_CODE_TYPE_UNSUPPORTED = ErrorDefinition(code=33066,
                                                                                               message='不支持的UI实时工作区类型')
AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_REQUIRED = ErrorDefinition(code=33067, message='缺少实时工作区ID')
AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_ACCESS_DENIED = ErrorDefinition(code=33068, message='无权关闭该实时工作区')
AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_ACCESS_DENIED_CODE_ACCESS_DENIED = ErrorDefinition(code=33069,
                                                                                         message='无权查看该实时工作区')
AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_EXECUTOR_USER_EXECUTION_INVALID = ErrorDefinition(code=33070,
                                                                                        message='该执行器未开放给其他用户使用')
AUTO_UI_PAGE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=33071,
                                                                         message='页面步骤-有关联数据，请先删除绑定的数据后再删除！')
AUTO_UI_PAGE_ELEMENT_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=33072,
                                                                       message='元素-有关联数据，请先删除绑定的数据后再删除！')
AUTO_UI_PAGE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID_CODE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(
    code=33073, message='页面步骤详情-有关联数据，请先删除绑定的数据后再删除！')
AUTO_UI_STEP_STEP_PAGE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=33074,
                                                                         message='页面步骤详情-有关联数据，请先删除绑定的数据后再删除！')
AUTO_UI_STEP_CASE_STEP_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=33075,
                                                                         message='用例步骤详情-有关联数据，请先删除绑定的数据后再删除！')
AUTO_UI_TEST_CASE_CASE_DATA_FACTORY_TEST_ENVIRONMENT_EXECUTION_INVALID = ErrorDefinition(code=33076,
                                                                                         message='数据工厂执行前请先初始化测试环境')
AUTO_UI_TEST_CASE_TEST_CASE_STEP_PAGE_CONFIG_NODE_EXECUTION_INVALID = ErrorDefinition(code=33100,
                                                                                      message='页面步骤中存在未保存配置的节点：{}，请先点击节点保存配置后再执行')
AUTO_UI_TEST_CASE_TEST_CASE_CASE_STEP_SAVE_INVALID = ErrorDefinition(code=401,
                                                                     message='请刷新这个用例步骤的数据，这个数据我之前在保存的时候，有一些问题，请刷新后重试')
AUTO_UI_UI_AUTH_EXECUTOR_AUTH_CACHE_CONFIG_EXECUTION_INVALID = ErrorDefinition(code=33077,
                                                                               message='只有自动授权配置可以接收执行器回传缓存')
AUTO_UI_UI_AUTH_AUTH_API_INFO_REQUIRED = ErrorDefinition(code=33078, message='接口转入授权必须选择登录接口')
AUTO_UI_UI_AUTH_AUTH_CACHE_UNSUPPORTED = ErrorDefinition(code=33079, message='当前授权方式不支持刷新缓存')
AUTO_UI_UI_CASE_EXECUTOR_USER_EXECUTION_INVALID = ErrorDefinition(code=33080, message='该执行器未开放给其他用户使用')
UI_AGENT_CASE_NOT_FOUND = ErrorDefinition(code=33103, message='UI Case 不存在或已删除。')
UI_AGENT_EXECUTION_TOKEN_INVALID = ErrorDefinition(code=33107, message='执行令牌无效、已过期或不属于当前用户。')
UI_AGENT_STEP_OUT_OF_ORDER = ErrorDefinition(code=33108, message='步骤下标无效或重复。')
UI_AGENT_CASE_CHANGED = ErrorDefinition(code=33109, message='UI Case 在运行期间发生变化，请重新发起执行。')
UI_AGENT_ARTIFACT_INVALID = ErrorDefinition(code=33110, message='执行证据不符合要求：{}')
UI_AGENT_COMPLETE_INVALID = ErrorDefinition(code=33111, message='成功结果必须包含全部步骤，且每个步骤只能提交一次。')
UI_AGENT_CAPABILITY_MISSING = ErrorDefinition(code=33112, message='代理缺少执行当前 UI 步骤所需的浏览器能力。')
UI_AGENT_REPORT_INVALID = ErrorDefinition(code=33113, message='代理 UI 执行报告结构错误：{}')
UI_AGENT_CASE_FEATURE_UNSUPPORTED = ErrorDefinition(code=33114,
                                                    message='当前代理 UI 协议暂不支持该 Case 的平台托管能力：{}')
UI_AGENT_RUNTIME_OPERATION_INVALID = ErrorDefinition(code=33115, message='代理 UI 运行操作无效：{}')
UI_CASE_PUBLICATION_NOT_FOUND = ErrorDefinition(code=33116, message='UI 用例不存在或已删除')
UI_CASE_PUBLICATION_REQUIRES_PASSED = ErrorDefinition(code=33117, message='用例必须执行通过后才能提交预发布或正式发布')
UI_CASE_PUBLICATION_OWNER_REQUIRED = ErrorDefinition(code=33118, message='请配置项目产品负责人；只有产品负责人可以通过发布或退回未发布')
UI_CASE_PUBLICATION_INVALID_TRANSITION = ErrorDefinition(code=33119, message='发布状态流转无效，请先提交预发布，由产品负责人通过或退回')
