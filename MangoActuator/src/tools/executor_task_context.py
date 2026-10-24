from contextvars import ContextVar, Token


_executor_task_id: ContextVar[int | None] = ContextVar('executor_task_id', default=None)
_executor_connection_id: ContextVar[str | None] = ContextVar(
    'executor_task_connection_id',
    default=None,
)
_executor_task_metadata: ContextVar[dict] = ContextVar(
    'executor_task_metadata',
    default={},
)


def set_executor_task_id(
        task_id: int,
        connection_id: str | None = None,
        **metadata,
) -> tuple[Token, Token, Token]:
    clean_metadata = {
        str(key): value
        for key, value in metadata.items()
        if value not in (None, '')
    }
    return (
        _executor_task_id.set(task_id),
        _executor_connection_id.set(connection_id),
        _executor_task_metadata.set(clean_metadata),
    )


def reset_executor_task_id(token: tuple[Token, ...]) -> None:
    task_token, connection_token, *metadata_tokens = token
    _executor_task_id.reset(task_token)
    _executor_connection_id.reset(connection_token)
    if metadata_tokens:
        _executor_task_metadata.reset(metadata_tokens[0])


def is_executor_task() -> bool:
    return _executor_task_id.get() is not None


def get_executor_task_context() -> tuple[int | None, str | None]:
    return _executor_task_id.get(), _executor_connection_id.get()


def get_executor_task_log_context() -> dict:
    task_id, connection_id = get_executor_task_context()
    context = dict(_executor_task_metadata.get())
    if connection_id:
        context['connection_id'] = connection_id
    if task_id is not None:
        context = {'task_id': task_id, **context}
    return context


def format_executor_task_log(message: str, **extra) -> str:
    context = get_executor_task_log_context()
    context.update({key: value for key, value in extra.items() if value not in (None, '')})
    if not context:
        return message
    fields = ', '.join(f'{key}={value}' for key, value in context.items())
    return f'{message} [{fields}]'
