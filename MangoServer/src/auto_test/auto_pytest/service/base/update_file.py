# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 17:05
# @Author : 毛鹏
import os
from datetime import datetime

from src.auto_test.auto_pytest.service.base import git_obj
from src.models.pytest_model import FileModel, UpdateFileModel


class UpdateFile:

    def __init__(self, file_type: str):
        self.file_type: str = file_type

        self.repo = git_obj()
        self.repo.clone()

    def get_git_update_time(self, file_path):
        commits = list(self.repo.iter_commits(paths=file_path, max_count=1))
        if commits:
            return datetime.fromtimestamp(commits[0].committed_date)
        else:
            return datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')

    def list_files(self, directory, components=False, test_case=False, tools=False, is_upload=False) -> list[FileModel]:
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
                                path=os.path.join('mango_pytest',
                                                  os.path.relpath(str(abs_path), self.repo.local_dir)),
                                time=self.get_git_update_time(abs_path)
                            ))
                        if components and file != "__init__.py":
                            file_list.append(FileModel(
                                name=str(os.path.join(parent_dir, file)),
                                path=os.path.join('mango_pytest',
                                                  os.path.relpath(str(abs_path), self.repo.local_dir)),
                                time=self.get_git_update_time(abs_path)
                            ))
                        if test_case and (file.startswith('test') or file.endswith('test')):
                            file_list.append(FileModel(
                                name=str(os.path.join(parent_dir, file)),
                                path=os.path.join('mango_pytest',
                                                  os.path.relpath(str(abs_path), self.repo.local_dir)),
                                time=self.get_git_update_time(abs_path)
                            ))

        return file_list

    def generate_json(self, directory):
        subdir_path = os.path.join(directory, self.file_type)
        if os.path.isdir(subdir_path) and os.path.exists(subdir_path):
            return self.list_files(subdir_path, components=True)

    def find_test_files(self, is_project=False, auto_test_dir='auto_test') -> list[UpdateFileModel]:
        directory = os.path.join(self.repo.local_dir, auto_test_dir)
        subdirectories = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path) and not '.' in item and '__pycache__' != item:
                module_path = os.path.join(item_path, 'test_case')
                if os.path.exists(module_path):
                    module_name = [d for d in os.listdir(module_path) if
                                   os.path.isdir(os.path.join(module_path, d)) and '__pycache__' not in d]
                else:
                    module_name = []
                auto_test = self.generate_json(item_path)
                if is_project:
                    subdirectories.append(UpdateFileModel(
                        project_name=item,
                        auto_test=auto_test if auto_test else [],
                        init_file_path=os.path.join('mango_pytest', auto_test_dir, item, '__init__.py'),
                        module_name=module_name
                    ))
                else:
                    subdirectories.append(UpdateFileModel(
                        project_name=item,
                        auto_test=auto_test if auto_test else [],
                        init_file_path=os.path.join('mango_pytest', auto_test_dir, item, '__init__.py'),
                        module_name=module_name

                    ))
        return subdirectories
