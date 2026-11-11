"""按已授权查询集读取 JSON ID 引用，不加载配置正文或执行数据。"""
from django.db import connections
from django.db.models import BooleanField, F, Func, JSONField, Value


def collect_json_references(queryset, owner_field, reference_field, target_ids):
    targets = set(target_ids)
    result = {target_id: set() for target_id in targets}
    if not targets:
        return result
    if connections[queryset.db].vendor == 'mysql':
        queryset = queryset.annotate(_reference_match=Func(
            F(reference_field), Value([*targets, *map(str, targets)], output_field=JSONField()),
            function='JSON_OVERLAPS', output_field=BooleanField(),
        )).filter(_reference_match=True)
    for owner_id, references in queryset.values_list(owner_field, reference_field).iterator(chunk_size=1000):
        if not isinstance(references, list):
            continue
        for reference in references:
            if type(reference) is int:
                reference_id = reference
            elif isinstance(reference, str) and reference.isascii() and reference.isdecimal():
                reference_id = int(reference)
            else:
                continue
            if reference_id in targets:
                result[reference_id].add(owner_id)
    return result


def reference_case_page(queryset, case_ids, page, page_size):
    cases = queryset.filter(id__in=case_ids).order_by('id')
    count = cases.count()
    cases = cases.select_related('project_product', 'case_people', 'update_user').only(
        'id', 'name', 'scenario_tags', 'update_time', 'case_people__name', 'update_user__name', 'project_product__name',
    )
    rows = [{
        'case_id': case.id, 'case_name': case.name,
        'scenario_tags': case.scenario_tags,
        'case_people_name': case.case_people.name if case.case_people_id else '',
        'update_user_name': case.update_user.name if case.update_user_id else '',
        'update_time': case.update_time.strftime('%Y-%m-%d %H:%M:%S'),
        'project_product_id': case.project_product_id,
        'project_product_name': case.project_product.name,
    } for case in cases[(page - 1) * page_size:page * page_size]]
    return rows, count
