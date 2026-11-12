from typing import Literal

from src.apps.monitoring.presenters import task_data
from src.apps.monitoring.schemas.task import MonitoringTaskCreate, MonitoringTaskPatch
from src.apps.monitoring.selectors.task import MonitoringTaskSelector
from src.apps.monitoring.selectors.script_context import MonitoringScriptContextSelector
from src.apps.monitoring.services.tasks.task_mutation import MonitoringTaskMutationService
from src.apps.monitoring.services.logging.task_log import MonitoringTaskLogService
from src.interfaces.mcp.common import current_user, ok, paginate_queryset


def register_monitoring_tools(mcp):
    @mcp.tool()
    def get_monitoring_script_context() -> dict:
        """编写或修改监控脚本前调用。返回 Skill 入口、monitoring 执行节点心跳上报的常用依赖版本和生效规则；不是 MCP 本机依赖清单。依赖结果 null 表示未确认，不代表支持或缺包；无在线节点、旧节点未上报时不可宣称已验证。随后通过 get_mcp_skill 读取 mango-monitoring-script-builder 及所需 references；禁止安装新依赖。"""
        return ok(MonitoringScriptContextSelector.get())

    @mcp.tool()
    def list_monitoring_tasks(project_product_id: int | None = None, keyword: str | None = None,
                              page: int = 1, page_size: int = 10) -> dict:
        """分页查看有权访问的预警监控脚本任务，不返回脚本正文和服务器路径。"""
        queryset = MonitoringTaskSelector.visible(current_user())
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if keyword:
            queryset = queryset.filter(name__icontains=keyword)
        rows, count, page, page_size = paginate_queryset(queryset.defer('script_content').order_by('-id'), page, page_size, 100)
        return ok({'items': [task_data(row) for row in rows], 'count': count, 'page': page, 'page_size': page_size})

    @mcp.tool()
    def get_monitoring_task(monitoring_task_id: int) -> dict:
        """查看监控任务配置及脚本正文；不启动脚本。"""
        return ok(task_data(MonitoringTaskSelector.get(current_user(), monitoring_task_id), include_script=True))

    @mcp.tool()
    def create_monitoring_task(project_product_id: int, fields: MonitoringTaskCreate) -> dict:
        """新增 Python 监控脚本。先调用 get_monitoring_script_context，并通过 get_mcp_skill 读取 mango-monitoring-script-builder 及编写指南。只使用已确认依赖或标准库，不安装新包；保存为待执行、不自动启动，勿写入凭据。"""
        return ok(task_data(MonitoringTaskMutationService.create(current_user(), project_product_id, fields)))

    @mcp.tool()
    def update_monitoring_task(monitoring_task_id: int, fields: MonitoringTaskPatch) -> dict:
        """编辑前先 get_monitoring_task 回读原配置、get_monitoring_script_context 核实依赖，并通过 get_mcp_skill 读取 mango-monitoring-script-builder。省略字段不修改，禁止安装新包，不允许修改路径/PID/状态。运行中的脚本需用户授权停止再启动才使用新代码。"""
        return ok(task_data(MonitoringTaskMutationService.update(current_user(), monitoring_task_id, fields)))

    @mcp.tool()
    def get_monitoring_task_logs(monitoring_task_id: int, limit: int = 200) -> dict:
        """读取任务日志尾部（最多1000行/64KiB），本机文件缺失时展示已保存的失败诊断或缺失提示；不启动任务。"""
        return ok(MonitoringTaskLogService.tail(current_user(), monitoring_task_id, limit))

    @mcp.tool()
    def control_monitoring_task(monitoring_task_id: int, action: Literal['start', 'stop']) -> dict:
        """统一启停监控脚本：action=start 请求异步启动（要求服务在线，拒绝重复启动）；action=stop 请求异步停止。不由 MCP 本机执行脚本或杀进程。"""
        operation = MonitoringTaskMutationService.start if action == 'start' else MonitoringTaskMutationService.stop
        return ok(task_data(operation(current_user(), monitoring_task_id)))
