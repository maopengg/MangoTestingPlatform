from src.common.utils.json_references import collect_json_references


class UiConfigurationReferenceSelector:
    @staticmethod
    def public_variables(cases, ids):
        return collect_json_references(cases, 'id', 'front_public', ids)
