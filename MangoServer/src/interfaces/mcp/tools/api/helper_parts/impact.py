from __future__ import annotations

from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
from src.apps.test_center.enums import (
    TestCaseTypeEnum,
)
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector

API_CASE_RESULT_EXPORT_RELATIVE_DIR = "mcp_export/api_case_result"
API_CASE_RESULT_EXPORT_RETENTION_DAYS = 7

FILE_UPLOAD_USAGE = {
    "description": "API 接口定义和 API case 场景参数中的 multipart.files 用于描述 multipart/form-data 文件参数。",
    "required_format": {"body_type": "multipart", "body_config": {"fields": [], "files": [
        {"key": "请求文件字段名", "file_id": 1, "file_name": "可选发送文件名"}]}},
    "strict_rule": "文件必须来自测试配置-测试文件中的 FileData.id，不能直接传本地路径、URL、裸文件名或二进制内容。",
    "workflow": [
        "先调用 system_file 分组的 upload_system_file 上传真实文件，记录返回的 file.name 或上传时传入的 name。",
        "在 body_config.files 中写入 file_id，并把 key 设置为接口要求的文件字段名。",
        "执行时后端会按 file_id 读取 FileData.test_file 并发送文件。",
    ],
    "example": {"body_type": "multipart", "body_config": {"fields": [{"key": "name", "value": "demo"}],
                                                          "files": [{"key": "file", "file_id": 1}]}},
    "notes": [
        "示例中的 key 是请求参数名；如果接口字段名叫 upload_file，则 key 写 upload_file。",
        "建议先用 list_system_files 查询确认 file_id 和项目产品是否匹配。",
        "远程 MCP 服务通常无法读取调用者本机路径，因此只接受 FileData.id。",
    ],
}


def _api_case_delete_impact(case_id: int) -> dict:
    from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum

    case = ApiQuerySelector.api_case().select_related("project_product", "module", "case_people").get(id=case_id)
    step_ids = list(ApiQuerySelector.api_case_detailed().filter(case_id=case_id).values_list("id", flat=True))
    scenario_ids = list(
        ApiQuerySelector.api_case_detailed_parameter().filter(case_detailed_id__in=step_ids).values_list("id",
                                                                                                         flat=True)
    )
    case_factory_count = DataFactoryQuerySelector.data_factory_case_config().filter(
        source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
        source_id=case_id,
    ).count()
    scenario_factory_count = DataFactoryQuerySelector.data_factory_case_config().filter(
        source_type=DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
        source_id__in=scenario_ids,
    ).count()
    task_detail_count = TaskCenterQuerySelector.tasks_details().filter(api_case_id=case_id).count()
    report_detail_count = TestCenterQuerySelector.test_suite_details().filter(
        type=TestCaseTypeEnum.API.value,
        case_id=case_id,
    ).count()
    release_count = ApiQuerySelector.api_case_release().filter(api_case_id=case_id).count()
    revision_count = ApiQuerySelector.api_case_revision().filter(api_case_id=case_id).count()
    can_delete = not step_ids and task_detail_count == 0
    blockers = []
    if step_ids:
        blockers.append("该 API case 下存在接口步骤。请先删除页面可见的步骤和场景后，再删除 API case。")
    if task_detail_count:
        blockers.append("该 API case 已被定时任务绑定。请先解除定时任务绑定后，再删除 API case。")
    return {
        "case": {
            "id": case.id,
            "name": case.name,
            "project_product_id": case.project_product_id,
            "project_product_name": case.project_product.name if case.project_product else None,
            "module_id": case.module_id,
            "module_name": case.module.name if case.module else None,
            "case_people_id": case.case_people_id,
            "case_people_name": case.case_people.name if case.case_people else None,
            "status": case.status,
        },
        "can_delete": can_delete,
        "will_delete": {
            "api_case": 1 if can_delete else 0,
            "api_case_releases": release_count if can_delete else 0,
            "api_case_revisions": revision_count if can_delete else 0,
            "case_data_factory_configs": case_factory_count if can_delete else 0,
        },
        "references": {
            "api_case_step_count": len(step_ids),
            "api_case_scenario_count": len(scenario_ids),
            "scenario_data_factory_config_count": scenario_factory_count,
            "task_detail_count": task_detail_count,
            "historical_report_detail_count": report_detail_count,
        },
        "blockers": blockers,
        "risk": "确认后删除 API case 及页面不可单独删除的版本数据。页面可见的步骤、场景和定时任务绑定需要用户先手动删除；历史测试报告明细按 case_id 保存，不会随 case 删除自动删除。",
    }


