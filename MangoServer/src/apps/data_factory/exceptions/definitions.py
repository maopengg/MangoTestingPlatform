"""Business error definitions for this Django app."""

from src.common.exceptions.definitions import ErrorDefinition

DATA_SOURCE_BINDING_CONFLICT = ErrorDefinition(code=34161, message='当前逻辑数据库已绑定{}，请编辑现有绑定或先解绑')

DATA_FACTORY_SCENARIO_MODULE_TEMPLATE_BINDING_INVALID = ErrorDefinition(code=34000, message='场景模板必须绑定模块')
DATA_FACTORY_PROJECT_PRODUCT_MODULE_INVALID = ErrorDefinition(code=34001, message='模块不属于当前项目/产品')
DATA_FACTORY_PROJECT_PRODUCT_ENTITY_INVALID = ErrorDefinition(code=34002, message='实体不属于当前项目/产品')
DATA_FACTORY_MODULE_ENTITY_INVALID = ErrorDefinition(code=34003, message='实体不属于当前模块')
DATA_FACTORY_ENTITY_NAME_TEMPLATE_DUPLICATED = ErrorDefinition(code=34004, message='当前实体下已存在模板名称：{}')
DATA_FACTORY_FIELD_INVALID = ErrorDefinition(code=34005, message='字段覆盖规则格式错误：{}')
DATA_FACTORY_CONFIG_INVALID = ErrorDefinition(code=34006, message='数据工厂配置校验失败：{}')
DATA_FACTORY_FIELD_DEPENDENCY_ENTITY_REQUIRED = ErrorDefinition(
    code=34195, message='字段“{}”的依赖配置不完整：缺少依赖实体 ID（dependency_entity_id），请选择依赖实体后保存',
)
DATA_FACTORY_FIELD_GENERATOR_CONFIG_INVALID = ErrorDefinition(
    code=34196, message='字段“{}”的生成配置无效：{}。请修改该字段的生成规则后重试',
)
DATA_FACTORY_SCENARIO_TEMPLATE_NOT_ALLOWED = ErrorDefinition(code=34007, message='数据工厂场景模板“{}”不能启用：{}')
DATA_FACTORY_DATABASE_DATA_SOURCE_ENTITY_RECORD_EXECUTION_INVALID = ErrorDefinition(code=34008,
                                                                                    message='执行明细 {} 未记录数据库绑定，且实体未绑定逻辑数据源，无法安全清理')
DATA_FACTORY_DATABASE_DATA_SOURCE_RECORD_EXECUTION_BINDING_INVALID = ErrorDefinition(code=34009,
                                                                                     message='执行明细 {} 未记录数据库绑定，当前找不到逻辑数据源 {} 与实际数据库 {} 的绑定，无法安全清理')
DATA_FACTORY_DATABASE_DATA_SOURCE_PERMISSION_RECORD_EXECUTION_INVALID = ErrorDefinition(code=34010,
                                                                                        message='执行明细 {} 未记录数据库绑定，逻辑数据源 {} 与实际数据库 {} 存在多个环境绑定，无法确认清理权限')
DATA_FACTORY_CLEANUP_INVALID = ErrorDefinition(code=34011, message='清理后仍检测到残留数据：表 {}，主键 {}={}，残留 {} 条')
DATA_FACTORY_DELETE_NOT_FOUND = ErrorDefinition(code=34012, message='测试对象不存在或已删除，请使用存在的测试对象id查询')
DATA_SOURCE_DATABASE_TYPE_UNSUPPORTED = ErrorDefinition(code=34013, message='暂不支持的数据库类型：{}')
DATA_SOURCE_SQL_DATABASE_UNSUPPORTED = ErrorDefinition(code=34014, message='当前数据库不支持 SQL 能力：{}')
DATA_SOURCE_DATABASE_CONFIG_DELETE_BINDING_INVALID = ErrorDefinition(code=34015,
                                                                     message='该数据库配置已被环境绑定引用，请先解除绑定后再删除')
DATA_SOURCE_DATABASE_PERMISSION_READ_BINDING_INVALID = ErrorDefinition(code=34016,
                                                                       message='当前环境的数据库绑定未开启读取权限')
DATA_SOURCE_INVALID = ErrorDefinition(code=34017, message='请输入Redis查询命令')
DATA_SOURCE_EXECUTION_NOT_ALLOWED = ErrorDefinition(code=34018, message='Redis仅支持只读查询命令，当前命令不允许执行：{}')
DATA_SOURCE_NAME_INVALID = ErrorDefinition(code=34019, message='请输入合法的Elasticsearch索引名称')
DATA_SOURCE_JSON_INVALID = ErrorDefinition(code=34020, message='Elasticsearch查询条件必须是JSON对象')
DATA_SOURCE_FAILED = ErrorDefinition(code=34021, message='Redis查询失败：{}')
DATA_SOURCE_FAILED_CODE_FAILED = ErrorDefinition(code=34022, message='Elasticsearch查询失败：{}')
DATA_SOURCE_SQL_DATABASE_INVALID = ErrorDefinition(code=34023, message='{} SQL语法或数据库对象错误：{}')
DATA_SOURCE_SQL_PARAMETER_INVALID = ErrorDefinition(code=34024, message='{} SQL参数或数据格式错误：{}')
DATA_SOURCE_SQL_DATABASE_INVALID_CODE_SQL_DATABASE_INVALID = ErrorDefinition(code=34025,
                                                                             message='{} SQL违反数据库约束：{}')
