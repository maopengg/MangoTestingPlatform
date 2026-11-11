from __future__ import annotations

from typing import Literal

from mangotools.enums import StatusEnum

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceSourceType, ApiCaseTraceStepType
from src.apps.auto_api.schemas.resource_cleanup import (
    ApiResourceEsIdentityMapping, ApiResourceChildMapping, ApiResourceRejectionRecovery,
)
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_case.batch_execution import ApiCaseBatchExecutionService
from src.apps.auto_api.services.test_case.test_case import TestCase
from src.apps.test_center.services.execution_result import ExecutionResultService
from src.common.exceptions import MangoServerError
from src.interfaces.mcp.common import (
    current_user,
    fail,
    ok,
)
from ..helper_parts.case_result import (
    _api_case_step_result_items,
    _case_tree,
)
from ..helper_parts.execution import (
    _selected_env,
)


def register_case_execution_tools(mcp):
    @mcp.tool()
    def get_api_case_resource_cleanup_schema() -> dict:
        """获取API创建资源清理规则格式。通过update_api_case.resource_cleanup保存，随Case修订冻结。

        仅test/dev。先创建Case与步骤；触发步骤单场景且不重试。创建请求的唯一名称需引用
        ${{api_resource_<key>}}；身份来源为本轮租户、创建人缓存。响应ID、groupId及版本分别映射。
        SQL只接受已保存的表/字段规则，不接受自由SQL。自动清理失败会使Case不能通过；重试只处理原台账。
        ES数组可使用projects[].projectId与projects[].projectVersion，必须同一数组且仅含本轮唯一对象。
        负向创建需显式配置rejection_response={"success":false}；有创建ID仍登记清理，拒绝后完整观察无新增。
        name_source_key仅复用同执行前序资源的名称；同名意外创建的新记录单独登记，原资源不被接管。
        version_updates登记同执行后续写步骤：请求必须引用原业务ID，响应必须返回相同ID及新版本，
        SQL回读须一致，才能为清理采用该版本；不自动采用数据库当前版本。
        """
        from src.apps.auto_api.schemas.resource_cleanup import ApiResourceCleanupRules
        return ok(ApiResourceCleanupRules.model_json_schema())

    @mcp.tool()
    def get_api_case_resource_cleanup_results(case_id: int, trace_id: str | None = None, resource_id: int | None = None,
                                             page: int = 1, page_size: int = 10) -> dict:
        """分页查询API资源清理台账；resource_id可读取单项冻结规则和所有权证据，不返回凭据或业务响应正文。"""
        from src.apps.auto_api.selectors.resource_cleanup import ApiResourceCleanupSelector
        return ok(ApiResourceCleanupSelector.results(user=current_user(), case_id=case_id, trace_id=trace_id, resource_id=resource_id,
                                                     page=page, page_size=page_size))

    @mcp.tool()
    def cleanup_api_case_resources(case_id: int, resource_id: int, preview: bool = True,
                                  identity_mapping: ApiResourceEsIdentityMapping | None = None,
                                  child_mapping: list[ApiResourceChildMapping] | None = None,
                                  rejection_recovery: ApiResourceRejectionRecovery | None = None) -> dict:
        """预览或重试指定原执行资源清理，默认仅预览；preview=false才清理。

        原执行必须已结束或有进程替换证据。只使用原冻结的环境、规则及所有权证据，
        不重新执行业务创建，不按名称前缀发现目标，不修改历史业务断言为通过。
        identity_mapping仅可更正es_business_id_path、es_version_path，例如projects[].projectId及
        projects[].projectVersion；先preview=true核验SQL与ES身份，再实际清理。原冻结目标不变，
        更正单独记录操作者及时间；数组必须仅含本轮唯一对象，不支持删除共享文档。
        child_mapping只可将原快照中已不存在的附属表映射到当前真实表及外键字段，
        原租户、根身份、数据源及行数上限均不变；先预览验证，原快照不覆盖。
        rejection_recovery仅补核历史明确拒绝契约，如{"rejection_response":{"success":false}}。
        必须有原执行已结束、完整结果校验和、精确步骤请求及拒绝响应证据；仍执行完整无新增观察，
        不接受调用者自报“已拒绝/已清理”，不覆盖原规则或把业务失败改为通过。
        """
        from src.apps.auto_api.services.resource_cleanup import ApiResourceCleanupRetryService
        return ok(ApiResourceCleanupRetryService.retry(user=current_user(), case_id=case_id,
                                                       resource_id=resource_id, preview=preview,
                                                       identity_mapping=identity_mapping, child_mapping=child_mapping,
                                                       rejection_recovery=rejection_recovery))

    @mcp.tool()
    def run_api_case(
            case_id: int,
            test_env_id: int | None = None,
            case_sort: int | None = None,
            user_id: int | None = None,
            revision_id: int | None = None,
            release_id: int | None = None,
    ) -> dict:
        """执行 API case。

        默认不传 revision_id/release_id 时，执行当前编辑态，适合 MCP 创建、修改、调试和临时验证。
        如果需要验证某个不可变历史修订或正式发布版本，再显式传 revision_id 或 release_id。
        发布版本用于上线/正式执行链路，不是调试执行的前置条件。
        """
        try:
            user = current_user(user_id)
            env_id = _selected_env(user.id, test_env_id)
            runner = TestCase(
                user_id=user.id,
                test_env=env_id,
                case_id=case_id,
                trace_source_type=ApiCaseTraceSourceType.MCP,
                revision_id=revision_id,
                release_id=release_id,
            )
            run_result = runner.test_case(case_sort).model_dump()
            effective_revision_id = run_result.get("case_revision_id")
            effective_release_id = run_result.get("case_release_id")
            with runner.trace_recorder.guard(ApiCaseTraceStepType.REPORT_WRITE.value):
                execution_result = ExecutionResultService.save_result(
                    source_type=ExecutionResultService.SOURCE_MCP,
                    target_type=ExecutionResultService.TARGET_API_CASE,
                    target_id=case_id,
                    revision_id=effective_revision_id,
                    release_id=effective_release_id,
                    test_env=env_id,
                    status=run_result.get("status"),
                    error_message=run_result.get("error_message"),
                    result_data=run_result,
                    trigger_user_id=user.id,
                    trace_id=run_result.get("trace_id"),
                )
        except MangoServerError as exc:
            return fail(exc.msg, "API_CASE_RUN_FAILED")
        payload = {
            "case_id": case_id,
            "test_env_id": env_id,
            "case_sort": case_sort,
            "revision_id": effective_revision_id,
            "release_id": effective_release_id,
            "version_label": run_result.get("version_label"),
            "execution_result_id": execution_result.id,
            "run_result": run_result,
            "result_query_tool": "get_api_case_run_result",
        }
        if StatusEnum.SUCCESS.value != run_result.get("status"):
            return fail(run_result.get("error_message") or "API case 执行失败", "API_CASE_RUN_FAILED", payload)
        return ok(
            payload,
            "API case 执行完成",
        )

    @mcp.tool()
    def debug_api_case_step(
            case_id: int,
            case_detailed_id: int,
            test_env_id: int | None = None,
            context_id: str | None = None,
            user_id: int | None = None,
    ) -> dict:
        """只调试 API case 的一个步骤，并自动复用前置步骤已生成的缓存。

        case_detailed_id 来自 list_api_case_steps 的 step_id。第一个步骤会执行用例前置并创建 context_id；
        后续步骤传入上一次返回的 context_id，即可恢复前一步累计缓存后只执行当前步骤，不会重复执行前面的接口。
        未传 context_id 时，后端会尝试查找同一用户、同一环境两小时内最新且完整的调试上下文。
        前置步骤必须全部成功；重跑前置步骤后，旧的后续步骤快照会自动失效。参数化 API case 暂不支持单步调试。
        """
        try:
            user = current_user(user_id)
            env_id = _selected_env(user.id, test_env_id)
            runner = TestCase(
                user_id=user.id,
                test_env=env_id,
                case_id=case_id,
                trace_source_type=ApiCaseTraceSourceType.MCP,
                update_case_status=False,
            )
            run_result = runner.debug_step(
                case_detailed_id=case_detailed_id,
                context_id=context_id,
            ).model_dump()
            payload = {
                "case_id": case_id,
                "case_detailed_id": case_detailed_id,
                "test_env_id": env_id,
                **runner.debug_context_payload(),
                "run_result": run_result,
                "result_query_tool": "get_api_case_step_result",
            }
        except MangoServerError as exc:
            return fail(
                exc.msg,
                f"API_CASE_STEP_DEBUG_{exc.code}",
                {
                    "case_id": case_id,
                    "case_detailed_id": case_detailed_id,
                    "test_env_id": test_env_id,
                    "context_id": context_id,
                },
            )
        if StatusEnum.SUCCESS.value != run_result.get("status"):
            return fail(
                run_result.get("error_message") or "API case 当前步骤调试失败",
                "API_CASE_STEP_DEBUG_FAILED",
                payload,
            )
        return ok(payload, "API case 当前步骤调试完成")

    @mcp.tool()
    def run_api_case_batch(
            case_ids: list[int],
            execution_name: str,
            test_env_id: int,
            execution_version: Literal["editing", "prepublished", "published"],
            api_concurrency_limit: int | None = None,
    ) -> dict:
        """批量执行 API case 并生成测试报告。

        test_env_id 必须显式传入，不使用用户默认环境。execution_name 是本次执行名称，
        写入测试报告。execution_version 必须选择 editing、prepublished 或 published：
        editing 会统一冻结并执行所有 Case 的当前编辑态，不改变发布状态；
        prepublished 固定执行待审核修订；存在没有预发布候选的 Case 时整体拒绝，不回退编辑态；
        published 会统一执行当前发布版本，只要存在尚未发布的 Case 就整体拒绝创建报告。
        api_concurrency_limit 可不传，
        不传时使用当前平台 API 最大执行容量，传入时必须为 1 到平台最大容量之间的整数。
        本次报告的执行人自动使用当前 MCP 鉴权用户，不支持指定其他用户。
        """
        try:
            user = current_user()
            result = ApiCaseBatchExecutionService.execute(
                case_ids=case_ids,
                execution_name=execution_name,
                test_env=test_env_id,
                execution_version=execution_version,
                user_id=user.id,
                api_concurrency_limit=api_concurrency_limit,
            )
        except Exception as exc:
            return fail(str(exc), "API_CASE_BATCH_RUN_FAILED")
        result["test_env_id"] = result["test_env"]
        result["versions"] = result["executions"]
        result["result_query_tool"] = "get_test_report_detail"
        return ok(
            result,
            "API case 批量异步执行任务创建成功",
        )

    @mcp.tool()
    def get_api_case_run_result(case_id: int) -> dict:
        """查询 API case 最近一次执行结果，包括步骤和场景 result_data。"""
        return ok(_case_tree(case_id, include_result_data=True))

    @mcp.tool()
    def get_api_case_callback_results(case_id: int, trace_id: str | None = None,
                                      run_id: int | None = None, page: int = 1, page_size: int = 10,
                                      trigger_step_key: str | None = None) -> dict:
        """分页查询 Case 回调验证结果。trace_id 限定某次执行，trigger_step_key（step-ID）限定触发步骤；返回事件数、投递数、验证状态，不返回密钥或原始报文。"""
        from src.apps.auto_api.selectors.callback import ApiCallbackSelector
        from src.interfaces.mcp.common import current_user
        return ok(ApiCallbackSelector.results(user=current_user(), case_id=case_id, trace_id=trace_id,
                                              run_id=run_id, trigger_step_key=trigger_step_key,
                                              page=max(1, page), page_size=max(1, min(100, page_size))))

    @mcp.tool()
    def get_api_case_callback_deliveries(case_id: int, run_id: int, page: int = 1, page_size: int = 10) -> dict:
        """分页查询一次回调验证的投递与检查结果，不返回原始正文和秘密。使用页面详情查看原始证据。"""
        from src.apps.auto_api.selectors.callback import ApiCallbackSelector
        from src.interfaces.mcp.common import current_user
        return ok(ApiCallbackSelector.deliveries(user=current_user(), case_id=case_id, run_id=run_id,
                                                 page=max(1, page), page_size=max(1, min(100, page_size))))

    @mcp.tool()
    def get_api_case_step_result(
            case_id: int,
            step_id: int | None = None,
            scenario_id: int | None = None,
            step_name: str | None = None,
            json_path: str | None = None,
            sample_limit: int = 5,
            export_full: bool = False,
    ) -> dict:
        """精确查询 API case 最近一次执行结果中的某一步/某场景。

        json_path 支持点路径或简单 JSONPath，例如 response.json.data.result、$.response.json.data.result、response.sse_events[0]。
        返回会包含命中值类型、count、sample 和是否截断；适合统计大响应，不需要拉取完整 case tree。
        export_full=True 时会把每个命中的完整值导出为 JSON 文件并返回 download_url；传 json_path 时只导出该路径命中的值，不传则导出场景完整 result_data。导出文件保存 7 天后自动清理。
        """
        if sample_limit < 1:
            sample_limit = 1
        if sample_limit > 20:
            sample_limit = 20
        data = _api_case_step_result_items(
            case_id=case_id,
            step_id=step_id,
            scenario_id=scenario_id,
            step_name=step_name,
            json_path=json_path,
            sample_limit=sample_limit,
            export_full=export_full,
        )
        return ok(data)

    @mcp.tool()
    def get_api_case_execution_trace(
            trace_id: str | None = None,
            test_suite_detail_id: int | None = None,
            include_list: bool = False,
    ) -> dict:
        """查询 API case 执行链路。trace_id 精确查询；test_suite_detail_id 默认返回最新一条，可用 include_list 返回最近 trace 列表。"""
        if not trace_id and not test_suite_detail_id:
            return fail("trace_id 和 test_suite_detail_id 至少传一个。", "TRACE_QUERY_ARGUMENT_REQUIRED")
        from src.apps.auto_api.services.execution_trace.builder import ApiCaseExecutionTraceBuilder

        return ok(ApiCaseExecutionTraceBuilder.get_trace_data(
            trace_id=trace_id,
            test_suite_detail_id=test_suite_detail_id,
            include_list=include_list,
        ))

    @mcp.tool()
    def analyze_api_case_failure(case_id: int, step_id: int | None = None, scenario_id: int | None = None) -> dict:
        """基于最近一次执行结果分析 API case 失败原因。"""
        parameters = ApiQuerySelector.api_case_detailed_parameter().filter(case_detailed__case_id=case_id)
        if step_id is not None:
            parameters = parameters.filter(case_detailed_id=step_id)
        if scenario_id is not None:
            parameters = parameters.filter(id=scenario_id)
        evidence = []
        suggestions = []
        failure_type = "unknown"
        for parameter in parameters:
            result_data = ExecutionResultService.latest_api_case_parameter_result(
                case_id=case_id,
                parameter_id=parameter.id,
            )
            error_message = result_data.get("error_message") or ""
            response = result_data.get("response") or {}
            request = result_data.get("request") or {}
            status = parameter.status
            if status == 1 and not error_message:
                continue
            if error_message:
                evidence.append(f"scenario={parameter.name}, error={error_message}")
            if response.get("code"):
                evidence.append(f"scenario={parameter.name}, response.code={response.get('code')}")
            if response.get("code") in [401, 403]:
                failure_type = "auth_error"
                suggestions.append("检查 Authorization/Cookie 等认证请求头是否已创建并绑定到用例或场景")
            if request and not request.get("headers"):
                suggestions.append(
                    "当前请求没有请求头，必要时调用 create_api_header 并绑定 front_headers 或 scenario.headers")
        if not evidence:
            return ok(
                {
                    "summary": "未发现失败场景，最近一次结果可能为成功或尚未执行",
                    "failure_type": "none",
                    "evidence": [],
                    "suggestions": [],
                }
            )
        return ok(
            {
                "summary": evidence[0],
                "failure_type": failure_type,
                "evidence": evidence,
                "suggestions": list(dict.fromkeys(suggestions)),
            }
        )
