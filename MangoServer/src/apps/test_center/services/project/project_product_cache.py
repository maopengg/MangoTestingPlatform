from collections.abc import Callable
from typing import TypeVar

from django.core.cache import cache

T = TypeVar('T')


class ProjectProductCacheService:
    CACHE_TIMEOUT = 60 * 5
    KEY_PREFIX = 'system:project-product:options:v1'

    @classmethod
    def key(cls, project_id: int) -> str:
        return f'{cls.KEY_PREFIX}:{int(project_id)}'

    @classmethod
    def get_options(
            cls,
            project_id: int,
            loader: Callable[[], T] | None = None,
    ) -> T:
        key = cls.key(project_id)
        cached = cache.get(key)
        if cached is not None:
            return cached
        data = loader() if loader else cls._load_options(project_id)
        cache.set(key, data, cls.CACHE_TIMEOUT)
        return data

    @staticmethod
    def _load_options(project_id: int) -> list[dict]:
        from src.apps.test_center.models import ProjectProduct

        products = ProjectProduct.objects.filter(
            project_id=project_id
        ).values_list('id', 'name')
        return [
            {'value': product_id, 'label': product_name}
            for product_id, product_name in products
        ]

    @classmethod
    def invalidate(cls, project_id: int | None) -> None:
        if project_id:
            cache.delete(cls.key(project_id))

    @classmethod
    def invalidate_many(cls, project_ids) -> None:
        keys = [
            cls.key(project_id)
            for project_id in set(project_ids)
            if project_id
        ]
        if keys:
            cache.delete_many(keys)
