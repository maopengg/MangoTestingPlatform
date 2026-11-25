from django.db import InterfaceError, OperationalError, connections

from src.common.logging import log
from src.common.logging.diagnostics import safe_exception_diagnostics


def is_connection_lost(error):
    code, _ = safe_exception_diagnostics(error)
    return isinstance(error, (InterfaceError, OperationalError)) and code in (0, 2006, 2013, 2055)


def read_with_connection_recovery(read, *, using='default'):
    """仅用于已核对无写入的 ORM 查询；事务内不重连，不包装整个工具或业务流程。"""
    try:
        return read()
    except (InterfaceError, OperationalError) as error:
        connection = connections[using]
        if connection.in_atomic_block or not is_connection_lost(error):
            raise
        code, _ = safe_exception_diagnostics(error)
        connection.close()
        log.system.warning('event=readonly_connection_recovery exception_type=%s driver_error_number=%s attempt=1',
                           type(error).__name__, code)
        return read()
