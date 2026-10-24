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
        self._runtime_path = self.init_runtime_path()
        self.init_folder()
        self.init_web_static_cache_folder()

    @staticmethod
    def init_project_path():
        if getattr(sys, 'frozen', False):
            executable = Path(sys.executable).resolve()
            if sys.platform == 'darwin' and '.app/Contents/MacOS' in str(executable):
                return str(Path.home() / 'Library' / 'Application Support' / 'MangoActuator')
            return os.path.dirname(sys.executable)
        return str(Path(__file__).resolve().parent.parent.parent)

    def init_runtime_path(self):
        runtime_path = os.getenv('MANGO_ACTUATOR_RUNTIME_DIR')
        if runtime_path:
            path = Path(runtime_path).expanduser()
            if path.is_absolute():
                return str(path)
            return str(Path(self._root_path) / path)
        return os.path.join(self._root_path, 'runtime')

    def init_folder(self):
        os.makedirs(self.runtime_path(), exist_ok=True)
        for i in self.folder_list:
            os.makedirs(os.path.join(self.runtime_path(), i), exist_ok=True)

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

    def runtime_path(self):
        return self._runtime_path

    def cache_file(self):
        return os.path.join(self.cache(), 'cache.db')

    def cache(self):
        return os.path.join(self.runtime_path(), 'cache')

    def web_static_cache(self):
        return os.path.join(self.cache(), 'web_static_cache')

    def init_web_static_cache_folder(self):
        os.makedirs(self.web_static_cache(), exist_ok=True)

    def logs(self, folder_name='logs'):
        return self._runtime_join(folder_name)

    def allure(self, folder_name='allure'):
        return self._runtime_join(folder_name)

    def screenshot(self, folder_name='screenshot'):
        return self._runtime_join(folder_name)

    def upload(self, folder_name='upload'):
        return self._runtime_join(folder_name)

    def download(self, folder_name='download'):
        return self._runtime_join(folder_name)

    def videos(self, folder_name='videos'):
        return self._runtime_join(folder_name)

    def _runtime_join(self, folder_name):
        path = Path(str(folder_name or ''))
        if path.is_absolute():
            return str(path)
        return str(Path(self.runtime_path()) / path)


project_dir = ProjectDir()
if __name__ == '__main__':
    print(project_dir.root_path())
    print(project_dir.runtime_path())
    print(project_dir.logs())
    print(project_dir.cache())
    print(project_dir.screenshot())
    print(project_dir.upload())
    print(project_dir.videos())
    print(project_dir.cache_file())
    print(project_dir.cache())
