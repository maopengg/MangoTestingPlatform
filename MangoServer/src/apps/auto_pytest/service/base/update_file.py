# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-02-18 17:05
# @Author : 毛鹏
import os

from src.apps.auto_pytest.service.base import git_obj
from src.common.exceptions import PytestError, ERROR_MSG_0061, ERROR_MSG_0062, ERROR_MSG_0063
from src.common.models.pytest_model import FileModel, UpdateFileModel


class UpdateFile:

    def __init__(self, test_dirs: list):
        self.test_dirs = test_dirs
        self.warehouse_name = 'mango_pytest'
        self.repo = git_obj()

    def list_files(self, directory, components=False, test_case=False, tools=False, is_upload=False,
                   include_feature=False) -> list[FileModel]:
        file_list = []
        for root, dirs, files in os.walk(directory):
            if '__pycache__' not in dirs and '__pycache__' not in root:
                for file in files:
                    abs_path = os.path.join(root, file)
                    parent_dir = os.path.basename(os.path.normpath(root))
                    if file not in '.pyc':
                        if is_upload or tools:
                            file_list.append(FileModel(
                                name=str(os.path.join(parent_dir, file)),
                                path=self.__path(abs_path),
                                time=self.repo.get_file_last_commit_time(abs_path)
                            ))
                        if components and file != "__init__.py":
                            file_list.append(FileModel(
                                name=str(os.path.join(parent_dir, file)),
                                path=self.__path(abs_path),
                                time=self.repo.get_file_last_commit_time(abs_path)
                            ))
                        if test_case and (file.startswith('test') or file.endswith('test')):
                            file_list.append(FileModel(
                                name=str(os.path.join(parent_dir, file)),
                                path=self.__path(abs_path),
                                time=self.repo.get_file_last_commit_time(abs_path)
                            ))
                        if include_feature and file.endswith('.feature'):
                            file_list.append(FileModel(
                                name=str(os.path.join(parent_dir, file)),
                                path=self.__path(abs_path),
                                time=self.repo.get_file_last_commit_time(abs_path)
                            ))

        return file_list

    def generate_json(self, directory):
        if not self.test_dirs:
            raise PytestError(*ERROR_MSG_0061)

        all_files = []
        for test_dir in self.test_dirs:
            subdir_path = os.path.join(directory, test_dir)
            if not os.path.exists(subdir_path) or not os.path.isdir(subdir_path):
                raise PytestError(*ERROR_MSG_0062, value=(test_dir,))
            files = self.list_files(subdir_path, components=True, include_feature=True)
            all_files.extend(files)
        return all_files

    def find_test_files(self, project_name: str, auto_test_dir='auto_tests') -> list[UpdateFileModel]:
        directory = os.path.join(self.repo.local_dir, auto_test_dir)
        subdirectories = []
        item_path = os.path.join(directory, project_name)
        if not os.path.exists(item_path) or not os.path.isdir(item_path):
            raise PytestError(*ERROR_MSG_0063, value=(project_name,))
        module_path = os.path.join(item_path, 'test_case')
        if os.path.exists(module_path):
            module_name = [d for d in os.listdir(module_path) if
                           os.path.isdir(os.path.join(module_path, d)) and '__pycache__' not in d]
        else:
            module_name = []
        auto_test = self.generate_json(item_path)
        subdirectories.append(UpdateFileModel(
            project_name=project_name,
            auto_test=auto_test if auto_test else [],
            init_file_path=os.path.join(self.warehouse_name, auto_test_dir, project_name, '__init__.py'),
            module_name=module_name
        ))
        return subdirectories

    def __path(self, abs_path):
        return os.path.join(self.warehouse_name, os.path.relpath(str(abs_path), self.repo.local_dir)).replace('\\', '/')