DATA_SOURCE_SQL_EXECUTION_FAILED = ErrorDefinition(code=34026, message='{} SQL执行或连接失败：{}')
DATA_SOURCE_SQL_EXECUTION_TIMEOUT = ErrorDefinition(code=34027, message='{} SQL执行超时：{}')
DATA_SOURCE_INVALID_CODE_INVALID = ErrorDefinition(code=34028, message='Redis命令格式错误：{}')
DATA_SOURCE_PERMISSION_FAILED = ErrorDefinition(code=34029, message='Redis认证或权限校验失败：{}')
DATA_SOURCE_PARAMETER_INVALID = ErrorDefinition(code=34030, message='Redis命令或参数错误：{}')
DATA_SOURCE_TYPE_INVALID = ErrorDefinition(code=34031, message='Redis数据类型不匹配：{}')
DATA_SOURCE_WRITE_NOT_ALLOWED = ErrorDefinition(code=34032, message='Redis当前实例不允许写入：{}')
DATA_SOURCE_REDIS_NETWORK_FAILED = ErrorDefinition(code=34033, message='Redis网络或TLS连接失败：{}')
DATA_SOURCE_ELASTICSEARCH_QUERY_INVALID = ErrorDefinition(code=34034, message='Elasticsearch查询语法错误：{}')
DATA_SOURCE_PERMISSION_FAILED_CODE_PERMISSION_FAILED = ErrorDefinition(code=34035,
                                                                       message='Elasticsearch访问权限不足，请检查账号的索引或集群权限：{}')
DATA_SOURCE_NOT_FOUND = ErrorDefinition(code=34036, message='Elasticsearch索引不存在：{}')
DATA_SOURCE_REQUEST_SERVICE_INVALID = ErrorDefinition(code=34037, message='Elasticsearch请求过多或服务暂时过载：{}')
DATA_SOURCE_JSON_PARSE_INVALID = ErrorDefinition(code=34038, message='Elasticsearch返回了无法解析的JSON数据：{}')
DATA_SOURCE_ELASTICSEARCH_NETWORK_FAILED = ErrorDefinition(code=34039, message='Elasticsearch网络或TLS连接失败：{}')
DATA_SOURCE_REQUEST_FAILED = ErrorDefinition(code=34040, message='Elasticsearch请求失败（HTTP {}）：{}')
DATA_SOURCE_DATA_SOURCE_PERMISSION_WRITE_BINDING_INVALID = ErrorDefinition(code=34041,
                                                                           message='当前环境的数据源绑定未开启写入权限')
DATA_SOURCE_DATABASE_INVALID = ErrorDefinition(code=34042, message='数据库地址不可达：请先填写数据库域名和端口')
DATA_SOURCE_DATABASE_TIMEOUT = ErrorDefinition(code=34043,
                                               message='数据库地址不可达：{}:{} 连接超时，请检查网络、防火墙或白名单')
DATA_SOURCE_DATABASE_PERMISSION_INVALID = ErrorDefinition(code=34044,
                                                          message='数据库地址不可达：无法连接 {}:{}，请检查域名/IP、端口、网络权限或防火墙')
DATA_SOURCE_DATABASE_USER_PERMISSION_FAILED = ErrorDefinition(code=34045,
                                                              message='主库连接失败：网络已连通，但无法连接主库 {}，请检查库名、用户名、密码和数据库权限。错误：{}')
DATA_SOURCE_TEST_ENVIRONMENT_INVALID = ErrorDefinition(code=34046, message='请先在顶部选择测试环境')
DATA_SOURCE_TEST_ENVIRONMENT_PARAMETER_INVALID = ErrorDefinition(code=34047, message='测试环境或产品参数不合法')
DATA_SOURCE_TEST_ENVIRONMENT_DATA_SOURCE_BINDING_INVALID = ErrorDefinition(code=34048,
                                                                           message='逻辑数据源未绑定当前测试环境')
