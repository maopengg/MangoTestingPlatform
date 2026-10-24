from rest_framework import serializers


class GraderCatalogSerializer(serializers.Serializer):
    grader_key = serializers.CharField(read_only=True)
    grader_version = serializers.IntegerField(read_only=True)
