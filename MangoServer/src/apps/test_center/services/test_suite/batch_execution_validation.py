from collections.abc import Iterable

from src.apps.test_center.enums.environment import EnvironmentEnum


class BatchExecutionValidationService:
    """API、UI、Pytest 批量执行共用的基础校验。"""

    @staticmethod
    def normalize_case_ids(case_ids, *, error_class, error_message) -> list[int]:
        if not isinstance(case_ids, (list, tuple)) or any(
                isinstance(case_id, (bool, float)) for case_id in case_ids
        ):
            raise error_class(error_message)
        try:
            normalized = [int(case_id) for case_id in case_ids]
        except (TypeError, ValueError) as error:
            raise error_class(error_message, error=str(error)) from error
        if not normalized or len(set(normalized)) != len(normalized):
            raise error_class(error_message)
        return normalized

    @staticmethod
    def normalize_test_environment(value, *, error_class, error_message) -> int:
        if isinstance(value, (bool, float)) or value is None or value == '':
            raise error_class(error_message)
        if isinstance(value, str):
            value = value.strip()
            if not value.isdigit():
                raise error_class(error_message)
        try:
            normalized = int(value)
        except (TypeError, ValueError) as error:
            raise error_class(error_message, error=str(error)) from error
        if normalized not in EnvironmentEnum.get_key_list():
            raise error_class(error_message)
        return normalized

    @staticmethod
    def ensure_all_cases_found(
            cases: dict[int, object],
            case_ids: list[int],
            *,
            error_class,
            error_message,
    ) -> None:
        if len(cases) != len(case_ids):
            raise error_class(error_message)

    @staticmethod
    def ensure_same_project(
            projects: Iterable[tuple[int, str]],
            *,
            error_class,
            error_message,
    ) -> tuple[int, str]:
        project_map = dict(projects)
        if len(project_map) != 1:
            project_names = '、'.join(sorted(project_map.values()))
            raise error_class(error_message, value=(project_names,))
        return next(iter(project_map.items()))
