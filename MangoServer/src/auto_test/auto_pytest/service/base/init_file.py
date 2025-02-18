# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 17:05
# @Author : 毛鹏
import os


def find_test_files(directory):
    test_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.startswith('test') or file.endswith('test'):
                test_files.append(os.path.join(root, file))
    return test_files


if __name__ == '__main__':
    target_directory = r'D:\GitCode\PytestAutoTest\auto_test\api_ztool\test_case'
    result = find_test_files(target_directory)
    for file in result:
        print(file)
