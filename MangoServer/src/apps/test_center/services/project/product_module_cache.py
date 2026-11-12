from collections.abc import Callable
from typing import TypeVar

from django.core.cache import cache

T = TypeVar('T')


class ProductModuleCacheService:
    CACHE_TIMEOUT = 60 * 5
    TREE_KEY_PREFIX = 'system:product-module:tree:v1'
    NAME_KEY_PREFIX = 'system:product-module:name:v1'

    @classmethod
    def tree_key(cls, project_product_id: int) -> str:
        return f'{cls.TREE_KEY_PREFIX}:{int(project_product_id)}'

    @classmethod
    def name_key(cls, project_product_id: int) -> str:
        return f'{cls.NAME_KEY_PREFIX}:{int(project_product_id)}'

    @classmethod
    def get_tree(cls, project_product_id: int, loader: Callable[[], T]) -> T:
        return cls._get_or_set(cls.tree_key(project_product_id), loader)

    @classmethod
    def get_names(cls, project_product_id: int, loader: Callable[[], T]) -> T:
        return cls._get_or_set(cls.name_key(project_product_id), loader)

    @classmethod
    def _get_or_set(cls, key: str, loader: Callable[[], T]) -> T:
        cached = cache.get(key)
        if cached is not None:
            return cached
        data = loader()
        cache.set(key, data, cls.CACHE_TIMEOUT)
        return data

    @classmethod
    def invalidate(cls, project_product_id: int | None) -> None:
        if not project_product_id:
            return
        cache.delete_many([
            cls.tree_key(project_product_id),
            cls.name_key(project_product_id),
        ])

    @classmethod
    def invalidate_many(cls, project_product_ids) -> None:
        keys = []
        for project_product_id in set(project_product_ids):
            if not project_product_id:
                continue
            keys.extend([
                cls.tree_key(project_product_id),
                cls.name_key(project_product_id),
            ])
        if keys:
            cache.delete_many(keys)
