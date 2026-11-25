from __future__ import annotations

from django.db import transaction

from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_case.mutation_io import ApiCaseMutationService
from src.apps.auto_api.services.api_case.step import ApiCaseStepService
from src.apps.auto_api.services.api_info.mutation import ApiInfoMutationService
from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
from src.interfaces.mcp.common import create_dangerous_action_preview, current_user, ok
from .helper_parts.impact import (
    _api_case_delete_impact,
    _api_case_revision_delete_impact,
    _api_case_scenario_delete_impact,
    _api_case_step_delete_impact,
)
from .helpers import (
    ApiCaseRevisionService,
    MangoServerError,
    fail,
    validate_dangerous_action_confirmation,
)
from .helpers import _api_info_delete_impact, _api_info_revision_delete_impact


def register_delete_tools(mcp):
    @mcp.tool()
    def preview_delete_api_info_impact(api_info_id: int) -> dict:
        """预览删除 API 接口定义的影响。删除属于危险操作，必须先预览，再由用户二次确认。"""
        api_info = ApiQuerySelector.api_info().get(id=api_info_id)
        confirm_text = f"DELETE_API_INFO:{api_info_id}:{api_info.name}"
        return ok(
            create_dangerous_action_preview(
                "delete_api_info",
                api_info_id,
                confirm_text,
                _api_info_delete_impact(api_info_id),
            ),
            "已生成 API 接口定义删除影响预览，请二次确认后删除",
        )

    @mcp.tool()
    def delete_api_info(
            api_info_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """确认后删除 API 接口定义。

        必须先调用 preview_delete_api_info_impact。确认后只删除 ApiInfo 接口定义；
        如果接口定义已被 API case 步骤绑定，删除会被阻止并返回绑定 case/步骤信息。
        """
        error = validate_dangerous_action_confirmation("delete_api_info", api_info_id, preview_token, confirm_text)
        if error:
            return error
        try:
            with transaction.atomic():
                before = _api_info_delete_impact(api_info_id)
                if not before.get("can_delete"):
                    return fail(
                        "接口定义仍被当前编辑态步骤或旧版 Case 快照引用，不能删除。",
                        "DELETE_API_INFO_BLOCKED",
                        before,
                    )
                ApiInfoMutationService.delete_definition(api_info_id)
        except MangoServerError as exc:
            return fail(exc.msg, "DELETE_API_INFO_FAILED", {"code": exc.code})
        return ok({"api_info_id": api_info_id, "deleted": before.get("will_delete", {})}, "API 接口定义删除成功")

    @mcp.tool()
    def preview_delete_api_info_revision_impact(api_info_id: int, revision_id: int) -> dict:
        """预览删除 API 接口未发布修订的影响，并生成确认 token。"""
        revision = ApiQuerySelector.api_info_revision().get(id=revision_id, api_info_id=api_info_id)
        confirm_text = f"DELETE_API_INFO_REVISION:{api_info_id}:r{revision.revision_no}"
        return ok(
            create_dangerous_action_preview(
                "delete_api_info_revision",
                revision_id,
                confirm_text,
                _api_info_revision_delete_impact(api_info_id, revision_id),
            ),
            "已生成 API 接口修订删除影响预览，请二次确认后删除",
        )

    @mcp.tool()
    def delete_api_info_revision(
            api_info_id: int,
            revision_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """删除 API 接口未发布修订。必须先调用 preview_delete_api_info_revision_impact。

        已发布、被 API Case 步骤固定引用或存在后续子修订的修订不能删除。
        """
        error = validate_dangerous_action_confirmation(
            "delete_api_info_revision",
            revision_id,
            preview_token,
            confirm_text,
        )
        if error:
            return error
        try:
            with transaction.atomic():
                before = _api_info_revision_delete_impact(api_info_id, revision_id)
                if not before.get("can_delete"):
                    return fail(
                        "该接口修订存在发布、固定引用或后续子修订，不能删除。",
                        "DELETE_API_INFO_REVISION_BLOCKED",
                        before,
                    )
                deleted = ApiInfoRevisionService.delete_unpublished_revision(api_info_id, revision_id)
        except MangoServerError as exc:
            return fail(exc.msg, "DELETE_API_INFO_REVISION_FAILED", {"code": exc.code})
        except Exception as exc:
            return fail(str(exc), "DELETE_API_INFO_REVISION_FAILED")
        return ok({"api_info_id": api_info_id, **deleted}, "API 接口修订删除成功")

    @mcp.tool()
    def preview_delete_api_case_impact(case_id: int) -> dict:
        """预览删除 API case 的影响。删除属于危险操作，必须先预览，再由用户二次确认。"""
        return ok(
            create_dangerous_action_preview(
                "delete_api_case",
                case_id,
                f"DELETE_API_CASE:{case_id}",
                _api_case_delete_impact(case_id),
            ),
            "已生成 API case 删除影响预览",
        )

    @mcp.tool()
    def delete_api_case(
            case_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """确认后删除 API case。

        必须先调用 preview_delete_api_case_impact。确认后删除 API case、版本数据及已清理并验证的附属资源台账，不再次删除被测数据；
        已结束回调及对应投递记录也随 Case 删除；尚未完成清理的资源或等待中的回调会阻止删除。
        如果仍有步骤、场景或定时任务绑定，删除会被阻止，需要用户先手动删除页面可见的关联数据。
        """
        error = validate_dangerous_action_confirmation("delete_api_case", case_id, preview_token, confirm_text)
        if error:
            return error
        try:
            with transaction.atomic():
                before = _api_case_delete_impact(case_id)
                if not before.get("can_delete"):
                    return fail(
                        "；".join(before.get("blockers") or ["API case 仍有关联数据，请先处理后再删除。"]),
                        "DELETE_API_CASE_BLOCKED",
                        before,
                    )
                ApiCaseMutationService.delete(case_id)
        except Exception as exc:
            return fail(str(exc), "DELETE_API_CASE_FAILED")
        return ok({"case_id": case_id, "deleted": before.get("will_delete", {})}, "API case 删除成功")

    @mcp.tool()
    def preview_delete_api_case_revision_impact(case_id: int, revision_id: int) -> dict:
        """预览删除 API Case 未发布修订的影响，并生成确认 token。"""
        revision = ApiQuerySelector.api_case_revision().get(id=revision_id, api_case_id=case_id)
        confirm_text = f"DELETE_API_CASE_REVISION:{case_id}:r{revision.revision_no}"
        return ok(
            create_dangerous_action_preview(
                "delete_api_case_revision",
                revision_id,
                confirm_text,
                _api_case_revision_delete_impact(case_id, revision_id),
            ),
            "已生成 API Case 修订删除影响预览，请二次确认后删除",
        )

    @mcp.tool()
    def delete_api_case_revision(
            case_id: int,
            revision_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """删除 API Case 未发布修订。必须先调用 preview_delete_api_case_revision_impact。

        已发布、存在后续子修订或被定时任务绑定的修订不能删除。
        历史测试报告不会阻止删除，删除时会解除其修订引用。
        """
        error = validate_dangerous_action_confirmation(
            "delete_api_case_revision",
            revision_id,
            preview_token,
            confirm_text,
        )
        if error:
            return error
        try:
            with transaction.atomic():
                before = _api_case_revision_delete_impact(case_id, revision_id)
                if not before.get("can_delete"):
                    return fail(
                        "该 API Case 修订存在发布、后续子修订或定时任务绑定，不能删除。",
                        "DELETE_API_CASE_REVISION_BLOCKED",
                        before,
                    )
                deleted = ApiCaseRevisionService.delete_unpublished_revision(case_id, revision_id)
        except MangoServerError as exc:
            return fail(exc.msg, "DELETE_API_CASE_REVISION_FAILED", {"code": exc.code})
        except Exception as exc:
            return fail(str(exc), "DELETE_API_CASE_REVISION_FAILED")
        return ok({"case_id": case_id, **deleted}, "API Case 修订删除成功")

    @mcp.tool()
    def preview_delete_api_case_step_impact(step_id: int) -> dict:
        """预览删除 API Case 接口步骤的影响，并生成确认 token。

        更换步骤绑定接口时必须使用“删除旧步骤 -> 新增目标接口 -> 排序”的流程，不要直接修改 step.api_info。
        """
        step = ApiQuerySelector.api_case_detailed().select_related("api_info").get(id=step_id)
        api_name = step.api_info.name if step.api_info else ""
        confirm_text = f"DELETE_API_CASE_STEP:{step_id}:{api_name}"
        return ok(
            create_dangerous_action_preview(
                "delete_api_case_step",
                step_id,
                confirm_text,
                _api_case_step_delete_impact(step_id),
            ),
            "已生成 API Case 步骤删除影响预览，请二次确认后删除",
        )

    @mcp.tool()
    def delete_api_case_step(
            step_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """删除 API Case 接口步骤。必须先调用 preview_delete_api_case_step_impact。

        删除步骤会同时删除步骤下全部场景参数。更换接口时，删除后调用 add_api_case_step 新增目标接口，
        再调用 sort_api_case_steps 按页面拖动后的顺序保存。
        """
        error = validate_dangerous_action_confirmation(
            "delete_api_case_step",
            step_id,
            preview_token,
            confirm_text,
        )
        if error:
            return error
        try:
            with transaction.atomic():
                before = _api_case_step_delete_impact(step_id)
                ApiCaseStepService.delete_step(
                    step_id,
                    operator_id=current_user().id,
                    source='mcp',
                )
        except Exception as exc:
            return fail(str(exc), "DELETE_API_CASE_STEP_FAILED")
        return ok({"step_id": step_id, "deleted": before.get("will_delete", {})}, "API Case 步骤删除成功")

    @mcp.tool()
    def preview_delete_api_case_scenario_impact(scenario_id: int) -> dict:
        """预览删除 API Case 场景参数的影响，并生成确认 token。"""
        scenario = ApiQuerySelector.api_case_detailed_parameter().get(id=scenario_id)
        confirm_text = f"DELETE_API_CASE_SCENARIO:{scenario_id}:{scenario.name}"
        return ok(
            create_dangerous_action_preview(
                "delete_api_case_scenario",
                scenario_id,
                confirm_text,
                _api_case_scenario_delete_impact(scenario_id),
            ),
            "已生成 API Case 场景删除影响预览，请二次确认后删除",
        )

    @mcp.tool()
    def delete_api_case_scenario(
            scenario_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """删除 API Case 场景参数。必须先调用 preview_delete_api_case_scenario_impact。"""
        error = validate_dangerous_action_confirmation(
            "delete_api_case_scenario",
            scenario_id,
            preview_token,
            confirm_text,
        )
        if error:
            return error
        try:
            with transaction.atomic():
                before = _api_case_scenario_delete_impact(scenario_id)
                ApiCaseStepService.delete_parameters(
                    [scenario_id],
                    operator_id=current_user().id,
                    source='mcp',
                )
        except Exception as exc:
            return fail(str(exc), "DELETE_API_CASE_SCENARIO_FAILED")
        return ok({"scenario_id": scenario_id, "deleted": before.get("will_delete", {})}, "API Case 场景删除成功")
