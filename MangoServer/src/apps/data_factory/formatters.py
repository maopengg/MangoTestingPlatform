def format_datasource_alias(instance):
    from src.apps.data_factory.api.serializers.datasource_alias import DataFactoryDatasourceAliasSerializerC

    return DataFactoryDatasourceAliasSerializerC(instance=instance).data if instance is not None else None


def format_case_config(instance):
    from src.apps.data_factory.api.serializers.case_config import DataFactoryCaseConfigSerializerC

    return DataFactoryCaseConfigSerializerC(instance=instance).data if instance is not None else None


def format_template(instance):
    from src.apps.data_factory.api.serializers.template import DataFactoryTemplateSerializerC

    return DataFactoryTemplateSerializerC(instance=instance).data if instance is not None else None
