## 芒果执行器客户端（MangoActuator）

**MangoActuator** 是芒果测试平台的桌面执行器，主要用于在本地或测试机上执行接口测试、UI 自动化、性能测试、Pytest 用例等任务，并将执行结果、日志、截图等信息回传到后端 `MangoServer`。

### 核心功能

- **用例执行**
  - 支持接口测试、UI 测试、Pytest 用例、性能脚本等多种测试类型。
  - 支持从服务端拉取用例并本地执行。
- **结果上报**
  - 将用例执行结果、日志、截图、视频等上传到后端。
- **图形界面**
  - 提供图形化界面（Windows / Linux）用于选择任务、查看执行进度和日志。
- **多环境支持**
  - 提供不同的依赖文件（如 `requirements.txt`、`pytest_requirements.txt`、`android_requirements.txt`、`linux_requirements.txt` 等），适配不同运行环境。

### 技术栈与结构

- **语言 / 框架**：Python 3，图形界面（如 PyQt / PySide 等，具体见 `src/pages` 实现），与后端通过 HTTP / WebSocket 通信。
- **目录结构（部分）**：
  - `main.py`：Windows 平台图形客户端入口。
  - `linux_main.py`：Linux 平台启动入口。
  - `src/`：
    - `pages/`：界面与窗口（登录、主页、设置、Pytest、UI 等）。
    - `consumer/`：与后端交互的消费者（接口、UI、Pytest、性能等）。
    - `network/`：HTTP 客户端、WebSocket 客户端等。
    - `services/`：用例执行逻辑封装（case_flow、test_case 等）。
    - `tools/`：通用工具、日志采集、消息通知等。
  - `dist/`：打包后的可执行程序（如 `芒果执行器.exe`）及运行目录。
  - `logs/`：客户端运行日志。
  - `Dockerfile`：可选的容器化构建文件（视具体使用场景）。

### 部署与安装文档

MangoActuator 的安装、依赖环境配置、启动方式及打包为可执行文件等全部内容，请统一参考官方部署教程：

- [Windows 部署教程（包含执行器部署）](http://43.142.161.61:8002/pages/%E9%83%A8%E7%BD%B2%E6%95%99%E7%A8%8B/windows.html)



