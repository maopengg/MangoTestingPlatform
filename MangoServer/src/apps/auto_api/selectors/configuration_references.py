from src.apps.auto_api.models import ApiCaseDetailedParameter
from src.common.utils.json_references import collect_json_references


class ApiConfigurationReferenceSelector:
    @staticmethod
    def public_variables(cases, ids):
        return collect_json_references(cases, 'id', 'front_public', ids)

    @staticmethod
    def headers(cases, ids):
        result = collect_json_references(cases, 'id', 'front_headers', ids)
        parameters = ApiCaseDetailedParameter.objects.filter(case_detailed__case_id__in=cases.values('id'))
        scenario_references = collect_json_references(parameters, 'case_detailed__case_id', 'headers', ids)
        for header_id, case_ids in scenario_references.items():
            result[header_id].update(case_ids)
        return result
