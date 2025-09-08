# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-09-08 16:18
# @Author : 毛鹏
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


def pytest_test_case(**kwargs):
    import pytest
    allure_results_dir = os.path.join(kwargs.get('allure'), f'allure-results-{uuid.uuid4()}')
    kwargs.get('log').debug(f'生成的用例存储目录：{allure_results_dir}')
    os.makedirs(allure_results_dir, exist_ok=True)
    os.environ[kwargs.get('test_env_name')] = f'{kwargs.get("test_env")}'

    pytest_args = [
        os.path.abspath(kwargs.get('file_path')),
        '--alluredir',
        allure_results_dir
    ]

    if kwargs.get('quiet'): pytest_args.append('-q')
    if kwargs.get('verbose'): pytest_args.append('-v')
    if kwargs.get('show_output'): pytest_args.append('-s')

    kwargs.get('log').debug('启动 pytest 参数：{}'.format(pytest_args))
    exit_code = pytest.main(pytest_args)

    kwargs.get('log').debug(f"文件<{kwargs.get('file_path')}>执行输出:{exit_code}")
    report_data = read_allure_json_results(allure_results_dir)
    delete_allure_results(allure_results_dir)
    return report_data


def read_allure_json_results(results_dir):
    report_data = []
    for json_file in Path(results_dir).glob('*-result.json'):
        with open(json_file, 'r', encoding='utf-8') as f:
            res_dict = json.load(f)
            for i in res_dict.get('attachments', []):
                try:
                    with open(os.path.join(results_dir, i.get('source')), 'r', encoding='utf-8') as text:
                        content = text.read()
                        i['source'] = content
                except FileNotFoundError:
                    i['source'] = '用例执行失败，这一项没有生成内容，所以没有结果'
            report_data.append(res_dict)
    return report_data


def delete_allure_results(results_dir):
    if os.path.exists(results_dir):
        shutil.rmtree(results_dir)
