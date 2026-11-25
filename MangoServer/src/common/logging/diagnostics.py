import traceback


def safe_exception_diagnostics(error: Exception) -> tuple[int | None, str]:
    """驱动异常正文可能包含 SQL 参数；诊断只保留数字错误码与栈位置。"""
    code = None
    frames = []
    seen = set()
    current = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if code is None and current.args and type(current.args[0]) is int:
            code = current.args[0]
        frames.append(type(current).__name__)
        frames.extend(f'{frame.filename}:{frame.lineno} {frame.name}'
                      for frame in traceback.extract_tb(current.__traceback__))
        current = current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    return code, '\n'.join(frames)
