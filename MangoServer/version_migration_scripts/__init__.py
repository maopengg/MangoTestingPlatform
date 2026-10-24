# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据清洗
# @Time   : 2025-01-24 11:36
# @Author : 毛鹏

def data_cleanup(v, **kwargs):
    data_script_7_1_0 = 'python version_migration_scripts/v_7_1_0_2026_07_22_api_version_data.py'
    if v == '4.7':
        from version_migration_scripts.v_4_7_2025_01_24 import main_4_7
        return main_4_7()
    elif v == '5.5':
        from version_migration_scripts.v_5_2_2025_04_13 import main_5_5
        return main_5_5()
    elif v == '5.8':
        from version_migration_scripts.v_5_8_2025_09_24 import main_5_8
        return main_5_8()
    elif v == '6.0':
        from version_migration_scripts.v_5_9_2026_03_07_timezone import main_timezone
        return main_timezone()
    elif v == '6.3.1':
        from version_migration_scripts.v_6_3_1_2026_06_16_api_body import main_6_3_1
        return main_6_3_1()
    elif v == '7.0.3':
        from version_migration_scripts.v_7_0_3_2026_07_17_product_module import main_7_0_3
        return main_7_0_3()
    elif v == '7.1.0':
        env = kwargs.get('env') or kwargs.get('stage_env') or 'test'
        stage = kwargs.get('stage') if kwargs.get('stage') is not None else 'all'
        limit = kwargs.get('limit') if kwargs.get('limit') is not None else 100
        sleep = kwargs.get('sleep') if kwargs.get('sleep') is not None else 0.2
        days = kwargs.get('days') if kwargs.get('days') is not None else 10
        return {
            'message': '7.1.0 数据迁移不支持通过接口直接执行，请在后端项目目录手动执行下面命令。',
            'workdir': 'MangoServer',
            'status_command': (
                f'{data_script_7_1_0} '
                f'--env {env} --stage status'
            ),
            'execute_command': (
                f'{data_script_7_1_0} '
                f'--env {env} --stage {stage} --limit {limit} --sleep {sleep} --days {days} --execute'
            ),
            'dry_run_command': (
                f'{data_script_7_1_0} '
                f'--env {env} --stage {stage} --limit {limit} --sleep {sleep} --days {days}'
            ),
            'notes': [
                '默认 dry-run 不写库，确认输出无异常后再追加 --execute。',
                'stage=all 会执行 API Info/API Case 版本初始化、定时任务绑定、测试报告明细绑定、修订快照修复和报告摘要回填。',
                '如果报告结果体较大，可调整 --max-result-mb；默认超过 20MB 的结果会跳过摘要回填。',
            ],
        }
    else:
        raise ValueError(f'不支持的数据清洗版本：{v}')
