"""Business error definitions for this Django app."""

from src.common.exceptions.definitions import ErrorDefinition

API_CASE_POSTERIOR_CLEANUP_FAILED = ErrorDefinition(code=31223, message='用例后置清理未全部完成：{}')
API_CASE_POSTERIOR_SQL_CONFIG_INVALID = ErrorDefinition(code=31224, message='用例后置数据库操作配置无效：第{}项必须是对象')

API_AUTH_CONFIG_AUTH_CONFIG_DELETE_NOT_FOUND = ErrorDefinition(code=31000,
                                                               message='API授权配置不存在或已删除，请使用存在的授权配置ID查询')
API_CASE_POSTERIOR_SQL_PROJECT_PRODUCT_SQL_DATABASE_CASE_EXECUTION_FAILED = ErrorDefinition(code=31001,
                                                                                            message='用例后置SQL执行失败（第{}项，key={}，逻辑数据库ID={}，执行环境={}，项目产品ID={}）：{}')
API_DATA_SOURCE_OPERATION_DATABASE_DATA_SOURCE_REQUIRED = ErrorDefinition(code=31002,
                                                                          message='数据库操作必须选择逻辑数据源')
API_DATA_SOURCE_OPERATION_DATABASE_EXECUTION_REQUIRED = ErrorDefinition(code=31003,
                                                                        message='数据库操作缺少当前执行环境上下文')
API_PROJECT_PRODUCT_API_INFO_MODULE_REQUEST_TYPE_DUPLICATED = ErrorDefinition(code=1092,
                                                                              message='接口定义已存在相同的项目产品、模块、端类型、请求方法、协议类型、请求体类型和URL，重复接口ID：{}')
API_PROJECT_PRODUCT_TYPE_VARIABLE_DUPLICATED = ErrorDefinition(code=1106,
                                                               message='已存在项目/产品、环境、类型、Key和Value完全相同的全局变量，重复变量ID：{}')
API_CASE_EXECUTION_REQUIRED = ErrorDefinition(code=1109, message='请选择要批量执行的API用例')
API_TASK_NAME_EXECUTION_INVALID = ErrorDefinition(code=1110, message='请输入本次批量执行的任务名称')
API_TASK_NAME_EXECUTION_TOO_LONG = ErrorDefinition(code=1111, message='批量执行任务名称不能超过128个字符')
API_TEST_ENVIRONMENT_EXECUTION_REQUIRED = ErrorDefinition(code=1115, message='批量执行前请选择有效的测试环境')
API_CASE_STEP_NOT_FOUND = ErrorDefinition(code=1116, message='调试步骤不存在或不属于当前API用例')
API_CASE_STEP_PROJECT_MISMATCH = ErrorDefinition(code=1190, message='执行编排只能选择同一项目下的接口')
API_CACHE_STEP_NOT_FOUND = ErrorDefinition(code=1117, message='未找到当前步骤可用的前置缓存，请先调试上一步')
API_TEST_ENVIRONMENT_USER_INVALID = ErrorDefinition(code=1118,
                                                    message='单步调试上下文已失效或与当前用户、测试环境不一致，请从第一步重新开始调试')
API_HEADER_REQUEST_DELETE_INVALID = ErrorDefinition(code=31004, message='请求头已默认启用，请先关闭后再删除')
API_HEADER_SCENARIO_REQUEST_DELETE_INVALID = ErrorDefinition(code=31005,
                                                             message='请求头正在被API Case或场景使用，请先解除引用后再删除')
API_HEADER_PROJECT_PRODUCT_REQUEST_DELETE_INVALID = ErrorDefinition(code=31006,
                                                                    message='批量删除只能选择同一项目/产品的请求头')
API_PUBLIC_DATA_SOURCE_SQL_DATABASE_VARIABLE_EXECUTION_NOT_ALLOWED = ErrorDefinition(code=31007,
                                                                                     message='SQL全局变量仅允许执行查询语句，不允许增删改数据库数据')
API_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_REQUIRED = ErrorDefinition(code=31008, message='SQL断言必须选择逻辑数据源')
API_SQL_ASSERTION_SQL_DATABASE_ASSERTION_EXECUTION_NOT_ALLOWED = ErrorDefinition(code=31009,
                                                                                 message='SQL断言仅允许执行查询语句，不允许增删改数据库数据')
API_VERSION_CASE_NOT_FOUND = ErrorDefinition(code=1123, message='API用例不存在，Case ID：{}')
API_VERSION_CASE_REVISION_NOT_FOUND = ErrorDefinition(code=1124, message='用例修订不存在或不属于当前Case')
API_VERSION_CASE_VERSION_EXECUTION_INVALID = ErrorDefinition(code=1125,
                                                             message='当前用例没有可执行的已发布版本，请先发布')
API_VERSION_CASE_REVISION_CONFIG_FAILED = ErrorDefinition(code=1126, message='用例修订校验失败，配置可能已被修改')
API_VERSION_CASE_VERSION_EXECUTION_INVALID_CODE_CASE_VERSION_EXECUTION_INVALID = ErrorDefinition(code=1127,
                                                                                                 message='用例发布版本不可执行：{}')
API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID = ErrorDefinition(code=1128,
                                                                     message='用例修订的接口绑定不完整或不一致')
API_VERSION_API_INFO_NOT_FOUND = ErrorDefinition(code=1129, message='API接口不存在，接口 ID：{}')
API_VERSION_API_INFO_REVISION_NOT_FOUND = ErrorDefinition(code=1130, message='接口修订不存在或不属于当前接口')
API_VERSION_API_INFO_REVISION_CONFIG_FAILED = ErrorDefinition(code=1131, message='接口修订校验失败，配置可能已被修改')
API_VERSION_API_INFO_VERSION_INVALID = ErrorDefinition(code=1132, message='当前接口没有已发布版本，请先发布')
API_VERSION_PROJECT_PRODUCT_CASE_TASK_BINDING_INVALID = ErrorDefinition(code=1134,
                                                                        message='定时任务与 API 用例不属于同一项目产品，禁止绑定')
API_VERSION_CASE_REVISION_INVALID = ErrorDefinition(code=1135, message='用例修订不完整，禁止发布：{}')
API_VERSION_CASE_VERSION_UNSUPPORTED = ErrorDefinition(code=1136, message='不支持的用例快照结构版本：{}')
API_VERSION_DEPENDENCY_FREEZE_UNSUPPORTED = ErrorDefinition(code=1137,
                                                            message='用例版本依赖尚未支持完整冻结，禁止发布或执行：{}')
API_VERSION_CASE_SCENARIO_INVALID = ErrorDefinition(code=1138, message='一次批量操作只能修改同一个 API 用例中的场景')
API_VERSION_CASE_STEP_ORDER_INVALID = ErrorDefinition(code=1139, message='步骤排序只能包含同一个 API 用例中的有效步骤')
API_VERSION_API_INFO_VERSION_UNSUPPORTED = ErrorDefinition(code=1140, message='不支持的接口快照结构版本：{}')
API_VERSION_API_INFO_REVISION_CONFIG_EXECUTION_GENERATE_INVALID = ErrorDefinition(code=1148,
                                                                                  message='接口当前编辑态尚未执行成功，或成功执行后配置又发生了修改；请重新调试通过后再生成修订')
