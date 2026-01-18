from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON, SmallInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database.session import Base


class Role(Base):
    __tablename__ = ""roles""

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)  # 角色名称
    description = Column(String(64), nullable=True)  # 角色描述
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship back-reference
    users = relationship(""User"", back_populates=""role"")


class User(Base):
    __tablename__ = ""users""

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)  # 昵称
    username = Column(String(64), unique=True, nullable=False)  # 登录账号
    email = Column(String(100), unique=True, index=True, nullable=False)  # Added for compatibility
    hashed_password = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey(""roles.id""), nullable=True)  # 关联角色
    ip = Column(String(64), nullable=True)  # 登录IP
    mailbox = Column(JSON, default=list)  # 邮箱列表
    selected_project = Column(Integer, nullable=True)  # 选中的项目ID
    selected_environment = Column(Integer, nullable=True)  # 选中的环境ID
    last_login_time = Column(DateTime(timezone=True), nullable=True)  # 最后登录时间
    config = Column(JSON, default=dict)  # 用户配置
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    role = relationship(""Role"", back_populates=""users"")
    projects = relationship(""Project"", back_populates=""owner"")
    test_suites = relationship(""TestSuite"", back_populates=""user"")
    tasks = relationship(""Task"", back_populates=""case_people"")
    api_cases = relationship(""ApiCase"", back_populates=""case_people"")
    ui_cases = relationship(""UiCase"", back_populates=""case_people"")


class UserLogs(Base):
    __tablename__ = ""user_logs""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey(""users.id""), nullable=True)
    source_type = Column(String(64), nullable=True)  # 来源类型
    ip = Column(String(64), nullable=True)  # IP
    url = Column(String(256), nullable=True)  # URL
    method = Column(String(64), nullable=True)  # HTTP方法
    status_code = Column(String(64), nullable=True)  # 状态码
    request_data = Column(Text, nullable=True)  # 请求数据
    response_data = Column(Text, nullable=True)  # 响应数据

    user = relationship(""User"")


class Project(Base):
    __tablename__ = ""projects""

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)  # 项目名称
    description = Column(Text)
    status = Column(Integer, default=1)  # 状态
    owner_id = Column(Integer, ForeignKey(""users.id""))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship(""User"", back_populates=""projects"")
    project_products = relationship(""ProjectProduct"", back_populates=""project"")
    test_suites = relationship(""TestSuite"", back_populates=""project_product"")
    tasks = relationship(""Task"", back_populates=""project_product"")
    api_tests = relationship(""ApiTest"", back_populates=""project"")
    api_cases = relationship(""ApiCase"", back_populates=""project_product"")
    ui_cases = relationship(""UiCase"", back_populates=""project_product"")
    monitoring_tasks = relationship(""MonitoringTask"", back_populates=""project_product"")
    

class ProjectProduct(Base):
    __tablename__ = ""project_products""

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey(""projects.id""))
    name = Column(String(64), unique=True, nullable=False)  # 产品名称
    ui_client_type = Column(Integer, default=0)  # UI客户端类型
    api_client_type = Column(Integer, default=0)  # API客户端类型
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship(""Project"", back_populates=""project_products"")
    product_modules = relationship(""ProductModule"", back_populates=""project_product"")
    test_objects = relationship(""TestObject"", back_populates=""project_product"")
    notice_groups = relationship(""NoticeGroup"", back_populates=""project"")
    test_suites = relationship(""TestSuite"", back_populates=""project_product"")
    tasks = relationship(""Task"", back_populates=""project_product"")
    api_tests = relationship(""ApiTest"", back_populates=""project_product"")
    api_cases = relationship(""ApiCase"", back_populates=""project_product"")
    api_headers = relationship(""ApiHeaders"", back_populates=""project_product"")
    api_publics = relationship(""ApiPublic"", back_populates=""project_product"")
    ui_cases = relationship(""UiCase"", back_populates=""project_product"")
    ui_publics = relationship(""UiPublic"", back_populates=""project_product"")
    pages = relationship(""Page"", back_populates=""project_product"")
    page_steps = relationship(""PageSteps"", back_populates=""project_product"")
    monitoring_tasks = relationship(""MonitoringTask"", back_populates=""project_product"")
    file_data = relationship(""FileData"", back_populates=""project_product"")


