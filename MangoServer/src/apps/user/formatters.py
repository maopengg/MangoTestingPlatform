def format_user(instance):
    from src.apps.user.api.serializers.user import UserSerializers

    return UserSerializers(instance=instance).data if instance is not None else None


def format_user_simple(instance):
    from src.apps.user.api.serializers.user import UserSimpleSerializers

    return UserSimpleSerializers(instance=instance).data if instance is not None else None
