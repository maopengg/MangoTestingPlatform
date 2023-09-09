# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: txt文件处理类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏

class FileOperation:

    def __init__(self):
        self.w = open("CacheToken.txt", 'w', encoding='utf-8')
        self.r = open("CacheToken.txt", 'r')
        self.a = open("CacheToken.txt", 'a')

    # 读
    def file_reading(self):
        rr = self.r.read()
        return rr

    # 写
    def file_write(self, text):
        self.w.write(text + "\n")
        self.w.close()

    # 追加
    def files_were_added(self, text):
        self.a.write(text + "\n")
        self.a.close()


if __name__ == '__main__':
    r = FileOperation()
