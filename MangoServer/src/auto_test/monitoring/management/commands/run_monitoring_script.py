# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: Django management command 用于执行监控脚本
# @Time   : 2025-01-09
# @Author : 毛鹏
import sys
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    执行监控脚本的 Django management command
    
    用法:
        python manage.py run_monitoring_script <script_path> <task_id>
    
    这个 command 会在 Django 环境中执行脚本，脚本不需要自己初始化 Django
    """
    help = '执行监控脚本（在 Django 环境中）'

    def add_arguments(self, parser):
        parser.add_argument('script_path', type=str, help='脚本文件路径')
        parser.add_argument('task_id', type=int, help='任务ID')

    def handle(self, *args, **options):
        script_path = options['script_path']
        task_id = options['task_id']
        
        # 修改 sys.argv，让脚本可以通过 sys.argv[1] 获取 task_id
        # 脚本原本期望: python script.py <task_id>
        # 所以 sys.argv 应该是: ['script.py', '<task_id>']
        original_argv = sys.argv[:]
        sys.argv = [script_path, str(task_id)]
        
        try:
            # 在 Django 环境中执行脚本
            with open(script_path, 'r', encoding='utf-8') as f:
                script_code = f.read()
            
            # 创建脚本的命名空间
            script_globals = {
                '__file__': script_path,
                '__name__': '__main__',
            }
            
            # 执行脚本代码（在 Django 环境中，所以所有 Django 相关的导入都能正常工作）
            exec(compile(script_code, script_path, 'exec'), script_globals)
        finally:
            # 恢复原始 sys.argv
            sys.argv = original_argv

