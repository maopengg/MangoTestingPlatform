from src.apps.auto_api.exceptions import AutoApiError

from src.apps.auto_api.models import ApiCaseRelease
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.perf.services.compilation.functions import collect_perf_functions


class PerfSourceCaseService:
    """Expose published, immutable service-automation cases to performance scenarios."""

    @staticmethod
    def _preview_payload(payload: dict) -> dict:
        case_payload = payload.get("api_case") or {}
        steps = []
        incompatible_reasons = []
        dependencies = payload.get("dependencies") or {}
        if dependencies.get("data_factory_configs"):
            incompatible_reasons.append("包含数据工厂配置")
        if case_payload.get("parametrize"):
            incompatible_reasons.append("包含 Case 参数组；性能模式不再支持参数组，请改用 perf_* 数据方法后重新发布 Case")
        try:
            collect_perf_functions(payload)
        except ValueError as error:
            incompatible_reasons.append(str(error))
        for field, label in (("front_sql", "用例前置 SQL"), ("posterior_sql", "用例后置 SQL"),
                             ("front_auth_config", "授权配置"), ("front_public", "全局变量依赖")):
            if case_payload.get(field):
                incompatible_reasons.append(f"包含{label}")
        for step_index, step in enumerate(payload.get("api_case_detailed") or []):
            parameters = step.get("api_case_detailed_parameter") or []
            for parameter_index, parameter in enumerate(parameters):
                name = parameter.get("name") or f"步骤 {step_index + 1}.{parameter_index + 1}"
                unsupported = []
                if parameter.get("protocol_type") not in (None, "http"):
                    unsupported.append("非 HTTP 协议")
                if parameter.get("body_type") == "multipart":
                    unsupported.append("文件上传")
                for field, label in (("front_sql", "前置 SQL"), ("front_func", "前置函数"), ("ass_sql", "SQL 断言"),
                                     ("ass_schema", "Schema 断言"), ("posterior_sql", "后置 SQL"),
                                     ("posterior_func", "后置函数"), ("posterior_file", "文件下载"),
                                     ("sse_config", "SSE 配置")):
                    if parameter.get(field):
                        unsupported.append(label)
                if unsupported:
                    incompatible_reasons.append(f"“{name}”包含{'、'.join(unsupported)}")
                steps.append({
                    "key": f"{step.get('logical_id') or step.get('id')}-{parameter.get('id') or parameter_index}",
                    "name": name,
                    "api_info_id": step.get("api_info_id") or step.get("api_info"),
                    "extractor_count": len(parameter.get("posterior_response") or []) + len(
                        parameter.get("posterior_response_text") or []),
                    "check_count": len(parameter.get("ass_general") or []) + len(
                        parameter.get("ass_jsonpath") or []) + int(parameter.get("ass_json_all") is not None) + int(
                        parameter.get("ass_text_all") is not None),
                })
        return {"case_flow": case_payload.get("case_flow") or "", "steps": steps, "step_count": len(steps),
                "compatible": not incompatible_reasons, "incompatible_reasons": incompatible_reasons}

    @classmethod
    def serialize_release(cls, release) -> dict:
        preview = cls._preview_payload(release.revision.payload or {})
        module = release.api_case.module
        return {
            "key": release.id, "release_id": release.id, "case_id": release.api_case_id,
            "revision_id": release.revision_id, "revision_no": release.revision.revision_no,
            "revision_checksum": release.revision.checksum, "version_label": release.version_label,
            "name": release.api_case.name, "module_id": release.api_case.module_id,
            "module_full_path": module.get_full_path(),
            "title": f"{release.api_case.name} · {module.get_full_path()}（{release.version_label}）",
            "disabled": not preview["compatible"], **preview,
        }

    @classmethod
    def list_options(cls, scenario) -> list[dict]:
        queryset = ApiCaseRelease.objects.filter(api_case__project_product_id=scenario.project_product_id,
                                                 is_current=True,
                                                 status=ApiCaseRelease.STATUS_PUBLISHED).select_related("api_case",
                                                                                                        "api_case__module",
                                                                                                        "revision")
        options = [cls.serialize_release(item) for item in queryset]
        return sorted(options, key=lambda item: (item["module_full_path"], item["name"], item["case_id"]))

    @classmethod
    def resolve_release(cls, scenario, release_id: int):
        queryset = ApiCaseRelease.objects.select_related("api_case", "api_case__module", "revision").filter(
            id=release_id,
            api_case__project_product_id=scenario.project_product_id,
        )
        if release_id != scenario.source_case_release_id:
            queryset = queryset.filter(is_current=True, status=ApiCaseRelease.STATUS_PUBLISHED)
        release = queryset.first()
        if release is None:
            return None
        try:
            ApiCaseRevisionService.verify_execution_revision(release.revision)
        except AutoApiError:
            return None
        return release
