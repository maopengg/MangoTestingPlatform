# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 17:05
# @Author : 毛鹏
import os

from src.tools import project_dir


def list_files(directory, exclude_file=None, prefix=None, suffix=None, is_upload=False):
    file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if is_upload:
                file_list.append(file)
            if exclude_file and file != exclude_file:
                file_list.append(file)
            if prefix or suffix:
                if file.startswith(prefix) or file.endswith(suffix):
                    file_list.append(file)

    return file_list


def generate_json(directory):
    result = {}
    for subdir in os.listdir(directory):
        subdir_path = os.path.join(directory, subdir)
        if os.path.isdir(subdir_path):
            if subdir == "act":
                result["act"] = list_files(subdir_path, exclude_file="__init__.py")
            elif subdir == "test_case":
                result["test_case"] = list_files(subdir_path, prefix="test", suffix="test")
            elif subdir == "upload":
                result["upload"] = list_files(subdir_path, is_upload=True)
    return result


# 示例用法

def find_test_files(directory):
    subdirectories = []
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path) and not '.' in item:
            subdirectories.append({item: generate_json(item_path)})
    return subdirectories


def save(dir='src/auto_test/auto_pytest/mango_pytest/auto_test'):
    from src.auto_test.auto_pytest.views.pytest_project import PytestProjectCRUD
    from src.auto_test.auto_pytest.views.pytest_case import PytestCaseCRUD
    from src.auto_test.auto_pytest.views.pytest_act import PytestActCRUD
    for project in find_test_files(os.path.join(project_dir.root_path(), dir)):
        for project_dir_name, project_dirs in project.items():
            PytestProjectCRUD.inside_post({'name': project_dir_name})
            for i in project_dirs.get('act', []):
                PytestActCRUD.inside_post({'name': i, 'file_name': i})
            for i in project_dirs.get('test_case', []):
                PytestCaseCRUD.inside_post({'name': i, 'file_name': i})
            for i in project_dirs.get('upload', []):
                print(i)


if __name__ == '__main__':
    save()
