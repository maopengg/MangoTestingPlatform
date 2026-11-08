from django.core.management.base import BaseCommand

from src.apps.monitoring.services.log_path import MonitoringLogPathService


class Command(BaseCommand):
    help = '迁移后补齐监控任务的空日志路径；默认只预览，不启动脚本或修改运行状态'

    def add_arguments(self, parser):
        parser.add_argument('--task-ids', nargs='+', type=int, help='只处理指定任务；省略则检查全部缺失路径')
        parser.add_argument('--apply', action='store_true', help='确认写入缺失的相对日志路径')

    def handle(self, *args, **options):
        result = MonitoringLogPathService.repair_missing(options['task_ids'], apply=options['apply'])
        if options['apply']:
            self.stdout.write(f"已补齐 {result['repaired']} 个监控任务日志路径；已有路径、状态和执行时间未修改。")
        else:
            self.stdout.write(f"发现 {result['missing']} 个监控任务缺少日志路径；仅预览，确认后添加 --apply 写入。")