class ProductModule(Base):
    __tablename__ = ""product_modules""

    id = Column(Integer, primary_key=True, index=True)
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    name = Column(String(64), nullable=False)  # 模块名称
    superior_module_1 = Column(String(64), nullable=True)  # 一级模块名称
    superior_module_2 = Column(String(64), nullable=True)  # 二级模块名称
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project_product = relationship(""ProjectProduct"", back_populates=""product_modules"")
    api_tests = relationship(""ApiTest"", back_populates=""module"")
    api_cases = relationship(""ApiCase"", back_populates=""module"")
    ui_cases = relationship(""UiCase"", back_populates=""module"")
    pages = relationship(""Page"", back_populates=""module"")
    page_steps = relationship(""PageSteps"", back_populates=""module"")


class TestObject(Base):
    __tablename__ = ""test_objects""

    id = Column(Integer, primary_key=True, index=True)
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    executor_name_id = Column(Integer, ForeignKey(""users.id""))  # 执行人
    environment = Column(Integer)  # 环境备注
    name = Column(String(64), nullable=False)  # 被测试的对象名称
    value = Column(String(1024), nullable=False)  # 被测试的对象值
    db_c_status = Column(Integer, default=0)  # 查询权限
    db_rud_status = Column(Integer, default=0)  # 增删改权限
    auto_type = Column(Integer, default=0)  # 自动化使用类型
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project_product = relationship(""ProjectProduct"", back_populates=""test_objects"")
    user = relationship(""User"")
    databases = relationship(""Database"", back_populates=""test_object"")


class NoticeGroup(Base):
    __tablename__ = ""notice_groups""

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey(""projects.id""))
    name = Column(String(64), nullable=False)  # 通知组名称
    mail = Column(JSON, default=list)  # 邮箱
    feishu = Column(String(255), nullable=True)  # 飞书通知
    dingding = Column(String(255), nullable=True)  # 钉钉通知
    work_weixin = Column(String(255), nullable=True)  # 企业微信通知
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship(""Project"", back_populates=""notice_groups"")


class Database(Base):
    __tablename__ = ""databases""

    id = Column(Integer, primary_key=True, index=True)
    test_object_id = Column(Integer, ForeignKey(""test_objects.id""))
    name = Column(String(64), nullable=False)  # 数据库名称
    user = Column(String(64), nullable=False)  # 登录用户名
    password = Column(String(64), nullable=False)  # 登录密码
    host = Column(String(64), nullable=False)  # 数据库地址
    port = Column(Integer, nullable=False)  # 端口
    status = Column(Integer, default=0)  # 是否启用
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    test_object = relationship(""TestObject"", back_populates=""databases"")


class FileData(Base):
    __tablename__ = ""file_data""

    id = Column(Integer, primary_key=True, index=True)
    project_product_id = Column(Integer, ForeignKey(""project_products.id""), nullable=True)
    type = Column(Integer)  # 类型
    name = Column(String(255), unique=True, nullable=False)  # 文件名称
    test_file_path = Column(String(512), nullable=True)  # 文件路径（代替Django的FileField）
    failed_screenshot_path = Column(String(512), nullable=True)  # 失败截图路径（代替Django的ImageField）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project_product = relationship(""ProjectProduct"", back_populates=""file_data"")


