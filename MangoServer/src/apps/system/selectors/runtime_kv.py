from django.db.models import Q
from django.db.models.functions import Now

from src.apps.system.models import RuntimeKVEntry


class RuntimeKVSelector:
    @staticmethod
    def active(namespace, using='default'):
        return RuntimeKVEntry.objects.using(using).filter(namespace=namespace).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=Now()),
        ).annotate(kv_now=Now())

    @classmethod
    def entries(cls, namespace, keys, using='default'):
        return cls.active(namespace, using).filter(key__in=keys)

    @classmethod
    def scan(cls, namespace, prefix='', after_id=0, page_size=100, using='default'):
        # 扫描仅返回元数据，不读取敏感值；游标避免大 OFFSET。
        return cls.active(namespace, using).filter(key__startswith=prefix, id__gt=after_id).order_by('id').defer(
            'value',
        )[:page_size]
