from django.core.management.base import BaseCommand

from src.apps.system.services.system_initialization import SystemInitializationService


class Command(BaseCommand):
    help = '幂等初始化系统配置、时间任务、断言缓存、默认角色和默认用户'

    def handle(self, *args, **options):
        result = SystemInitializationService.initialize()
        self.stdout.write(self.style.SUCCESS(f'系统初始化完成：{result}'))