class TimeTasks(Base):
    __tablename__ = ""time_tasks""

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)  # 定时策略名称
    cron = Column(String(64), nullable=False)  # cron表达式
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Task(Base):
    __tablename__ = ""tasks""

    id = Column(Integer, primary_key=True, index=True)
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    test_env = Column(Integer, default=0)  # 测试环境
    name = Column(String(64), nullable=False)  # 任务名称
    case_people_id = Column(Integer, ForeignKey(""users.id""))  # 用例责任人
    status = Column(Integer, default=0)  # 任务状态
    timing_strategy_id = Column(Integer, ForeignKey(""time_tasks.id""))  # 定时策略
    is_notice = Column(Integer, default=0)  # 是否发送通知
    notice_group_id = Column(Integer, ForeignKey(""notice_groups.id""), nullable=True)  # 通知组
    fail_notice = Column(Integer, default=0)  # 只有失败发送
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project_product = relationship(""ProjectProduct"", back_populates=""tasks"")
    case_people = relationship(""User"", back_populates=""tasks"")
    timing_strategy = relationship(""TimeTasks"")
    notice_group = relationship(""NoticeGroup"")
    task_details = relationship(""TaskDetail"", back_populates=""task"")
    test_suites = relationship(""TestSuite"", back_populates=""tasks"")


class TaskDetail(Base):
    __tablename__ = ""task_details""

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Integer, default=0)  # 任务类型 (0:UI, 1:API, 2:Pytest)
    task_id = Column(Integer, ForeignKey(""tasks.id""))
    ui_case_id = Column(Integer, ForeignKey(""ui_cases.id""), nullable=True)  # UI用例
    api_case_id = Column(Integer, ForeignKey(""api_cases.id""), nullable=True)  # API用例
    pytest_case_id = Column(Integer, ForeignKey(""pytest_cases.id""), nullable=True)  # Pytest用例
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship(""Task"", back_populates=""task_details"")
    ui_case = relationship(""UiCase"")
    api_case = relationship(""ApiCase"")
    pytest_case = relationship(""PytestCase"")


class CacheData(Base):
    __tablename__ = ""cache_data""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    describe = Column(String(1024), nullable=True)  # 描述
    key = Column(String(128), unique=True, nullable=False)  # 键
    value = Column(Text, nullable=True)  # 值
    value_type = Column(Integer, nullable=True)  # 值的类型枚举


class TestSuite(Base):
    __tablename__ = ""test_suites""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    test_env = Column(Integer)  # 测试环境
    user_id = Column(Integer, ForeignKey(""users.id""))  # 用例执行人
    tasks_id = Column(Integer, ForeignKey(""tasks.id""), nullable=True)  # 关联任务
    status = Column(Integer)  # 测试结果
    is_notice = Column(Integer)  # 是否发送通知

    project_product = relationship(""ProjectProduct"", back_populates=""test_suites"")
    user = relationship(""User"", back_populates=""test_suites"")
    tasks = relationship(""Task"", back_populates=""test_suites"")
    test_suite_details = relationship(""TestSuiteDetail"", back_populates=""test_suite"")


class TestSuiteDetail(Base):
    __tablename__ = ""test_suite_details""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    test_suite_id = Column(Integer, ForeignKey(""test_suites.id""))
    type = Column(Integer)  # 类型 (0:UI, 1:API, 2:Pytest)
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    test_env = Column(Integer)  # 测试环境
    case_id = Column(Integer)  # 用例ID
    case_name = Column(String(528), nullable=True)  # 用例名称
    parametrize = Column(JSON, default=list)  # 参数化
    status = Column(Integer)  # 测试结果 (0:失败, 1:成功, 2:待开始, 3:进行中)
    error_message = Column(Text, nullable=True)  # 错误提示
    result_data = Column(JSON, nullable=True)  # 用例缓存数据
    retry = Column(Integer, default=0)  # 重试次数
    push_time = Column(DateTime(timezone=True), nullable=True)  # 推送时间
    case_sum = Column(Integer, default=0)  # 用例数
    success = Column(Integer, default=0)  # 成功数
    fail = Column(Integer, default=0)  # 失败数
    warning = Column(Integer, default=0)  # 警告数

    test_suite = relationship(""TestSuite"", back_populates=""test_suite_details"")
    project_product = relationship(""ProjectProduct"")


