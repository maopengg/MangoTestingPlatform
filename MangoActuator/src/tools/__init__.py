# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-05 20:39
# @Author : 毛鹏

import os

import sys
from pathlib import Path


class ProjectDir:

    def __init__(self):
        self.folder_list = ['logs', 'cache', 'screenshot', 'upload', 'videos', 'download', 'allure']
        self._root_path = self.init_project_path()
        self.init_folder()

    @staticmethod
    def init_project_path():
        if sys.platform.startswith('linux'):
            from pathlib import Path
            return str(Path(__file__).resolve().parent.parent.parent)
        else:
            current_directory = os.path.abspath(__file__)
            project_root_directory = os.path.dirname(os.path.dirname(os.path.dirname(current_directory)))
            current_dir2 = os.path.dirname(sys.executable)
            if 'python.exe' not in sys.executable:
                project_root_directory = current_dir2
            return project_root_directory

    def init_folder(self):
        for i in self.folder_list:
            subdirectory = os.path.join(self._root_path, i)
            if not os.path.exists(subdirectory):
                os.makedirs(subdirectory)

    def resource_path(self, relative_path):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS  # type: ignore
        else:
            base_path = self.root_path()
        return os.path.join(base_path, relative_path)

    def root_path(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return self._root_path

    def cache_file(self):
        return os.path.join(self.cache(), 'cache.db')

    def cache(self):
        return os.path.join(self.root_path(), 'cache')

    def logs(self, folder_name='logs'):
        return os.path.join(self.root_path(), folder_name)

    def allure(self, folder_name='allure'):
        return os.path.join(self.root_path(), folder_name)

    def screenshot(self, folder_name='screenshot'):
        return os.path.join(self.root_path(), folder_name)

    def upload(self, folder_name='upload'):
        return os.path.join(self.root_path(), folder_name)

    def download(self, folder_name='download'):
        return os.path.join(self.root_path(), folder_name)

    def videos(self, folder_name='videos'):
        return os.path.join(self.root_path(), folder_name)


project_dir = ProjectDir()
if __name__ == '__main__':
    print(project_dir.root_path())
    print(project_dir.logs())
    print(project_dir.cache())
    print(project_dir.screenshot())
    print(project_dir.upload())
    print(project_dir.videos())
    print(project_dir.cache_file())
    print(project_dir.cache())
