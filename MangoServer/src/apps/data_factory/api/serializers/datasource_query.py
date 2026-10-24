from rest_framework import serializers


class LogicalDatasourceQuerySerializer(serializers.Serializer):
    datasource_alias_id = serializers.IntegerField(min_value=1)
    project_product_id = serializers.IntegerField(min_value=1)
    test_env = serializers.IntegerField()
    sql = serializers.CharField(max_length=20000)
