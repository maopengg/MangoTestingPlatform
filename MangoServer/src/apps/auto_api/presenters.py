def _serialize(serializer_class, instance, *, many=False):
    return serializer_class(instance=instance, many=many).data


def _presenter(module_name, class_name):
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)


def format_module_coverage_scan(instance, *, many=False):
    serializer = _presenter("src.apps.auto_api.api.serializers.module_coverage_scan", "ModuleCoverageScanSerializer")
    return _serialize(serializer, instance, many=many)


def format_module_coverage_case(instance, *, many=False):
    serializer = _presenter("src.apps.auto_api.api.serializers.module_coverage_case", "ModuleCoverageCaseSerializer")
    return _serialize(serializer, instance, many=many)


def format_module_coverage_case_snapshot(instance, *, many=False):
    serializer = _presenter("src.apps.auto_api.api.serializers.module_coverage_case",
                            "ModuleCoverageCaseSnapshotSerializer")
    return _serialize(serializer, instance, many=many)


def format_module_coverage_interface(instance, *, many=False):
    serializer = _presenter("src.apps.auto_api.api.serializers.module_coverage_interface",
                            "ModuleCoverageInterfaceSerializer")
    return _serialize(serializer, instance, many=many)


def format_module_coverage_interface_snapshot(instance, *, many=False):
    serializer = _presenter("src.apps.auto_api.api.serializers.module_coverage_interface",
                            "ModuleCoverageInterfaceSnapshotSerializer")
    return _serialize(serializer, instance, many=many)
