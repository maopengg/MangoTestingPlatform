from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from src.apps.auto_api.models import (
    ApiCaseRelease,
)
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.common.exceptions import MangoServerError
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    current_user,
    fail,
    ok,
)
from ..helpers import (
    _published_api_case_modify_impact,
)


def register_case_revision_tools(mcp):
    @mcp.tool()
    def preview_modify_published_api_case_impact(case_id: int) -> dict:
        """预览直接修改已发布 API Case 的影响。已发布 Case 必须先预览并确认后才能调用直接修改类工具。"""
        api_case = ApiQuerySelector.api_case().get(id=case_id)
        confirm_text = f"MODIFY_PUBLISHED_API_CASE:{case_id}:{api_case.name}"
        return ok(
            create_dangerous_action_preview(
                "modify_published_api_case",
                case_id,
                confirm_text,
                _published_api_case_modify_impact(case_id),
            ),
            "已生成修改已发布 API Case 影响预览",
        )

    @mcp.tool()
    def preview_checkout_api_case_revision_impact(case_id: int, revision_id: int) -> dict:
        """预检 Case 历史修订迁出依赖；返回可直接迁出、可从快照恢复和无法恢复的步骤。"""
        return ok(ApiCaseRevisionService.inspect_checkout_impact(case_id, revision_id))

    @mcp.tool()
    def checkout_api_case_revision_to_editing(
            case_id: int,
            revision_id: int,
            restore_missing_dependencies: bool = False,
    ) -> dict:
        """把 Case 历史修订迁出到当前编辑态；会覆盖当前编辑态，原历史修订保留。

        仅在场景有变化、需要基于历史修订继续调整，或需要先备份/恢复当前编辑态数据时使用。
        普通调试和临时验证不要迁出修订，直接使用 run_api_case 执行当前编辑态。
        """

        ApiCaseRevisionService.checkout_to_editing(
            case_id,
            revision_id,
            operator_id=current_user().id,
            restore_missing_dependencies=restore_missing_dependencies,
        )
        return ok({'case_id': case_id, 'revision_id': revision_id, 'status': 'editing'})

    @mcp.tool()
    def create_api_case_revision_from_current(
            case_id: int,
            summary: Annotated[str | None, Field(max_length=256)] = None,
    ) -> dict:
        """把 Case 当前编辑态保存为不可变聚合 Revision。

        不要求 run_api_case 成功，也不要求场景必须配置断言；确认当前配置后即可调用。
        创建 Case、编辑步骤/场景、排序和失败调试都不会自动生成修订。生成修订不等于发布，
        也不会影响当前发布版本。
        summary 为可选修订摘要，最多256个字符。
        """
        revision = ApiCaseRevisionService.record_current(
            case_id, operator_id=current_user().id, summary=summary, source='mcp',
        )
        return ok({'revision_id': revision.id, 'revision_no': revision.revision_no})

    @mcp.tool()
    def update_api_case_publication_status(
            case_id: int,
            target_status: Literal['prepublished', 'published', 'unpublished'],
            revision_id: int | None = None,
    ) -> dict:
        """流转 API Case 发布状态。

        target_status=prepublished：把当前候选修订提交预发布，必须传 revision_id；Case 当前执行状态
        必须为通过，失败、未执行或执行中的 Case 不允许提交预发布；提交后旧正式版本转为历史版本，
        Case 仅处于预发布状态，不会被定时任务选中。提交前，调用方 AI 必须先用 get_api_case_detail_full 读取完整
        Case，确认所有写数据步骤都有使用本次执行唯一标识的删除、撤销、恢复、用例级后置 SQL/函数
        或数据工厂清理闭环。API 创建的子表、关联表、业务或异步数据必须先由 Case 清理，再清理数据
        工厂数据。无法确认副作用或清理有效性时不得提交。

        target_status=published：由项目产品负责人通过当前预发布并生成正式版本，不传 revision_id。
        Case 当前执行状态必须为通过，失败、未执行或执行中的 Case 不允许正式发布。
        target_status=unpublished：具备用例修改权限且在产品数据范围内的用户均可退回当前预发布，不要求产品负责人身份；不删除修订，不传 revision_id，不恢复旧正式版本。
        服务端会校验当前状态、唯一候选修订；审批正式发布额外校验项目产品负责人身份，不允许跳过预发布直接正式发布。
        """
        if target_status == ApiCaseRevisionService.PUBLICATION_PREPUBLISHED:
            if revision_id is None:
                return fail(
                    '提交预发布时必须提供 revision_id',
                    'API_CASE_REVISION_REQUIRED',
                )
            release = ApiCaseRevisionService.submit_prepublication(case_id, revision_id)
            return ok({
                'case_id': release.api_case_id,
                'revision_id': release.revision_id,
                'release_id': getattr(release, 'id', None),
                'status': ApiCaseRevisionService.PUBLICATION_PREPUBLISHED,
                'version_label': getattr(release, 'version_label', None),
                'is_current': getattr(release, 'is_current', False),
            }, 'API Case 修订已提交预发布')

        if target_status == ApiCaseRevisionService.PUBLICATION_PUBLISHED:
            release = ApiCaseRevisionService.approve_prepublication(
                case_id,
                operator_id=current_user().id,
            )
            return ok({
                'case_id': release.api_case_id,
                'revision_id': release.revision_id,
                'release_id': release.id,
                'status': release.status,
                'version_label': release.version_label,
                'is_current': release.is_current,
            }, 'API Case 预发布已通过并正式发布')

        if target_status == ApiCaseRevisionService.PUBLICATION_UNPUBLISHED:
            revision = ApiCaseRevisionService.revert_prepublication(
                case_id,
                operator_id=current_user().id,
            )
            return ok({
                'case_id': revision.api_case_id,
                'revision_id': revision.id,
                'release_id': None,
                'status': ApiCaseRevisionService.PUBLICATION_UNPUBLISHED,
                'version_label': None,
                'is_current': False,
            }, 'API Case 预发布已退回未发布')

        return fail(
            'target_status 仅支持 prepublished、published 或 unpublished',
            'API_CASE_PUBLICATION_STATUS_INVALID',
        )

    @mcp.tool()
    def unpublish_api_case_revision(
            case_id: int,
            release_id: int | None = None,
            revision_id: int | None = None,
    ) -> dict:
        """直接取消 API Case 当前发布版本，无需预览确认。

        取消发布只会把当前 Release 标记为已取消发布并解除 current 状态，不删除 Case、Revision、
        历史报告或执行结果。release_id、revision_id 可用于校验目标；均不传时取消当前发布版本。
        取消后，按当前发布版本动态选取 Case 的定时任务和批量执行将不再选中该 Case。
        """
        release = ApiQuerySelector.api_case_release().filter(
            api_case_id=case_id,
            is_current=True,
            status=ApiCaseRelease.STATUS_PUBLISHED,
        ).first()
        if release is None:
            return fail("当前 API Case 没有可取消的已发布版本", "API_CASE_RELEASE_NOT_FOUND")
        if release_id is not None and release.id != int(release_id):
            return fail(
                "release_id 不是当前发布版本，请刷新 Case 发布状态后重试",
                "API_CASE_RELEASE_MISMATCH",
                {"case_id": case_id, "current_release_id": release.id},
            )
        if revision_id is not None and release.revision_id != int(revision_id):
            return fail(
                "revision_id 不是当前发布修订，请刷新 Case 发布状态后重试",
                "API_CASE_REVISION_MISMATCH",
                {"case_id": case_id, "current_revision_id": release.revision_id},
            )
        try:
            ApiCaseRevisionService.verify_product_owner(case_id, current_user().id)
            release = ApiCaseRevisionService.unpublish(case_id, release.id)
        except MangoServerError as error:
            return fail(error.msg, str(error.code))
        return ok({
            "case_id": release.api_case_id,
            "revision_id": release.revision_id,
            "release_id": release.id,
            "version_label": release.version_label,
            "status": release.status,
            "is_current": release.is_current,
        }, "API Case 已取消发布")
