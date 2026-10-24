"""Business error definitions for this Django app."""

from src.common.exceptions.definitions import ErrorDefinition

DATA_SOURCE_BINDING_CONFLICT = ErrorDefinition(code=34161, message='当前逻辑数据库已绑定{}，请编辑现有绑定或先解绑')

DATA_FACTORY_SCENARIO_MODULE_TEMPLATE_BINDING_INVALID = ErrorDefinition(code=34000, message='场景模板必须绑定模块')
DATA_FACTORY_PROJECT_PRODUCT_MODULE_INVALID = ErrorDefinition(code=34001, message='模块不属于当前项目/产品')
DATA_FACTORY_PROJECT_PRODUCT_ENTITY_INVALID = ErrorDefinition(code=34002, message='实体不属于当前项目/产品')
DATA_FACTORY_MODULE_ENTITY_INVALID = ErrorDefinition(code=34003, message='实体不属于当前模块')
DATA_FACTORY_ENTITY_NAME_TEMPLATE_DUPLICATED = ErrorDefinition(code=34004, message='当前实体下已存在模板名称：{}')
DATA_FACTORY_FIELD_INVALID = ErrorDefinition(code=34005, message='字段覆盖规则格式错误：{}')
DATA_FACTORY_CONFIG_INVALID = ErrorDefinition(code=34006, message='输出配置格式错误：{}')
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
SQL_AUDIT_SOURCE_TYPE_REQUIRED = ErrorDefinition(code=34162, message='SQL执行来源 source_type 不能为空')
SQL_AUDIT_SOURCE_STAGE_REQUIRED = ErrorDefinition(code=34163, message='SQL执行来源 source_stage 不能为空')
SQL_AUDIT_REQUEST_RUNNING = ErrorDefinition(code=34164, message='SQL请求 {} 正在执行，请勿重复提交')
SQL_AUDIT_REPLAY_FAILED = ErrorDefinition(code=34165, message='SQL请求上次执行失败：{}')
DATA_FACTORY_RUNNER_PARTS_EXECUTION_PRIMARY_KEY_REQUIRED = ErrorDefinition(
    code=34166,
    message='实体 {} 创建数据后未获得清理主键 {}，已回滚本次创建；请检查实体主键配置与真实表结构',
)
DATA_FACTORY_ENTITY_UNAVAILABLE = ErrorDefinition(
    code=34167,
    message='数据工厂实体“{}”已停用（来源：{}，原因：{}，时间：{}）',
)
DATA_FACTORY_CASE_AUTO_CLEANUP_FAILED = ErrorDefinition(
    code=34168,
    message='用例数据工厂自动清理失败：{}',
)
DATA_FACTORY_TEMPLATE_DELETE_REFERENCED = ErrorDefinition(
    code=34169, message='场景模板“{}”不能删除：{}。请先解除引用，或改为停用',
)
DATA_FACTORY_TEMPLATE_NOT_FOUND = ErrorDefinition(code=34170, message='场景模板不存在或已删除，请刷新后重试')
DATA_SOURCE_ELASTICSEARCH_AUTHENTICATION_FAILED = ErrorDefinition(
    code=34171, message='Elasticsearch账号认证失败，请检查账号和密码：{}',
)
DATA_SOURCE_DEFAULT_DATABASE_REQUIRED = ErrorDefinition(
    code=34172, message='未选择默认数据库，请在逻辑数据库环境绑定中选择数据库，或在SQL中使用库.表查询',
)
