# Auto UI 测试分类

`auto_ui/tests` 按是否涉及执行器分为两类：

- `domain/`：不发送执行器任务的领域规则，包括参数化、配置校验、元素自愈准出、数据脱敏和结果更新。
- `executor/`：所有会选择执行器、发送任务、接收结果或控制直播的场景。

执行器测试继续按业务边界拆分：

| 文件                                       | 覆盖范围                               |
|------------------------------------------|------------------------------------|
| `executor/test_mango_mock_lab.py`        | Mango Mock 靶场按钮、元素查找和自愈样例          |
| `executor/test_element_service.py`       | 元素检测任务创建、工作区执行器绑定、无效元素拒绝           |
| `executor/test_dispatch.py`              | 页面步骤、元素检测、Case 任务发送和 OPEN 执行器回退    |
| `executor/test_executor_slot.py`         | 同一用户槽位复用、最多 5 用户、运行/直播保护和 5 分钟空闲回收 |
| `executor/test_auth.py`                  | 自动授权浏览器启动与缓存采集                     |
| `executor/test_browser_session.py`       | 新浏览器上下文与录制浏览器任务                    |
| `executor/test_case_live.py`             | Case/页面步骤直播会话创建、启动、停止与权限           |
| `executor/test_callbacks.py`             | 元素、步骤、Case、授权的执行器结果回传              |
| `executor/live_stream/test_runtime.py`   | 实时连接、令牌、推流、控制和服务健康                 |
| `executor/live_stream/test_scenarios.py` | 多观看者、单槽位单控制页、跨槽位并行控制、工作区复用和容量拒绝    |

Mango Mock 的外部页面仅用于人工或完整链路验收。稳定定位器保存在
`executor/fixtures/mango_mock_lab.py`，单元测试不会依赖外部网络。
