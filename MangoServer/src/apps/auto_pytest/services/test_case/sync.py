import ast
import hashlib
import posixpath

from django.utils import timezone

from src.apps.auto_pytest.enums import (
    FileStatusEnum,
    PytestAssetStatusEnum,
    PytestCasePublicationStatusEnum,
    PytestSourceStatusEnum,
)
from src.apps.auto_pytest.models import PytestCase, PytestProduct
from src.apps.auto_pytest.services.base.update_file import UpdateFile
from src.apps.auto_pytest.services.git_management.repository_lock import GitRepositoryLockService
from src.apps.auto_pytest.services.git_management.repository_service import RepositoryGitService


class PytestCaseSyncService:
    @staticmethod
    def _string_constants(tree: ast.AST) -> dict[str, str]:
        constants = {}
        for node in getattr(tree, "body", []):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = value.value
        return constants

    @classmethod
    def _feature_references(cls, content: str) -> list[str]:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []
        constants = cls._string_constants(tree)
        references = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function_name = None
            if isinstance(node.func, ast.Name):
                function_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                function_name = node.func.attr
            if function_name not in {"scenario", "scenarios"} or not node.args:
                continue
            argument = node.args[0]
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                reference = argument.value
            elif isinstance(argument, ast.Name):
                reference = constants.get(argument.id)
            else:
                reference = None
            if reference and reference.lower().endswith(".feature") and reference not in references:
                references.append(reference)
        return references

    @staticmethod
    def _infer_feature_path(python_path: str, feature_paths: list[str]) -> str | None:
        python_stem = posixpath.splitext(posixpath.basename(python_path))[0]
        candidate_stems = [python_stem]
        if python_stem.startswith("test_"):
            candidate_stems.append(python_stem.removeprefix("test_"))
        candidates = [
            path
            for path in feature_paths
            if posixpath.splitext(posixpath.basename(path))[0] in candidate_stems
        ]
        if not candidates:
            return None
        python_directory = posixpath.dirname(python_path)
        return max(
            candidates,
            key=lambda path: len(posixpath.commonpath([python_directory, posixpath.dirname(path)])),
        )

    @classmethod
    def _find_feature_path(cls, python_path: str, feature_paths: list[str], git_service) -> str | None:
        repository_python_path = git_service.repo_file_path(python_path)
        repository_feature_paths = {
            git_service.repo_file_path(path): path for path in feature_paths
        }
        content = git_service.remote_file_content(python_path)
        for reference in cls._feature_references(content):
            normalized_reference = reference.replace("\\", "/")
            candidates = [
                posixpath.normpath(
                    posixpath.join(posixpath.dirname(repository_python_path), normalized_reference)
                ),
                posixpath.normpath(normalized_reference.lstrip("/")),
            ]
            for candidate in candidates:
                if candidate in repository_feature_paths:
                    return repository_feature_paths[candidate]
        return cls._infer_feature_path(python_path, feature_paths)

    @classmethod
    def resolve_case_feature_path(
            cls,
            case: PytestCase,
            *,
            persist: bool = False,
    ) -> str | None:
        git_service = RepositoryGitService.for_product(case.project_product)
        feature_files = [
            git_service.display_file_path(path)
            for path in git_service.list_repository_files(
                root_dirs=[case.project_product.file_name],
                extensions=[".feature"],
            )
        ]
        feature_path = cls._find_feature_path(case.file_path, feature_files, git_service)
        if persist and feature_path and feature_path != case.feature_file_path:
            PytestCase.objects.filter(id=case.id).update(feature_file_path=feature_path)
            case.feature_file_path = feature_path
        return feature_path

    @classmethod
    def sync(cls, product_id: int, operator_id: int | None = None) -> dict:
        product = PytestProduct.objects.select_related("repository", "repository__credential").get(id=product_id)
        with GitRepositoryLockService.locked("scan_pytest_cases", product.repository_id):
            return cls._sync_locked(product, operator_id)

    @staticmethod
    def _sync_locked(product: PytestProduct, operator_id: int | None) -> dict:
        git_service = RepositoryGitService.for_product(product)
        ref_info = git_service.current_ref_info()
        existing_paths = set(
            PytestCase.objects.filter(project_product=product).values_list("file_path", flat=True)
        )
        active_paths: set[str] = set()
        created_count = 0
        updated_count = 0
        changed_count = 0
        restored_count = 0
        renamed_count = 0
        now = timezone.now()

        PytestCase.objects.filter(
            project_product=product,
            publication_status=PytestCasePublicationStatusEnum.PUBLISHED.value,
            asset_status=PytestAssetStatusEnum.DRAFT.value,
        ).update(asset_status=PytestAssetStatusEnum.PUBLISHED.value)

        feature_files = [
            git_service.display_file_path(path)
            for path in git_service.list_repository_files(
                root_dirs=[product.file_name],
                extensions=[".feature"],
            )
        ]
        projects = UpdateFile(product.test_dir, git_service).find_test_files(product.file_name)
        discovered_files = [
            file
            for project in projects
            for file in project.auto_test
            if file.path.endswith(".py")
        ]
        active_paths = {file.path for file in discovered_files}
        for file in discovered_files:
            content = git_service.remote_file_content(file.path)
            source_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            defaults = {
                "name": file.name,
                "file_name": file.name,
                "file_status": FileStatusEnum.UNBOUND.value,
                "source_status": PytestSourceStatusEnum.ACTIVE.value,
                "asset_status": PytestAssetStatusEnum.DRAFT.value,
                "file_update_time": file.time.replace(tzinfo=None),
                "feature_file_path": PytestCaseSyncService._find_feature_path(
                    file.path,
                    feature_files,
                    git_service,
                ),
                "source_hash": source_hash,
                "source_commit": ref_info.get("commit_hash"),
                "first_seen_commit": ref_info.get("commit_hash"),
                "last_seen_commit": ref_info.get("commit_hash"),
                "last_seen_time": now,
                "missing_since": None,
            }
            if operator_id is not None:
                defaults["update_user_id"] = operator_id
            pytest_case = PytestCase.objects.filter(
                project_product=product,
                file_path=file.path,
            ).first()
            created = False
            renamed = False
            if pytest_case is None:
                rename_candidates = list(
                    PytestCase.objects.filter(
                        project_product=product,
                        source_hash=source_hash,
                    )
                    .exclude(file_path__in=active_paths)
                    .order_by("id")[:2]
                )
                if len(rename_candidates) == 1:
                    pytest_case = rename_candidates[0]
                    pytest_case.previous_file_path = pytest_case.file_path
                    pytest_case.file_path = file.path
                    pytest_case.name = file.name
                    pytest_case.file_name = file.name
                    renamed = True
                else:
                    pytest_case, created = PytestCase.objects.get_or_create(
                        project_product=product,
                        file_path=file.path,
                        defaults=defaults,
                    )
            if created:
                created_count += 1
                continue

            was_missing = (
                    pytest_case.source_status == PytestSourceStatusEnum.MISSING.value
            )
            source_changed = bool(
                pytest_case.source_hash and pytest_case.source_hash != source_hash
            )
            pytest_case.file_update_time = defaults["file_update_time"]
            pytest_case.feature_file_path = defaults["feature_file_path"]
            pytest_case.file_status = (
                FileStatusEnum.ALREADY_BOUND.value
                if pytest_case.module_id
                else FileStatusEnum.UNBOUND.value
            )
            pytest_case.source_status = (
                PytestSourceStatusEnum.MODIFIED.value
                if source_changed
                else PytestSourceStatusEnum.ACTIVE.value
            )
            if (
                    pytest_case.publication_status == PytestCasePublicationStatusEnum.PUBLISHED.value
                    and pytest_case.asset_status == PytestAssetStatusEnum.DRAFT.value
            ):
                pytest_case.asset_status = PytestAssetStatusEnum.PUBLISHED.value
            pytest_case.source_hash = defaults["source_hash"]
            pytest_case.source_commit = defaults["source_commit"]
            pytest_case.first_seen_commit = (
                    pytest_case.first_seen_commit or defaults["first_seen_commit"]
            )
            pytest_case.last_seen_commit = defaults["last_seen_commit"]
            pytest_case.last_seen_time = now
            pytest_case.missing_since = None
            update_fields = [
                "file_update_time",
                "feature_file_path",
                "file_status",
                "source_status",
                "asset_status",
                "source_hash",
                "source_commit",
                "first_seen_commit",
                "last_seen_commit",
                "last_seen_time",
                "missing_since",
                "update_time",
            ]
            if renamed:
                update_fields.extend(["file_path", "previous_file_path", "name", "file_name"])
                renamed_count += 1
            if operator_id is not None:
                pytest_case.update_user_id = operator_id
                update_fields.append("update_user")
            pytest_case.save(update_fields=update_fields)
            updated_count += 1
            changed_count += int(source_changed)
            restored_count += int(was_missing)

        deleted_paths = existing_paths - active_paths
        deleted_queryset = PytestCase.objects.filter(
            project_product=product,
            file_path__in=deleted_paths,
        ).exclude(source_status=PytestSourceStatusEnum.MISSING.value)
        deleted_count = deleted_queryset.update(
            source_status=PytestSourceStatusEnum.MISSING.value,
            missing_since=now,
        )
        return {
            "project_id": product.id,
            "created_count": created_count,
            "updated_count": updated_count,
            "changed_count": changed_count,
            "restored_count": restored_count,
            "renamed_count": renamed_count,
            "deleted_mark_count": deleted_count,
        }
