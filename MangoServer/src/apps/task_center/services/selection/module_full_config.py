from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from mangotools.enums import StatusEnum

from src.apps.task_center.enums.execution import AutomationExecutionScopeEnum
from src.apps.task_center.exceptions import (
    SYSTEM_TASK_CATEGORY_MINIMUM_REQUIRED,
    SYSTEM_TASK_MODULE_CONFIG_PROJECT_PRODUCT_MODULE_TASK_CONFIG_REQUIRED,
    SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID,
    SYSTEM_TASK_MODULE_CONFIG_MODULE_TASK_DUPLICATED,
    TaskCenterError,
)
from src.apps.task_center.models import Tasks, TimeTasks
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.test_center.models import NoticeGroup, ProductModule, ProjectProduct
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.models import User


class ModuleFullTaskConfigService:
    """按项目产品批量维护模块全量任务，一行配置对应一条 Tasks。"""

    @staticmethod
    def _product(project_product_id: int, *, lock: bool = False) -> ProjectProduct:
        queryset = ProjectProduct.objects
        if lock:
            queryset = queryset.select_for_update()
        product = queryset.select_related('project').filter(id=project_product_id).first()
        if product is None:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_PROJECT_PRODUCT_MODULE_TASK_CONFIG_REQUIRED)
        return product

    @staticmethod
    def _identity(task_or_row) -> tuple:
        if isinstance(task_or_row, dict):
            return (
                task_or_row['project_product_id'], task_or_row['module_id'],
                tuple(ModuleFullTaskConfigService._normalized_int_values(
                    task_or_row['test_envs'],
                )),
                tuple(ModuleFullTaskConfigService._normalized_int_values(
                    task_or_row['case_types'],
                )),
                tuple(sorted(set(task_or_row['execution_scenes']))), task_or_row['execution_scope'],
            )
        return (
            task_or_row.project_product_id, task_or_row.module_id,
            tuple(ModuleFullTaskConfigService._normalized_int_values(task_or_row.test_envs)),
            tuple(ModuleFullTaskConfigService._normalized_int_values(task_or_row.case_types)),
            tuple(sorted(set(task_or_row.execution_scenes or []))),
            task_or_row.execution_scope,
        )

    @staticmethod
    def _normalized_int_values(value) -> list[int]:
        return sorted({int(item) for item in (value or [])})

    @staticmethod
    def _payload_list(payload: dict, plural_key: str, singular_key: str) -> list:
        value = payload.get(plural_key)
        if value is not None:
            return value
        singular = payload.get(singular_key)
        return [] if singular in (None, '') else [singular]

    @staticmethod
    def _timing_ids(value) -> list[int]:
        if not isinstance(value, list) or not value:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_MINIMUM_REQUIRED)
        try:
            ids = sorted({int(item) for item in value})
        except (TypeError, ValueError) as error:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID, error=str(error)) from error
        if TimeTasks.objects.filter(id__in=ids).count() != len(ids):
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID)
        return ids

    @staticmethod
    def _notice(product: ProjectProduct, payload: dict) -> tuple[int, int | None, int]:
        try:
            is_notice = int(payload.get('is_notice', 0))
            fail_notice = int(payload.get('fail_notice', 0))
        except (TypeError, ValueError) as error:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID, error=str(error)) from error
        if is_notice not in (0, 1) or fail_notice not in (0, 1):
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID)
        notice_group_id = payload.get('notice_group')
        if notice_group_id in (None, ''):
            return is_notice, None, fail_notice if is_notice else 0
        notice = NoticeGroup.objects.filter(id=notice_group_id, project_id=product.project_id).first()
        if notice is None:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID)
        return is_notice, notice.id, fail_notice if is_notice else 0

    @classmethod
    def _normalize(cls, product: ProjectProduct, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID)
        try:
            module_id = int(payload.get('module_id'))
            environments = ScheduledTaskCaseSelectionService.normalize_test_envs(
                cls._payload_list(payload, 'test_envs', 'test_env'),
            )
            case_types = ScheduledTaskCaseSelectionService.normalize_case_types(
                cls._payload_list(payload, 'case_types', 'case_type'),
            )
            scenes = ScheduledTaskCaseSelectionService.normalize_execution_scenes(
                cls._payload_list(payload, 'execution_scenes', 'execution_scene'),
            )
            status = int(payload.get('status', StatusEnum.SUCCESS.value))
            case_people_id = int(payload.get('case_people'))
        except (TypeError, ValueError, IndexError) as error:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID, error=str(error)) from error
        module = ProductModule.objects.select_related('parent', 'parent__parent').filter(
            id=module_id,
            project_product_id=product.id,
        ).first()
        name = str(payload.get('name') or '').strip()
        if (
                module is None
                or not name
                or not environments
                or not scenes
                or not User.objects.filter(id=case_people_id).exists()
        ):
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID)
        if status not in (StatusEnum.FAIL.value, StatusEnum.SUCCESS.value):
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID)
        ScheduledTaskCaseSelectionService.validate_environments_rule(
            execution_scenes=scenes,
            execution_scope=AutomationExecutionScopeEnum.MODULE.value,
            test_envs=environments,
        )
        is_notice, notice_group_id, fail_notice = cls._notice(product, payload)
        return {
            'task_id': payload.get('task_id'),
            'project_product_id': product.id,
            'module_id': module.id,
            'module': module,
            'module_full_path': module.get_full_path(),
            'name': name,
            'test_envs': environments,
            'case_types': case_types,
            'execution_scenes': scenes,
            'execution_scope': AutomationExecutionScopeEnum.MODULE.value,
            'timing_ids': cls._timing_ids(payload.get('timing_strategies')),
            'api_concurrency_limit': ApiConcurrencyService.validate_optional(
                payload.get('api_concurrency_limit'), TaskCenterError,
            ),
            'is_notice': is_notice,
            'notice_group_id': notice_group_id,
            'fail_notice': fail_notice,
            'case_people_id': case_people_id,
            'status': status,
        }

    @staticmethod
    def _ancestor_ids(module: ProductModule) -> set[int]:
        result = set()
        current = module.parent
        while current is not None:
            result.add(current.id)
            current = current.parent
        return result

    @classmethod
    def _exclude_submitted_descendants(cls, rows: list[dict]) -> list[dict]:
        configured_module_ids = {row['module_id'] for row in rows}
        return [
            row for row in rows
            if not cls._ancestor_ids(row['module']).intersection(configured_module_ids)
        ]

    @staticmethod
    def _task_name(row: dict) -> str:
        return row['name'][:64] if row['name'] else f'模块全量/{row["module_full_path"]}'[:64]

    @classmethod
    def _values(cls, row: dict, update_user_id: int | None) -> dict:
        return {
            'project_product_id': row['project_product_id'],
            'module_id': row['module_id'],
            'test_envs': row['test_envs'],
            'case_types': row['case_types'],
            'execution_scenes': row['execution_scenes'],
            'execution_scope': AutomationExecutionScopeEnum.MODULE.value,
            'name': cls._task_name(row),
            'case_people_id': row['case_people_id'],
            'status': row['status'],
            'is_notice': row['is_notice'],
            'notice_group_id': row['notice_group_id'],
            'fail_notice': row['fail_notice'],
            'api_concurrency_limit': row['api_concurrency_limit'],
            'update_user_id': update_user_id,
        }

    @classmethod
    def _covered_task_ids(cls, tasks: list[Tasks], module_ids: set[int], exclude_ids=None) -> list[int]:
        excluded = set(exclude_ids or [])
        return [
            task.id for task in tasks
            if task.id not in excluded
               and task.module is not None
               and cls._ancestor_ids(task.module).intersection(module_ids)
        ]

    @classmethod
    @transaction.atomic
    def create_rows(cls, project_product_id: int, rows, update_user_id: int | None = None) -> dict:
        product = cls._product(project_product_id, lock=True)
        if not isinstance(rows, list) or not rows:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID)
        normalized = cls._exclude_submitted_descendants([
            cls._normalize(product, row) for row in rows
        ])
        identities = [cls._identity(row) for row in normalized]
        if len(identities) != len(set(identities)):
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_TASK_DUPLICATED, value=('当前提交中存在重复配置',))
        existing = list(Tasks.objects.select_for_update().filter(
            project_product_id=product.id,
            execution_scope=AutomationExecutionScopeEnum.MODULE.value,
        ).select_related('module', 'module__parent', 'module__parent__parent'))
        incoming_module_ids = {row['module_id'] for row in normalized}
        for row in normalized:
            ancestor_ids = cls._ancestor_ids(row['module'])
            if any(task.module_id in ancestor_ids for task in existing):
                raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_TASK_DUPLICATED,
                                      value=('所选模块已由上级任务组覆盖',),
                                      )
        covered_ids = cls._covered_task_ids(existing, incoming_module_ids)
        remaining_identities = {
            cls._identity(task) for task in existing if task.id not in covered_ids
        }
        if any(identity in remaining_identities for identity in identities):
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_TASK_DUPLICATED, value=('任务组配置已存在',))
        created = []
        try:
            for row in normalized:
                task = Tasks.objects.create(**cls._values(row, update_user_id))
                task.timing_strategies.set(row['timing_ids'])
                created.append(task)
            if covered_ids:
                Tasks.objects.filter(id__in=covered_ids).delete()
        except IntegrityError as error:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_TASK_DUPLICATED, error=str(error)) from error
        except ProtectedError as error:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID, error=str(error)) from error
        return {
            'create_count': len(created),
            'delete_count': len(covered_ids),
            'items': [cls.serialize(task) for task in created],
        }

    @classmethod
    @transaction.atomic
    def update_row(cls, task_id: int, payload: dict, update_user_id: int | None = None) -> dict:
        task_ref = Tasks.objects.filter(
            id=task_id,
            execution_scope=AutomationExecutionScopeEnum.MODULE.value,
        ).values('project_product_id').first()
        if task_ref is None:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID)
        product = cls._product(task_ref['project_product_id'], lock=True)
        task = Tasks.objects.select_for_update().filter(
            id=task_id,
            project_product_id=product.id,
            execution_scope=AutomationExecutionScopeEnum.MODULE.value,
        ).first()
        if task is None:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID)
        row = cls._normalize(product, payload)
        existing = list(Tasks.objects.select_for_update().filter(
            project_product_id=product.id,
            execution_scope=AutomationExecutionScopeEnum.MODULE.value,
        ).select_related('module', 'module__parent', 'module__parent__parent'))
        covered_ids = cls._covered_task_ids(existing, {row['module_id']}, exclude_ids={task.id})
        ancestor_ids = cls._ancestor_ids(row['module'])
        if any(other.id != task.id and other.module_id in ancestor_ids for other in existing):
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_TASK_DUPLICATED,
                                  value=('所选模块已由上级任务组覆盖',),
                                  )
        for other in existing:
            if other.id == task.id or other.id in covered_ids:
                continue
            if cls._identity(other) == cls._identity(row):
                raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_TASK_DUPLICATED, value=('任务组配置已存在',))
        for field, value in cls._values(row, update_user_id).items():
            setattr(task, field, value)
        try:
            task.save()
            task.timing_strategies.set(row['timing_ids'])
            if covered_ids:
                Tasks.objects.filter(id__in=covered_ids).delete()
        except IntegrityError as error:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_TASK_DUPLICATED, error=str(error)) from error
        except ProtectedError as error:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID, error=str(error)) from error
        return {'item': cls.serialize(task), 'delete_count': len(covered_ids)}

    @classmethod
    @transaction.atomic
    def delete_row(cls, task_id: int) -> None:
        task = Tasks.objects.select_for_update().filter(
            id=task_id,
            execution_scope=AutomationExecutionScopeEnum.MODULE.value,
        ).first()
        if task is None:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID)
        try:
            Tasks.objects.filter(id=task.id).delete()
        except ProtectedError as error:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID, error=str(error)) from error

    @classmethod
    @transaction.atomic
    def replace(cls, project_product_id: int, rows, update_user_id: int | None = None) -> dict:
        product = cls._product(project_product_id, lock=True)
        if not isinstance(rows, list):
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID)
        normalized = cls._exclude_submitted_descendants([
            cls._normalize(product, row) for row in rows
        ])
        identities = [cls._identity(row) for row in normalized]
        if len(identities) != len(set(identities)):
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_TASK_DUPLICATED, value=('当前提交中存在重复配置',))

        existing = list(Tasks.objects.select_for_update().filter(
            project_product_id=product.id,
            execution_scope=AutomationExecutionScopeEnum.MODULE.value,
        ).select_related('module', 'module__parent', 'module__parent__parent'))
        existing_by_identity = {cls._identity(task): task for task in existing}
        existing_by_id = {task.id: task for task in existing}
        submitted_ids = set()
        create_count = update_count = 0
        try:
            for row in normalized:
                task = existing_by_identity.get(cls._identity(row))
                if task is None and row['task_id'] not in (None, ''):
                    try:
                        task = existing_by_id.get(int(row['task_id']))
                    except (TypeError, ValueError):
                        task = None
                    if task is None:
                        raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID)
                values = cls._values(row, update_user_id)
                if task is None:
                    task = Tasks.objects.create(**values)
                    create_count += 1
                else:
                    for field, value in values.items():
                        setattr(task, field, value)
                    task.save()
                    update_count += 1
                task.timing_strategies.set(row['timing_ids'])
                submitted_ids.add(task.id)
        except IntegrityError as error:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_TASK_DUPLICATED,
                                  value=('项目产品、模块、环境、用例类型、执行场景和执行范围必须唯一',),
                                  error=str(error),
                                  ) from error

        removed = Tasks.objects.filter(
            project_product_id=product.id,
            execution_scope=AutomationExecutionScopeEnum.MODULE.value,
        ).exclude(id__in=submitted_ids)
        delete_count = removed.count()
        try:
            removed.delete()
        except ProtectedError as error:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID, error=str(error)) from error
        return {
            'create_count': create_count,
            'update_count': update_count,
            'delete_count': delete_count,
            'disabled_count': 0,
        }

    @classmethod
    def matrix(cls, project_product_id: int) -> dict:
        product = cls._product(project_product_id)
        modules = list(ProductModuleService.with_full_paths(
            ProductModule.objects.filter(project_product_id=product.id),
        ))
        tasks = Tasks.objects.filter(
            project_product_id=product.id,
            execution_scope=AutomationExecutionScopeEnum.MODULE.value,
        ).select_related(
            'module', 'module__parent', 'module__parent__parent', 'notice_group', 'case_people',
            'update_user',
        ).prefetch_related('timing_strategies')
        return {
            'project_product_id': product.id,
            'modules': [{
                'id': module.id,
                'name': module.name,
                'full_path': module.get_full_path(),
                'parent_id': module.parent_id,
                'level': module.level,
            } for module in modules],
            'items': [cls.serialize(task) for task in tasks],
        }

    @staticmethod
    def serialize(task: Tasks) -> dict:
        identity = ModuleFullTaskConfigService._identity(task)
        return {
            'task_id': task.id,
            'name': task.name,
            'module_id': task.module_id,
            'module_full_path': task.module.get_full_path(),
            'module': {
                'id': task.module_id,
                'name': task.module.name,
                'full_path': task.module.get_full_path(),
                'parent_id': task.module.parent_id,
                'level': task.module.level,
            },
            'test_envs': list(identity[2]),
            'case_types': list(identity[3]),
            'execution_scenes': list(identity[4]),
            'execution_scope': task.execution_scope,
            'timing_strategies': [item.id for item in task.timing_strategies.all()],
            'api_concurrency_limit': task.api_concurrency_limit,
            'case_people': task.case_people_id,
            'is_notice': task.is_notice,
            'notice_group': task.notice_group_id,
            'fail_notice': task.fail_notice,
            'status': task.status,
            'update_user_name': (
                (task.update_user.name or task.update_user.username)
                if task.update_user_id
                else None
            ),
            'update_time': task.update_time.strftime('%Y-%m-%d %H:%M:%S'),
        }
