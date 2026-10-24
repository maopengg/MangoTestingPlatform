from __future__ import annotations

from src.apps.auto_ui.services.agent_execution import AgentUiExecutionService
from src.apps.auto_ui.services.agent_runtime import AgentUiRuntimeOperationService
from src.interfaces.mcp.tools.ui.helpers import _selected_env, current_user, ok


def register_agent_ui_execution_tools(mcp):
    @mcp.tool()
    def agent_ui_get_case(case_id: int, parameter_set_index: int = 0) -> dict:
        """读取 UI Case 的步骤结构和目标，不返回授权、环境或运行期敏感数据。"""
        return ok(AgentUiExecutionService.get_case(
            case_id=case_id,
            parameter_set_index=parameter_set_index,
        ))

    @mcp.tool()
    def agent_ui_create_execution(
            case_id: int,
            test_env_id: int | None = None,
            capabilities: dict | None = None,
            evidence_policy: dict | None = None,
            parameter_set_index: int = 0,
    ) -> dict:
        """生成无状态执行令牌，并一次性返回 Case 的运行步骤、上下文和浏览器授权。"""
        user = current_user()
        result = AgentUiExecutionService.create_execution(
            case_id=case_id,
            test_env=_selected_env(user.id, test_env_id),
            user_id=user.id,
            username=user.username,
            capability_manifest=capabilities,
            evidence_policy=evidence_policy,
            parameter_set_index=parameter_set_index,
        )
        return ok(result, "代理 UI 执行数据已创建")

    @mcp.tool()
    def agent_ui_execute_runtime(
            execution_token: str,
            project_product_id: int,
            request: dict,
    ) -> dict:
        """执行 Case 数据源、SQL 节点和条件分支校验；普通变量由调用方上下文管理。"""
        user = current_user()
        return ok(AgentUiRuntimeOperationService.execute(
            execution_token=execution_token,
            project_product_id=project_product_id,
            user_id=user.id,
            username=user.username,
            request=request,
        ), "代理 UI 运行操作已处理")

    @mcp.tool()
    def agent_ui_upload_artifact(
            execution_token: str,
            project_product_id: int,
            file_name: str,
            content_type: str,
            content_base64: str,
            kind: str = "screenshot",
            step_index: int | None = None,
    ) -> dict:
        """上传截图、日志或 Trace，返回可在结果回传中引用的签名 artifact_ref。"""
        user = current_user()
        return ok(AgentUiExecutionService.upload_artifact(
            execution_token=execution_token,
            project_product_id=project_product_id,
            user_id=user.id,
            file_name=file_name,
            content_type=content_type,
            content_base64=content_base64,
            kind=kind,
            step_index=step_index,
        ), "执行证据已保存")

    @mcp.tool()
    def agent_ui_report_step(
            execution_token: str,
            project_product_id: int,
            step_index: int,
            report: dict,
    ) -> dict:
        """回传一个步骤的动作、断言和证据，结果直接写入平台现有执行结果体系。"""
        user = current_user()
        return ok(AgentUiExecutionService.report_step(
            execution_token=execution_token,
            project_product_id=project_product_id,
            user_id=user.id,
            step_index=step_index,
            report=report,
        ), "步骤结果已接收")

    @mcp.tool()
    def agent_ui_complete_execution(
            execution_token: str,
            project_product_id: int,
            report: dict,
    ) -> dict:
        """提交 Case 最终结果及步骤摘要，写入平台现有 UI Case 执行结果。"""
        user = current_user()
        return ok(AgentUiExecutionService.complete_execution(
            execution_token=execution_token,
            project_product_id=project_product_id,
            user_id=user.id,
            report=report,
        ), "代理 UI 执行结果已保存")


__all__ = ["register_agent_ui_execution_tools"]
