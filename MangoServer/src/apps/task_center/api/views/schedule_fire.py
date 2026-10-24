from src.apps.task_center.api.serializers.schedule_fire import ScheduleFireSerializers, ScheduleFireSerializersC
from src.apps.task_center.models import ScheduleFire
from src.common.responses.model_crud import ModelCRUD


class ScheduleFireCRUD(ModelCRUD):
    model = ScheduleFire
    queryset = ScheduleFire.objects.all()
    serializer_class = ScheduleFireSerializersC
    serializer = ScheduleFireSerializers
    page_permission_key = 'timing.fire_record'
