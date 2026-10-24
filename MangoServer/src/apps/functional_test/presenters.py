def _serialize(serializer_class, instance, *, many=False):
    return serializer_class(instance=instance, many=many).data


def _presenter(serializer_module, serializer_name):
    module = __import__(serializer_module, fromlist=[serializer_name])
    return getattr(module, serializer_name)


def prepare_suite_queryset(queryset):
    serializer = _presenter("src.apps.functional_test.api.serializers.suite", "ManualTestSuiteSerializerC")
    return serializer.setup_eager_loading(queryset)


def format_suite(instance, *, many=False):
    return _serialize(_presenter("src.apps.functional_test.api.serializers.suite", "ManualTestSuiteSerializerC"),
                      instance, many=many)


def prepare_case_list_queryset(queryset):
    serializer = _presenter("src.apps.functional_test.api.serializers.case", "ManualTestCaseListSerializer")
    return serializer.setup_eager_loading(queryset)


def format_case_list(instance, *, many=False):
    return _serialize(_presenter("src.apps.functional_test.api.serializers.case", "ManualTestCaseListSerializer"),
                      instance, many=many)


def prepare_case_queryset(queryset):
    serializer = _presenter("src.apps.functional_test.api.serializers.case", "ManualTestCaseSerializerC")
    return serializer.setup_eager_loading(queryset)


def format_case(instance, *, many=False):
    return _serialize(_presenter("src.apps.functional_test.api.serializers.case", "ManualTestCaseSerializerC"),
                      instance, many=many)


def prepare_context_resource_queryset(queryset):
    serializer = _presenter("src.apps.functional_test.api.serializers.context_resource",
                            "FunctionalTestContextResourceSerializerC")
    return serializer.setup_eager_loading(queryset)


def format_context_resource(instance, *, many=False):
    return _serialize(_presenter("src.apps.functional_test.api.serializers.context_resource",
                                 "FunctionalTestContextResourceSerializerC"), instance, many=many)


def format_automation_binding(instance, *, many=False):
    return _serialize(_presenter("src.apps.functional_test.api.serializers.automation_binding",
                                 "ManualTestAutomationBindingSerializer"), instance, many=many)


def prepare_plan_list_queryset(queryset):
    serializer = _presenter("src.apps.functional_test.api.serializers.plan", "FunctionalTestPlanListSerializer")
    return serializer.setup_eager_loading(queryset)


def format_plan_list(instance, *, many=False):
    return _serialize(_presenter("src.apps.functional_test.api.serializers.plan", "FunctionalTestPlanListSerializer"),
                      instance, many=many)


def format_plan(instance):
    return _serialize(_presenter("src.apps.functional_test.api.serializers.plan", "FunctionalTestPlanSerializer"),
                      instance)


def format_plan_case(instance):
    return _serialize(_presenter("src.apps.functional_test.api.serializers.plan", "FunctionalTestPlanCaseSerializer"),
                      instance)
