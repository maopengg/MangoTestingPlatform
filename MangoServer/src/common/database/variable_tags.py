from django.db import transaction
from django.utils import timezone

from src.common.enums.variable_tags import VariableTagOperationEnum
from src.common.exceptions import MangoServerError, SAVE_VALIDATION_FAILED
from src.common.utils.variable_tags import normalize_variable_tags


@transaction.atomic
def update_variable_tags(queryset, ids, tags, operation, operator_id):
    tags = normalize_variable_tags(tags)
    if type(operation) is not int or operation not in VariableTagOperationEnum.get_key_list():
        raise MangoServerError(SAVE_VALIDATION_FAILED, value=({'tags': ['请选择有效的分类操作']},))
    if not isinstance(ids, list) or not ids or len(ids) > 200 or any(
            not ((type(i) is int and i > 0) or (isinstance(i, str) and i.isascii() and i.isdecimal() and int(i) > 0))
            for i in ids):
        raise MangoServerError(SAVE_VALIDATION_FAILED, value=({'ids': ['请选择1至200条变量记录']},))
    ids = [int(i) for i in ids]
    rows = list(queryset.filter(id__in=ids).select_for_update().order_by('id'))
    if len(rows) != len(set(ids)):
        raise MangoServerError(SAVE_VALIDATION_FAILED, value=({'ids': ['部分变量不存在或无权修改，请刷新后重试']},))
    changes = []
    for row in rows:
        current = row.tags or []
        if operation == VariableTagOperationEnum.ADD.value:
            updated = normalize_variable_tags(current + tags)
        elif operation == VariableTagOperationEnum.REMOVE.value:
            updated = [tag for tag in current if tag not in tags]
        else:
            updated = tags
        if updated == current:
            continue
        changes.append((row, updated))
    for row, updated in changes:
        row.tags = updated
        row.update_user_id = operator_id
        row.update_time = timezone.now()
        row.save(update_fields=['tags', 'update_user', 'update_time'])
    return {'count': len(rows)}
