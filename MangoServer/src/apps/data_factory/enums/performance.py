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
