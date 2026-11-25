import hashlib
import json
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from src.apps.data_factory.schemas.cleanup_history import CleanupEventEvidence, CleanupHistoryEntry
from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService


class ResourceCleanupHistoryService:
    @classmethod
    def fail_pending(cls, execution_id, message):
        from src.apps.data_factory.models import DataFactoryExecutionItem
        from src.apps.data_factory.enums import DataFactoryCleanupStatusEnum
        from src.apps.data_factory.enums.cleanup_history import ResourceCleanupEventEnum
        rows = DataFactoryExecutionItem.objects.filter(execution_id=execution_id, cleanup_status__in=[
            DataFactoryCleanupStatusEnum.NOT_CLEANED.value, DataFactoryCleanupStatusEnum.SKIPPED.value,
            DataFactoryCleanupStatusEnum.PENDING_MANUAL.value]).only('id', 'cleanup_resources')
        for item in rows:
            state = item.cleanup_resources or {}
            if state.get('snapshots'):
                cls.append(ResourceCleanupEventEnum.FAILED, item=item, message=message,
                    sql_verified=state.get('sql_cleaned', False), snapshot_digest=cls.digest(state['snapshots']))

    @staticmethod
    def digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
            separators=(',', ':'), default=str).encode()).hexdigest()

    @staticmethod
    def entries(raw):
        from pydantic import ValidationError
        from src.apps.data_factory.exceptions import DataFactoryError, DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID
        try:
            if raw is not None and not isinstance(raw, dict):
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('资源证据结构损坏，保留原记录，禁止覆盖历史',))
            values = (raw or {}).get('cleanup_history', [])
            if not isinstance(values, list):
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('清理历史结构损坏，保留原证据，请管理员核查；禁止覆盖历史',))
            history = [CleanupHistoryEntry.model_validate(value).model_dump(mode='json', exclude_none=True) for value in values]
            if len({value['id'] for value in history}) != len(history):
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('清理历史存在重复事件编号，保留原证据，请管理员核查',))
            return history
        except ValidationError as error:
            raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID,
                value=('清理历史证据校验失败，保留原记录，请管理员核查；禁止覆盖历史',)) from error

    @classmethod
    def merge(cls, current, incoming, entry=None):
        # 仅追加服务器生成的事件，旧状态保存不能覆盖、裁剪或伪造已经持久化的历史。
        history = cls.entries(current)
        if entry is not None and not any(value['id'] == entry['id'] for value in history):
            history.append(CleanupHistoryEntry.model_validate(entry).model_dump(mode='json', exclude_none=True))
        return {**incoming, 'cleanup_history': history}

    @classmethod
    @transaction.atomic
    def save_factory_state(cls, item, fields):
        from src.apps.data_factory.models import DataFactoryExecutionItem
        current = DataFactoryExecutionItem.objects.select_for_update().only('cleanup_resources').get(id=item.id)
        item.cleanup_resources = cls.merge(current.cleanup_resources, item.cleanup_resources)
        item.save(update_fields=fields)

    @classmethod
    @transaction.atomic
    def append_factory(cls, item, entry):
        from src.apps.data_factory.models import DataFactoryExecutionItem
        current = DataFactoryExecutionItem.objects.select_for_update().only('cleanup_resources').get(id=item.id)
        raw = cls.merge(current.cleanup_resources, current.cleanup_resources, entry)
        current.cleanup_resources = raw
        current.save(update_fields=['cleanup_resources', 'update_time'])
        item.cleanup_resources = cls.merge(raw, item.cleanup_resources)

    @classmethod
    def append(cls, kind, *, item=None, resource=None, operator_id=None, **evidence):
        if item is not None:
            from src.apps.data_factory.schemas.cleanup_resource import CleanupResourceState
            from pydantic import ValidationError
            try:
                state = CleanupResourceState.model_validate(item.cleanup_resources or {})
            except ValidationError:
                state = None
            if state is not None:
                evidence.setdefault('checkpoints', state.checkpoints)
                evidence.setdefault('results', state.results)
        parsed = CleanupEventEvidence(**evidence)
        entry = CleanupHistoryEntry(id=uuid4().hex, create_time=timezone.now(), operator_id=operator_id,
            kind=kind.value, evidence=parsed).model_dump(mode='json', exclude_none=True)
        if item is not None:
            CleanupPersistenceService.write(lambda: cls.append_factory(item, entry))
        else:
            from src.apps.auto_api.services.resource_cleanup.resource_cleanup import ApiResourceCleanupService
            from src.apps.auto_api.schemas.resource_cleanup import ApiResourceProof
            ApiResourceCleanupService.persist(resource, ApiResourceProof.model_validate(resource.proof), _history_entry=entry)
        return entry