DATA_SOURCE_DATA_SOURCE_INVALID = ErrorDefinition(code=34049, message='逻辑数据源分类与实际数据源分类不一致')
DATA_SOURCE_DATA_SOURCE_TYPE_INVALID = ErrorDefinition(code=34050, message='逻辑数据源类型与实际数据源类型不一致')
DATA_SOURCE_DATA_SOURCE_EXECUTION_INVALID = ErrorDefinition(code=34051, message='当前逻辑数据源已停用，请启用后再执行')
DATA_SOURCE_DATA_SOURCE_REQUIRED = ErrorDefinition(code=34052, message='{}必须选择逻辑数据源')
DATA_SOURCE_PROJECT_PRODUCT_DATA_SOURCE_INVALID = ErrorDefinition(code=34053,
                                                                  message='{}选择的逻辑数据源不属于当前项目产品')
DATA_SOURCE_SQL_DATA_SOURCE_TYPE_INVALID = ErrorDefinition(code=34054,
                                                           message='{}仅支持MySQL、PostgreSQL和SQLite数据源，当前类型：{}')
DATA_SOURCE_OPERATION_REQUIRED = ErrorDefinition(code=34055, message='{}不能为空')
DATA_SOURCE_OPERATION_PARAMETER_INVALID = ErrorDefinition(code=34056, message='{}参数不合法')
DATA_SOURCE_OPERATION_DATA_SOURCE_TYPE_EXECUTION_UNSUPPORTED = ErrorDefinition(code=34057,
                                                                               message='暂不支持执行该数据源类型：{}')
DATA_SOURCE_OPERATION_DATABASE_EXECUTION_FAILED = ErrorDefinition(code=34058, message='数据库操作执行失败：{}')
DATA_SOURCE_OPERATION_INVALID = ErrorDefinition(code=34059, message='{}必须是非空字符串')
DATA_SOURCE_OPERATION_INVALID_CODE_INVALID = ErrorDefinition(code=34060, message='{}内容过长')
DATA_SOURCE_OPERATION_EXECUTION_INVALID = ErrorDefinition(code=34061, message='{}仅支持执行一条语句')
DATA_SOURCE_OPERATION_JSON_EXECUTION_INVALID = ErrorDefinition(code=34062,
                                                               message='Elasticsearch执行内容必须是JSON对象')
DATA_SOURCE_OPERATION_EXECUTION_INVALID_CODE_EXECUTION_INVALID = ErrorDefinition(code=34063,
                                                                                 message='Elasticsearch执行内容只能包含index和query')
DATA_SOURCE_OPERATION_NAME_REQUIRED = ErrorDefinition(code=34064, message='Elasticsearch索引名称不能为空')
DATA_SOURCE_OPERATION_JSON_INVALID = ErrorDefinition(code=34065, message='Elasticsearch query必须是JSON对象')
DATA_SOURCE_OPERATION_SQL_REQUIRED = ErrorDefinition(code=34066, message='缺少SQLAlchemy依赖')
DATA_SOURCE_OPERATION_DATA_SOURCE_EXECUTION_UNSUPPORTED = ErrorDefinition(code=34067,
                                                                          message='不支持的数据源执行动作：{}')
DATA_SOURCE_OPERATION_DATABASE_EXECUTION_WRITE_INVALID = ErrorDefinition(code=34068,
                                                                         message='当前数据库操作包含写入行为，请确认后重新执行')
DATA_SOURCE_OPERATION_DATA_SOURCE_DELETE_NOT_FOUND = ErrorDefinition(code=34069, message='数据源连接不存在或已删除')
DATA_SOURCE_SQL_REQUIRED = ErrorDefinition(code=1073, message='请输入SQL')
DATA_SOURCE_SINGLE_SQL_REQUIRED = ErrorDefinition(code=1074, message='仅支持单条查询语句')
DATA_SOURCE_QUERY_ONLY = ErrorDefinition(code=1075, message='仅支持查询语句')
DATA_SOURCE_SQLALCHEMY_REQUIRED = ErrorDefinition(code=1076, message='请先安装 SQLAlchemy 依赖后再使用数据库查询')
DATA_FACTORY_CASE_CONFIG_CASE_TYPE_REQUIRED = ErrorDefinition(code=34070, message='用例来源类型不能为空')
DATA_FACTORY_CASE_CONFIG_CASE_TYPE_REQUIRED_CODE_CASE_TYPE_REQUIRED = ErrorDefinition(code=34071,
                                                                                      message='用例来源类型不能为空')
DATA_FACTORY_CASE_CONFIG_STATUS_TEMPLATE_REQUIRED = ErrorDefinition(code=34072, message='状态模板不能为空')
DATA_FACTORY_CLEANUP_DATABASE_RECORD_EXECUTION_CLEANUP_INVALID = ErrorDefinition(code=34073,
                                                                                 message='执行明细 {} 未记录实际数据库，无法安全清理')
