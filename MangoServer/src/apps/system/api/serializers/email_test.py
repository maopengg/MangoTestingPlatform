from rest_framework import serializers


class EmailTestSerializer(serializers.Serializer):
    recipient = serializers.EmailField(max_length=254)
