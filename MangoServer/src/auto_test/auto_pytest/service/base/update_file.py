# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 17:05
# @Author : 毛鹏
import os
from datetime import datetime

from git import Repo

from src.enums.pytest_enum import PytestFileTypeEnum
from src.models.pytest_model import FileModel, PytestAutoTestModel, UpdateFileModel
from src.tools import project_dir


class UpdateFile:

    def __init__(self, file_type: PytestFileTypeEnum):
        self.file_type: PytestFileTypeEnum = file_type
        self.dir = 'src/auto_test/auto_pytest/mango_pytest/auto_test'

        self.local_warehouse_path = os.path.join(project_dir.root_path(), 'src/auto_test/auto_pytest/mango_pytest')
        self.repo = Repo(self.local_warehouse_path)

    def get_git_update_time(self, file_path):
        commits = list(self.repo.iter_commits(paths=file_path, max_count=1))
        if commits:
            return datetime.fromtimestamp(commits[0].committed_date)
        else:
            return datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')

    def list_files(self, directory, act=False, test_case=False, tools=False, is_upload=False) -> list[FileModel]:
        file_list = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                path = os.path.normpath(os.path.join(root, file))
                parent_dir = os.path.basename(os.path.normpath(root))

                file_name_with_parent = f"{parent_dir}/{file}"
                time = self.get_git_update_time(path)
                if is_upload or tools:
                    file_list.append(FileModel(name=file_name_with_parent, path=path, time=time))
                if act and file != "__init__.py":
                    file_list.append(FileModel(name=file_name_with_parent, path=path, time=time))
                if test_case and (file.startswith('test') or file.endswith('test')):
                    file_list.append(FileModel(name=file_name_with_parent, path=path, time=time))

        return file_list

    def generate_json(self, directory) -> list[PytestAutoTestModel]:
        result = []
        for subdir in os.listdir(directory):
            subdir_path = os.path.join(directory, subdir)
            if os.path.isdir(subdir_path):
                auto_test_model = PytestAutoTestModel()
                if self.file_type == PytestFileTypeEnum.ACT:
                    auto_test_model.act = self.list_files(subdir_path, act=True)
                elif self.file_type == PytestFileTypeEnum.TEST_CASE:
                    auto_test_model.test_case = self.list_files(subdir_path, test_case=True)
                elif self.file_type == PytestFileTypeEnum.UPLOAD:
                    auto_test_model.upload = self.list_files(subdir_path, is_upload=True)
                else:
                    auto_test_model.tools = self.list_files(subdir_path, tools=True)
                result.append(auto_test_model)
        return result

    def find_test_files(self, is_project=False) -> list[UpdateFileModel]:
        directory = os.path.join(project_dir.root_path(), self.dir)
        subdirectories = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path) and not '.' in item:
                if is_project:
                    subdirectories.append(UpdateFileModel(
                        project_name=item,
                        file=self.generate_json(item_path),
                        init_file_path=os.path.normpath(os.path.join(item_path, '__init__.py'))
                    ))
                else:
                    subdirectories.append(UpdateFileModel(
                        project_name=item,
                        file=self.generate_json(item_path),
                        init_file_path=os.path.normpath(os.path.join(item_path, '__init__.py'))
                    ))
        return subdirectories


if __name__ == '__main__':
    for project in UpdateFile(PytestFileTypeEnum.TEST_CASE).find_test_files():
        print(project.project_name)
        print(project.file)
        print(project.init_file_path)