API_VERSION_API_INFO_VERSION_DELETE_INVALID = ErrorDefinition(code=1151,
                                                              message='历史版本存在已删除的接口依赖，请确认恢复依赖后再迁出：{}')
API_VERSION_API_INFO_VERSION_REQUIRED = ErrorDefinition(code=1152, message='历史版本缺少完整接口快照，无法恢复迁出：{}')
API_VERSION_API_INFO_STEP_DELETE_NOT_ALLOWED = ErrorDefinition(code=1153,
                                                               message='接口仍被编辑态步骤或旧版历史快照引用，不能删除：{}')
API_VERSION_API_INFO_REVISION_DELETE_NOT_ALLOWED = ErrorDefinition(code=1154,
                                                                   message='接口修订仍被旧版历史快照引用，不能删除：{}')
API_VERSION_SELECTED_CASES_UNPUBLISHED = ErrorDefinition(code=1155,
                                                         message='选择已发布版本执行时，以下API用例尚未发布：{}')
API_VERSION_VERSION_EXECUTION_INVALID = ErrorDefinition(code=1156,
                                                        message='执行版本只能是 editing、prepublished 或 published，当前值：{}')
API_VERSION_SELECTED_CASES_NOT_PREPUBLISHED = ErrorDefinition(code=1163,
    message='选择预发布版本执行时，以下API用例没有待审核的预发布修订：{}')
API_VERSION_CASE_EXECUTION_INVALID = ErrorDefinition(code=1157,
                                                     message='所选用例来自多个项目：{}。一次批量执行只能选择同一项目下的用例')
API_VERSION_EXECUTION_UNSUPPORTED = ErrorDefinition(code=1158,
                                                    message='批量执行不支持指定 case_release_id，请使用 execution_version 选择 editing、prepublished 或 published')
API_VERSION_JSON_SCENARIO_RESPONSE_ASSERTION_GENERATE_INVALID = ErrorDefinition(code=1159,
                                                                                message='该场景没有最近一次响应 JSON，无法生成 Schema 断言')
API_VERSION_CASE_MODULE_TASK_BINDING_INVALID = ErrorDefinition(code=1160,
                                                               message='定时任务已限定模块，禁止绑定其他模块的 API 用例')
API_VERSION_CASE_VERSION_INVALID = ErrorDefinition(code=1161, message='当前用例没有可取消的已发布版本')
API_VERSION_VERSION_INVALID = ErrorDefinition(code=1162, message='所选版本已不是当前发布版本，请刷新后重试')
API_CASE_PREPUBLICATION_ALREADY_EXISTS = ErrorDefinition(code=31205,
                                                         message='当前用例已有预发布修订，请等待产品负责人审批发布，或退回旧候选后再提交')
API_CASE_PREPUBLICATION_NOT_FOUND = ErrorDefinition(code=31206, message='当前用例没有待处理的预发布修订')
API_CASE_PREPUBLICATION_OWNER_REQUIRED = ErrorDefinition(code=31207,
                                                         message='当前项目产品尚未配置负责人，无法提交预发布')
API_CASE_PREPUBLICATION_APPROVAL_FORBIDDEN = ErrorDefinition(code=31208,
                                                             message='只有当前用例所属项目产品的负责人可以审批并正式发布预发布修订')
API_CASE_PREPUBLICATION_REVISION_DELETE_NOT_ALLOWED = ErrorDefinition(code=31209,
                                                                      message='该修订正在预发布，需先退回后才能删除')
API_CASE_PREPUBLICATION_PRODUCT_CHANGE_NOT_ALLOWED = ErrorDefinition(code=31210,
                                                                     message='当前用例存在预发布修订，需先由产品负责人处理后才能修改项目产品')
API_CASE_PREPUBLICATION_CURRENT_REVISION_NOT_ALLOWED = ErrorDefinition(code=31211,
                                                                       message='该修订已经是当前正式版本，无需重复提交预发布')
API_CASE_PREPUBLICATION_REVISION_FROZEN = ErrorDefinition(code=31212,
                                                          message='当前用例已有待审核的预发布修订，暂不能生成新修订。可等待产品负责人审批发布；如需提交当前编辑内容，具备用例修改权限的用户可在用例版本页面或通过 MCP 退回旧候选，再复核并生成新修订、提交预发布。当前编辑态的执行结果不会更新旧候选。')
API_CASE_REVISION_NOT_ACTIVE_CANDIDATE = ErrorDefinition(code=31213, message='只有当前未发布候选修订可以提交预发布')
API_CASE_PUBLICATION_REQUIRES_PASSED = ErrorDefinition(code=31214,
                                                       message='用例尚未处于执行通过状态，请执行通过后再提交预发布或正式发布')
API_EXECUTION_UNKNOWN_ERROR = ErrorDefinition(code=1002, message='请求发生未知异常，请检查接口数据后再联系管理员查看')
API_JSON_SERIALIZATION_ERROR = ErrorDefinition(code=1003,
                                               message='【{}】数据必须是JSON格式，请检查数据是否可以序列化为JSON')
API_POST_JSONPATH_CONFIG_EMPTY = ErrorDefinition(code=1006,
                                                 message='后置jsonpath提取时，缓存的key或jsonpath表达式不允许为空')
API_ASSERTION_FAILED = ErrorDefinition(code=1007, message='通用断言失败')
API_CASE_EMPTY = ErrorDefinition(code=1008, message='用例是空，请先配置用例')
API_CUSTOM_FUNCTION_PARSE_FAILED = ErrorDefinition(code=1014, message='自定义函数解析失败：{}')
API_POST_REGEX_RESPONSE_EMPTY = ErrorDefinition(code=1015,
                                                message='后置正则提取失败，目标缓存Key：【{}】，正则表达式：【{}】：响应文本为空')
API_DOWNLOAD_FAILED = ErrorDefinition(code=1016, message='下载文件异常，请联系管理员，{}')
API_POST_REGEX_NO_MATCH = ErrorDefinition(code=1017,
                                          message='后置正则提取未匹配到内容，目标缓存Key：【{}】，正则表达式：【{}】，响应文本长度：【{}】')
API_GLOBAL_SQL_NO_RESULT = ErrorDefinition(code=1033, message='全局变量sql在数据库中查询不到结果，sql：{}')
API_CASE_PRE_SQL_EMPTY = ErrorDefinition(code=1035, message='用例场景前置sql的sql不允许为空')
API_HEADER_KEY_JSON_INVALID = ErrorDefinition(code=1040, message='请求头的key不允许传JSON格式')
API_TEST_OBJECT_CONFIG_NOT_FOUND = ErrorDefinition(code=1046,
                                                   message='未找到当前用例对应的测试对象配置，请前往“测试配置 > 测试对象”检查项目/产品、测试环境和自动化类型。')
