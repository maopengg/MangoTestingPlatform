from rest_framework import serializers


class CallbackQuerySerializer(serializers.Serializer):
    case_id = serializers.IntegerField(min_value=1)
    trace_id = serializers.CharField(max_length=64, required=False)
    run_id = serializers.IntegerField(min_value=1, required=False)
    trigger_step_key = serializers.RegexField(r'^step-[1-9][0-9]*$', max_length=64, required=False)
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=10)


class CallbackDeliveryQuerySerializer(serializers.Serializer):
    case_id = serializers.IntegerField(min_value=1)
    run_id = serializers.IntegerField(min_value=1)
    delivery_id = serializers.IntegerField(min_value=1, required=False)
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=10)


class CallbackDownloadQuerySerializer(serializers.Serializer):
    case_id = serializers.IntegerField(min_value=1)
    run_id = serializers.IntegerField(min_value=1)
    delivery_id = serializers.IntegerField(min_value=1)
