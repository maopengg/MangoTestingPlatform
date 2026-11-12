from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.services.runtime_kv import RuntimeKV


class ActuatorConfigRuntimeService:
    """请求与回调共用结果存储；值包含 status、username 及可选 config/message。"""

    @staticmethod
    def set_snapshot(request_id: str, data: dict):
        return RuntimeKV.namespace(RuntimeKVNamespaceEnum.ACTUATOR_CONFIG).set(
            f'snapshot:{request_id}', data,
        )

    @staticmethod
    def get_snapshot(request_id: str):
        return RuntimeKV.namespace(RuntimeKVNamespaceEnum.ACTUATOR_CONFIG).get(f'snapshot:{request_id}')

    @staticmethod
    def set_save_result(request_id: str, data: dict):
        return RuntimeKV.namespace(RuntimeKVNamespaceEnum.ACTUATOR_CONFIG).set(
            f'save:{request_id}', data,
        )

    @staticmethod
    def get_save_result(request_id: str):
        return RuntimeKV.namespace(RuntimeKVNamespaceEnum.ACTUATOR_CONFIG).get(f'save:{request_id}')
