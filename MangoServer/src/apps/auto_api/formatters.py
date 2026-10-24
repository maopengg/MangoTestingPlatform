MODULE_COVERAGE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def format_api_case(instance):
    from src.apps.auto_api.api.serializers.api_case_presentation import ApiCaseSerializersC

    return ApiCaseSerializersC(instance=instance).data if instance is not None else None
