def _presenter(module_name, class_name):
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)


def prepare_test_suite_queryset(queryset):
    serializer = _presenter("src.apps.test_center.api.serializers.test_suite", "TestSuiteSerializersC")
    return serializer.setup_eager_loading(queryset)


def format_test_suite(instance, *, many=False):
    serializer = _presenter("src.apps.test_center.api.serializers.test_suite", "TestSuiteSerializersC")
    return serializer(instance=instance, many=many).data


def prepare_test_suite_detail_queryset(queryset):
    serializer = _presenter("src.apps.test_center.api.serializers.test_suite_details", "TestSuiteDetailsSerializersC")
    return serializer.setup_eager_loading(queryset)


def format_test_suite_detail(instance, *, many=False):
    serializer = _presenter("src.apps.test_center.api.serializers.test_suite_details", "TestSuiteDetailsSerializersC")
    return serializer(instance=instance, many=many).data
