# 芒果执行器

MangoActuator 是芒果测试平台的统一执行器。同一套核心代码可按机器用途安装不同能力依赖，支持 Pytest、Web UI、Android UI、iOS UI 和性能测试；来源 API 不作为独立执行器能力。

## 目录约定

根目录只保留当前启动入口、README 和 Git/Docker 必需的隐藏配置文件：

```text
MangoActuator/
├── desktop_main.py            # 带 tkinter 图形界面的桌面入口
├── headless_main.py           # 不带桌面界面的服务入口
├── README.md
├── assets/                   # 图标、图片等静态资源
├── config/                   # 能力协议与安装预设配置
├── deploy/docker/            # 容器构建文件
├── deploy/packages/          # 容器离线安装包（当前包含双架构 k6）
├── requirements/             # 按运行环境和能力分类的 Python 依赖
├── scripts/                  # 安装、诊断、构建和启动脚本
├── local_packages/           # 项目内部 Python wheel
├── src/                      # 执行器业务代码
└── tests/                    # 自动化测试
```

执行器核心版本只在 `src/settings/settings.json` 的 `version` 中维护。能力预设不会生成另一套版本号。

## 依赖文件

| 文件 | 用途 |
| --- | --- |
| `requirements/desktop.txt` | Windows tkinter 桌面基础依赖 |
| `requirements/desktop-local.txt` | 桌面端内部包 |
| `requirements/linux.txt` | Linux、macOS、容器基础依赖 |
| `requirements/linux-local.txt` | 无桌面 UI 的服务型执行器内部包 |
| `requirements/pytest.txt` | Pytest 能力 |
| `requirements/android.txt` | Android UI 能力 |
| `requirements/ios.txt` | iOS UI 能力，仅 macOS 可用 |

建议在执行器目录中创建独立虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
```

Windows PowerShell 对应的 Python 路径为 `.venv\Scripts\python.exe`。

## Windows 桌面执行器

安装 tkinter 桌面端基础依赖和内部包：

```powershell
.venv\Scripts\python.exe -m pip install -r requirements/desktop.txt
.venv\Scripts\python.exe -m pip install --force-reinstall -r requirements/desktop-local.txt
.venv\Scripts\python.exe desktop_main.py
```

构建 Windows 可执行文件：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows_tk.ps1
```

也可以直接使用统一的跨平台打包入口：

```bash
.venv/bin/python desktop_main.py --build
```

产物输出到 `dist/`，临时构建文件输出到 `runtime/pyinstaller/`。Windows 生成单文件 `.exe`，macOS 生成 `.app` 应用包。

## Linux、macOS 基础环境

所有无界面执行器先安装基础依赖：

```bash
.venv/bin/python -m pip install -r requirements/linux.txt
.venv/bin/python -m pip install --force-reinstall -r requirements/linux-local.txt
```

然后根据用途安装一个能力预设。安装脚本会写入本机 `runtime/capabilities.json`，不会修改服务端数据库。

## 能力预设安装

查看预设和检查本机能力：

```bash
.venv/bin/python scripts/manage_capabilities.py list
.venv/bin/python scripts/manage_capabilities.py doctor
```

### Pytest 执行器

```bash
.venv/bin/python scripts/manage_capabilities.py install pytest
.venv/bin/python headless_main.py --profile pytest
```

### 标准执行器

标准预设包含 Pytest、Web UI 和性能测试。脚本会安装 Pytest 依赖、Chromium 和固定版本 k6：

```bash
.venv/bin/python scripts/manage_capabilities.py install standard
.venv/bin/python headless_main.py --profile standard
```

### Android 执行器

Android 预设包含标准能力和 Android UI：

```bash
.venv/bin/python scripts/manage_capabilities.py install android
.venv/bin/python headless_main.py --profile android
```

Android 机器还需要预先安装并配置 ADB、Android SDK 和目标设备。

### 全能力执行器

`full` 会安装当前操作系统支持的全部能力；iOS UI 会在非 macOS 系统上自动跳过：

```bash
.venv/bin/python scripts/manage_capabilities.py install full
.venv/bin/python headless_main.py --profile full
```

iOS 机器还需要 Xcode、WebDriverAgent、Appium 运行环境和已授权设备。

### 自定义能力组合

能力编码可以任意组合：

```bash
.venv/bin/python scripts/manage_capabilities.py install perf web_ui
.venv/bin/python headless_main.py --profile custom --capabilities perf,web_ui
```

可用能力编码：`pytest`、`web_ui`、`android_ui`、`ios_ui`、`perf`。

## Docker 部署

标准执行器镜像：

```bash
docker build \
  --build-arg ACTUATOR_PROFILE=standard \
  -f deploy/docker/Dockerfile \
  -t mango-actuator:standard .
```

Android 执行器镜像：

```bash
docker build \
  --build-arg ACTUATOR_PROFILE=android \
  -f deploy/docker/Dockerfile \
  -t mango-actuator:android .
```

容器直接运行 `headless_main.py`。Linux `amd64`、`arm64` 的固定版本 k6 安装包保存在
`deploy/packages/k6/`，构建时按目标架构直接安装，不会访问 Docker Hub 或在容器启动时临时下载。

### 容器直播显示环境

镜像显式安装 `xvfb`、`xauth`、`x11-utils`，构建时通过 `xvfb-run` 和
`xdpyinfo` 验证虚拟屏幕可用。直接运行 `headless_main.py` 即可：Linux 无
`DISPLAY` 时自动使用 `xvfb-run` 启动，不需要在部署命令外再包装一次。

- 启动时实际检查显示连接，日志会明确输出“直播显示环境可用/不可用”和原因。
- `ACTUATOR_XVFB_SCREEN` 默认 `1440x900x24`，可调整虚拟屏幕尺寸。
- `ACTUATOR_DISABLE_XVFB_BOOTSTRAP=1` 显式禁止自动创建显示环境；没有可用的外部
  `DISPLAY` 时不提供直播，但不阻止其他能力启动。一般容器部署不要设置为 `1`。
- 已配置 `DISPLAY` 时复用并检查该显示环境，不再创建第二个虚拟屏幕。
- Compose 已设置 `init: true`；使用独立 `docker run` 时请加 `--init`，用于信号转发和子进程回收。

显示检查通过只代表执行器具备本机直播条件；连接平台仍需服务地址、鉴权和实时服务链路正常。

## 安装原则

- 核心代码版本由 `src/settings/settings.json` 统一控制。
- `config/capabilities.lock.json` 只管理能力协议、依赖文件和安装预设。
- 安装预设决定本机准备哪些依赖，运行时仍以真实探测结果为准。
- 未就绪的能力不会影响其他能力启动，也不应领取对应任务。
- 性能测试使用 k6，不再使用 Locust。

## 帮助文档

[Windows/macOS 部署教程](http://160.202.231.91:36696/pages/%E9%83%A8%E7%BD%B2%E6%95%99%E7%A8%8B/windows.html)
