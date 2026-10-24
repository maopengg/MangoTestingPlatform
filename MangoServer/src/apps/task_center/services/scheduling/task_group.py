import re

from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from mangotools.enums import StatusEnum

from src.apps.task_center.enums.execution import AutomationExecutionSceneEnum, AutomationExecutionScopeEnum, ReportRetentionPolicyEnum
from src.apps.task_center.enums.schedule import ScheduledTaskGroupSyncStatusEnum
from src.apps.task_center.exceptions import (
    SYSTEM_TASK_GROUP_TASK_NOT_FOUND,
    SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID,
    SYSTEM_TASK_GROUP_STABILITY_SCENE_CONFLICT,
    SYSTEM_TASK_GROUP_MODULE_TASK_NOT_ALLOWED,
    SYSTEM_TASK_GROUP_PROJECT_PRODUCT_TASK_NAME_DUPLICATED,
    TaskCenterError,
)
from src.apps.task_center.models import (
    ScheduledTaskGroup,
    ScheduledTaskGroupModule,
    Tasks,
    TasksDetails,
    TimeTasks,
)
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.task_center.services.selection.task_group_recent_results import TaskGroupRecentResultService
from src.apps.test_center.models import NoticeGroup, ProductModule, ProjectProduct
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.models import User


class ScheduledTaskGroupService:
    """维护模块任务组，并把公共配置物化为现有 Tasks 调度单元。"""

    TEMPLATE_FIELDS = {'任务组名称', '模块名称', '模块完整路径'}
    TEMPLATE_PATTERN = re.compile(r'\$\{\{([^{}]+)\}\}')
    LEGACY_TEMPLATE_TOKENS = {
        '{group_name}': '${{任务组名称}}',
        '{module_name}': '${{模块名称}}',
        '{module_full_path}': '${{模块完整路径}}',
    }
    DEFAULT_TASK_NAME_TEMPLATE = '【${{任务组名称}}】${{模块名称}}'

    @staticmethod
    def _product(project_product_id: int, *, lock: bool = False) -> ProjectProduct:
        queryset = ProjectProduct.objects
        if lock:
            queryset = queryset.select_for_update()
        product = queryset.select_related('project').filter(id=project_product_id).first()
        if product is None:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('请选择项目产品',))
        return product

    @staticmethod
    def _int_list(value, *, required: bool = False) -> list[int]:
        if value in (None, ''):
            value = []
        if not isinstance(value, (list, tuple, set)):
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('多选字段格式错误',))
        try:
            result = sorted({int(item.get('id') if isinstance(item, dict) else item) for item in value})
        except (TypeError, ValueError, AttributeError) as error:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('多选字段格式错误',),
                                  error=str(error)) from error
        if required and not result:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('必填多选字段不能为空',))
        return result

    @classmethod
    def _timing_ids(cls, value) -> list[int]:
        ids = cls._int_list(value, required=True)
        if TimeTasks.objects.filter(id__in=ids).count() != len(ids):
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('定时策略不存在',))
        return ids

    @classmethod
    def _modules(cls, product: ProjectProduct, value) -> list[ProductModule]:
        ids = cls._int_list(value, required=True)
        modules = list(
            ProductModuleService.with_full_paths(
                ProductModule.objects.filter(project_product_id=product.id, id__in=ids),
            )
        )
        if len(modules) != len(ids):
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('模块不存在或不属于当前产品',))
        selected = set(ids)
        for module in modules:
            current = module.parent
            while current is not None:
                if current.id in selected:
                    raise TaskCenterError(SYSTEM_TASK_GROUP_MODULE_TASK_NOT_ALLOWED,
                                          value=(f'{current.get_full_path()} / {module.get_full_path()}',),
                                          )
                current = current.parent if current.parent_id else None
        return sorted(modules, key=lambda item: (item.get_full_path(), item.id))

    @staticmethod
    def _notice(product: ProjectProduct, payload: dict) -> tuple[int, int | None, int]:
        try:
            is_notice = int(payload.get('is_notice', 0))
            fail_notice = int(payload.get('fail_notice', 0))
        except (TypeError, ValueError) as error:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('通知配置格式错误',),
                                  error=str(error)) from error
        if is_notice not in (0, 1) or fail_notice not in (0, 1):
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('通知开关只能是0或1',))
        notice_group_id = payload.get('notice_group')
        if isinstance(notice_group_id, dict):
            notice_group_id = notice_group_id.get('id')
        if notice_group_id in (None, ''):
            return is_notice, None, fail_notice
        notice = NoticeGroup.objects.filter(id=notice_group_id, project_id=product.project_id).first()
        if notice is None:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('通知组不存在',))
        return is_notice, notice.id, fail_notice

    @classmethod
    def _template(cls, value) -> str:
        template = str(value or cls.DEFAULT_TASK_NAME_TEMPLATE).strip()
        if not template:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('子任务名称模板不能为空',))
        for legacy_token, current_token in cls.LEGACY_TEMPLATE_TOKENS.items():
            template = template.replace(legacy_token, current_token)
        fields = set(cls.TEMPLATE_PATTERN.findall(template))
        unsupported = fields - cls.TEMPLATE_FIELDS
        if unsupported:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID,
                                  value=(f'名称模板不支持字段：{", ".join(sorted(unsupported))}',),
                                  )
        remaining = cls.TEMPLATE_PATTERN.sub('', template)
        if '{' in remaining or '}' in remaining:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID,
                                  value=('子任务名称模板格式错误',),
                                  )
        return template

    @classmethod
    def _render_task_name_template(
            cls,
            template: str,
            *,
            group_name: str,
            module: ProductModule,
    ) -> str:
        rendered = cls._template(template)
        values = {
            '任务组名称': group_name,
            '模块名称': module.name,
            '模块完整路径': module.get_full_path(),
        }
        for field, field_value in values.items():
            rendered = rendered.replace('$' + '{{' + field + '}}', field_value)
        return rendered

    @classmethod
    def normalize(cls, product: ProjectProduct, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('请求体必须是对象',))
        name = str(payload.get('name') or '').strip()
        if not name:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('请输入任务组名称',))
        try:
            status = int(payload.get('status', StatusEnum.FAIL.value))
            case_people = payload.get('case_people')
            case_people_id = int(case_people.get('id') if isinstance(case_people, dict) else case_people)
        except (TypeError, ValueError, AttributeError) as error:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('负责人或启用状态格式错误',),
                                  error=str(error)) from error
        if status not in (StatusEnum.FAIL.value, StatusEnum.SUCCESS.value):
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('启用状态只能是0或1',))
        if not User.objects.filter(id=case_people_id).exists():
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('负责人不存在',))
        test_envs = ScheduledTaskCaseSelectionService.normalize_test_envs(payload.get('test_envs'))
        case_types = ScheduledTaskCaseSelectionService.normalize_case_types(payload.get('case_types') or [])
        execution_scenes = ScheduledTaskCaseSelectionService.normalize_execution_scenes(
            payload.get('execution_scenes')
        )
        if not test_envs or not execution_scenes:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('测试环境和执行场景不能为空',))
        if (
            AutomationExecutionSceneEnum.STABILITY_MONITORING.value in execution_scenes
            and set(execution_scenes).intersection({
                AutomationExecutionSceneEnum.PRODUCTION_INSPECTION.value,
                AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value,
            })
        ):
            raise TaskCenterError(SYSTEM_TASK_GROUP_STABILITY_SCENE_CONFLICT)
        ScheduledTaskCaseSelectionService.validate_environments_rule(
            execution_scenes=execution_scenes,
            execution_scope=AutomationExecutionScopeEnum.MODULE.value,
            test_envs=test_envs,
        )
        is_notice, notice_group_id, fail_notice = cls._notice(product, payload)
        initial_policy = payload.get('new_task_report_retention_policy', ReportRetentionPolicyEnum.ALL.value)
        if not isinstance(initial_policy, str) or initial_policy not in ReportRetentionPolicyEnum.obj():
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('子任务报告保留策略无效',))
        return {
            'new_task_report_retention_policy': initial_policy,
            'name': name[:64],
            'module_objects': cls._modules(product, payload.get('module_ids')),
            'timing_ids': cls._timing_ids(payload.get('timing_strategies')),
            'test_envs': test_envs,
            'case_types': case_types,
            'execution_scenes': execution_scenes,
            'case_people_id': case_people_id,
            'status': status,
            'is_notice': is_notice,
            'notice_group_id': notice_group_id,
            'fail_notice': fail_notice,
            'task_name_template': cls._template(payload.get('task_name_template')),
        }

    @staticmethod
    def _group_values(data: dict, update_user_id: int | None) -> dict:
        return {
            'name': data['name'],
            'test_envs': data['test_envs'],
            'case_types': data['case_types'],
            'execution_scenes': data['execution_scenes'],
            'case_people_id': data['case_people_id'],
            'status': data['status'],
            'is_notice': data['is_notice'],
            'notice_group_id': data['notice_group_id'],
            'fail_notice': data['fail_notice'],
            'task_name_template': data['task_name_template'],
            'update_user_id': update_user_id,
        }

    @classmethod
    def _task_name(cls, group: ScheduledTaskGroup, module: ProductModule) -> str:
        return cls._render_task_name_template(
            group.task_name_template,
            group_name=group.name,
            module=module,
        )[:64]

    @classmethod
    def _task_values(
            cls,
            group: ScheduledTaskGroup,
            member: ScheduledTaskGroupModule,
            update_user_id: int | None,
    ) -> dict:
        return {
            'project_product_id': group.project_product_id,
            'module_id': member.module_id,
            'task_group_id': group.id,
            'task_group_revision': group.revision,
            'update_user_id': update_user_id,
            'test_envs': list(group.test_envs or []),
            'case_types': list(group.case_types or []),
            'execution_scenes': list(group.execution_scenes or []),
            'execution_scope': AutomationExecutionScopeEnum.MODULE.value,
            'name': cls._task_name(group, member.module),
            'case_people_id': group.case_people_id,
            'status': int(bool(group.status) and bool(member.child_enabled)),
            'is_notice': group.is_notice,
            'notice_group_id': group.notice_group_id,
            'fail_notice': group.fail_notice,
        }

    @classmethod
    def _sync_members(
            cls,
            group: ScheduledTaskGroup,
            modules: list[ProductModule],
            update_user_id: int | None,
            *,
            new_task_report_retention_policy: str = ReportRetentionPolicyEnum.ALL.value,
    ) -> dict:
        members = {
            item.module_id: item
            for item in ScheduledTaskGroupModule.objects.select_for_update()
            .filter(task_group=group)
            .select_related('module', 'module__parent', 'module__parent__parent', 'task')
        }
        desired_ids = {module.id for module in modules}
        created = updated = removed = 0
        for member in members.values():
            if member.module_id in desired_ids:
                continue
            if member.active:
                member.active = False
                member.sync_status = ScheduledTaskGroupSyncStatusEnum.ARCHIVED.value
                member.sync_error = ''
                member.save(update_fields=['active', 'sync_status', 'sync_error', 'update_time'])
                if member.task_id:
                    Tasks.objects.filter(id=member.task_id).update(
                        status=0,
                        task_group=None,
                        task_group_revision=group.revision,
                    )
                removed += 1
        for module in modules:
            member = members.get(module.id)
            if member is None:
                member = ScheduledTaskGroupModule.objects.create(
                    task_group=group,
                    module=module,
                    child_enabled=True,
                    active=True,
                )
            else:
                member.active = True
                member.module = module
            values = cls._task_values(group, member, update_user_id)
            if member.task_id:
                task = member.task
                for field, value in values.items():
                    setattr(task, field, value)
                task.save()
                updated += 1
            else:
                task = Tasks.objects.create(**values, report_retention_policy=new_task_report_retention_policy)
                member.task = task
                created += 1
            task.timing_strategies.set(group.timing_strategies.all())
            member.synced_revision = group.revision
            member.sync_status = ScheduledTaskGroupSyncStatusEnum.SYNCED.value
            member.sync_error = ''
            member.save()
        return {'create_count': created, 'update_count': updated, 'remove_count': removed}

    @classmethod
    @transaction.atomic
    def create(cls, payload: dict, update_user_id: int | None = None) -> dict:
        try:
            project_product_id = int(payload.get('project_product_id'))
        except (TypeError, ValueError) as error:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('请选择项目产品',),
                                  error=str(error)) from error
        product = cls._product(project_product_id, lock=True)
        data = cls.normalize(product, payload)
        try:
            group = ScheduledTaskGroup.objects.create(
                project_product=product,
                sync_status=ScheduledTaskGroupSyncStatusEnum.PENDING.value,
                **cls._group_values(data, update_user_id),
            )
            group.timing_strategies.set(data['timing_ids'])
            sync_result = cls._sync_members(group, data['module_objects'], update_user_id,
                new_task_report_retention_policy=data['new_task_report_retention_policy'])
            group.sync_status = ScheduledTaskGroupSyncStatusEnum.SYNCED.value
            group.save(update_fields=['sync_status', 'update_time'])
        except IntegrityError as error:
            raise TaskCenterError(SYSTEM_TASK_GROUP_PROJECT_PRODUCT_TASK_NAME_DUPLICATED, error=str(error)) from error
        return {'item': cls.serialize(group), **sync_result}

    @classmethod
    @transaction.atomic
    def update(cls, group_id: int, payload: dict, update_user_id: int | None = None) -> dict:
        group = ScheduledTaskGroup.objects.select_for_update().filter(id=group_id, archived=False).first()
        if group is None:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_NOT_FOUND)
        product = cls._product(group.project_product_id, lock=True)
        data = cls.normalize(product, payload)
        for field, value in cls._group_values(data, update_user_id).items():
            setattr(group, field, value)
        group.revision += 1
        group.sync_status = ScheduledTaskGroupSyncStatusEnum.PENDING.value
        try:
            group.save()
            group.timing_strategies.set(data['timing_ids'])
            sync_result = cls._sync_members(group, data['module_objects'], update_user_id)
            group.sync_status = ScheduledTaskGroupSyncStatusEnum.SYNCED.value
            group.save(update_fields=['sync_status', 'update_time'])
        except IntegrityError as error:
            raise TaskCenterError(SYSTEM_TASK_GROUP_PROJECT_PRODUCT_TASK_NAME_DUPLICATED, error=str(error)) from error
        return {'item': cls.serialize(group), **sync_result}

    @classmethod
    @transaction.atomic
    def delete(cls, group_id: int) -> None:
        group = ScheduledTaskGroup.objects.select_for_update().filter(id=group_id, archived=False).first()
        if group is None:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_NOT_FOUND)
        task_ids = list(Tasks.objects.filter(task_group=group).values_list('id', flat=True))
        ScheduledTaskGroupModule.objects.filter(task_group=group).delete()
        if task_ids:
            TasksDetails.objects.filter(task_id__in=task_ids).delete()
            Tasks.objects.filter(id__in=task_ids).delete()
        group.delete()

    @classmethod
    @transaction.atomic
    def set_member_enabled(
            cls,
            group_id: int,
            member_id: int,
            enabled: bool,
            update_user_id: int | None = None,
    ) -> dict:
        member = ScheduledTaskGroupModule.objects.select_for_update().select_related(
            'task_group', 'task', 'module'
        ).filter(id=member_id, task_group_id=group_id, active=True).first()
        if member is None or member.task_group.archived:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_NOT_FOUND)
        member.child_enabled = bool(enabled)
        member.save(update_fields=['child_enabled', 'update_time'])
        if member.task_id:
            member.task.status = int(bool(member.task_group.status) and member.child_enabled)
            member.task.update_user_id = update_user_id
            member.task.save(update_fields=['status', 'update_user', 'update_time'])
        return cls.serialize_member(member)

    @classmethod
    def preview(cls, payload: dict, group_id: int | None = None) -> dict:
        try:
            product_id = int(payload.get('project_product_id'))
        except (TypeError, ValueError) as error:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('请选择项目产品',),
                                  error=str(error)) from error
        data = cls.normalize(cls._product(product_id), payload)
        existing = {}
        if group_id:
            existing = {
                item.module_id: item
                for item in ScheduledTaskGroupModule.objects.filter(
                    task_group_id=group_id, active=True
                ).select_related('module', 'module__parent', 'module__parent__parent')
            }
        desired = {module.id: module for module in data['module_objects']}
        rows = []
        for module_id, module in desired.items():
            rows.append({
                'action': 'update' if module_id in existing else 'create',
                'module_id': module_id,
                'module_full_path': module.get_full_path(),
                'task_name': cls._render_task_name_template(
                    data['task_name_template'],
                    group_name=data['name'],
                    module=module,
                )[:64],
            })
        for module_id, member in existing.items():
            if module_id not in desired:
                rows.append({
                    'action': 'remove',
                    'module_id': module_id,
                    'module_full_path': member.module.get_full_path(),
                    'task_name': member.task.name if member.task_id else '-',
                })
        return {
            'create_count': sum(row['action'] == 'create' for row in rows),
            'update_count': sum(row['action'] == 'update' for row in rows),
            'remove_count': sum(row['action'] == 'remove' for row in rows),
            'rows': sorted(rows, key=lambda row: (row['module_full_path'], row['action'])),
        }

    @classmethod
    def queryset(cls):
        return ScheduledTaskGroup.objects.filter(archived=False).select_related(
            'project_product',
            'project_product__project',
            'case_people',
            'notice_group',
            'update_user',
        ).prefetch_related('timing_strategies').annotate(
            module_count=Count('members', filter=Q(members__active=True), distinct=True),
            enabled_task_count=Count(
                'members',
                filter=Q(members__active=True, members__task__status=1),
                distinct=True,
            ),
        )

    @classmethod
    def list(cls, filters: dict) -> dict:
        queryset = cls.queryset()
        project_product_id = filters.get('project_product_id')
        if project_product_id not in (None, ''):
            queryset = queryset.filter(project_product_id=project_product_id)
        project_product_ids = filters.get('project_product_ids')
        if project_product_ids is not None:
            queryset = queryset.filter(project_product_id__in=project_product_ids)
        module_ids = cls._int_list(filters.get('module_ids') or [])
        if module_ids:
            queryset = queryset.filter(members__active=True, members__module_id__in=module_ids)
        for field, caster in (
                ('test_envs', int),
                ('case_types', int),
                ('execution_scenes', str),
        ):
            raw_values = filters.get(field) or []
            if not isinstance(raw_values, (list, tuple, set)):
                raw_values = [raw_values]
            values = [caster(value) for value in raw_values if value not in (None, '')]
            if values:
                condition = Q()
                for value in values:
                    condition |= Q(**{f'{field}__contains': [value]})
                queryset = queryset.filter(condition)
        name = str(filters.get('name') or '').strip()
        if name:
            queryset = queryset.filter(name__icontains=name)
        for field in ('status', 'is_notice', 'sync_status'):
            value = filters.get(field)
            if value not in (None, ''):
                queryset = queryset.filter(**{field: value})
        count = queryset.distinct().count()
        try:
            page = max(1, int(filters.get('page') or 1))
            page_size = min(100, max(1, int(filters.get('page_size') or filters.get('pageSize') or 20)))
        except (TypeError, ValueError):
            page, page_size = 1, 20
        items = list(queryset.distinct()[(page - 1) * page_size:page * page_size])
        recent = TaskGroupRecentResultService.get_recent_results([item.id for item in items])
        return {
            'items': [{**cls.serialize(item), 'recent_results': recent.get(str(item.id), [])} for item in items],
            'count': count,
            'page': page,
            'page_size': page_size,
        }

    @classmethod
    def options(cls, project_product_ids: 'list[int] | None' = None) -> 'list[dict]':
        queryset = ScheduledTaskGroup.objects.filter(archived=False).select_related(
            'project_product',
            'project_product__project',
        )
        if project_product_ids is not None:
            queryset = queryset.filter(project_product_id__in=project_product_ids)
        return [
            {
                'key': group.id,
                'title': group.name,
                'project_product_id': group.project_product_id,
                'project_product_name': group.project_product.name,
                'project_name': group.project_product.project.name,
            }
            for group in queryset.order_by(
                'project_product__project__name',
                'project_product__name',
                'name',
                'id',
            )
        ]

    @classmethod
    def detail(cls, group_id: int) -> dict:
        group = cls.queryset().filter(id=group_id).first()
        if group is None:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_NOT_FOUND)
        data = cls.serialize(group)
        data['members'] = [
            cls.serialize_member(member)
            for member in ScheduledTaskGroupModule.objects.filter(
                task_group=group, active=True
            ).select_related('module', 'module__parent', 'module__parent__parent', 'task')
        ]
        return data

    @staticmethod
    def serialize_member(member: ScheduledTaskGroupModule) -> dict:
        return {
            'id': member.id,
            'module': {
                'id': member.module_id,
                'name': member.module.name,
                'full_path': member.module.get_full_path(),
                'level': member.module.level,
                'parent_id': member.module.parent_id,
            },
            'task_id': member.task_id,
            'task_name': member.task.name if member.task_id else '-',
            'child_enabled': member.child_enabled,
            'effective_enabled': bool(member.task.status) if member.task_id else False,
            'sync_status': member.sync_status,
            'sync_error': member.sync_error,
            'synced_revision': member.synced_revision,
        }

    @staticmethod
    def serialize(group: ScheduledTaskGroup) -> dict:
        module_count = getattr(group, 'module_count', None)
        enabled_task_count = getattr(group, 'enabled_task_count', None)
        if module_count is None:
            module_count = group.members.filter(active=True).count()
        if enabled_task_count is None:
            enabled_task_count = group.members.filter(active=True, task__status=1).count()
        return {
            'id': group.id,
            'name': group.name,
            'project_product': {
                'id': group.project_product_id,
                'name': group.project_product.name,
                'project': {
                    'id': group.project_product.project_id,
                    'name': group.project_product.project.name,
                },
            },
            'timing_strategies': [
                {'id': item.id, 'name': item.name, 'cron': item.cron}
                for item in group.timing_strategies.all()
            ],
            'test_envs': list(group.test_envs or []),
            'case_types': list(group.case_types or []),
            'execution_scenes': list(group.execution_scenes or []),
            'case_people': {
                'id': group.case_people_id,
                'name': group.case_people.name,
            },
            'status': group.status,
            'is_notice': group.is_notice,
            'fail_notice': group.fail_notice,
            'notice_group': (
                {'id': group.notice_group_id, 'name': group.notice_group.name}
                if group.notice_group_id else None
            ),
            'task_name_template': group.task_name_template,
            'revision': group.revision,
            'sync_status': group.sync_status,
            'module_count': module_count,
            'enabled_task_count': enabled_task_count,
            'update_user_name': getattr(group.update_user, 'name', None),
            'update_time': group.update_time.strftime('%Y-%m-%d %H:%M:%S') if group.update_time else None,
        }