API_CODE_VARIABLE_FUNCTION_INVALID = ErrorDefinition(code=1068, message='代码变量【{}】自定义函数使用方法不正确：{}')
API_POST_FUNCTION_FAILED = ErrorDefinition(code=1069, message='接口后置自定义函数执行失败：{}')
API_CASE_PRE_FUNCTION_FAILED = ErrorDefinition(code=1070, message='用例场景前置自定义函数执行失败：{}')
API_CASE_POST_FUNCTION_FAILED = ErrorDefinition(code=1071, message='用例场景后置自定义函数执行失败：{}')
API_AUTH_CODE_INVALID = ErrorDefinition(code=1072, message='授权自定义代码写法不正确：{}')
API_PROTOCOL_UNSUPPORTED = ErrorDefinition(code=1078,
                                           message='当前协议类型【{}】暂不支持执行，一期仅支持标准HTTP、SSE和MCP')
API_REQUEST_BODY_INVALID = ErrorDefinition(code=1079, message='请求体类型【{}】配置错误：{}')
API_UPLOAD_FILE_NOT_FOUND = ErrorDefinition(code=1080, message='上传文件【{}】不存在')
API_UPLOAD_FILE_UNBOUND = ErrorDefinition(code=1081, message='上传文件【{}】没有绑定测试文件，请先在测试文件中上传文件')
API_PROXY_CONNECTION_FAILED = ErrorDefinition(code=1083, message='代理连接失败，请检查服务器代理配置或关闭代理：{}')
API_TARGET_CONNECTION_FAILED = ErrorDefinition(code=1084,
                                               message='目标服务器连接失败，请检查域名、网络、服务状态或端口：{}')
API_TARGET_NO_RESPONSE = ErrorDefinition(code=1085, message='目标服务器没有响应或连接被中断：{}')
API_REQUEST_TIMEOUT = ErrorDefinition(code=1086, message='接口请求超时，请检查目标服务响应时间或调整API超时时间：{}')
API_TLS_FAILED = ErrorDefinition(code=1087, message='SSL证书或TLS握手失败，请检查HTTPS证书配置：{}')
API_URL_INVALID = ErrorDefinition(code=1088, message='请求地址格式不正确，请检查URL和测试环境配置：{}')
API_TOO_MANY_REDIRECTS = ErrorDefinition(code=1089, message='接口重定向次数过多，请检查目标接口重定向配置：{}')
API_RESPONSE_DECODE_FAILED = ErrorDefinition(code=1090, message='响应内容解码失败，请检查响应编码或压缩格式：{}')
API_POST_REGEX_INVALID = ErrorDefinition(code=1091, message='后置正则表达式错误，目标缓存Key：【{}】，表达式：【{}】，错误：{}')
API_POSITIVE_INTEGER_REQUIRED = ErrorDefinition(code=1094, message='{}配置错误，请填写大于0的整数，当前值：{}')
API_DOWNLOAD_SAVE_FAILED = ErrorDefinition(code=1095, message='下载响应文件保存失败，请检查下载目录权限或文件名：{}')
API_UPLOAD_FILE_READ_FAILED = ErrorDefinition(code=1105,
                                              message='上传文件【{}】读取失败，请到测试配置-测试文件中重新上传文件；错误：{}')
API_CONCURRENCY_LIMIT_EXCEEDED = ErrorDefinition(code=1108, message='API执行并发不能超过当前平台API最大执行容量{}')
API_CASE_STEP_DEBUG_BUSY = ErrorDefinition(code=1119, message='当前API用例正在进行单步调试，请稍后重试')
API_PARAMETERIZED_STEP_DEBUG_UNSUPPORTED = ErrorDefinition(code=1120,
                                                           message='参数化API用例暂不支持单步调试，请使用完整执行')
API_STEP_DEBUG_ENV_REQUIRED = ErrorDefinition(code=1121, message='单步调试前请选择有效的测试环境')
GRPC_API_API_INFO_BINDING_REQUIRED = ErrorDefinition(code=1201,
                                                     message='gRPC接口缺少方法绑定，请先把gRPC Method导入为ApiInfo')
GRPC_API_EXECUTOR_API_INFO_EXECUTION_UNSUPPORTED = ErrorDefinition(code=1202,
                                                                   message='gRPC接口方法【{}】是流式调用，当前自动化执行仅支持Unary RPC。Server Streaming、Client Streaming、Bidirectional Streaming暂不支持，请改用Unary方法或等待流式执行器扩展')
GRPC_API_JSON_PARAMETER_TYPE_INVALID = ErrorDefinition(code=1203, message='gRPC调用参数必须是JSON对象，当前类型：{}')
GRPC_API_INVALID = ErrorDefinition(code=1204, message='gRPC依赖未安装，请安装grpcio和protobuf后重试')
GRPC_API_FILE_INVALID = ErrorDefinition(code=1205, message='gRPC描述文件不可用：{}')
GRPC_API_API_INFO_REQUEST_RESPONSE_BINDING_NOT_FOUND = ErrorDefinition(code=1206,
                                                                       message='gRPC请求Message【{}】或响应Message【{}】不存在，请检查proto/descriptor是否与接口绑定一致')
GRPC_API_REQUEST_FAILED = ErrorDefinition(code=1207, message='gRPC请求Message构造失败：{}')
GRPC_API_FAILED = ErrorDefinition(code=1208, message='gRPC调用失败：{}')
GRPC_API_STATUS_INVALID = ErrorDefinition(code=1209,
                                          message='gRPC返回状态不符合预期，方法【{}】，实际状态【{}】，预期状态【{}】，详情：{}')
MCP_API_API_INFO_BINDING_INVALID = ErrorDefinition(code=31200,
                                                   message='MCP接口未绑定Tool，请先在MCP工具中导入或重新绑定')
MCP_API_SERVICE_INVALID = ErrorDefinition(code=1141, message='MCP Tool【{}】不可用或已下线，请重新同步MCP服务')
MCP_API_API_INFO_VERSION_RECORD_EXECUTION_BINDING_REQUIRED = ErrorDefinition(code=1142,
                                                                             message='MCP接口版本缺少Tool绑定快照，请重新记录接口版本后再执行')
MCP_API_FAILED = ErrorDefinition(code=1143, message='MCP Tool调用失败：{}')
MCP_API_JSON_PARAMETER_INVALID = ErrorDefinition(code=1144, message='MCP Tool参数必须是JSON对象，当前值：{}')
MCP_API_TYPE_INVALID = ErrorDefinition(code=1145, message='MCP Tool仅支持tool类型导入API自动化，当前类型：{}')
MCP_API_API_INFO_TYPE_NOT_ALLOWED = ErrorDefinition(code=1146,
                                                    message='MCP Tool【{}】不是API自动化或通用类型，不能导入API自动化')
MCP_API_PROJECT_PRODUCT_MODULE_CONFIG_REQUIRED = ErrorDefinition(code=1147,
                                                                 message='MCP Tool【{}】缺少项目/产品或模块，请先配置归属后再导入')
MCP_API_PARAMETER_INVALID = ErrorDefinition(code=1150, message='MCP Tool参数不符合 inputSchema：{}')
MCP_API_INVALID = ErrorDefinition(code=31201, message='MCP Tool返回业务错误，Tool：【{}】，错误内容：{}')
MCP_API_CONFIG_INVALID = ErrorDefinition(code=31202,
                                         message='MCP配置错误：expected_result 只能是 success、error 或 any，当前值：{}')
MCP_API_SCENARIO_INVALID = ErrorDefinition(code=31203,
                                           message='MCP Tool预期返回业务错误，但实际调用成功；如这是正常场景，请把 expected_result 改为 success 或 any')
