# Mango Service 项目结构详解

## 项目概览

`
mango_service/
 main.py                 # 应用入口点
 requirements.txt        # 项目依赖
 README.md              # 项目介绍和使用说明
 PROJECT_SUMMARY.md     # 重构项目总结
 STRUCTURE.md          # 本文件，项目结构详解
 .env.example          # 环境变量示例
 Dockerfile            # Docker镜像构建配置
 docker-compose.yml    # Docker Compose部署配置
 start.sh              # 启动脚本
 config/               # 配置文件目录（预留）
 docs/                 # 文档目录（预留）
 src/                  # 源代码主目录
    api/              # API路由和端点
       v1/           # API版本1
           endpoints/ # 各模块API端点
    core/             # 核心功能模块
    database/         # 数据库配置
    models/           # 数据模型定义
    schemas/          # Pydantic数据验证模型
    services/         # 业务逻辑服务
    utils/            # 工具函数
 tests/                # 测试文件
`

## 模块详细介绍

### 1. API 模块 (src/api/)
- **v1/endpoints/auth.py**: 认证相关端点（登录、注册、token等）
- **v1/endpoints/users.py**: 用户管理端点
- **v1/endpoints/projects.py**: 项目管理端点
- **v1/endpoints/api_tests.py**: API测试管理端点
- **v1/endpoints/ui_tests.py**: UI测试管理端点
- **v1/endpoints/pytest_tests.py**: Pytest集成端点
- **v1/endpoints/perf_tests.py**: 性能测试端点
- **v1/endpoints/monitoring.py**: 监控管理端点
- **v1/endpoints/websocket.py**: WebSocket实时通信端点

### 2. 核心模块 (src/core/)
- **deps.py**: 依赖注入和数据库会话管理
- **exceptions.py**: 自定义异常和异常处理器
- **middleware.py**: 中间件（日志、认证等）
- **security.py**: 安全相关（密码加密、JWT等）
- **websocket_manager.py**: WebSocket连接管理器

### 3. 数据模型 (src/models/)
- **User**: 用户模型
- **Project**: 项目模型
- **ApiTest**: API测试模型
- **TestCase**: 测试用例模型
- **TestResult**: 测试结果模型
- **ApiCase**: API用例模型
- **ApiCaseDetailed**: API用例详情模型
- **Task**: 任务模型
- **TaskDetail**: 任务详情模型
- **MonitoringTask**: 监控任务模型
- **MonitoringReport**: 监控报告模型

### 4. 数据验证模型 (src/schemas/)
- 包含所有用于请求/响应验证的Pydantic模型
- 用户相关：UserCreate, UserOut, Token等
- 项目相关：ProjectCreate, ProjectOut等
- 测试相关：ApiTestCreate, TestCaseOut等
- 监控相关：MonitoringTaskCreate, MonitoringTaskOut等

### 5. 业务服务 (src/services/)
- **user_service.py**: 用户管理服务
- **api_test_service.py**: API测试服务
- **ui_test_service.py**: UI测试服务
- **pytest_service.py**: Pytest集成服务
- **perf_test_service.py**: 性能测试服务
- **task_service.py**: 任务调度服务（含APScheduler）
- **monitoring_service.py**: 监控服务
- **api_executor.py**: API测试执行器

### 6. 数据库配置 (src/database/)
- **session.py**: 数据库会话配置（异步支持）

### 7. 工具函数 (src/utils/)
- **logger.py**: 日志系统配置（基于loguru）

### 8. 测试文件 (tests/)
- **conftest.py**: pytest配置和fixture
- **test_api.py**: API端点测试

## 主要特性

1. **异步支持**: 所有数据库操作和API端点都是异步的
2. **类型安全**: 使用Pydantic进行数据验证和类型提示
3. **自动文档**: FastAPI自动生成交互式API文档
4. **认证授权**: JWT-based认证系统
5. **实时通信**: WebSocket支持
6. **任务调度**: APScheduler集成
7. **日志系统**: 结构化日志记录
8. **部署友好**: Docker和Docker Compose支持

## 开发约定

1. 所有API端点使用异步函数
2. 数据库操作使用异步SQLAlchemy
3. 错误处理使用自定义异常
4. 依赖注入用于数据库会话和认证
5. Pydantic模型用于数据验证
6. 业务逻辑封装在服务层
7. 遵循RESTful API设计原则
