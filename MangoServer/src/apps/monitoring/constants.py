TASK_DIAGNOSTIC_MESSAGE = '监控任务运行诊断'

# 常用依赖探测白名单，不是完整环境清单；键为导入模块，值为分发包名。
SCRIPT_DEPENDENCIES = (
    ('requests', 'requests'), ('httpx', 'httpx'), ('openpyxl', 'openpyxl'), ('mangotools', 'mangotools'),
)
