import posixpath

from django.db.models import QuerySet

from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_pytest.services.git_management.repository_service import RepositoryGitService


class PytestCaseDirectoryTreeService:
    @staticmethod
    def _relative_path(case: PytestCase) -> str:
        git_service = RepositoryGitService.for_product(case.project_product)
        file_path = git_service.repo_file_path(case.file_path)
        repository_root = git_service.repo_file_path(case.project_product.file_name).rstrip("/")
        if repository_root == ".":
            return file_path
        prefix = f"{repository_root}/"
        return file_path[len(prefix):] if file_path.startswith(prefix) else posixpath.basename(file_path)

    @staticmethod
    def _new_node(
            *,
            key: str,
            title: str,
            node_type: str,
            path: str,
            breadcrumb: list[str],
            repository_id: int,
            pytest_project_id: int | None = None,
    ) -> dict:
        return {
            "key": key,
            "title": title,
            "type": node_type,
            "path": path,
            "breadcrumb": breadcrumb,
            "repository_id": repository_id,
            "pytest_project_id": pytest_project_id,
            "case_count": 0,
            "children": [],
            "_children": {},
        }

    @classmethod
    def build(cls, queryset: QuerySet) -> list[dict]:
        repositories: dict[int, dict] = {}
        cases = queryset.select_related("project_product", "project_product__repository").order_by(
            "project_product__repository__name",
            "project_product__name",
            "file_path",
        )
        for case in cases:
            project = case.project_product
            if project is None:
                continue
            git_service = RepositoryGitService.for_product(project)
            repository = project.repository
            repository_id = repository.id
            repository_key = repository_id
            repository_title = repository.name
            repository_node = repositories.setdefault(
                repository_key,
                cls._new_node(
                    key=f"repository:{repository_key}",
                    title=repository_title,
                    node_type="repository",
                    path="",
                    breadcrumb=[repository_title],
                    repository_id=repository_id,
                ),
            )
            repository_node["case_count"] += 1
            project_title = project.name or posixpath.basename(project.file_name)
            project_node = repository_node["_children"].setdefault(
                f"project:{project.id}",
                cls._new_node(
                    key=f"project:{project.id}",
                    title=project_title,
                    node_type="project",
                    path=project.file_name,
                    breadcrumb=[repository_title, project_title],
                    repository_id=repository_id,
                    pytest_project_id=project.id,
                ),
            )
            project_node["case_count"] += 1
            relative_path = cls._relative_path(case)
            parts = [part for part in relative_path.split("/") if part]
            current = project_node
            current_path = git_service.repo_file_path(project.file_name).rstrip("/")
            breadcrumb = list(project_node["breadcrumb"])
            for part in parts[:-1]:
                current_path = f"{current_path}/{part}"
                breadcrumb = [*breadcrumb, part]
                child = current["_children"].setdefault(
                    part,
                    cls._new_node(
                        key=f"directory:{project.id}:{current_path}",
                        title=part,
                        node_type="directory",
                        path=git_service.display_file_path(current_path),
                        breadcrumb=breadcrumb,
                        repository_id=repository_id,
                        pytest_project_id=project.id,
                    ),
                )
                child["case_count"] += 1
                current = child
            file_name = parts[-1] if parts else posixpath.basename(case.file_path)
            file_path = git_service.display_file_path(case.file_path)
            current["_children"].setdefault(
                file_name,
                {
                    "key": f"file:{case.id}",
                    "case_id": case.id,
                    "title": file_name,
                    "type": "file",
                    "path": file_path,
                    "breadcrumb": [*breadcrumb, file_name],
                    "repository_id": repository_id,
                    "repository_name": repository_title,
                    "pytest_project_id": project.id,
                    "pytest_project_name": project_title,
                    "case_count": 1,
                    "source_status": case.source_status,
                    "asset_status": case.asset_status,
                    "children": [],
                },
            )

        def finalize(node: dict) -> dict:
            children = [finalize(child) for child in node.pop("_children", {}).values()]
            node["children"] = sorted(
                children,
                key=lambda child: (child["type"] == "file", child["title"].lower()),
            )
            return node

        return [
            finalize(node)
            for node in sorted(repositories.values(), key=lambda item: item["title"].lower())
        ]
