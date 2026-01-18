# Mango Service API 文档

## 认证相关

### POST /auth/token
获取访问令牌
- 请求体: OAuth2PasswordRequestForm
- 响应: Token (access_token, token_type)

### POST /auth/register
用户注册
- 请求体: UserCreate (username, email, password)
- 响应: UserOut

### GET /auth/profile
获取当前用户信息
- 需要认证
- 响应: UserOut

## 用户管理

### GET /users
获取用户列表
- 需要认证
- 查询参数: skip, limit
- 响应: List[UserOut]

### POST /users
创建用户（仅管理员）
- 需要管理员权限
- 请求体: UserCreate
- 响应: UserOut

## 项目管理

### GET /projects
获取项目列表
- 需要认证
- 查询参数: skip, limit
- 响应: List[ProjectOut]

### POST /projects
创建项目
- 需要认证
- 请求体: ProjectCreate
- 响应: ProjectOut

### GET /projects/{project_id}
获取特定项目
- 需要认证
- 响应: ProjectOut

### PUT /projects/{project_id}
更新项目
- 需要认证
- 请求体: ProjectUpdate
- 响应: ProjectOut

### DELETE /projects/{project_id}
删除项目
- 需要认证
- 响应: Message

## API测试管理

### GET /api-tests
获取API测试列表
- 需要认证
- 查询参数: skip, limit
- 响应: List[ApiTestOut]

### POST /api-tests
创建API测试
- 需要认证
- 请求体: ApiTestCreate
- 响应: ApiTestOut

### GET /api-tests/{api_test_id}
获取特定API测试
- 需要认证
- 响应: ApiTestOut

### PUT /api-tests/{api_test_id}
更新API测试
- 需要认证
- 请求体: ApiTestUpdate
- 响应: ApiTestOut

### DELETE /api-tests/{api_test_id}
删除API测试
- 需要认证
- 响应: Message

## UI测试管理

### GET /ui-tests
获取UI测试列表
- 需要认证
- 查询参数: skip, limit
- 响应: List[TestCaseOut]

### POST /ui-tests
创建UI测试
- 需要认证
- 请求体: TestCaseCreate
- 响应: TestCaseOut

### GET /ui-tests/{ui_test_id}
获取特定UI测试
- 需要认证
- 响应: TestCaseOut

### PUT /ui-tests/{ui_test_id}
更新UI测试
- 需要认证
- 请求体: TestCaseUpdate
- 响应: TestCaseOut

### DELETE /ui-tests/{ui_test_id}
删除UI测试
- 需要认证
- 响应: Message

## Pytest管理

### GET /pytest-tests
获取Pytest列表
- 需要认证
- 查询参数: skip, limit
- 响应: List[TestCaseOut]

### POST /pytest-tests
创建Pytest
- 需要认证
- 请求体: TestCaseCreate
- 响应: TestCaseOut

### GET /pytest-tests/{pytest_id}
获取特定Pytest
- 需要认证
- 响应: TestCaseOut

### PUT /pytest-tests/{pytest_id}
更新Pytest
- 需要认证
- 请求体: TestCaseUpdate
- 响应: TestCaseOut

### DELETE /pytest-tests/{pytest_id}
删除Pytest
- 需要认证
- 响应: Message

### POST /pytest-tests/{pytest_id}/execute
立即执行Pytest
- 需要认证
- 响应: Execution result

## 性能测试管理

### GET /perf-tests
获取性能测试列表
- 需要认证
- 查询参数: skip, limit
- 响应: List[TestCaseOut]

### POST /perf-tests
创建性能测试
- 需要认证
- 请求体: TestCaseCreate
- 响应: TestCaseOut

### GET /perf-tests/{perf_test_id}
获取特定性能测试
- 需要认证
- 响应: TestCaseOut

### PUT /perf-tests/{perf_test_id}
更新性能测试
- 需要认证
- 请求体: TestCaseUpdate
- 响应: TestCaseOut

### DELETE /perf-tests/{perf_test_id}
删除性能测试
- 需要认证
- 响应: Message

### POST /perf-tests/{perf_test_id}/execute
立即执行性能测试
- 需要认证
- 响应: Performance test result

## 任务调度管理

### POST /tasks
创建任务
- 需要认证
- 请求体: Task data
- 响应: Task info

### GET /tasks
获取任务列表
- 需要认证
- 查询参数: skip, limit
- 响应: List[Task info]

### POST /tasks/{task_id}/execute
立即执行任务
- 需要认证
- 响应: Execution result

### POST /tasks/{task_id}/schedule
调度任务
- 需要认证
- 请求体: Schedule data (cron_expression)
- 响应: Schedule result

## 监控管理

### GET /monitoring/tasks
获取监控任务列表
- 需要认证
- 查询参数: skip, limit
- 响应: List[MonitoringTaskOut]

### POST /monitoring/tasks
创建监控任务
- 需要认证
- 请求体: MonitoringTaskCreate
- 响应: MonitoringTaskOut

### GET /monitoring/tasks/{task_id}
获取特定监控任务
- 需要认证
- 响应: MonitoringTaskOut

### PUT /monitoring/tasks/{task_id}
更新监控任务
- 需要认证
- 请求体: MonitoringTaskUpdate
- 响应: MonitoringTaskOut

### DELETE /monitoring/tasks/{task_id}
删除监控任务
- 需要认证
- 响应: Message

### POST /monitoring/tasks/{task_id}/execute
立即执行监控任务
- 需要认证
- 响应: Execution result

### GET /monitoring/reports/{report_id}
获取特定监控报告
- 需要认证
- 响应: Monitoring report

### GET /monitoring/reports/task/{task_id}
获取特定任务的监控报告
- 需要认证
- 查询参数: skip, limit
- 响应: List[Monitoring report]

## WebSocket端点

### ws://host/ws/{client_id}
通用WebSocket连接端点

### ws://host/notifications/{user_id}
用户通知WebSocket连接端点

## 系统端点

### GET /
应用首页
- 响应: Welcome message

### GET /health
健康检查
- 响应: Health status
