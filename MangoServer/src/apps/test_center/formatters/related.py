def format_project(instance):
    from src.apps.test_center.api.serializers.project import ProjectSerializers

    return ProjectSerializers(instance=instance).data if instance is not None else None


def format_project_product(instance):
    from src.apps.test_center.api.serializers.project_product import ProjectProductSerializersC

    return ProjectProductSerializersC(instance=instance).data if instance is not None else None


def format_project_product_summary(instance):
    if instance is None:
        return None
    project = instance.project
    return {
        'id': instance.id,
        'name': instance.name,
        'api_client_type': instance.api_client_type,
        'ui_client_type': instance.ui_client_type,
        'project': {'id': project.id, 'name': project.name} if project else None,
    }


def format_product_module_summary(instance):
    if instance is None:
        return None
    return {'id': instance.id, 'name': instance.name, 'full_path': instance.get_full_path()}


def format_product_module(instance):
    from src.apps.test_center.api.serializers.product_module_mutation import ProductModuleSerializers

    return ProductModuleSerializers(instance=instance).data if instance is not None else None


def format_product_module_compact(instance):
    from src.apps.test_center.api.serializers.product_module import ProductModuleSerializersC

    return ProductModuleSerializersC(instance=instance).data if instance is not None else None


def format_notice_group(instance):
    from src.apps.test_center.api.serializers.notice_group import NoticeGroupSerializers

    return NoticeGroupSerializers(instance=instance).data if instance is not None else None


def format_test_object(instance):
    from src.apps.test_center.api.serializers.test_object import TestObjectSerializers

    return TestObjectSerializers(instance=instance).data if instance is not None else None


def format_test_suite(instance):
    from src.apps.test_center.api.serializers.test_suite import TestSuiteSerializers

    return TestSuiteSerializers(instance=instance).data if instance is not None else None


def format_data_source(instance):
    from src.apps.test_center.api.serializers.data_source import DataSourceSerializerC

    return DataSourceSerializerC(instance=instance).data if instance is not None else None
