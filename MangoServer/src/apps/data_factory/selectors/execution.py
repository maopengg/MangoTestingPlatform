# -*- coding: utf-8 -*-
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.data_factory.enums import DataFactoryExecutionSourceEnum
from src.apps.data_factory.models import DataFactoryExecution


def format_execution_source_info(obj: DataFactoryExecution) -> dict:
    if hasattr(obj, "_data_factory_source_info"):
        return obj._data_factory_source_info

    source_label = DataFactoryExecutionSourceEnum.obj().get(obj.source_type, obj.source_type)
    template_name = obj.template.name if obj.template_id and obj.template else None
    info = {
        "source_type": obj.source_type,
        "source_type_name": source_label,
        "source_id": obj.source_id,
        "template_id": obj.template_id,
        "template_name": template_name,
        "display": template_name or (f"{source_label}#{obj.source_id}" if obj.source_id else source_label),
    }
    if not obj.source_id:
        obj._data_factory_source_info = info
        return info

    executor = (obj.context or {}).get("__executor") or {}
    executor_user_id = executor.get("user_id")
    if executor_user_id:
        from src.apps.user.models import User

        executor_user = User.objects.filter(id=executor_user_id).only("id", "name", "username").first()
        info["executor_id"] = executor_user_id
        if executor_user:
            info.update({
                "executor_name": executor_user.name,
                "executor_username": executor_user.username,
            })

    if obj.source_type == DataFactoryExecutionSourceEnum.API_CASE.value:
        from src.apps.auto_api.models import ApiCase

        api_case = ApiCase.objects.select_related("case_people").filter(id=obj.source_id).first()
        if api_case:
            info.update({
                "case_id": api_case.id,
                "case_name": api_case.name,
                "case_owner_id": api_case.case_people_id,
                "case_owner_name": api_case.case_people.name if api_case.case_people_id else None,
                "case_owner_username": api_case.case_people.username if api_case.case_people_id else None,
                "display": f"{source_label}：{api_case.name}",
            })
    elif obj.source_type == DataFactoryExecutionSourceEnum.API_CASE_PARAMETER.value:
        from src.apps.auto_api.models import ApiCaseDetailedParameter
        from src.apps.auto_api.enums import MethodEnum

        parameter = ApiCaseDetailedParameter.objects.select_related(
            "case_detailed__case",
            "case_detailed__case__case_people",
            "case_detailed__api_info",
        ).filter(id=obj.source_id).first()
        if parameter:
            api_case = parameter.case_detailed.case
            api_info = ApiInfoRuntimeService.resolve_runtime(parameter.case_detailed.api_info_id, allow_draft=True)
            info.update({
                "case_id": api_case.id,
                "case_name": api_case.name,
                "case_owner_id": api_case.case_people_id,
                "case_owner_name": api_case.case_people.name if api_case.case_people_id else None,
                "case_owner_username": api_case.case_people.username if api_case.case_people_id else None,
                "api_info_id": api_info.id,
                "api_info_name": api_info.name,
                "api_info_method": api_info.method,
                "api_info_method_name": MethodEnum.obj().get(api_info.method, api_info.method),
                "api_info_url": api_info.url,
                "scenario_id": parameter.id,
                "scenario_name": parameter.name,
                "display": f"{source_label}：{api_case.name} / {api_info.name} / {parameter.name}",
            })
    elif obj.source_type == DataFactoryExecutionSourceEnum.UI_CASE.value:
        from src.apps.auto_ui.models import UiCase

        ui_case = UiCase.objects.select_related("case_people", "module").filter(id=obj.source_id).first()
        if ui_case:
            info.update({
                "case_id": ui_case.id,
                "case_name": ui_case.name,
                "case_owner_id": ui_case.case_people_id,
                "case_owner_name": ui_case.case_people.name if ui_case.case_people_id else None,
                "case_owner_username": ui_case.case_people.username if ui_case.case_people_id else None,
                "ui_module_id": ui_case.module_id,
                "ui_module_name": ui_case.module.name if ui_case.module_id else None,
                "display": f"{source_label}：{ui_case.name}",
            })

    if template_name:
        info["display"] = f"{info['display']} / 模板：{template_name}"
    obj._data_factory_source_info = info
    return info