def _api_case_revision_delete_impact(case_id: int, revision_id: int) -> dict:
    revision = ApiQuerySelector.api_case_revision().select_related("api_case", "parent_revision").get(
        id=revision_id,
        api_case_id=case_id,
    )
    release_ids = list(
        ApiQuerySelector.api_case_release().filter(revision_id=revision_id)
        .order_by("id")
        .values_list("id", flat=True)
    )
    child_revisions = list(
        ApiQuerySelector.api_case_revision().filter(parent_revision_id=revision_id)
        .order_by("revision_no")
        .values("id", "revision_no")
    )
    task_detail_ids = list(
        TaskCenterQuerySelector.tasks_details().filter(api_case_revision_id=revision_id)
        .order_by("id")
        .values_list("id", flat=True)
    )
    report_detail_ids = list(
        TestCenterQuerySelector.test_suite_details().filter(api_case_revision_id=revision_id)
        .order_by("id")
        .values_list("id", flat=True)
    )
    blockers = []
    if release_ids:
        blockers.append("该 API Case 修订已发布为版本，不能删除。")
    if child_revisions:
        blockers.append("该 API Case 修订存在后续子修订，不能删除；请从最新的叶子修订开始倒序删除。")
    if task_detail_ids:
        blockers.append("该 API Case 修订已被定时任务绑定，不能删除。")
    can_delete = not blockers
    return {
        "revision": {
            "case_id": revision.api_case_id,
            "case_name": revision.api_case.name,
            "revision_id": revision.id,
            "revision_no": revision.revision_no,
            "summary": revision.summary,
            "parent_revision_id": revision.parent_revision_id,
        },
        "can_delete": can_delete,
        "will_delete": {
            "api_case_revision": 1 if can_delete else 0,
            "will_detach_report_detail_ids": report_detail_ids if can_delete else [],
        },
        "references": {
            "release_ids": release_ids,
            "child_revisions": child_revisions,
            "task_detail_ids": task_detail_ids,
            "report_detail_ids": report_detail_ids,
        },
        "blockers": blockers,
        "risk": "确认后删除该未发布 API Case 修订；历史测试报告保留，但会解除对该修订的引用。",
    }


def _api_case_scenario_delete_impact(scenario_id: int) -> dict:
    from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum

    scenario = ApiQuerySelector.api_case_detailed_parameter().select_related(
        "case_detailed",
        "case_detailed__case",
        "case_detailed__api_info",
    ).get(id=scenario_id)
    step = scenario.case_detailed
    case = step.case
    data_factory_config_ids = list(
        DataFactoryQuerySelector.data_factory_case_config().filter(
            source_type=DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
            source_id=scenario_id,
        ).values_list("id", flat=True)
    )
    step_scenario_count = ApiQuerySelector.api_case_detailed_parameter().filter(case_detailed_id=step.id).count()
    return {
        "scenario": {
            "id": scenario.id,
            "name": scenario.name,
            "step_id": step.id,
            "api_info_id": step.api_info_id,
            "api_info_name": step.api_info.name if step.api_info else None,
            "case_id": case.id,
            "case_name": case.name,
        },
        "will_delete": {
            "api_case_scenario": 1,
            "scenario_data_factory_config_ids": data_factory_config_ids,
            "scenario_data_factory_config_count": len(data_factory_config_ids),
        },
        "references": {
            "step_scenario_count_before_delete": step_scenario_count,
            "step_scenario_count_after_delete": max(step_scenario_count - 1, 0),
        },
        "risk": "确认后会删除该 API Case 场景参数，并清理该场景绑定的数据工厂配置；不会删除 API Case、步骤或接口定义。",
    }


def _api_case_step_delete_impact(step_id: int) -> dict:
    from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum

    step = ApiQuerySelector.api_case_detailed().select_related("case", "api_info").get(id=step_id)
    scenario_ids = list(
        ApiQuerySelector.api_case_detailed_parameter().filter(case_detailed=step).values_list("id", flat=True))
    data_factory_config_ids = list(
        DataFactoryQuerySelector.data_factory_case_config().filter(
            source_type=DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
            source_id__in=scenario_ids,
        ).values_list("id", flat=True)
    )
    case_step_count = ApiQuerySelector.api_case_detailed().filter(case_id=step.case_id).count()
    return {
        "step": {
            "id": step.id,
            "case_id": step.case_id,
            "case_name": step.case.name,
            "api_info_id": step.api_info_id,
            "api_info_name": step.api_info.name if step.api_info else None,
            "case_sort": step.case_sort,
        },
        "will_delete": {
            "api_case_step": 1,
            "api_case_scenario_ids": scenario_ids,
            "api_case_scenario_count": len(scenario_ids),
            "scenario_data_factory_config_ids": data_factory_config_ids,
            "scenario_data_factory_config_count": len(data_factory_config_ids),
        },
        "references": {
            "case_step_count_before_delete": case_step_count,
            "case_step_count_after_delete": max(case_step_count - 1, 0),
        },
        "risk": "确认后会删除该 API Case 接口步骤、步骤下全部场景参数，并清理场景绑定的数据工厂配置；不会删除 API Case 或 ApiInfo 接口定义。",
        "next_steps": [
            "如果目的是更换步骤绑定接口，请先删除旧步骤。",
            "再调用 add_api_case_step(case_id, api_info_release_id 或 api_info_id, case_sort) 新增目标接口，目标接口必须已发布。",
            "最后调用 sort_api_case_steps 按拖拽后的顺序重新写入 case_sort。",
        ],
    }