DATA_FACTORY_CLEANUP_ENTITY_CONFIG_REQUIRED = ErrorDefinition(code=34074, message='实体 {} 未配置表名')
DATA_FACTORY_CLEANUP_EXECUTION_CLEANUP_REQUIRED = ErrorDefinition(code=34075, message='执行明细 {} 缺少主键值，无法清理')
DATA_FACTORY_CLEANUP_CLEANUP_INVALID = ErrorDefinition(code=34076,
                                                       message='一次清理涉及多个业务库，无法保证跨库事务一致性，请拆分后清理')
DATA_FACTORY_CLEANUP_DATABASE_RECORD_EXECUTION_CLEANUP_INVALID_CODE_DATABASE_RECORD_EXECUTION_CLEANUP_INVALID = ErrorDefinition(
    code=34077, message='执行明细 {} 未记录实际数据库，无法安全清理')
DATA_FACTORY_CLEANUP_SQL_RECORD_EXECUTION_CLEANUP_INVALID = ErrorDefinition(code=34078,
                                                                            message='SQL清理数据未命中任何记录：执行明细 {}，表 {}，主键 {}={}')
DATA_FACTORY_CLEANUP_ENTITY_RECORD_TEMPLATE_EXECUTION_CLEANUP_INVALID = ErrorDefinition(code=34079,
                                                                                        message='执行明细 {} 未记录模板，无法推导清理实体')
DATA_FACTORY_CLEANUP_SQL_INVALID = ErrorDefinition(code=34080, message='请先安装 SQLAlchemy 依赖后再使用数据工厂')
DATA_FACTORY_CLEANUP_SQL_INVALID_CODE_SQL_INVALID = ErrorDefinition(code=34081,
                                                                    message='请先安装 SQLAlchemy 依赖后再使用数据工厂')
DATA_FACTORY_CLEANUP_SQL_CLEANUP_FAILED = ErrorDefinition(code=34082, message='SQL清理数据失败：{}')
DATA_FACTORY_DATASOURCE_TEST_ENVIRONMENT_DATABASE_PERMISSION_INVALID = ErrorDefinition(code=34083,
                                                                                       message='需要指定测试环境后才能校验数据库权限')
DATA_FACTORY_DATASOURCE_TEST_ENVIRONMENT_DATABASE_CONFIG_BINDING_REQUIRED = ErrorDefinition(code=34084,
                                                                                            message='当前测试环境未配置可用的数据库绑定')
DATA_FACTORY_DATASOURCE_EXECUTION_INVALID = ErrorDefinition(code=34085,
                                                            message='当前产品和环境没有对应的测试对象，无法建立执行上下文')
DATA_FACTORY_DATASOURCE_DATABASE_ENTITY_BINDING_INVALID = ErrorDefinition(code=34086,
                                                                          message='实体 {} 未绑定逻辑数据库')
DATA_FACTORY_DATASOURCE_TEST_ENVIRONMENT_DATABASE_ENTITY_PARSE_INVALID = ErrorDefinition(code=34087,
                                                                                         message='实体 {} 需要指定测试环境后才能解析数据库')
DATA_FACTORY_DATASOURCE_DATABASE_ENTITY_BINDING_INVALID_CODE_DATABASE_ENTITY_BINDING_INVALID = ErrorDefinition(
    code=34088, message='实体 {} 未绑定逻辑数据库')
DATA_FACTORY_DATASOURCE_DATABASE_REQUIRED = ErrorDefinition(code=34089, message='逻辑数据库不能为空')
DATA_FACTORY_DATASOURCE_TEST_ENVIRONMENT_DATABASE_PARSE_INVALID = ErrorDefinition(code=34090,
                                                                                  message='需要指定测试环境后才能解析数据库')
DATA_FACTORY_DISCOVER_DATABASE_REQUIRED = ErrorDefinition(code=34091, message='逻辑数据库不能为空')
DATA_FACTORY_DISCOVER_TEST_ENVIRONMENT_REQUIRED = ErrorDefinition(code=34092,
                                                                  message='测试对象或产品和测试环境不能为空')
DATA_FACTORY_DISCOVER_REQUIRED = ErrorDefinition(code=34093, message='表名不能为空')
DATA_FACTORY_DISCOVER_READ_FAILED = ErrorDefinition(code=34094, message='读取数据表失败：{}')
DATA_FACTORY_DISCOVER_NOT_FOUND = ErrorDefinition(code=34095, message='数据表不存在：{}')
DATA_FACTORY_DISCOVER_READ_FAILED_CODE_READ_FAILED = ErrorDefinition(code=34096, message='读取表结构失败：{}')
DATA_FACTORY_DISCOVER_SQL_READ_FAILED = ErrorDefinition(code=34097, message='批量读取 MySQL 表结构失败：{}')
DATA_FACTORY_ENTITY_SCENARIO_TEMPLATE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=34098,
                                                                                        message='场景模板-有关联数据，请先删除绑定的数据后再删除！')