MOCK_API_CONFIG_INVALID = ErrorDefinition(code=1401, message='Mock配置不合法：{}')
MOCK_API_CREATE_NOT_ALLOWED = ErrorDefinition(code=1403, message='Mock URL标识创建后不允许修改')
MOCK_API_USER_CONFIG_UPDATE_CONFLICT = ErrorDefinition(code=1404, message='Mock配置已被其他用户更新，请刷新后重试')
MOCK_API_API_INFO_NOT_FOUND = ErrorDefinition(code=1405, message='Mock接口不存在')
QUALITY_COVERAGE_MODULE_NOT_FOUND = ErrorDefinition(code=31010, message='模块覆盖扫描不存在')
QUALITY_COVERAGE_MODULE_UPLOAD_NOT_ALLOWED = ErrorDefinition(
    code=31011,
    message='模块覆盖扫描已结束，历史快照不可修改；如需修正ApiInfo绑定，请使用接口绑定修正入口生成增量快照',
)
QUALITY_COVERAGE_PROJECT_PRODUCT_MODULE_INVALID = ErrorDefinition(code=31012, message='模块不属于指定项目产品')
QUALITY_COVERAGE_UPLOAD_INVALID = ErrorDefinition(code=31013, message='相同扫描项已上传不同内容，请更换幂等键后重试')
QUALITY_COVERAGE_EXECUTION_INVALID = ErrorDefinition(code=31014,
                                                     message='增量扫描的基线提交与平台当前提交不一致，请重新执行完整扫描')
QUALITY_COVERAGE_PROJECT_PRODUCT_BINDING_NOT_FOUND = ErrorDefinition(code=31015,
                                                                     message='绑定的API Case不存在或不属于当前项目产品')
QUALITY_COVERAGE_INVALID = ErrorDefinition(code=31016, message='调用流程结构不正确：{}')
QUALITY_COVERAGE_TASK_STATUS_NOT_ALLOWED = ErrorDefinition(code=31017, message='扫描任务状态不能从“{}”变更为“{}”')
QUALITY_COVERAGE_FIELD_REQUIRED = ErrorDefinition(code=31018, message='缺少必填字段：{}')
QUALITY_COVERAGE_FIELD_INVALID = ErrorDefinition(code=31019, message='字段“{}”的值“{}”不在允许范围内')
QUALITY_COVERAGE_MODULE_NOT_ALLOWED = ErrorDefinition(code=31020,
                                                      message='该扫描已落后于当前已完成扫描，不能覆盖较新的模块 Case')
QUALITY_COVERAGE_UPLOAD_INVALID_CODE_UPLOAD_INVALID = ErrorDefinition(code=31021,
                                                                      message='单批上传数量必须在1到{}条之间')
QUALITY_COVERAGE_INVALID_CODE_INVALID = ErrorDefinition(code=31022,
                                                        message='完整扫描范围减少超过50%，请显式确认范围缩减')
QUALITY_COVERAGE_PROJECT_PRODUCT_PERMISSION_INVALID = ErrorDefinition(code=31023, message='没有目标项目产品的数据权限')
QUALITY_COVERAGE_SCAN_UPLOAD_INCOMPLETE = ErrorDefinition(code=31024, message='扫描上传不完整：期望{}{}条，实际接收{}条')
QUALITY_COVERAGE_CONTENT_HASH_MISMATCH = ErrorDefinition(code=31025, message='客户端内容哈希与平台规范化内容不一致')
QUALITY_COVERAGE_MODULE_INVALID = ErrorDefinition(code=31026, message='模块覆盖扫描校验未通过：{}')
QUALITY_COVERAGE_CODE_PARSE_NOT_ALLOWED = ErrorDefinition(code=31027,
                                                          message='代码链路未完整：完整{}个，占位{}个，未解析Gap{}个。占位图或内部未解析边界不能完成扫描')
QUALITY_COVERAGE_API_INFO_INVALID = ErrorDefinition(code=31028,
                                                    message='单接口扫描必须指定有效的目标接口，且预期接口数必须为1')
QUALITY_COVERAGE_API_INFO_UPLOAD_INVALID = ErrorDefinition(code=31029, message='上传接口与单接口扫描目标不一致')
QUALITY_COVERAGE_API_INFO_MODULE_NOT_FOUND = ErrorDefinition(code=31030,
                                                             message='模块覆盖接口不存在或已失效，请使用 list_module_coverage_interfaces 返回的当前接口快照ID查询')
MODULE_COVERAGE_ANALYSIS_BLOCKED = ErrorDefinition(code=31500, message='接口覆盖策略为暂不处理或排除覆盖，请先人工重新纳入后再分析链路或生成场景')
MODULE_COVERAGE_POLICY_REASON_REQUIRED = ErrorDefinition(code=31501, message='暂不处理或排除覆盖时必须填写处理原因')
MODULE_COVERAGE_POLICY_INPUT_INVALID = ErrorDefinition(code=31502, message='接口覆盖策略参数无效：{}')
WEBSOCKET_API_TEST_ENVIRONMENT_PATH_FAILED = ErrorDefinition(code=1301,
                                                             message='WebSocket连接失败，请检查测试环境地址、路径、网络和鉴权信息：{}')
WEBSOCKET_API_CONFIG_INVALID = ErrorDefinition(code=1302, message='WebSocket消息脚本配置错误：{}')
WEBSOCKET_API_TIMEOUT = ErrorDefinition(code=1303, message='等待WebSocket消息超时，未在 {} 秒内收到满足条件的消息')
WEBSOCKET_API_SERVICE_INVALID = ErrorDefinition(code=1304, message='WebSocket连接被服务端关闭，关闭码：{}，原因：{}')
WEBSOCKET_API_JSONPATH_JSON_ASSERTION_EXECUTION_INVALID = ErrorDefinition(code=1305,
                                                                          message='收到的WebSocket消息不是合法JSON，无法执行JSONPath断言：{}')
WEBSOCKET_API_EXECUTION_FAILED = ErrorDefinition(code=1306, message='WebSocket执行失败：{}')
AUTO_API_API_CASE_DATA_FACTORY_STATUS_TEMPLATE_REQUIRED = ErrorDefinition(code=31031, message='状态模板不能为空')
AUTO_API_API_CASE_DETAILED_PARAMETER_TIME_INVALID = ErrorDefinition(code=31032,
                                                                    message='强制等待时间必须是0~32767之间的整数，当前值：【{}】')
AUTO_API_API_CASE_DETAILED_PARAMETER_TIME_OUT_OF_RANGE = ErrorDefinition(code=31033,
                                                                         message='强制等待时间【{}】超出允许范围0~32767秒')
AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_REQUIRED = ErrorDefinition(code=31034,
                                                                          message='通用断言第{}项必须选择断言方法')
AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_NOT_FOUND = ErrorDefinition(code=31035,
                                                                           message='通用断言第{}项的断言方法【{}】不存在')
AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_CONFIG_INVALID = ErrorDefinition(code=31036,
                                                                                message='通用断言第{}项必须配置实际值')
AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_NOT_FOUND = ErrorDefinition(code=31037,
                                                                               message='SQL断言第{}项的断言方法【{}】不存在')
AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_REQUIRED = ErrorDefinition(code=31038,
                                                                              message='SQL断言第{}项的SQL语句不能为空')
AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_REQUIRED_CODE_SQL_ASSERTION_REQUIRED = ErrorDefinition(code=31039,
                                                                                                          message='SQL断言第{}项的预期值不能为空')
AUTO_API_API_CASE_DETAILED_PARAMETER_RESPONSE_ASSERTION_TYPE_NOT_FOUND = ErrorDefinition(code=31040,
                                                                                         message='响应提取断言第{}项的断言类型【{}】不存在，只支持jsonpath、regex或cache')
AUTO_API_API_CASE_DETAILED_PARAMETER_RESPONSE_ASSERTION_REQUIRED = ErrorDefinition(code=31041,
                                                                                   message='响应提取断言第{}项的{}不能为空')
AUTO_API_API_CASE_DETAILED_PARAMETER_CACHE_RESPONSE_ASSERTION_EXPRESSION_INVALID = ErrorDefinition(code=31042,
                                                                                                   message='响应提取断言第{}项的缓存表达式必须使用完整的${{{{key}}}}格式')
AUTO_API_API_CASE_DETAILED_PARAMETER_RESPONSE_ASSERTION_REQUIRED_CODE_RESPONSE_ASSERTION_REQUIRED = ErrorDefinition(
    code=31043, message='响应提取断言第{}项必须选择断言方法')
AUTO_API_API_CASE_DETAILED_PARAMETER_RESPONSE_ASSERTION_NOT_FOUND = ErrorDefinition(code=31044,
                                                                                    message='响应提取断言第{}项的断言方法【{}】不存在')
AUTO_API_API_CASE_DETAILED_PARAMETER_CACHE_REQUIRED = ErrorDefinition(code=31045, message='{}第{}项的缓存Key不能为空')
AUTO_API_API_CASE_DETAILED_PARAMETER_REQUIRED = ErrorDefinition(code=31046, message='{}第{}项的{}不能为空')
AUTO_API_API_CASE_DETAILED_PARAMETER_REGEX_RESPONSE_ASSERTION_EXPRESSION_INVALID = ErrorDefinition(code=31047,
                                                                                                   message='响应提取断言第{}项的正则表达式不合法：{}')
AUTO_API_API_CASE_DETAILED_PARAMETER_SCENARIO_ASSERTION_PARAMETER_REQUIRED = ErrorDefinition(code=31048,
                                                                                             message='断言验证失败：场景参数ID不能为空')
AUTO_API_API_CASE_DETAILED_PARAMETER_SCENARIO_ASSERTION_PARAMETER_EXECUTION_FAILED = ErrorDefinition(code=31049,
                                                                                                     message='断言验证失败：场景参数ID和执行环境必须是整数')
AUTO_API_API_CASE_VERSION_PARTS_EDITING_REVISION_VERSION_DELETE_NOT_ALLOWED = ErrorDefinition(code=31050,
                                                                                              message='该修订已发布为版本，不能删除')
AUTO_API_API_CASE_VERSION_PARTS_EDITING_REVISION_DELETE_NOT_ALLOWED = ErrorDefinition(code=31051,
                                                                                      message='该修订存在后续子修订，不能删除')
AUTO_API_API_CASE_VERSION_PARTS_EDITING_REVISION_TASK_DELETE_BINDING_NOT_ALLOWED = ErrorDefinition(code=31052,
                                                                                                   message='该修订已被定时任务绑定，不能删除')
AUTO_API_API_INFO_API_INFO_SCENARIO_ASSERTION_GENERATE_INVALID = ErrorDefinition(code=31053,
                                                                                 message='接口定义级结构化断言已停用，请在 API case 场景的结构化断言中生成或维护')
AUTO_API_API_INFO_VERSION_REVISION_VERSION_DELETE_NOT_ALLOWED = ErrorDefinition(code=31054,
                                                                                message='该修订已发布为版本，不能删除')
AUTO_API_API_INFO_VERSION_STEP_REVISION_DELETE_NOT_ALLOWED = ErrorDefinition(code=31055,
                                                                             message='该修订已被API Case步骤固定引用，不能删除')
AUTO_API_API_INFO_VERSION_REVISION_DELETE_NOT_ALLOWED = ErrorDefinition(code=31056,
                                                                        message='该修订存在后续子修订，不能删除')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_AUTH_FAILED = ErrorDefinition(code=31057,
                                                                             message='API授权Token刷新失败：{}')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_AUTH_UNSUPPORTED = ErrorDefinition(code=31058,
                                                                                  message='不支持的授权方式：{}')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_AUTH_CACHE_INVALID = ErrorDefinition(code=31059,
                                                                                    message='API授权缓存不可用，请手动刷新：{}')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_AUTH_CODE_INVALID = ErrorDefinition(code=31060,
                                                                                   message='自定义授权代码必须定义 auth(context) 函数')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_AUTH_CODE_INVALID_CODE_AUTH_CODE_INVALID = ErrorDefinition(code=31061,
                                                                                                          message='自定义授权代码 auth(context) 必须返回 dict')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_AUTH_API_INFO_CODE_INVALID = ErrorDefinition(code=31062,
                                                                                            message='授权数据为空，请检查登录接口后置提取或自定义代码返回值')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_AUTH_API_INFO_CODE_INVALID_CODE_AUTH_API_INFO_CODE_INVALID = ErrorDefinition(
    code=31063, message='授权数据为空，请检查登录接口后置提取或自定义代码返回值')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_INVALID = ErrorDefinition(code=31064, message='Token有效期必须大于0')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_TIME_NOT_ALLOWED = ErrorDefinition(code=31065,
                                                                                  message='提前刷新时间不能小于0')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_TIME_INVALID = ErrorDefinition(code=31066,
                                                                              message='提前刷新时间必须小于Token有效期')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_AUTH_API_INFO_REQUIRED = ErrorDefinition(code=31067,
                                                                                        message='接口登录授权必须选择登录接口')
AUTO_API_CUSTOM_AUTH_CODE_REQUIRED = ErrorDefinition(code=31068, message='自定义代码授权必须填写代码')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_AUTH_TIMEOUT = ErrorDefinition(code=31069,
                                                                              message='API授权Token刷新等待超时：{}')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_NOTICE_REQUIRED = ErrorDefinition(code=31070,
                                                                                 message='到期通知必须选择通知组')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_TIME_NOTICE_NOT_ALLOWED = ErrorDefinition(code=31071,
                                                                                         message='提前通知时间不能小于0')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_TIME_NOTICE_INVALID = ErrorDefinition(code=31072,
                                                                                     message='提前通知时间必须小于Token有效期')
AUTO_API_BASE_API_BASE_TEST_SETUP_AUTH_MANAGER_AUTH_FAILED_CODE_AUTH_FAILED = ErrorDefinition(code=31073,
                                                                                              message='API授权Token刷新失败：{}')
AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_CONFIG_REQUIRED = ErrorDefinition(code=31074,
                                                                          message='{}配置错误（第{}项）：缓存Key不能为空')
AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_REGEX_CONFIG_EXPRESSION_REQUIRED = ErrorDefinition(code=31075,
                                                                                           message='{}配置错误（第{}项，缓存Key：【{}】）：正则表达式不能为空')
AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_REGEX_RESPONSE_EXECUTION_FAILED = ErrorDefinition(code=31076,
                                                                                          message='{}失败（第{}项，缓存Key：【{}】）：当前响应没有文本内容，无法执行正则提取')
AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_RESPONSE_EXPRESSION_NO_MATCH = ErrorDefinition(code=31077,
                                                                                       message='{}未匹配到内容（第{}项，缓存Key：【{}】），表达式：【{}】，响应文本长度：【{}】')
AUTO_API_BASE_API_BASE_TEST_SETUP_CONFIG_PARSE_FAILED = ErrorDefinition(code=31078, message='{}配置解析失败（第{}项）：{}')
AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_REGEX_EXPRESSION_FAILED = ErrorDefinition(code=31079,
                                                                                  message='{}失败（第{}项，缓存Key：【{}】）：正则表达式错误，表达式：【{}】，错误：{}')
AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_WRITE_FAILED = ErrorDefinition(code=31080,
                                                                       message='{}缓存写入失败（第{}项，缓存Key：【{}】）：{}')
AUTO_API_BASE_API_BASE_TEST_SETUP_PUBLIC_BASE_CODE_VARIABLE_INVALID = ErrorDefinition(code=31081,
                                                                                      message='代码变量【{}】必须定义 variable(context) 函数')
AUTO_API_BASE_API_BASE_TEST_SETUP_PUBLIC_BASE_CODE_VARIABLE_INVALID_CODE_CODE_VARIABLE_INVALID = ErrorDefinition(
    code=31082, message='代码变量【{}】的 variable(context) 必须返回 dict')
AUTO_API_CODE_VARIABLE_RESULT_EMPTY = ErrorDefinition(code=31083, message='代码变量【{}】返回数据为空')
AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_ASSERTION_PARAMETER_NOT_FOUND = ErrorDefinition(code=31084,
                                                                                              message='断言验证失败：场景参数ID【{}】不存在')
AUTO_API_BASE_ASSERTION_VERIFICATION_ASSERTION_FAILED = ErrorDefinition(code=31085,
                                                                        message='断言验证失败：assertions必须是对象')
AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_ASSERTION_RESULT_EXECUTION_FAILED = ErrorDefinition(code=31086,
                                                                                                  message='断言验证失败：最近一次执行结果格式不正确，请重新执行当前场景')
AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_RESPONSE_ASSERTION_RESULT_EXECUTION_FAILED = ErrorDefinition(code=31087,
                                                                                                           message='断言验证失败：当前场景没有可用的响应结果，请先执行当前场景')
AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_ASSERTION_CONFIG_REQUIRED = ErrorDefinition(code=31088,
                                                                                          message='断言验证失败：当前场景未配置任何断言')
AUTO_API_BASE_ASSERTION_VERIFICATION_CACHE_SCENARIO_ASSERTION_EXECUTION_FAILED = ErrorDefinition(code=31089,
                                                                                                 message='断言验证失败：最近一次执行缓存格式不正确，请重新执行当前场景')
AUTO_API_BASE_ASSERTION_VERIFICATION_CACHE_SCENARIO_ASSERTION_EXECUTION_FAILED_CODE_CACHE_SCENARIO_ASSERTION_EXECUTION_FAILED = ErrorDefinition(
    code=31090, message='断言验证失败：最近一次数据工厂缓存格式不正确，请重新执行当前场景')
AUTO_API_BASE_ASSERTION_VERIFICATION_JSON_ASSERTION_FAILED = ErrorDefinition(code=31091,
                                                                             message='断言验证失败：ass_json_all必须是JSON对象或数组')
AUTO_API_BASE_ASSERTION_VERIFICATION_JSON_ASSERTION_FAILED_CODE_JSON_ASSERTION_FAILED = ErrorDefinition(code=31092,
                                                                                                        message='断言验证失败：ass_schema必须是JSON对象')
AUTO_API_BASE_ASSERTION_VERIFICATION_ASSERTION_FAILED_CODE_ASSERTION_FAILED = ErrorDefinition(code=31093,
                                                                                              message='断言验证失败：ass_text_all必须是字符串')
AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_RESPONSE_ASSERTION_EXECUTION_FAILED = ErrorDefinition(code=31094,
                                                                                                    message='断言验证失败：最近一次响应数据不完整，请重新执行当前场景；{}')
AUTO_API_ASSERTION_VALUE_ARRAY_REQUIRED = ErrorDefinition(code=31095, message='断言验证失败：{}必须是数组')
AUTO_API_BASE_CASE_DATA_FACTORY_TEST_ENVIRONMENT_EXECUTION_INVALID = ErrorDefinition(code=31096,
                                                                                     message='数据工厂执行前请先初始化测试环境')
AUTO_API_BASE_CASE_DATA_FACTORY_TEST_ENVIRONMENT_EXECUTION_INVALID_CODE_TEST_ENVIRONMENT_EXECUTION_INVALID = ErrorDefinition(
    code=31097, message='数据工厂执行前请先初始化测试环境')
AUTO_API_BASE_CASE_PARAMETER_TIME_CONFIG_INVALID = ErrorDefinition(code=31098,
                                                                   message='强制等待配置错误：等待时间【{}】不是有效秒数，请填写0~32767的整数')
AUTO_API_BASE_CASE_PARAMETER_TIME_CONFIG_OUT_OF_RANGE = ErrorDefinition(code=31099,
                                                                        message='强制等待配置错误：等待时间【{}】超出允许范围0~32767秒')
AUTO_API_BASE_CASE_PARAMETER_CACHE_ASSERTION_CONFIG_EXPRESSION_INVALID = ErrorDefinition(code=31100,
                                                                                         message='缓存值断言配置错误（第{}项）：缓存表达式必须使用完整的${{{{key}}}}格式')
AUTO_API_BASE_CASE_PARAMETER_RESPONSE_ASSERTION_TYPE_CONFIG_NOT_FOUND = ErrorDefinition(code=31101,
                                                                                        message='响应提取断言配置错误（第{}项）：断言类型【{}】不存在，只支持jsonpath、regex或cache')
AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_REQUIRED = ErrorDefinition(code=31102,
                                                                         message='{}配置错误（第{}项）：请选择断言方法')
AUTO_API_BASE_CASE_PARAMETER_CONFIG_REQUIRED = ErrorDefinition(code=31103, message='{}配置错误（第{}项）：{}不能为空')
AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_REQUIRED_CODE_ASSERTION_CONFIG_REQUIRED = ErrorDefinition(code=31104,
                                                                                                        message='通用断言配置错误（第{}项）：请选择断言方法')
AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_INVALID = ErrorDefinition(code=31105,
                                                                        message='通用断言配置错误（第{}项）：请配置实际值')
AUTO_API_BASE_CASE_PARAMETER_ASSERTION_RESULT_FAILED = ErrorDefinition(code=31106,
                                                                       message='{}组【{}】失败：共{}条，{}条通过，{}条失败；详情见断言结果')
AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_NOT_FOUND = ErrorDefinition(code=31107,
                                                                          message='{}配置错误（第{}项）：断言方法【{}】不存在')
AUTO_API_BASE_CASE_PARAMETER_JSON_ASSERTION_CONFIG_PARSE_FAILED = ErrorDefinition(code=31108,
                                                                                  message='JSON一致断言配置解析失败：{}')
AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_PARSE_FAILED = ErrorDefinition(code=31109,
                                                                             message='文本一致断言配置解析失败：{}')
AUTO_API_BASE_CASE_PARAMETER_TIME_CONFIG_INVALID_CODE_TIME_CONFIG_INVALID = ErrorDefinition(code=31110,
                                                                                            message='强制等待配置错误：等待时间【{}】不是有效秒数，请填写0~32767的整数')
AUTO_API_BASE_CASE_PARAMETER_PLAN_EXECUTION_FAILED = ErrorDefinition(code=31111,
                                                                     message='强制等待执行失败：计划等待【{}】秒，系统返回：{}')
AUTO_API_BASE_CASE_PARAMETER_SQL_DATABASE_CONFIG_REQUIRED = ErrorDefinition(code=31112,
                                                                            message='后置SQL配置错误（第{}项）：请选择逻辑数据库')
AUTO_API_BASE_CASE_PARAMETER_SQL_CONFIG_REQUIRED = ErrorDefinition(code=31113,
                                                                   message='后置SQL配置错误（第{}项）：SQL语句不能为空')
AUTO_API_BASE_CASE_PARAMETER_JSON_RESPONSE_FAILED = ErrorDefinition(code=31114, message='响应JSON提取失败：{}')
AUTO_API_BASE_CASE_PARAMETER_CACHE_JSON_RESPONSE_CONFIG_REQUIRED = ErrorDefinition(code=31115,
                                                                                   message='响应JSON提取配置错误（第{}项）：缓存Key不能为空')
AUTO_API_BASE_CASE_PARAMETER_CACHE_JSONPATH_JSON_RESPONSE_CONFIG_REQUIRED = ErrorDefinition(code=31116,
                                                                                            message='响应JSON提取配置错误（第{}项，缓存Key：【{}】）：JSONPath不能为空')
AUTO_API_BASE_CASE_PARAMETER_REGEX_RESPONSE_ASSERTION_CONFIG_EXPRESSION_INVALID = ErrorDefinition(code=31117,
                                                                                                  message='响应提取断言配置错误（第{}项）：正则表达式【{}】不合法，错误：{}')
AUTO_API_BASE_CASE_PARAMETER_PARSE_FAILED = ErrorDefinition(code=31118,
                                                            message='{}预期值解析失败（第{}项，原始预期值：【{}】）：{}')
AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_PARSE_FAILED_CODE_ASSERTION_CONFIG_PARSE_FAILED = ErrorDefinition(
    code=31119, message='通用断言配置解析失败（第{}项）：{}')
AUTO_API_BASE_CASE_PARAMETER_SQL_FAILED = ErrorDefinition(code=31120, message='后置SQL处理失败（第{}项）：{}')
AUTO_API_BASE_CASE_PARAMETER_SQL_DATABASE_FAILED = ErrorDefinition(code=31121,
                                                                   message='后置SQL处理失败（第{}项，数据库ID：{}）：{}；SQL：【{}】')
AUTO_API_BASE_CASE_PARAMETER_SQL_DATABASE_FAILED_CODE_SQL_DATABASE_FAILED = ErrorDefinition(code=31122,
                                                                                            message='后置SQL处理失败（第{}项，数据库ID：{}）：{}；SQL：【{}】')
AUTO_API_BASE_CASE_PARAMETER_CACHE_DATABASE_RESULT_WRITE_FAILED = ErrorDefinition(code=31123,
                                                                                  message='后置数据库操作失败（第{}项，缓存Key：【{}】）：结果为空，无法写入缓存')
AUTO_API_BASE_CASE_PARAMETER_JSON_RESPONSE_CONFIG_PARSE_FAILED = ErrorDefinition(code=31124,
                                                                                 message='响应JSON提取配置解析失败（第{}项）：{}')
AUTO_API_BASE_CASE_PARAMETER_CACHE_JSON_RESPONSE_RESULT_EXPRESSION_FAILED = ErrorDefinition(code=31125,
                                                                                            message='响应JSON缓存Key提取失败（第{}项）：表达式【{}】的结果为【{}】，缓存Key必须是非空字符串')
AUTO_API_BASE_CASE_PARAMETER_CACHE_JSON_RESPONSE_WRITE_FAILED = ErrorDefinition(code=31126,
                                                                                message='响应JSON提取缓存写入失败（第{}项，缓存Key：【{}】）：{}')
AUTO_API_BASE_CASE_PARAMETER_EXPRESSION_PARSE_FAILED = ErrorDefinition(code=31127,
                                                                       message='{}取值表达式解析失败（第{}项，原始表达式：【{}】）：{}')
AUTO_API_BASE_CASE_PARAMETER_CACHE_ASSERTION_EXPRESSION_NOT_FOUND = ErrorDefinition(code=31128,
                                                                                    message='缓存值断言取值失败（第{}项，缓存表达式：【{}】，缓存Key：【{}】）：当前运行缓存中不存在该Key或其值为空')
AUTO_API_BASE_CASE_PARAMETER_SQL_ASSERTION_CONFIG_INVALID = ErrorDefinition(code=31129,
                                                                            message='SQL断言配置错误（第{}项）：配置必须是对象')
AUTO_API_BASE_CASE_PARAMETER_JSONPATH_JSON_FAILED = ErrorDefinition(code=31130,
                                                                    message='{}取值失败（第{}项，JSONPath：【{}】）：{}')
AUTO_API_BASE_CASE_PARAMETER_CACHE_ASSERTION_EXPRESSION_FAILED = ErrorDefinition(code=31131,
                                                                                 message='缓存值断言取值失败（第{}项，缓存表达式：【{}】，缓存Key：【{}】）：{}')
AUTO_API_BASE_SQL_ENVIRONMENT_CONFIG_EXECUTION_INVALID = ErrorDefinition(code=31132, message='{}执行环境配置必须是数组')
AUTO_API_BASE_SQL_ENVIRONMENT_EXECUTION_INVALID = ErrorDefinition(code=31133, message='当前执行环境无效：{}')
AUTO_API_BASE_SQL_ENVIRONMENT_CONFIG_EXECUTION_INVALID_CODE_CONFIG_EXECUTION_INVALID = ErrorDefinition(code=31134,
                                                                                                       message='{}执行环境配置包含无效值：{}')
AUTO_API_BASE_SQL_ENVIRONMENT_EXECUTION_INVALID_CODE_EXECUTION_INVALID = ErrorDefinition(code=31135,
                                                                                         message='当前执行环境无效：{}')
AUTO_API_CASE_SCHEMA_INVALID = ErrorDefinition(code=31136, message='{}必须是数组')
AUTO_API_CASE_SCHEMA_DATABASE_TYPE_EXECUTION_UNSUPPORTED = ErrorDefinition(code=31137,
                                                                           message='{}第{}项的数据库类型暂不支持执行：{}')