class ApiTest(Base):
    __tablename__ = ""api_tests""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    module_id = Column(Integer, ForeignKey(""product_modules.id""))
    type = Column(Integer, default=1)  # 接口的类型
    name = Column(String(1024), nullable=False)  # 接口名称
    url = Column(String(1024), nullable=False)  # 请求url
    method = Column(Integer, nullable=False)  # 请求方法
    headers = Column(JSON, nullable=True)  # 请求头
    params = Column(Text, nullable=True)  # 参数
    is_text_params = Column(Integer, default=1)  # 请求方法
    data = Column(Text, nullable=True)  # data
    is_text_data = Column(Integer, default=1)  # 请求方法
    json = Column(Text, nullable=True)  # json
    is_text_json = Column(Integer, default=1)  # 请求方法
    file = Column(JSON, nullable=True)  # file
    posterior_json_path = Column(JSON, default=list)  # 后置jsonpath提取
    posterior_re = Column(JSON, default=list)  # 后置正则提取
    posterior_func = Column(Text, nullable=True)  # 后置自定义
    posterior_file = Column(String(1024), nullable=True)  # 下载文件名称key
    status = Column(Integer, default=2)  # 状态
    result_data = Column(JSON, nullable=True)  # 最近一次执行结果

    project_product = relationship(""ProjectProduct"", back_populates=""api_tests"")
    module = relationship(""ProductModule"", back_populates=""api_tests"")
    api_case_detailed = relationship(""ApiCaseDetailed"", back_populates=""api_info"")


class ApiCase(Base):
    __tablename__ = ""api_cases""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    module_id = Column(Integer, ForeignKey(""product_modules.id""))
    name = Column(String(64), nullable=False)  # 测试用例名称
    case_flow = Column(Text, nullable=True)  # 步骤顺序
    case_people_id = Column(Integer, ForeignKey(""users.id""))  # 用例责任人
    parametrize = Column(JSON, default=list)  # 参数化
    level = Column(Integer, default=1)  # 用例级别
    front_custom = Column(JSON, default=list)  # 前置方法
    front_sql = Column(JSON, default=list)  # 前置sql
    front_headers = Column(JSON, default=list)  # 前置请求头
    posterior_sql = Column(JSON, default=list)  # 后置sql
    status = Column(Integer, default=2)  # 状态

    project_product = relationship(""ProjectProduct"", back_populates=""api_cases"")
    module = relationship(""ProductModule"", back_populates=""api_cases"")
    case_people = relationship(""User"", back_populates=""api_cases"")
    api_case_detailed = relationship(""ApiCaseDetailed"", back_populates=""case"")


class ApiCaseDetailed(Base):
    __tablename__ = ""api_case_detailed""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    case_id = Column(Integer, ForeignKey(""api_cases.id""))
    api_info_id = Column(Integer, ForeignKey(""api_tests.id""))
    case_sort = Column(Integer, nullable=True)  # 用例排序
    status = Column(Integer, default=2)  # 状态
    error_message = Column(Text, nullable=True)  # 失败提示

    case = relationship(""ApiCase"", back_populates=""api_case_detailed"")
    api_info = relationship(""ApiTest"", back_populates=""api_case_detailed"")
    api_case_detailed_parameters = relationship(""ApiCaseDetailedParameter"", back_populates=""case_detailed"")


