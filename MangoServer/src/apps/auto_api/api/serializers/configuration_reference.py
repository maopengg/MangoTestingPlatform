from rest_framework import serializers


class ConfigurationReferenceCountsQuery(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1, max_length=200)


class ConfigurationReferenceCasesQuery(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    page = serializers.IntegerField(min_value=1, default=1)
    pageSize = serializers.IntegerField(min_value=1, max_value=100, default=20)
