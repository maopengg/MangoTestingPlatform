## 芒果测试平台后端（MangoServer）

芒果测试平台后端基于 **Django** 构建，提供接口测试、UI 测试、性能测试、Pytest 用例管理、定时任务、预警监控等一整套自动化测试管理与执行能力，对外通过 REST API 和 WebSocket 为前端 `mango-console` 以及桌面执行器 `MangoActuator` 提供服务。

### 核心功能

- **接口测试管理（`auto_api`）**：接口用例、用例集、参数化、断言、执行记录等。
- **UI 自动化测试（`auto_ui`）**：页面元素、用例步骤、用例集配置与执行。
- **Pytest 集成（`auto_pytest`）**：Pytest 用例编排、执行结果上报与展示。
- **性能测试（`auto_perf`）**：性能脚本管理与运行结果收集。
- **系统配置与通知（`auto_system`）**：项目 / 产品、通知组、计划任务等基础配置。
- **用户与权限（`auto_user`）**：用户、角色、权限控制。
- **预警监控（`monitoring`）**：
  - 监控任务管理（脚本上传 / 在线编辑、启动 / 停止、实时日志）。
  - 预警监控报告记录与统计，联动通知组发送告警。

### 技术栈与结构

- **语言 / 框架**：Python 3、Django、Django REST Framework、APScheduler。
- **目录结构（部分）**：
  - `manage.py`：Django 管理命令入口。
  - `src/`：Django 项目代码根目录。
    - `auto_test/`：业务应用（接口、UI、Pytest、性能、系统、用户、监控等）。
    - `enums/`：统一枚举定义（任务状态、日志级别等）。
    - `tools/`：通用工具（装饰器、统一响应、进程工具等）。
  - `requirements.txt`：后端依赖。
  - `Dockerfile`：后端容器化构建文件。

### 部署与安装文档

本项目的所有部署、安装及启动流程，请统一参考官方文档：

- **Windows 部署教程**（包含后端 `MangoServer`、前端 `mango-console`、执行器 `MangoActuator` 的完整部署步骤）：  
  [http://43.142.161.61:8002/pages/%E9%83%A8%E7%BD%B2%E6%95%99%E7%A8%8B/windows.html](http://43.142.161.61:8002/pages/%E9%83%A8%E7%BD%B2%E6%95%99%E7%A8%8B/windows.html)