class ApiCaseDetailedParameter(Base):
    __tablename__ = ""api_case_detailed_parameters""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    case_detailed_id = Column(Integer, ForeignKey(""api_case_detailed.id""))
    error_retry = Column(Integer, nullable=True)  # 失败重试
    retry_interval = Column(Integer, nullable=True)  # 重试间隔
    name = Column(String(128), nullable=False)  # 步骤名称
    headers = Column(JSON, default=list)  # 请求头
    is_case_headers = Column(Integer, default=1)  # 是否使用用例headers
    params = Column(Text, nullable=True)  # 参数
    data = Column(Text, nullable=True)  # data
    json = Column(Text, nullable=True)  # json
    file = Column(JSON, nullable=True)  # file
    # 前置
    front_sql = Column(JSON, default=list)  # 前置sql
    front_func = Column(Text, nullable=True)  # 前置自定义函数
    # 断言
    ass_general = Column(JSON, default=list)  # sql断言
    ass_sql = Column(JSON, default=list)  # sql断言
    ass_json_all = Column(JSON, nullable=True)  # 响应JSON全匹配断言
    ass_text_all = Column(Text, nullable=True)  # 响应文本全匹配断言
    ass_jsonpath = Column(JSON, default=list)  # 响应jsonpath断言
    # 后置
    posterior_sql = Column(JSON, default=list)  # 后置sql
    posterior_response = Column(JSON, default=list)  # 后置响应处理
    posterior_sleep = Column(Integer, nullable=True)  # 强制等待
    posterior_file = Column(JSON, default=dict)  # 文件下载
    posterior_func = Column(Text, nullable=True)  # 后置自定义
    status = Column(Integer, default=2)  # 状态
    result_data = Column(JSON, nullable=True)  # 最近一次执行结果

    case_detailed = relationship(""ApiCaseDetailed"", back_populates=""api_case_detailed_parameters"")


class ApiHeaders(Base):
    __tablename__ = ""api_headers""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    key = Column(String(128), nullable=False)  # 键
    value = Column(Text, nullable=False)  # 值
    status = Column(Integer, default=0)  # 是否默认开启

    project_product = relationship(""ProjectProduct"", back_populates=""api_headers"")


class ApiPublic(Base):
    __tablename__ = ""api_publics""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    type = Column(Integer, default=0)  # 自定义变量类型 (0:自定义, 1:sql, 2:登录, 3:header)
    name = Column(String(64), nullable=False)  # 名称
    key = Column(String(128), nullable=False)  # 键
    value = Column(Text, nullable=False)  # 值
    status = Column(Integer, default=0)  # 状态

    project_product = relationship(""ProjectProduct"", back_populates=""api_publics"")


class Page(Base):
    __tablename__ = ""pages""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    module_id = Column(Integer, ForeignKey(""product_modules.id""))
    name = Column(String(64), nullable=False)  # 页面名称
    url = Column(String(1048), nullable=False)  # url

    project_product = relationship(""ProjectProduct"", back_populates=""pages"")
    module = relationship(""ProductModule"", back_populates=""pages"")
    page_elements = relationship(""PageElement"", back_populates=""page"")
    page_steps = relationship(""PageSteps"", back_populates=""page"")


class PageElement(Base):
    __tablename__ = ""page_elements""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    page_id = Column(Integer, ForeignKey(""pages.id""))
    name = Column(String(64), nullable=False)  # 元素名称
    exp = Column(Integer, nullable=False)  # 元素表达式
    loc = Column(Text, nullable=False)  # 元素定位
    exp2 = Column(Integer, nullable=True)  # 元素表达式
    loc2 = Column(Text, nullable=True)  # 元素定位
    exp3 = Column(Integer, nullable=True)  # 元素表达式
    loc3 = Column(Text, nullable=True)  # 元素定位
    sleep = Column(Integer, nullable=True)  # 等待时间
    sub = Column(Integer, nullable=True)  # 下标
    sub2 = Column(Integer, nullable=True)  # 下标2
    sub3 = Column(Integer, nullable=True)  # 下标3
    is_iframe = Column(Integer, nullable=True)  # 是否在iframe里面
    prompt = Column(Text, nullable=True)  # AI元素定位提示词

    page = relationship(""Page"", back_populates=""page_elements"")
    page_steps_detailed = relationship(""PageStepsDetailed"", back_populates=""ele_name"")