AUTO_API_CASE_SCHEMA_INVALID_CODE_INVALID = ErrorDefinition(code=31138, message='{}第{}项必须是对象')
AUTO_API_CASE_SCHEMA_EXECUTION_INVALID = ErrorDefinition(code=31139, message='{}第{}项的执行环境必须是数组')
AUTO_API_CASE_SCHEMA_PROJECT_PRODUCT_PARAMETER_INVALID = ErrorDefinition(code=31140, message='{}的项目产品参数不合法')
AUTO_API_CASE_SCHEMA_DATABASE_NOT_FOUND = ErrorDefinition(code=31141, message='{}第{}项选择的逻辑数据库不存在')
AUTO_API_CASE_SCHEMA_PROJECT_PRODUCT_DATABASE_INVALID = ErrorDefinition(code=31142,
                                                                        message='{}第{}项选择的逻辑数据库不属于当前项目产品')
AUTO_API_CASE_SCHEMA_DATABASE_INVALID = ErrorDefinition(code=31143, message='{}第{}项选择的逻辑数据库已停用')
AUTO_API_CASE_SCHEMA_EXECUTION_INVALID_CODE_EXECUTION_INVALID = ErrorDefinition(code=31144,
                                                                                message='{}第{}项包含无效执行环境：{}')
AUTO_API_CASE_SCHEMA_ITEM_INVALID = ErrorDefinition(code=31145, message='{}第{}项格式错误：{}')
AUTO_API_CASE_EXECUTION_CONTENT_STRING_REQUIRED = ErrorDefinition(code=31146,
                                                                  message='{}第{}项的{}执行内容必须是非空字符串')
AUTO_API_CASE_SCHEMA_JSON_EXECUTION_INVALID = ErrorDefinition(code=31147,
                                                              message='{}第{}项的Elasticsearch执行内容必须是JSON对象')
AUTO_API_CORE_CASE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=31148,
                                                                     message='测试用例详情-有关联数据，请先删除绑定的数据后再删除！')
AUTO_API_CORE_TASK_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=31149,
                                                                     message='定时任务详情-有关联数据，请先删除绑定的数据后再删除！')
AUTO_API_DYNAMIC_ERROR = ErrorDefinition(code=31150, message='{}')
AUTO_API_GRPC_DEFINITION_SERVICE_NOT_FOUND = ErrorDefinition(code=31151, message='gRPC服务定义不存在：{}')
AUTO_API_GRPC_DEFINITION_PARSE_INVALID = ErrorDefinition(code=31152, message='gRPC descriptor 解析依赖 protobuf 未安装')
AUTO_API_GRPC_DEFINITION_FILE_SERVICE_UPLOAD_REQUIRED = ErrorDefinition(code=31153,
                                                                        message='gRPC服务定义缺少descriptor文件，请先上传FileDescriptorSet文件')
AUTO_API_GRPC_DEFINITION_SERVICE_NOT_FOUND_CODE_SERVICE_NOT_FOUND = ErrorDefinition(code=31154,
                                                                                    message='descriptor中未找到服务：{}')
AUTO_API_GRPC_DEFINITION_PROJECT_PRODUCT_MODULE_INVALID = ErrorDefinition(code=31155,
                                                                          message='导入gRPC Method前必须确定项目/产品和模块')
AUTO_API_GRPC_DEFINITION_PROJECT_PRODUCT_API_INFO_MODULE_REQUEST_TYPE_DUPLICATED = ErrorDefinition(code=31156,
                                                                                                   message='接口定义已存在相同的项目产品、模块、端类型、请求方法、协议类型、请求体类型和URL，重复接口ID：{}')
AUTO_API_GRPC_DEFINITION_FILE_READ_FAILED = ErrorDefinition(code=31157, message='gRPC descriptor文件读取失败：{}')
AUTO_API_GRPC_DEFINITION_INVALID = ErrorDefinition(code=31158, message='gRPC descriptor不是合法FileDescriptorSet：{}')
AUTO_API_PROTOCOLS_GRPC_JSON_INVALID = ErrorDefinition(code=31159, message='{}不符合JSON Schema：{}')
AUTO_API_PROTOCOLS_GRPC_JSON_INVALID_CODE_JSON_INVALID = ErrorDefinition(code=31160,
                                                                         message='{}的JSON Schema自身不合法：{}')
API_MCP_SESSION_CLOSED = ErrorDefinition(code=31204, message='MCP Session不存在或已关闭')
API_RECOVERY_CONFIG_INVALID = ErrorDefinition(code=31215, message='步骤执行配置必须为对象，且仅支持布尔值 is_recovery')
API_CURL_IMPORT_INVALID = ErrorDefinition(code=31216, message='cURL 命令格式不正确，请提供包含有效 HTTP/HTTPS 地址的 cURL（bash）命令')
API_AUTH_PUBLIC_VARIABLES_INVALID = ErrorDefinition(code=31217, message='授权关联公共变量无效：请选择同产品、适用当前被测环境且键名不重复的有效变量')
API_AUTH_CONTEXT_MISMATCH = ErrorDefinition(code=31218, message='用例与授权的租户或地址条件不匹配，请在用例中选择与该授权一致的公共变量')
API_AUTH_TARGET_INVALID = ErrorDefinition(code=31219, message='授权适用目标地址无效或与当前请求不匹配，请选择当前产品、被测环境中已配置的地址；留空使用默认地址')
API_CALLBACK_CONFIG_INVALID = ErrorDefinition(code=31220, message='回调验证配置无效：{}')
API_CALLBACK_EXECUTION_FAILED = ErrorDefinition(code=31221, message='回调验证未通过：{}')
API_EXTRACTION_CONFIG_INVALID = ErrorDefinition(code=31222, message='{}配置错误（第{}项）：{}')
API_CASE_REVISION_SUMMARY_INVALID = ErrorDefinition(code=31225, message='修订摘要必须是字符串，且最多{}个字符，请精简后重试')
API_CASE_TRACE_INTERRUPTED = ErrorDefinition(code=31226, message='本次执行链路未确认完成，最终结果或结果保存尚未确认。请按Trace编号核查原请求及清理记录，勿直接重复执行写入')
MODULE_COVERAGE_CASE_NOT_FOUND = ErrorDefinition(code=31227, message='绑定的API Case {} 不存在，请检查Case编号')
MODULE_COVERAGE_CASE_PRODUCT_MISMATCH = ErrorDefinition(code=31228, message='API Case {} 不属于当前产品 {}，不能绑定，请选择同产品用例')
MODULE_COVERAGE_CASE_MODULE_MISMATCH = ErrorDefinition(code=31229, message='覆盖场景模块 {} 与API Case {} 的模块 {} 不同：{}。请核对原绑定及接口Owner/Consumer关系，不要复制Case绕过校验')
MODULE_COVERAGE_CASE_REVISION_MISMATCH = ErrorDefinition(code=31230, message='API Case {} 的修订 {} 不存在或不属于该Case，请选择该Case的精确修订')
MODULE_COVERAGE_CASE_TARGET_MISMATCH = ErrorDefinition(code=31231, message='API Case {} 的修订 {} 未能证明调用覆盖目标接口 {}，不能保留跨模块绑定，请核对修订中的接口步骤')
API_RESOURCE_CONFIG_INVALID = ErrorDefinition(code=31232, message='API执行资源清理配置无效：{}')
API_RESOURCE_CLEANUP_FAILED = ErrorDefinition(code=31233, message='API执行资源清理未完成：{}。请按资源台账核查并重试清理，不要重跑创建请求')
