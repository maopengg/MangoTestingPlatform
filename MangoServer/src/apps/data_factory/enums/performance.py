from src.common.enums.base import BaseEnum


class DatasourceQueueLaneEnum(BaseEnum):
    NORMAL = 'normal'
    CLEANUP = 'cleanup'
    METADATA = 'metadata'


class DatasourcePermitKindEnum(BaseEnum):
    OPERATION = 'operation'
    CONNECTION = 'connection'


class DatasourcePermitStateEnum(BaseEnum):
    ACTIVE = 'active'
    SUSPECT = 'suspect'


class DatasourceTimingPhaseEnum(BaseEnum):
    OPERATION_SLOT = 'operation_slot'
    CONNECTION_SLOT = 'connection_slot'
    LOCAL_POOL = 'local_pool'
    SQL_RATE = 'sql_rate'
    CONTROL_LOCK = 'control_lock'
    CONTROL_IO = 'control_io'
    SCHEDULER_RESUME = 'scheduler_resume'
    CONNECT = 'connect'
    EXECUTE = 'execute'
    FETCH = 'fetch'