class PageSteps(Base):
    __tablename__ = ""page_steps""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    page_id = Column(Integer, ForeignKey(""pages.id""))
    module_id = Column(Integer, ForeignKey(""product_modules.id""))
    name = Column(String(64), nullable=False)  # 步骤名称
    run_flow = Column(Text, nullable=True)  # 步骤顺序
    status = Column(Integer, default=2)  # 状态
    result_data = Column(JSON, nullable=True)  # 测试结果
    flow_data = Column(JSON, default=dict)  # flow_data

    project_product = relationship(""ProjectProduct"", back_populates=""page_steps"")
    page = relationship(""Page"", back_populates=""page_steps"")
    module = relationship(""ProductModule"", back_populates=""page_steps"")
    page_steps_detailed = relationship(""PageStepsDetailed"", back_populates=""page_step"")
    ui_case_steps_detailed = relationship(""UiCaseStepsDetailed"", back_populates=""page_step"")


class PageStepsDetailed(Base):
    __tablename__ = ""page_steps_detailed""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    page_step_id = Column(Integer, ForeignKey(""page_steps.id""))
    type = Column(Integer, nullable=False)  # 操作类型 (0:操作, 1:断言)
    ele_name_id = Column(Integer, ForeignKey(""page_elements.id""), nullable=True)  # 元素
    step_sort = Column(Integer, nullable=False)  # 顺序的排序
    # 操作和断言
    ope_key = Column(String(1048), nullable=True)  # 对该元素的操作类型
    ope_value = Column(JSON, nullable=True)  # 对该元素的操作类型
    # sql
    sql_execute = Column(JSON, nullable=True)  # sql步骤
    key_list = Column(JSON, nullable=True)  # sql查询结果的key_list
    sql = Column(String(1048), nullable=True)  # sql
    # 自定义
    custom = Column(JSON, nullable=True)  # 自定义缓存步骤
    key = Column(String(1048), nullable=True)  # key
    value = Column(String(1048), nullable=True)  # value
    # 条件
    condition_value = Column(JSON, nullable=True)  # 条件判断
    # func
    func = Column(Text, nullable=True)  # func

    page_step = relationship(""PageSteps"", back_populates=""page_steps_detailed"")
    ele_name = relationship(""PageElement"", back_populates=""page_steps_detailed"")


class UiCase(Base):
    __tablename__ = ""ui_cases""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    module_id = Column(Integer, ForeignKey(""product_modules.id""))
    name = Column(String(64), nullable=False)  # 用例组名称
    case_flow = Column(Text, nullable=True)  # 步骤顺序
    case_people_id = Column(Integer, ForeignKey(""users.id""))  # 用例责任人
    parametrize = Column(JSON, default=list)  # 参数化
    status = Column(Integer, default=2)  # 状态 (0:失败, 1:成功, 2:待开始, 3:进行中)
    level = Column(Integer, default=0)  # 用例级别
    front_custom = Column(JSON, default=list)  # 前置自定义
    front_sql = Column(JSON, default=list)  # 前置sql
    posterior_sql = Column(JSON, default=list)  # 后置sql

    project_product = relationship(""ProjectProduct"", back_populates=""ui_cases"")
    module = relationship(""ProductModule"", back_populates=""ui_cases"")
    case_people = relationship(""User"", back_populates=""ui_cases"")
    ui_case_steps_detailed = relationship(""UiCaseStepsDetailed"", back_populates=""case"")


class UiCaseStepsDetailed(Base):
    __tablename__ = ""ui_case_steps_detailed""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    case_id = Column(Integer, ForeignKey(""ui_cases.id""))
    page_step_id = Column(Integer, ForeignKey(""page_steps.id""))
    case_sort = Column(Integer, nullable=False)  # 用例排序
    case_data = Column(JSON, nullable=True)  # 用例步骤数据
    switch_step_open_url = Column(Integer, default=0)  # 是否在执行页面的时候切换url
    error_retry = Column(Integer, nullable=True)  # 失败重试
    status = Column(Integer, default=2)  # 状态 (0:失败, 1:成功, 2:待开始, 3:进行中)
    error_message = Column(Text, nullable=True)  # 错误提示
    result_data = Column(JSON, nullable=True)  # 最近一次执行结果

    case = relationship(""UiCase"", back_populates=""ui_case_steps_detailed"")
    page_step = relationship(""PageSteps"", back_populates=""ui_case_steps_detailed"")


