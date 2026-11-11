"""仅保存可重建的变量分类查询结果，不保存变量值或执行上下文。"""
import hashlib
import json
from uuid import uuid4

from django.core.cache import cache
from django.core.exceptions import EmptyResultSet
from django.db import connections, transaction

from src.common.logging import log


class VariableTagSummaryCache:
    TIMEOUT = 60
    REVISION_TIMEOUT = 120
    PREFIX = 'variable-tags:v1'

    @classmethod
    def revision_key(cls, model_label, using):
        return f'{cls.PREFIX}:revision:{using}:{model_label}'

    @classmethod
    def get(cls, queryset, loader):
        using = queryset.db
        # 原子事务可能读到自身尚未提交的数据，不能发布到跨请求缓存。
        if connections[using].in_atomic_block:
            return loader()
        try:
            # 使用已完成权限过滤的查询指纹，包含产品范围和全部筛选条件。
            sql, params = queryset.order_by().values('pk').query.get_compiler(using=using).as_sql()
        except EmptyResultSet:
            return {'total': 0, 'untagged': 0, 'items': []}
        model_label = queryset.model._meta.label_lower
        try:
            revision_key = cls.revision_key(model_label, using)
            revision = cache.get(revision_key)
            if revision is None:
                cache.add(revision_key, uuid4().hex, cls.REVISION_TIMEOUT)
                revision = cache.get(revision_key)
            if revision is None:
                return loader()
            fingerprint = json.dumps([using, model_label, sql, params, revision], default=str,
                                     ensure_ascii=False, separators=(',', ':'))
            key = f'{cls.PREFIX}:summary:{hashlib.sha256(fingerprint.encode()).hexdigest()}'
            result = cache.get(key)
        except Exception:
            log.system.warning('变量分类查询缓存不可用，本次直接查询数据库')
            return loader()
        if result is not None:
            return result
        result = loader()
        try:
            # 若写入同时提交，结果仍只属于旧版本键，后续查询不会命中旧结果。
            cache.set(key, result, cls.TIMEOUT)
        except Exception:
            log.system.warning('变量分类查询结果未缓存，不影响本次查询结果')
        return result

    @classmethod
    def invalidate(cls, model_label, using='default'):
        try:
            # 切换版本令全部筛选条件下的旧结果失效，旧键最多60秒自动过期。
            cache.set(cls.revision_key(model_label, using), uuid4().hex, cls.REVISION_TIMEOUT)
        except Exception:
            log.system.warning('变量分类缓存失效失败，旧查询结果将按短期TTL自动过期')

    @classmethod
    def invalidate_after_commit(cls, model_label, using='default'):
        transaction.on_commit(lambda: cls.invalidate(model_label, using), using=using)
