def format_department(instance):
    from src.apps.user.api.serializers.department import DepartmentSerializers

    return DepartmentSerializers(instance=instance).data if instance is not None else None