class UiPublic(Base):
    __tablename__ = ""ui_publics""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    type = Column(Integer, nullable=False)  # 自定义变量类型 (0:自定义, 1:sql, 2:登录, 3:header)
    name = Column(String(64), nullable=False)  # 名称
    key = Column(String(128), nullable=False)  # 键
    value = Column(Text, nullable=False)  # 值
    status = Column(Integer, default=0)  # 状态

    project_product = relationship(""ProjectProduct"", back_populates=""ui_publics"")


class PytestCase(Base):
    __tablename__ = ""pytest_cases""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    module_id = Column(Integer, ForeignKey(""product_modules.id""))
    name = Column(String(64), nullable=False)  # 用例名称
    project_id = Column(Integer, ForeignKey(""pytest_products.id""))  # 项目ID
    case_type = Column(Integer, default=0)  # 用例类型
    case_level = Column(Integer, default=1)  # 用例级别
    case_describe = Column(Text, nullable=True)  # 用例描述
    case_script = Column(Text, nullable=True)  # 用例脚本
    status = Column(Integer, default=1)  # 状态
    case_people_id = Column(Integer, ForeignKey(""users.id""))  # 用例责任人

    project_product = relationship(""ProjectProduct"")
    module = relationship(""ProductModule"")
    project = relationship(""PytestProduct"")
    case_people = relationship(""User"")


class PytestProduct(Base):
    __tablename__ = ""pytest_products""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    name = Column(String(64), nullable=False)  # 项目名称
    environment = Column(String(255), nullable=True)  # 环境

    project_product = relationship(""ProjectProduct"")


class MonitoringTask(Base):
    __tablename__ = ""monitoring_tasks""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    project_product_id = Column(Integer, ForeignKey(""project_products.id""))
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    script_content = Column(Text, nullable=False)
    script_path = Column(String(512), nullable=True)
    log_path = Column(String(512), nullable=True)
    status = Column(Integer, default=0)  # 状态 (对应枚举值)
    pid = Column(Integer, nullable=True)  # 进程ID
    exit_code = Column(Integer, nullable=True)  # 退出码
    is_notice = Column(Integer, default=0)  # 是否发送通知
    notice_group_id = Column(Integer, ForeignKey(""notice_groups.id""), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)  # 启动时间
    stopped_at = Column(DateTime(timezone=True), nullable=True)  # 停止时间

    project_product = relationship(""ProjectProduct"", back_populates=""monitoring_tasks"")
    notice_group = relationship(""NoticeGroup"")
    reports = relationship(""MonitoringReport"", back_populates=""task"")


class MonitoringReport(Base):
    __tablename__ = ""monitoring_reports""

    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    task_id = Column(Integer, ForeignKey(""monitoring_tasks.id""), nullable=True)
    status = Column(Integer, default=1)  # 状态
    msg = Column(Text, nullable=True)  # 消息内容
    send_text = Column(Text, nullable=True)  # 详细信息
    is_notice = Column(Integer, default=0)  # 是否发送通知

    task = relationship(""MonitoringTask"", back_populates=""reports"")