DATA_FACTORY_ENTITY_DATABASE_ENTITY_UNSUPPORTED = ErrorDefinition(code=34099,
                                                                  message='实体是表级定义，同一逻辑数据库下同一张表只需要维护一个实体，不支持复制')
DATA_FACTORY_ENTITY_STATUS_REQUIRED = ErrorDefinition(code=34100, message='状态不能为空')
DATA_FACTORY_ENTITY_REQUIRED = ErrorDefinition(code=34101, message='产品不能为空')
DATA_FACTORY_ENTITY_MODULE_REQUIRED = ErrorDefinition(code=34102, message='模块不能为空')
DATA_FACTORY_ENTITY_PROJECT_PRODUCT_MODULE_INVALID = ErrorDefinition(code=34103, message='模块不属于当前项目/产品')
DATA_FACTORY_ENTITY_DATABASE_REQUIRED = ErrorDefinition(code=34104, message='逻辑数据库不能为空')
DATA_FACTORY_ENTITY_TEST_ENVIRONMENT_INVALID = ErrorDefinition(code=34105, message='请先在顶部选择测试环境')
DATA_FACTORY_ENTITY_MINIMUM_REQUIRED = ErrorDefinition(code=34106, message='请至少选择一张表')
DATA_FACTORY_FIELD_REQUIRED = ErrorDefinition(code=34107, message='entity_id 不能为空')
DATA_FACTORY_FIELD_INVALID_CODE_INVALID = ErrorDefinition(code=34108, message='fields 必须是列表')
DATA_FACTORY_FIELDS_LIST_REQUIRED = ErrorDefinition(code=34109, message='fields 必须是列表')
DATA_FACTORY_FIELD_FIELD_REQUIRED = ErrorDefinition(code=34110, message='字段 name 不能为空')
DATA_FACTORY_GENERATOR_FIELD_GENERATE_UNSUPPORTED = ErrorDefinition(code=34111, message='字段 {} 的生成方式不支持')
DATA_FACTORY_GENERATOR_FIELD_RESULT_GENERATE_INVALID = ErrorDefinition(code=34112,
                                                                       message='字段 {} 必填，但生成结果为空')
DATA_FACTORY_GENERATOR_FIELD_TOO_LONG = ErrorDefinition(code=34113, message='字段 {} 超过最大长度 {}')
DATA_FACTORY_GENERATOR_FIELD_INVALID = ErrorDefinition(code=34114, message='字段 {} 只能是 {}，当前是 {}')
DATA_FACTORY_GENERATOR_FIELD_CONFIG_REQUIRED = ErrorDefinition(code=34115, message='字段 {} 未配置枚举值')
DATA_FACTORY_GENERATOR_ENTITY_FIELD_NOT_FOUND = ErrorDefinition(code=34116, message='字段 {} 依赖的实体上下文不存在：{}')
DATA_FACTORY_GENERATOR_FIELD_CONFIG_REQUIRED_CODE_FIELD_CONFIG_REQUIRED = ErrorDefinition(code=34117,
                                                                                          message='字段 {} 未配置测试数据方法')
DATA_FACTORY_RUNNER_PARTS_EXECUTION_INVALID = ErrorDefinition(code=34118, message='检测到数据工厂循环依赖：{}')
DATA_FACTORY_RUNNER_PARTS_EXECUTION_SQL_CREATE_INVALID = ErrorDefinition(code=34119,
                                                                         message='当前阶段仅支持 SQL 创建方式')
DATA_FACTORY_RUNNER_PARTS_EXECUTION_ENTITY_CONFIG_REQUIRED = ErrorDefinition(code=34120, message='实体 {} 未配置表名')
DATA_FACTORY_RUNNER_PARTS_EXECUTION_SCENARIO_FIELD_CONFIG_NODE_RELATION_INVALID = ErrorDefinition(code=34121,
                                                                                                  message='字段 {} 的节点字段引用只能配置在场景关联项中')
DATA_FACTORY_RUNNER_PARTS_EXECUTION_FIELD_NOT_FOUND = ErrorDefinition(code=34122, message='字段 {} 依赖上下文不存在：{}')
DATA_FACTORY_RUNNER_PARTS_EXECUTION_FIELD_NODE_INVALID = ErrorDefinition(code=34123,
                                                                         message='字段 {} 引用的节点字段为空：{}.{}')
DATA_FACTORY_RUNNER_PARTS_PERSISTENCE_SQL_INVALID = ErrorDefinition(code=34124,
                                                                    message='请先安装 SQLAlchemy 依赖后再使用数据工厂')
