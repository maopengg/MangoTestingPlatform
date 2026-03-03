# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2026-03-03 10:55
# @Author : 毛鹏
import json

file_path = r'D:\code\MangoTestingPlatform\MangoActuator\tests\test.txt'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # 将文件内容解析为JSON
        json_data = json.loads(content)
        print(json_data)
        print(type(json_data))  # 应该是 dict 或 list
except FileNotFoundError:
    print(f"文件不存在: {file_path}")
except json.JSONDecodeError as e:
    print(f"JSON解析错误: {e}")