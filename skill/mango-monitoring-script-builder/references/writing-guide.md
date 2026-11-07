# 编写与验证指南

## 工具与保存

- `create_monitoring_task(project_product_id, fields)`：`fields` 至少含 `name`、`script_content`；可配置 `description`、`test_env`、`is_notice`、`notice_group_id`。启用通知必须选择产品所在项目的通知组。
- `update_monitoring_task(monitoring_task_id, fields)`：只提交修改的字段。省略不修改；`description`、`test_env`、`notice_group_id` 可传 null 清空，但清空通知组前须同时关闭通知；名称和脚本不可清空。
- `get_monitoring_task` 回读配置及代码；`list_monitoring_tasks` 只返回轻量列表；`get_monitoring_task_logs` 返回日志、失败诊断和截断标志，不执行脚本。
- `control_monitoring_task(monitoring_task_id, action="start" | "stop")` 是唯一启停入口。启动异步交给 monitoring-service，重复启动拒绝；停止也需轮询状态确认，不直接操作服务器 PID。

新增和编辑不自动启动；新增为待执行。正在运行的旧进程不会采用新保存的代码。单纯保存、排查、修依赖不等于授权启停。

## 依赖与缺包替换

先调用 `get_monitoring_script_context`。心跳报告只覆盖平台选定的常用包，不是任意依赖安装清单。节点检测的是同一个 Python 解释器的模块位置与安装版本，不执行包导入，因此不能代替脚本运行验证；多节点版本不一致时说明差异。

常见替代思路：

| 需求 | 优先方案 | 核对事项 |
| --- | --- | --- |
| 读写 CSV | 标准库 csv | 编码、分隔符、表头、空值与类型转换 |
| 读写 xlsx | 已确认可用的 openpyxl | 工作表、公式与缓存值、日期、格式；不能把 xls 当作 xlsx |
| 简单表格筛选 | 标准库 list/dict | 原 pandas 的缺失值与数值/字符串比较语义 |
| HTTP 请求 | 已确认的 requests/httpx，或 urllib.request | 超时、状态码、JSON、重试预算与证书验证 |

不运行 pip、uv、conda、包安装脚本或动态下载代码；不修改 sys.path 借用其他虚拟环境。禁止在脚本中安装依赖或通过关闭 TLS 校验掩盖连接问题。无法等价替代时保留原功能并说明阻碍。

## 普通脚本

运行器支持普通 Python 脚本，不强制继承 MonitorBase。一次性任务可以正常结束，不必改为无限循环；输出使用 `print(..., flush=True)`。文件和网络请求必须有明确输入、工作目录与超时，勿假定文件存在于后端本机。

## 平台能力模板

需要使用任务环境、逻辑数据库或平台通知时，可继承 MonitorBase。运行器会将示例中的基类导入替换为平台基类。选择 `test_env` 后才注入 `self.test_config`、`self.domain`、`self.domains` 和逻辑数据库配置。脚本可通过 `self.get_database_config(alias)`、`self.get_database_connection(alias)` 使用用户已配置、授权的被测数据源，不硬编码连接凭据，也不读取平台自身数据库。

```python
import time
from urllib.request import urlopen
from mangotools.monitoring import MonitorBase


class HealthMonitor(MonitorBase):
    def run(self):
        if not self.domain:
            self.log_error("请先为任务选择被测环境并配置目标域名")
            return
        failures = 0
        while True:
            try:
                with urlopen(self.domain.rstrip("/") + "/health", timeout=10) as response:
                    healthy = response.status == 200
            except Exception as error:
                healthy = False
                self.log_warning("健康检查异常：" + type(error).__name__)
            failures = 0 if healthy else failures + 1
            if failures == 3:
                self.send("连续三次健康检查失败", msg="接口健康预警")
            self.log("健康检查：" + ("正常" if healthy else "异常"))
            time.sleep(30)


if __name__ == "__main__":
    HealthMonitor().start_monitoring()
```

按业务需求调整检查逻辑，不把示例固定路径当作真实接口契约。循环必须有间隔，重试有预算；通知需要阈值/去重，避免每次轮询都推送。`self.send` 受任务通知开关与通知组约束，不绕过平台自行外发消息。

使用 `self.log`、`self.log_warning`、`self.log_error` 输出业务可读日志，不输出 Cookie、Token、密码、完整连接配置或用户数据。凭据从已授权配置或环境变量读取，不写入脚本正文。

## 验证与故障定位

保存后回读确认修改，不为验证语法而执行脚本；可使用不执行代码的本地静态语法检查。只有用户明确授权运行后，才启动并检查状态、当前执行时间和日志。

- 启动请求成功不是脚本成功；须区分待启动、运行中、完成、失败。
- `ModuleNotFoundError` 应记录实际模块名，依据执行节点上报能力选择替代方案，不安装包。
- 文件缺失、日志读取失败、旧执行原因未保存不能视为无错误。失败诊断可来自监控报告表；完整日志在多实例部署时仍依赖共享目录。
- 任务已运行不意味着业务检查成功；确认至少一轮检查和预期输出。不要为验证通知而擅自发送测试告警。