# Relationship back-populates
User.role = relationship(""Role"", back_populates=""users"")
Project.owner = relationship(""User"", back_populates=""projects"")
ProjectProduct.project = relationship(""Project"", back_populates=""project_products"")
ProductModule.project_product = relationship(""ProjectProduct"", back_populates=""product_modules"")
TestObject.project_product = relationship(""ProjectProduct"", back_populates=""test_objects"")
TestObject.user = relationship(""User"")
NoticeGroup.project = relationship(""Project"", back_populates=""notice_groups"")
Database.test_object = relationship(""TestObject"", back_populates=""databases"")
FileData.project_product = relationship(""ProjectProduct"", back_populates=""file_data"")
Task.project_product = relationship(""ProjectProduct"", back_populates=""tasks"")
Task.case_people = relationship(""User"", back_populates=""tasks"")
Task.timing_strategy = relationship(""TimeTasks"")
Task.notice_group = relationship(""NoticeGroup"")
TaskDetail.task = relationship(""Task"", back_populates=""task_details"")
TestSuite.project_product = relationship(""ProjectProduct"", back_populates=""test_suites"")
TestSuite.user = relationship(""User"", back_populates=""test_suites"")
TestSuite.tasks = relationship(""Task"", back_populates=""test_suites"")
TestSuiteDetail.test_suite = relationship(""TestSuite"", back_populates=""test_suite_details"")
TestSuiteDetail.project_product = relationship(""ProjectProduct"")
ApiTest.project_product = relationship(""ProjectProduct"", back_populates=""api_tests"")
ApiTest.module = relationship(""ProductModule"", back_populates=""api_tests"")
ApiTest.api_case_detailed = relationship(""ApiCaseDetailed"", back_populates=""api_info"")
ApiCase.project_product = relationship(""ProjectProduct"", back_populates=""api_cases"")
ApiCase.module = relationship(""ProductModule"", back_populates=""api_cases"")
ApiCase.case_people = relationship(""User"", back_populates=""api_cases"")
ApiCase.api_case_detailed = relationship(""ApiCaseDetailed"", back_populates=""case"")
ApiCaseDetailed.case = relationship(""ApiCase"", back_populates=""api_case_detailed"")
ApiCaseDetailed.api_info = relationship(""ApiTest"", back_populates=""api_case_detailed"")
ApiCaseDetailedParameter.case_detailed = relationship(""ApiCaseDetailed"", back_populates=""api_case_detailed_parameters"")
ApiHeaders.project_product = relationship(""ProjectProduct"", back_populates=""api_headers"")
ApiPublic.project_product = relationship(""ProjectProduct"", back_populates=""api_publics"")
Page.project_product = relationship(""ProjectProduct"", back_populates=""pages"")
Page.module = relationship(""ProductModule"", back_populates=""pages"")
Page.page_elements = relationship(""PageElement"", back_populates=""page"")
Page.page_steps = relationship(""PageSteps"", back_populates=""page"")
PageElement.page = relationship(""Page"", back_populates=""page_elements"")
PageElement.page_steps_detailed = relationship(""PageStepsDetailed"", back_populates=""ele_name"")
PageSteps.project_product = relationship(""ProjectProduct"", back_populates=""page_steps"")
PageSteps.page = relationship(""Page"", back_populates=""page_steps"")
PageSteps.module = relationship(""ProductModule"", back_populates=""page_steps"")
PageSteps.page_steps_detailed = relationship(""PageStepsDetailed"", back_populates=""page_step"")
PageSteps.ui_case_steps_detailed = relationship(""UiCaseStepsDetailed"", back_populates=""page_step"")
PageStepsDetailed.page_step = relationship(""PageSteps"", back_populates=""page_steps_detailed"")
PageStepsDetailed.ele_name = relationship(""PageElement"", back_populates=""page_steps_detailed"")
UiCase.project_product = relationship(""ProjectProduct"", back_populates=""ui_cases"")
UiCase.module = relationship(""ProductModule"", back_populates=""ui_cases"")
UiCase.case_people = relationship(""User"", back_populates=""ui_cases"")
UiCase.ui_case_steps_detailed = relationship(""UiCaseStepsDetailed"", back_populates=""case"")
UiCaseStepsDetailed.case = relationship(""UiCase"", back_populates=""ui_case_steps_detailed"")
UiCaseStepsDetailed.page_step = relationship(""PageSteps"", back_populates=""ui_case_steps_detailed"")
UiPublic.project_product = relationship(""ProjectProduct"", back_populates=""ui_publics"")
MonitoringTask.project_product = relationship(""ProjectProduct"", back_populates=""monitoring_tasks"")
MonitoringTask.notice_group = relationship(""NoticeGroup"")
MonitoringTask.reports = relationship(""MonitoringReport"", back_populates=""task"")
MonitoringReport.task = relationship(""MonitoringTask"", back_populates=""reports"")
