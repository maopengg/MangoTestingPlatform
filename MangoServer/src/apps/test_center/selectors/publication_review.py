from mangotools.enums import StatusEnum

from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.data_factory.enums.execution import DataFactoryExecutionStageEnum


def publication_configuration_summary(content, *, include_content=True):
    """描述待审核配置，不按场景标签推断业务安全或审批结论。"""
    items = list(content.get('review_items') or []) if include_content else []
    configuration_details = []
    counts = {'sql_count': 0, 'factory_count': 0, 'custom_count': 0, 'public_count': 0}
    fields = {
        'front_sql': ('前置 SQL', 'sql_count'), 'posterior_sql': ('后置 SQL', 'sql_count'),
        'ass_sql': ('SQL 断言', 'sql_count'), 'sql': ('SQL 步骤', 'sql_count'),
        'sql_execute': ('SQL 执行配置', 'sql_count'), 'data_factory_configs': ('数据工厂', 'factory_count'),
        'front_func': ('前置函数', 'custom_count'), 'posterior_func': ('后置函数', 'custom_count'),
        'func': ('Python 函数', 'custom_count'), 'front_custom': ('前置自定义', 'custom_count'),
        'custom': ('自定义变量', 'custom_count'), 'front_public': ('公共变量', 'public_count'),
        'front_auth_config': ('授权配置', None),
    }
    containers = {'api_case': '用例', 'api_case_detailed': '接口步骤', 'api_case_detailed_parameter': '参数场景',
                  'api_info_snapshot': '接口修订', 'payload': '', 'api_info': '接口',
                  'dependencies': '依赖', 'nodes': '页面节点', 'public_dependencies': '公共变量依赖',
                  'precondition': '节点前置', 'postcondition': '节点后置'}

    def safe_configuration(value):
        if isinstance(value, list):
            return [safe_configuration(item) for item in value]
        if isinstance(value, dict):
            def sensitive(key):
                normalized = str(key).lower().replace('-', '_')
                return any(part in normalized for part in ('password', 'secret', 'authorization', 'token', 'api_key', 'cookie'))
            secret_value = any(sensitive(value.get(key, '')) for key in ('key', 'name', 'field_name'))
            return {key: '***' if sensitive(key) or (key == 'value' and secret_value) else safe_configuration(item)
                    for key, item in value.items()}
        return value

    def text(value):
        if isinstance(value, str):
            return value[:4000] + ('\n（内容较长，请在用例详情查看完整配置）' if len(value) > 4000 else '')
        if isinstance(value, dict):
            # 只取操作内容，不把连接、凭证、请求头等配置一起返回。
            for key in ('sql', 'func', 'code', 'name', 'description'):
                if value.get(key):
                    return text(value[key])
            if value.get('actual'):
                return f"实际表达式／SQL：{text(value['actual'])}\n断言方法：{value.get('method') or '未设置'}\n预期值：{text(value.get('expect') or '')}"
            if value.get('key'):
                return f"变量：{value['key']}"
            return '已配置；字段：' + '、'.join(str(key) for key in value if key.lower() not in (
                'password', 'token', 'authorization', 'secret', 'api_key', 'headers', 'connection',
            ))
        return f'引用 ID：{value}'

    def visit(value, path):
        if isinstance(value, list):
            for index, item in enumerate(value, 1):
                visit(item, f'{path} #{index}')
        elif isinstance(value, dict):
            for key, item in value.items():
                if key in fields and item:
                    label, counter = fields[key]
                    entries = item if isinstance(item, list) else [item]
                    if counter:
                        counts[counter] += len(entries)
                    if not include_content:
                        continue
                    for index, entry in enumerate(entries, 1):
                        description = text(entry)
                        if key == 'data_factory_configs' and isinstance(entry, dict):
                            stage = DataFactoryExecutionStageEnum.obj().get(entry.get('stage'), '未设置')
                            template = entry.get('template__name') or entry.get('template_id') or entry.get('template') or '未设置'
                            description = f'{description}\n执行阶段：{stage}\n模板：{template}'
                        items.append({'label': f'{path} / {label} #{index}', 'content': description})
                        if counter in ('sql_count', 'factory_count'):
                            kind = 'sql' if counter == 'sql_count' else 'data_factory'
                            allowed = ('sql', 'actual', 'expect', 'method', 'name', 'key', 'value', 'global_variable_id', '说明') if kind == 'sql' else (
                                'id', 'name', 'source_type', 'source_id', 'stage', 'status', 'sort',
                                'template', 'template_id', 'template__name', 'cleanup_strategy', 'field_overrides',
                            )
                            configuration = {key: entry[key] for key in allowed if key in entry} if isinstance(entry, dict) else {'value': entry}
                            configuration_details.append({
                                'kind': kind, 'location': f'{path} / {label} #{index}',
                                'enabled': (entry['status'] == StatusEnum.SUCCESS.value) if isinstance(entry, dict) and 'status' in entry else None,
                                'configuration': safe_configuration(configuration),
                            })
                elif key in containers:
                    visit(item, ' / '.join(part for part in (path, containers[key]) if part))

    visit(content, '配置')
    return {**counts, 'configuration_items': items, 'configuration_details': configuration_details}


def publication_review_summary(case, *, product, case_type, status, is_pending, content, operator_id, revision=None):
    eligibility = []
    if not is_pending:
        eligibility.append('当前不是预发布状态')
    if case.status != StatusEnum.SUCCESS.value:
        eligibility.append('用例尚未处于执行通过状态')
    if not TestCenterQuerySelector.is_project_product_owner(product.id, operator_id):
        eligibility.append('只有项目产品负责人可以通过发布')
    latest = TestCenterQuerySelector.test_suite_details().filter(
        case_id=case.id, type=case_type, test_suite__project_product_id=product.id,
    ).order_by('-id').values('id', 'status', 'create_time', 'test_suite__test_env', 'api_case_revision_id').first()
    if latest:
        latest['test_env'] = latest.pop('test_suite__test_env')
        latest['create_time'] = latest['create_time'].isoformat() if latest['create_time'] else None
        latest['matches_revision'] = latest['api_case_revision_id'] == revision.id if revision else None
    return {'id': case.id, 'name': case.name, 'owner': case.case_people.name if case.case_people else '未设置',
            'product': product.name, 'module': case.module.get_full_path() if case.module else '未设置',
            'status': case.status, 'publication_status': status, 'scenario_tags': case.scenario_tags or [],
            'description': case.scenario_description or '', 'latest_execution': latest,
            'revision': f'r{revision.revision_no}' if revision else None,
            'steps': content.get('steps', []), 'step_details': content.get('step_details', []),
            'eligibility_reasons': eligibility, **publication_configuration_summary(content)}
