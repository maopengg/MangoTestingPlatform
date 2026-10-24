# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.functional_test.models import FunctionalTestGridView


class FunctionalTestGridViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = FunctionalTestGridView
        fields = "__all__"
        read_only_fields = ("user",)
