from rest_framework import serializers


EVALUATION_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class EvaluationModelSerializer(serializers.ModelSerializer):
    def build_standard_field(self, field_name, model_field):
        field_class, field_kwargs = super().build_standard_field(field_name, model_field)
        if issubclass(field_class, serializers.DateTimeField):
            field_kwargs["format"] = EVALUATION_DATETIME_FORMAT
        return field_class, field_kwargs