DATA_FACTORY_RUNNER_PARTS_PERSISTENCE_SQL_CREATE_FAILED = ErrorDefinition(code=34125, message='SQL创建数据失败：{}')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_STATUS_TEMPLATE_REQUIRED = ErrorDefinition(code=34126, message='状态模板ID不能为空')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_ENTITY_FIELD_CONFIG_REQUIRED = ErrorDefinition(code=34127,
                                                                                 message='字段 {} 未配置依赖实体 dependency_entity_id')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_ENTITY_FIELD_STATUS_TEMPLATE_INVALID = ErrorDefinition(code=34128,
                                                                                         message='字段 {} 的依赖状态模板不属于已选择的依赖实体')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_SCENARIO_TEMPLATE_RELATION_INVALID = ErrorDefinition(code=34129,
                                                                                       message='关联项 {} 不属于场景模板 {}')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_INVALID = ErrorDefinition(code=34130, message='检测到数据工厂循环依赖：{}')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_ENTITY_CONFIG_REQUIRED = ErrorDefinition(code=34131, message='实体 {} 未配置表名')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_SCENARIO_FIELD_CONFIG_NODE_RELATION_INVALID = ErrorDefinition(code=34132,
                                                                                                message='字段 {} 的节点字段引用只能配置在场景关联项中')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_STATUS_TEMPLATE_DELETE_NOT_FOUND = ErrorDefinition(code=34133,
                                                                                     message='状态模板不存在或已被删除，请刷新列表后重试')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_ENTITY_FIELD_STATUS_CONFIG_TEMPLATE_REQUIRED = ErrorDefinition(code=34134,
                                                                                                 message='字段 {} 依赖实体未配置默认状态模板')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_NODE_RELATION_EXECUTION_INVALID = ErrorDefinition(code=34135,
                                                                                          message='关联项 {} 的字段 {} 只能引用主节点或已先执行的关联节点')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_NODE_NOT_FOUND = ErrorDefinition(code=34136, message='节点 {} 不存在字段 {}')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_RELATION_NOT_FOUND = ErrorDefinition(code=34137,
                                                                             message='关联项 {} 不存在字段 {}')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_TYPE_NODE_INVALID = ErrorDefinition(code=34138,
                                                                            message='节点字段类型不一致：{}.{} 为 {}，{} 为 {}')
DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_STATUS_CONFIG_TEMPLATE_DELETE_NOT_FOUND = ErrorDefinition(code=34139,
                                                                                                  message='字段 {} 配置的依赖状态模板不存在或已被删除')
DATA_FACTORY_RUNNER_PARTS_SCENE_NODE_WRITEBACK_NOT_FOUND = ErrorDefinition(code=34140,
                                                                           message='插入后回写节点不存在：{}')
DATA_FACTORY_RUNNER_PARTS_SCENE_NODE_RELATION_WRITEBACK_INVALID = ErrorDefinition(code=34141,
                                                                                  message='插入后回写节点不唯一：{}，请使用 item:<关联项ID>')
DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_INVALID = ErrorDefinition(code=34142, message='字段覆盖规则格式错误：{}')
DATA_FACTORY_RUNNER_PARTS_SCENE_CONFIG_INVALID = ErrorDefinition(code=34143, message='输出配置格式错误：{}')
DATA_FACTORY_RUNNER_PARTS_SCENE_CONFIG_WRITEBACK_INVALID = ErrorDefinition(code=34144,
                                                                           message='插入后回写配置格式错误：{}')
DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_NODE_NOT_FOUND = ErrorDefinition(code=34145, message='目标节点 {} 不存在字段 {}')
DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_NODE_NOT_FOUND_CODE_FIELD_NODE_NOT_FOUND = ErrorDefinition(code=34146,
                                                                                                 message='来源节点 {} 不存在字段 {}')
DATA_FACTORY_RUNNER_PARTS_SCENE_ENTITY_WRITEBACK_NOT_ALLOWED = ErrorDefinition(code=34147,
                                                                               message='插入后回写不允许修改目标实体主键')
DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_CONFIG_GENERATE_INVALID = ErrorDefinition(code=34148,
                                                                                message='目标字段 {} 必须先配置为跳过生成')
DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_WRITEBACK_INVALID = ErrorDefinition(code=34149,
                                                                          message='目标字段 {} 插入时不可为空，无法延迟回写')
DATA_FACTORY_RUNNER_PARTS_SCENE_ENTITY_CONFIG_REQUIRED = ErrorDefinition(code=34150, message='目标实体 {} 未配置主键')
DATA_FACTORY_RUNNER_PARTS_SCENE_DATABASE_NODE_BINDING_WRITEBACK_INVALID = ErrorDefinition(code=34151,
                                                                                          message='插入后回写的来源节点和目标节点必须绑定同一个逻辑数据库')
DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_CONFIG_WRITEBACK_DUPLICATED = ErrorDefinition(code=34152,
                                                                                    message='目标字段重复配置回写：{}')
DATA_FACTORY_RUNNER_PARTS_SCENE_SCENARIO_NODE_CREATE_WRITEBACK_INVALID = ErrorDefinition(code=34153,
                                                                                         message='插入后回写只能引用当前 execution 已创建的场景节点')
