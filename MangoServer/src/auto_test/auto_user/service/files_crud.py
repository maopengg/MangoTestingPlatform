# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-01 11:55
# @Author : 毛鹏
import os
import shutil

from src.auto_test.auto_system.models import Project
from src.tools.other.path import FilePath


class FilesCRUD:

    def __init__(self, project_id=None):
        self.project_id = project_id
        #
        self.path = FilePath.auto_ensure_path_sep(fr'/files')
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        self.upload_folder = rf'/{project_id}/upload_folder'
        self.screenshot_folder = rf'/{project_id}/screenshot_folder'
        #
        self.project_path = f'{self.path}/{self.project_id}'
        self.project_upload_folder = f'{self.path}{self.upload_folder}'
        self.project_screenshot_folder = f'{self.path}{self.screenshot_folder}'

    def get_project_all_list(self):
        """
        返回文件夹list
        @return:
        """

        file_list = []
        for i in Project.objects.all():
            for root, dirs, files in os.walk(f'{self.path}{i.upload_folder}'):
                for file in files:
                    file_list.append({'project_id': i.id, 'project_name': i.name, 'file_name': file})
        return file_list

    def initialization(self):
        """
        启动项目初始化
        @return:
        """

        for i in Project.objects.all():
            self.upload_folder = rf'/{i.id}/upload_folder'
            self.screenshot_folder = rf'/{i.id}/screenshot_folder'
            #
            self.project_path = f'{self.path}/{i.id}'
            self.project_upload_folder = f'{self.path}{self.upload_folder}'
            self.project_screenshot_folder = f'{self.path}{self.screenshot_folder}'
            if not os.path.isdir(self.project_path):
                os.makedirs(self.project_path)
            if not os.path.isdir(self.project_upload_folder):
                project_obj = Project.objects.get(id=i.id)
                os.makedirs(self.project_upload_folder)
                project_obj.upload_folder = self.upload_folder
                project_obj.save()
            if not os.path.isdir(self.project_screenshot_folder):
                project_obj = Project.objects.get(id=i.id)
                os.makedirs(self.project_screenshot_folder)
                project_obj.screenshot_folder = self.screenshot_folder
                project_obj.save()

    def add_project(self):
        """
        添加一个项目
        @return:
        """
        os.makedirs(self.project_path)
        os.makedirs(self.project_upload_folder)
        os.makedirs(self.project_screenshot_folder)
        project_obj = Project.objects.get(id=self.project_id)
        project_obj.upload_folder = self.upload_folder
        project_obj.screenshot_folder = self.screenshot_folder
        project_obj.save()

    def delete_project(self):
        """
        删除整个项目
        @return:
        """
        shutil.rmtree(self.project_path)

    def upload_files(self, file_obj):
        """
        上传一个文件
        @param file_obj:
        @return:
        """
        file_path = os.path.join(self.project_upload_folder, file_obj.name)
        with open(file_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

    def delete_file(self, file_name):
        """
        删除一个文件
        @param file_name:
        @return:
        """
        file_path = os.path.join(self.project_upload_folder, file_name)
        os.remove(file_path)


if __name__ == '__main__':
    pass
