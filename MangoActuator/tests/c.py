# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-25 11:52
# @Author : 毛鹏
import json

# 读取 JSON 文件
with open('ope_json.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# 打开 ele-ope.md 文件以追加内容
with open('ele-ope.md', 'a', encoding='utf-8') as md_file:
    for section in data:
        for key, operations in section.items():
            md_file.write(f"## {key}\n")
            for operation in operations:
                md_file.write(f"- **{operation['label']}** (`{operation['value']}`)\n")
                if operation.get('parameter'):
                    md_file.write("  - **参数**:\n")
                    for param, value in operation['parameter'].items():
                        md_file.write(f"    - `{param}`: {value}\n")
                md_file.write("\n")
