"""显式回调请求去重，与结束时才保存的执行审计分离。"""
import hashlib

from django.utils import timezone

from src.apps.data_factory.exceptions import (
    DataFactoryError, DATASOURCE_AUDIT_REQUEST_CONFLICT, SQL_AUDIT_REQUEST_RUNNING,
)
from src.apps.data_factory.schemas.execution_audit import DatasourceAuditRequestClaim
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.services.runtime_kv import RuntimeKV


class DatasourceAuditRequestService:
    @staticmethod
    def key(request_id):
        return 'audit-request:' + hashlib.sha256(request_id.encode()).hexdigest()

    @staticmethod
    def store():
        return RuntimeKV.namespace(RuntimeKVNamespaceEnum.DATASOURCE_GOVERNOR).independent()

    @classmethod
    def claim(cls, request_id, signature):
        from src.apps.system.services.runtime_center.process_identity import RuntimeProcessIdentity
        value = DatasourceAuditRequestClaim(request_id=request_id, signature=signature,
            owner=RuntimeProcessIdentity.current()['process_token'], created_at=timezone.now().isoformat())
        store = cls.store()
        with store.control_connection():
            if store.set_if_absent(cls.key(request_id), value.model_dump(mode='json'), ttl=None):
                return
            current = DatasourceAuditRequestClaim.model_validate(store.get(cls.key(request_id)))
        if current.signature != signature:
            raise DataFactoryError(DATASOURCE_AUDIT_REQUEST_CONFLICT)
        raise DataFactoryError(SQL_AUDIT_REQUEST_RUNNING, value=(request_id,))

    @classmethod
    def retire(cls, request_id):
        # 仅随已确认终态审计的保留期清理；未结束请求的凭据永不自动删除。
        store = cls.store()
        with store.control_connection():
            store.delete(cls.key(request_id))