DATA_FACTORY_RUNNER_PARTS_SCENE_WRITEBACK_INVALID = ErrorDefinition(code=34154, message='插入后回写来源值为空：{}.{}')
DATA_FACTORY_RUNNER_PARTS_SCENE_NODE_GENERATE_WRITEBACK_REQUIRED = ErrorDefinition(code=34155,
                                                                                   message='插入后回写目标节点缺少已生成主键：{}')
DATA_FACTORY_RUNNER_PARTS_SCENE_SQL_INVALID = ErrorDefinition(code=34156,
                                                              message='请先安装 SQLAlchemy 依赖后再使用数据工厂')
DATA_FACTORY_RUNNER_PARTS_SCENE_SQL_WRITEBACK_FAILED = ErrorDefinition(code=34157, message='SQL回写数据失败：{}')
DATA_FACTORY_RUNNER_PARTS_SCENE_WRITEBACK_INVALID_CODE_WRITEBACK_INVALID = ErrorDefinition(code=34158,
                                                                                           message='插入后回写影响行数应为 1，实际为 {}')
DATA_FACTORY_TEMPLATE_STATUS_REQUIRED = ErrorDefinition(code=34159, message='状态不能为空')
DATA_FACTORY_TYPE_CAST_FIELD_TYPE_CONVERT_FAILED = ErrorDefinition(code=34160, message='字段值类型转换失败：{} -> {}')
SQL_AUDIT_SOURCE_TYPE_REQUIRED = ErrorDefinition(code=34162, message='平台未提供数据源执行来源 source_type，本次未执行。请管理员检查调用入口的来源登记')
SQL_AUDIT_SOURCE_STAGE_REQUIRED = ErrorDefinition(code=34163, message='平台未提供数据源执行阶段 source_stage，本次未执行。请管理员检查调用入口的来源登记')
SQL_AUDIT_REQUEST_RUNNING = ErrorDefinition(code=34164, message='数据源原请求 {} 尚未确认完成，平台不会重复发送。请管理员按请求编号核查原执行及清理记录；未完成的操作尚无最终审计记录')
SQL_AUDIT_REPLAY_FAILED = ErrorDefinition(code=34165, message='该数据源请求已有失败记录：{}。请查看原执行明细并核对实际数据后再决定是否重新执行')
DATASOURCE_AUDIT_UNAVAILABLE = ErrorDefinition(code=34173, message='平台无法创建数据源执行记录，本次操作尚未发送。请管理员排查执行记录存储')
DATASOURCE_AUDIT_COMPLETION_FAILED = ErrorDefinition(code=34174, message='平台保存数据源执行结果失败，最终状态无法确认。请管理员核对执行记录和实际数据；写入操作勿直接重试，避免重复数据')
DATASOURCE_AUDIT_REQUEST_CONFLICT = ErrorDefinition(code=34175, message='当前请求编号已被另一项数据源操作使用，本次请求被拒绝。请管理员检查请求编号生成逻辑')
DATASOURCE_AUDIT_RESULT_UNAVAILABLE = ErrorDefinition(code=34176, message='该请求已执行，但平台没有可再次返回的完整结果。请查看原执行记录，不要直接重复写入')
DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID = ErrorDefinition(code=34177, message='ES清理规则配置错误：{}。请修改场景模板的关联资源清理配置')
DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID = ErrorDefinition(code=34178, message='无法确认ES文档属于本次工厂执行，平台未删除该文档。请核对执行记录中的归属快照、租户和文档ID映射')
DATA_FACTORY_ES_CLEANUP_BASELINE_EXISTS = ErrorDefinition(code=34179, message='对应ES文档在本次造数提交前已存在，不能作为本次新建资源清理。请检查文档ID是否重复或映射错误')
DATA_FACTORY_ES_CLEANUP_TIMEOUT = ErrorDefinition(code=34180, message='数据库记录已清理，但ES清理观察窗口结束后仍未取得连续缺失验证。请查看文档回查明细，检查删除同步或清理操作后重试')
DATA_FACTORY_ES_CLEANUP_TARGET_CHANGED = ErrorDefinition(code=34181, message='当前ES连接或环境绑定与造数时不一致，平台未使用新配置删除历史数据。请管理员核对执行记录中的原连接和当前绑定')
DATA_FACTORY_ES_CLEANUP_VERIFICATION_FAILED = ErrorDefinition(code=34182, message='ES清理结果未确认：{}。请在数据工厂执行记录中处理并完成清理验证')
DATA_SOURCE_ELASTICSEARCH_REQUEST_TIMEOUT = ErrorDefinition(code=34183, message='ES操作等待响应超时，最终结果尚未确认。请回查执行记录对应资源，勿仅凭超时认定操作失败并重复写入')
DATASOURCE_POLICY_INVALID = ErrorDefinition(code=34184, message='数据源性能配置校验未通过。请管理员在系统运维－配置管理中检查数据源性能保护配置')
DATASOURCE_GOVERNOR_UNAVAILABLE = ErrorDefinition(code=34185, message='平台无法访问数据源执行配额服务，本次未取得执行许可。请管理员检查平台控制数据库和配额服务')
DATASOURCE_ADMISSION_TIMEOUT = ErrorDefinition(code=34186, message='当前未取得数据源执行名额，本次操作尚未发送。请管理员检查当前执行占用和等待队列')
DATASOURCE_RECONCILIATION_REQUIRED = ErrorDefinition(code=34191, message='数据源存在结果未确认的历史占用，当前无法取得执行名额，本次操作尚未发送。请管理员核查历史执行结果和配额记录，勿直接清空占用或调大配额')
DATASOURCE_SETTLEMENT_FAILED = ErrorDefinition(code=34192, message='平台未完成数据源配额结算。请管理员核查执行记录及配额占用；不要通过重复执行来释放名额')
DATA_FACTORY_UNIQUE_VALUE_CONFLICT = ErrorDefinition(code=34198, message='数据工厂实体“{}”插入失败：数据库返回1062唯一键冲突。请检查模板中的固定唯一值和并发造数规则；本轮独占数据应使用隔离值，需要复用的数据应配置复用关系。平台不会删除存量数据或自动重试该INSERT')
DATA_SOURCE_SERVER_QUERY_LIMIT_EXCEEDED = ErrorDefinition(code=34199, message='数据库已中止本次查询：MySQL返回3024，超过SQL或数据库设置的执行时间限制。请检查该用例或全局变量SQL中的MAX_EXECUTION_TIME及数据库超时配置，并优化查询范围和执行计划；这不是平台等待执行名额超时')
DATASOURCE_OPERATION_COST_EXCEEDED = ErrorDefinition(code=34187, message='{}')
DATA_FACTORY_CLEANUP_IN_PROGRESS = ErrorDefinition(code=34188, message='已有清理任务占用本次执行。请查看执行记录中的任务状态，勿重复提交清理')
DATA_FACTORY_CLEANUP_INTERRUPTED = ErrorDefinition(code=34189, message='数据工厂清理过程已中断，最终结果未确认。请在执行记录中核对实际数据和未完成项，再补清；不能视为已清理')
DATA_FACTORY_CLEANUP_TIMEOUT = ErrorDefinition(code=34190, message='数据工厂实际清理处理时间超过配置上限，仍有资源未确认清理完成。请查看执行记录中的未完成项并核查后重试')
DATA_FACTORY_CLEANUP_COORDINATION_FAILED = ErrorDefinition(code=34193, message='{}')
DATA_SOURCE_QUERY_RESULT_LIMIT_EXCEEDED = ErrorDefinition(code=34194, message='数据库查询结果超过返回行数上限：当前配置为 {} 行，已读取至少 {} 行。请检查用例 SQL 是否未限制查询条数或查询范围过大，并及时修改用例')
DATA_FACTORY_RUNNER_PARTS_EXECUTION_PRIMARY_KEY_REQUIRED = ErrorDefinition(
    code=34166,
    message='实体 {} 创建数据后未获得清理主键 {}，已回滚本次创建；请检查实体主键配置与真实表结构',
)
DATA_FACTORY_ENTITY_UNAVAILABLE = ErrorDefinition(
    code=34167,
    message='数据工厂实体“{}”已停用（来源：{}，原因：{}，时间：{}）',
)
DATA_FACTORY_ENTITY_ACTIVATION_INVALID = ErrorDefinition(
    code=34197, message='数据模型“{}”启用校验失败：{}。请按数据模型校验环境核对并同步表结构后重试',
)
DATA_FACTORY_CASE_AUTO_CLEANUP_FAILED = ErrorDefinition(
    code=34168,
    message='用例数据工厂自动清理失败：{}',
)
DATA_FACTORY_TEMPLATE_DELETE_REFERENCED = ErrorDefinition(
    code=34169, message='场景模板“{}”不能删除：{}。请先解除引用，或改为停用',
)
DATA_FACTORY_TEMPLATE_NOT_FOUND = ErrorDefinition(code=34170, message='场景模板不存在或已删除，请刷新后重试')
DATASOURCE_LIMIT_RETIREMENT_BLOCKED = ErrorDefinition(code=34200, message='旧数据源限流配置尚不能退役：{}')
DATA_SOURCE_ELASTICSEARCH_AUTHENTICATION_FAILED = ErrorDefinition(
    code=34171, message='Elasticsearch账号认证失败，请检查账号和密码：{}',
)
DATA_SOURCE_DEFAULT_DATABASE_REQUIRED = ErrorDefinition(
    code=34172, message='未选择默认数据库，请在逻辑数据库环境绑定中选择数据库，或在SQL中使用库.表查询',
)
