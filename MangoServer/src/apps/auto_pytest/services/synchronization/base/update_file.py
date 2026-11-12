# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-02-18 17:05
# @Author : 毛鹏
import os
from datetime import datetime

from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_TEST_DIRECTORY_REQUIRED,
    PYTEST_DIRECTORY_NOT_FOUND,
    PYTEST_PROJECT_NOT_FOUND,
)
from src.apps.auto_pytest.schemas.file import PytestFileSchema, PytestFileUpdateCommand


class UpdateFile:

    def __init__(self, test_dirs: list, git_service):
        self.test_dirs = test_dirs
        self.git_service = git_service

    def list_files(self, directory, components=False, test_case=False, tools=False, is_upload=False,
                   include_feature=False) -> list[PytestFileSchema]:
        file_list = []
        for file_path in self.git_service.list_repository_files(root_dirs=[directory], extensions=[".py", ".feature"]):
            if "__pycache__" in file_path:
                continue
            file = os.path.basename(file_path)
            parent_dir = os.path.basename(os.path.dirname(file_path))
            if file.endswith(".pyc"):
                continue
            if is_upload or tools:
                file_list.append(self.__file_model(parent_dir, file, file_path))
            if components and file != "__init__.py" and file.endswith(".py"):
                file_list.append(self.__file_model(parent_dir, file, file_path))
            if test_case and file.endswith(".py") and (file.startswith('test') or file.endswith('test.py')):
                file_list.append(self.__file_model(parent_dir, file, file_path))
            if include_feature and file.endswith('.feature'):
                file_list.append(self.__file_model(parent_dir, file, file_path))

        return file_list

    def generate_json(self, directory):
        if not self.test_dirs:
            raise AutoPytestError(PYTEST_TEST_DIRECTORY_REQUIRED)

        files_by_path = {}
        for test_dir in self.test_dirs:
            normalized_test_dir = str(test_dir).strip("/\\")
            subdir_path = directory if normalized_test_dir == "." else f"{directory}/{normalized_test_dir}"
            files = self.list_files(subdir_path, test_case=True, include_feature=True)
            if not files:
                raise AutoPytestError(PYTEST_DIRECTORY_NOT_FOUND, value=(test_dir,))
            for file in files:
                files_by_path.setdefault(file.path, file)
        return list(files_by_path.values())

    def find_test_files(self, project_path: str) -> list[PytestFileUpdateCommand]:
        directory = str(project_path or "").strip("/")
        subdirectories = []
        project_files = self.git_service.list_repository_files(root_dirs=[directory], extensions=[".py", ".feature"])
        if not project_files:
            raise AutoPytestError(PYTEST_PROJECT_NOT_FOUND, value=(project_path,))
        module_prefix = f"{directory}/test_case/"
        module_name = sorted({
            item[len(module_prefix):].split("/", 1)[0]
            for item in project_files
            if item.startswith(module_prefix) and "/" in item[len(module_prefix):]
        })
        auto_test = self.generate_json(directory)
        subdirectories.append(PytestFileUpdateCommand(
            project_name=os.path.basename(directory),
            auto_test=auto_test if auto_test else [],
            init_file_path=self.git_service.display_file_path(f"{directory}/__init__.py"),
            module_name=module_name
        ))
        return subdirectories

    def __file_model(self, parent_dir: str, file: str, file_path: str) -> PytestFileSchema:
        return PytestFileSchema(
            name=str(os.path.join(parent_dir, file)),
            path=self.git_service.display_file_path(file_path),
            time=datetime.now(),
        )
