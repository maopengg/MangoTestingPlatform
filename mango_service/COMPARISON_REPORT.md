# MangoService vs MangoServer 功能对比报告

## 对比概述

本文档对比了基于FastAPI的mango_service项目与原始Django MangoServer项目的功能完整性。

## 1. 用户管理模块

### MangoServer功能
- 用户模型包含：name, username, password, role, ip, mailbox, selected_project, selected_environment, last_login_time, config
- 角色模型包含：name, description
- 用户日志模型包含：create_time, user, source_type, ip, url, method, status_code, request_data, response_data
- 完整的级联删除约束

### mango_service当前状态
-  用户模型：基础字段（id, username, email, hashed_password, is_active, is_superuser, created_at, updated_at）
-  缺少：角色系统、邮箱列表、选中的项目/环境、配置、IP等
-  用户日志功能：未实现

### 需要补充
- [ ] 角色管理功能
- [ ] 用户配置和邮箱管理
- [ ] 用户日志记录

## 2. UI测试模块

### MangoServer功能
- 页面模型：项目产品、模块、页面名称、URL
- 页面元素模型：元素名称、表达式、定位、等待时间等
- 页面步骤模型：项目产品、页面、模块、步骤名称、运行流程等
- 页面步骤详情模型：步骤详情、操作类型、元素、SQL、自定义等
- UI用例模型：项目产品、模块、用例名称、步骤流程、责任人等
- UI用例步骤详情模型：用例步骤详情
- UI公共参数模型

### mango_service当前状态
-  基础TestCase模型：name, description, steps, project_id
-  缺少：页面、元素、步骤详情等专业UI测试模型

### 需要补充
- [ ] 完整的UI测试模型（页面、元素、步骤等）
- [ ] UI测试执行器

## 3. 系统配置模块

### MangoServer功能
- 项目模型：项目名称、状态
- 项目产品模型：项目、产品名称、UI/API客户端类型
- 产品模块模型：项目产品、模块名称、上级模块
- 测试对象模型：项目产品、执行人、环境、测试对象
- 通知组模型：项目、名称、邮箱、飞书、钉钉、企业微信
- 数据库模型：测试对象、数据库名称、连接信息
- 文件数据模型：项目产品、类型、文件名、文件
- 时间任务模型：定时策略名称、cron表达式
- 任务模型：项目产品、测试环境、任务名称、责任人、定时策略、通知组
- 任务详情模型：任务类型、任务、UI用例、API用例、Pytest用例
- 缓存数据模型：描述、键、值、值类型
- 测试套件模型：项目产品、测试环境、用户、任务
- 测试套件详情模型：测试套件、类型、项目产品、测试环境、用例ID、参数化、状态、错误消息等

### mango_service当前状态
-  基础Project模型：name, description, owner_id
-  基础Task模型：name, description, project_id, cron_expression, is_active
-  缺少：模块、测试对象、通知组、数据库配置、文件、缓存、测试套件等

### 需要补充
- [ ] 完整的系统配置模型
- [ ] 通知组和通知功能
- [ ] 测试套件管理

## 4. 监控模块

### MangoServer功能
- 监控任务模型：项目产品、名称、描述、脚本内容、脚本路径、日志路径、状态、PID、退出码、通知组、启动/停止时间
- 监控报告模型：任务、状态、消息、发送文本、是否通知

### mango_service当前状态
-  基础监控模型：MonitoringTask和MonitoringReport
-  缺少：脚本路径、PID、退出码、启动/停止时间等专业字段

### 需要补充
- [ ] 完整的监控模型字段
- [ ] 监控任务执行逻辑

## 5. API测试模块

### MangoServer功能
- API信息模型：项目产品、模块、类型、名称、URL、方法、请求头、参数、数据、JSON、文件、后置提取、状态、结果数据
- API用例模型：项目产品、模块、名称、步骤流程、责任人、参数化、前置/后置SQL、状态、级别
- API用例详情模型：用例、API信息、步骤排序、状态、错误消息
- API用例详情参数模型：用例详情、失败重试、名称、请求头、参数、数据、JSON、文件、前置SQL/函数、断言、后置SQL/响应/睡眠/文件/函数、状态、结果数据
- API请求头模型：项目产品、键、值、状态
- API公共参数模型：项目产品、类型、名称、键、值、状态

### mango_service当前状态
-  基础API测试模型：ApiTest（name, description, url, method, headers, body, project_id）
-  缺少：详细的API用例、参数化、断言、前后置处理等专业功能

### 需要补充
- [ ] 完整的API测试模型
- [ ] API用例参数化功能
- [ ] 断言和前后置处理功能

## 6. 性能测试模块

### MangoServer功能
- 集成Locust进行性能测试
- 性能脚本执行和管理

### mango_service当前状态
-  基础性能测试模型：使用TestCase模型
-  缺少：Locust集成、性能指标收集

### 需要补充
- [ ] Locust集成
- [ ] 性能指标收集和分析

## 7. 其他功能

### MangoServer功能
- WebSocket消费者：ChatConsumer
- 完整的中间件和日志系统
- 文件上传和管理
- 数据库连接管理
- 缓存系统
- 任务调度系统（APScheduler）
- 通知系统（邮件、飞书、钉钉、企业微信）

### mango_service当前状态
-  WebSocket基础功能
-  日志系统（loguru）
-  缺少：文件管理、通知系统、完整的缓存系统

## 总结

mango_service项目已实现了MangoServer的核心功能框架，但仍需补充以下关键功能：

1. 更完整的数据模型，以匹配MangoServer的复杂业务需求
2. 文件上传和管理功能
3. 通知系统（邮件、即时通讯）
4. 更完善的用户权限和角色管理
5. 完整的API测试和UI测试功能
6. 性能测试（Locust）集成
7. 测试套件管理功能
8. 任务调度和监控功能

虽然mango_service在架构上更加现代化（使用FastAPI和异步处理），但在功能完整性方面还需要进一步补充才能完全替代MangoServer。
